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
        db: AsyncSession
    ) -> List[str]:
        """
        Get list of agent types available to a specific user based on their organization.
        
        Args:
            user: The user requesting agents
            db: Database session
            
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
                is_free_agent = True
                owner_domain = None
                
                if isinstance(agent_instance, BaseAgent):
                    # Check for IS_FREE_AGENT class attribute
                    is_free_agent = getattr(agent_instance.__class__, 'IS_FREE_AGENT', True)
                    owner_domain = getattr(agent_instance.__class__, 'OWNER_DOMAIN', None)
                
                # If it's a free agent, it's available to everyone
                if is_free_agent:
                    available_agents.append(agent_type)
                    continue
                
                # For proprietary agents, check if user's organization matches
                if owner_domain:
                    # Get user's tenant subdomain
                    tenant_query = select(Tenant.subdomain).where(Tenant.id == user.tenant_id)
                    tenant_result = await db.execute(tenant_query)
                    user_subdomain = tenant_result.scalar_one_or_none()
                    
                    if user_subdomain == owner_domain:
                        available_agents.append(agent_type)
                        logger.info(f"Proprietary agent {agent_type} is available to user from {owner_domain} org")
                    else:
                        logger.info(f"Proprietary agent {agent_type} (owned by {owner_domain}) not available to user from {user_subdomain}")
                else:
                    # If we can't determine ownership, treat as unavailable for safety
                    logger.warning(f"Cannot determine ownership for agent {agent_type}, treating as unavailable")
            
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
                is_free_agent = getattr(agent_instance.__class__, 'IS_FREE_AGENT', True)
                if is_free_agent:
                    free_agents.append(agent_type)
        return free_agents
    
    async def _get_free_agents_only(self) -> List[str]:
        """Get only free agents as a safe fallback."""
        free_agents = []
        for agent_type in self.get_available_agents():
            agent_instance = self.get_agent(agent_type)
            if agent_instance:
                is_free_agent = getattr(agent_instance.__class__, 'IS_FREE_AGENT', True)
                if is_free_agent:
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


# Create tenant-aware singleton instance
tenant_aware_agent_manager = TenantAwareAgentManager()

# Export for use
__all__ = ["tenant_aware_agent_manager", "TenantAwareAgentManager"]