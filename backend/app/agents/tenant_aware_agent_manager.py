"""
Tenant-Aware Agent Manager

This enhanced agent manager filters agents based on organization ownership.
Proprietary agents are only available to their owner organizations.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.agent_manager import AgentManager
from app.models.models import Agent as AgentModel, User, Tenant
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TenantAwareAgentManager(AgentManager):
    """
    Enhanced agent manager that respects organization ownership of agents.
    """
    
    async def get_available_agents_for_user(
        self,
        user: User,
        db: AsyncSession,
        include_telephony_only: bool = False
    ) -> List[str]:
        """
        Get list of agent types available to a specific user based on their organization.
        
        Args:
            user: The user requesting agents
            db: Database session
            include_telephony_only: Whether to include telephony-only agents (default: False)
            
        Returns:
            List of available agent type names
        """
        try:
            # Get all dynamically discovered agents
            all_agents = self.get_available_agents()
            available_agents = []
            
            for agent_type in all_agents:
                # Get the agent instance to check its properties
                agent_instance = self.get_agent(agent_type)
                if not agent_instance:
                    continue
                
                # Check if agent has ownership properties defined
                owner_domains = None
                is_telephony_only = False
                
                if isinstance(agent_instance, BaseAgent):
                    # Check if OWNER_DOMAINS is explicitly defined
                    if hasattr(agent_instance.__class__, 'OWNER_DOMAINS'):
                        owner_domains = agent_instance.__class__.OWNER_DOMAINS
                    # Check if agent is telephony-only
                    is_telephony_only = getattr(agent_instance.__class__, 'TELEPHONY_ONLY', False)
                
                # Skip telephony-only agents if not requested
                if is_telephony_only and not include_telephony_only:
                    logger.info(f"Excluding telephony-only agent {agent_type} from chat context")
                    continue
                
                # If OWNER_DOMAINS is not defined, treat as available to all domains
                if owner_domains is None:
                    logger.info(f"Agent {agent_type} has no OWNER_DOMAINS defined, making available to all domains")
                    available_agents.append(agent_type)
                    continue
                
                # If it's a free agent (empty list), it's available to everyone
                if owner_domains == []:
                    available_agents.append(agent_type)
                    continue
                
                # For proprietary agents, check if user's organization is in the allowed list
                if owner_domains:
                    # Get user's tenant subdomain
                    tenant_query = select(Tenant.subdomain).where(Tenant.id == user.tenant_id)
                    tenant_result = await db.execute(tenant_query)
                    user_subdomain = tenant_result.scalar_one_or_none()
                    
                    if user_subdomain in owner_domains:
                        available_agents.append(agent_type)
                        logger.info(f"Proprietary agent {agent_type} is available to user from {user_subdomain} org (allowed orgs: {owner_domains})")
                    else:
                        logger.info(f"Proprietary agent {agent_type} (allowed orgs: {owner_domains}) not available to user from {user_subdomain}")
            
            logger.info(f"User {user.email} from org {user_subdomain if 'user_subdomain' in locals() else 'unknown'} has access to agents: {available_agents}")
            return available_agents
            
        except Exception as e:
            logger.error(f"Error filtering agents for user: {e}")
            # On error, return only free agents as a safe fallback
            return self._get_free_agents_only_sync()
    
    def _get_free_agents_only_sync(self) -> List[str]:
        """Get only free agents as a safe fallback (sync version)."""
        free_agents = []
        for agent_type in self.get_available_agents():
            agent_instance = self.get_agent(agent_type)
            if agent_instance:
                # Check if OWNER_DOMAINS is explicitly defined and is empty list
                if hasattr(agent_instance.__class__, 'OWNER_DOMAINS'):
                    owner_domains = agent_instance.__class__.OWNER_DOMAINS
                    if owner_domains == []:
                        free_agents.append(agent_type)
        return free_agents
    
    async def _get_free_agents_only(self) -> List[str]:
        """Get only free agents as a safe fallback."""
        free_agents = []
        for agent_type in self.get_available_agents():
            agent_instance = self.get_agent(agent_type)
            if agent_instance:
                # Check if OWNER_DOMAINS is explicitly defined and is empty list
                if hasattr(agent_instance.__class__, 'OWNER_DOMAINS'):
                    owner_domains = agent_instance.__class__.OWNER_DOMAINS
                    if owner_domains == []:
                        free_agents.append(agent_type)
        return free_agents
    
    async def process_conversation_with_tenant_context(
        self,
        message: str,
        user: User,
        db: AsyncSession,
        thread_id: Optional[str] = None,
        owner_id: Optional[UUID] = None,
        response_callback: Optional[Any] = None
    ) -> Tuple[str, str]:
        """
        Process a conversation with tenant-aware agent filtering.
        
        Args:
            message: The user's message
            user: The user making the request
            db: Database session
            thread_id: Optional thread ID
            owner_id: Optional owner ID
            response_callback: Optional callback for streaming
            
        Returns:
            Tuple of (agent_type, response)
        """
        # Get available agents for this user
        available_agents = await self.get_available_agents_for_user(user, db)
        
        # Temporarily override the discovered agents with filtered list
        original_agents = self.discovered_agents.copy()
        try:
            # Filter discovered agents to only those available to the user
            self.discovered_agents = {
                agent_type: agent 
                for agent_type, agent in original_agents.items() 
                if agent_type in available_agents
            }
            
            # Process the conversation with filtered agents
            return await self.process_conversation(
                message=message,
                conversation_agents=[],  # Ignored
                agents_config={},       # Ignored
                mention=None,          # Ignored
                db=db,
                thread_id=thread_id,
                owner_id=owner_id,
                response_callback=response_callback
            )
        finally:
            # Restore original agents
            self.discovered_agents = original_agents
    
    async def get_available_agents_for_telephony(
        self,
        tenant_id: UUID,
        db: AsyncSession
    ) -> List[str]:
        """
        Get list of agent types available for telephony for a specific tenant.
        This includes telephony-only agents.
        
        Args:
            tenant_id: The tenant ID
            db: Database session
            
        Returns:
            List of available agent type names
        """
        # Create a temporary user object for tenant context
        from app.models.models import Tenant
        
        tenant_query = select(Tenant).where(Tenant.id == tenant_id)
        tenant_result = await db.execute(tenant_query)
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return []
        
        # Create a minimal user object for filtering
        class TelephonyUser:
            def __init__(self, tenant_id, subdomain):
                self.tenant_id = tenant_id
                self.email = f"telephony@{subdomain}"
                self.username = "telephony"
                self.role = "telephony"
        
        telephony_user = TelephonyUser(tenant_id, tenant.subdomain)
        
        # Get agents including telephony-only ones
        return await self.get_available_agents_for_user(
            user=telephony_user,
            db=db,
            include_telephony_only=True
        )


# Create tenant-aware singleton instance
tenant_aware_agent_manager = TenantAwareAgentManager()

# Export for use
__all__ = ["tenant_aware_agent_manager", "TenantAwareAgentManager"]