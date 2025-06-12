"""
Enhanced Agent Manager with Database Synchronization

This enhanced version of the agent manager automatically synchronizes
dynamically discovered agents with the database to ensure consistency.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.agent_manager import AgentManager
from app.models.models import Agent

logger = logging.getLogger(__name__)

class EnhancedAgentManager(AgentManager):
    """
    Enhanced Agent Manager that maintains database synchronization
    for dynamically discovered agents.
    """
    
    def __init__(self):
        super().__init__()
        self._db_synced = False
    
    async def ensure_agents_synced_to_db(self, db: AsyncSession) -> bool:
        """
        Ensure all dynamically discovered agents have corresponding database records.
        
        Args:
            db: Database session
            
        Returns:
            True if sync was successful, False otherwise
        """
        if self._db_synced:
            return True
            
        try:
            logger.info("🔄 Syncing discovered agents to database...")
            
            # Get all discovered agents
            discovered_agents = self.get_available_agents()
            agent_descriptions = self.get_agent_descriptions()
            
            # Get existing agents from database
            result = await db.execute(select(Agent.agent_type))
            existing_agent_types = {row[0] for row in result.fetchall()}
            
            # Create missing agents
            agents_created = 0
            for agent_type in discovered_agents:
                if agent_type not in existing_agent_types:
                    description = agent_descriptions.get(agent_type, f"{agent_type} agent")
                    
                    # Create new agent record
                    new_agent = Agent(
                        agent_type=agent_type,
                        name=agent_type.replace('_', ' ').title(),
                        description=description,
                        is_free_agent=True,  # All dynamically discovered agents are free
                        owner_tenant_id=None,  # Free agents have no owner
                        configuration_template={},
                        capabilities=[],
                        is_active=True
                    )
                    
                    db.add(new_agent)
                    agents_created += 1
                    logger.info(f"➕ Created agent record for: {agent_type}")
            
            if agents_created > 0:
                await db.commit()
                logger.info(f"✅ Successfully created {agents_created} new agent records")
            
            self._db_synced = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Error syncing agents to database: {e}")
            await db.rollback()
            return False
    
    async def get_or_create_agent_record(self, agent_type: str, db: AsyncSession) -> Optional[Agent]:
        """
        Get an existing agent record or create a new one for the given agent type.
        
        Args:
            agent_type: The type of agent to get/create
            db: Database session
            
        Returns:
            Agent record if successful, None otherwise
        """
        try:
            # Ensure agents are synced to database first
            await self.ensure_agents_synced_to_db(db)
            
            # Try to get existing agent record
            result = await db.execute(
                select(Agent).where(Agent.agent_type == agent_type)
            )
            agent_record = result.scalar_one_or_none()
            
            if not agent_record:
                # Check if this is a known dynamically discovered agent
                if agent_type in self.get_available_agents():
                    description = self.agent_descriptions.get(agent_type, f"{agent_type} agent")
                    
                    # Create new agent record
                    agent_record = Agent(
                        agent_type=agent_type,
                        name=agent_type.replace('_', ' ').title(),
                        description=description,
                        is_free_agent=True,
                        owner_tenant_id=None,
                        configuration_template={},
                        capabilities=[],
                        is_active=True
                    )
                    
                    db.add(agent_record)
                    await db.flush()  # Get the ID without committing
                    logger.info(f"🆕 Created new agent record for: {agent_type}")
                else:
                    logger.warning(f"⚠️  Agent type '{agent_type}' not found in discovered agents")
                    return None
            
            return agent_record
            
        except Exception as e:
            logger.error(f"❌ Error getting/creating agent record for {agent_type}: {e}")
            return None

# Create enhanced singleton instance
enhanced_agent_manager = EnhancedAgentManager()

# Export both for compatibility
__all__ = ["enhanced_agent_manager", "EnhancedAgentManager"]