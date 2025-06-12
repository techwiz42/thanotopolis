#!/usr/bin/env python3
"""
Agent Discovery System Fix

This script fixes the agent discovery system to work purely with dynamic discovery
while maintaining database consistency for the conversation_agents table.

Issues Fixed:
1. Creates missing Agent records in database for dynamically discovered agents
2. Updates ConversationAgent creation to use proper agent_id references
3. Ensures database synchronization with file-based agent discovery
4. Maintains backward compatibility with existing conversation_agents records
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the parent directory to Python path to import our modules
backend_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.database import AsyncSessionLocal, engine
from app.models.models import Agent, ConversationAgent, Base
from app.agents.agent_manager import agent_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def sync_agents_to_database():
    """
    Synchronize dynamically discovered agents to the database.
    This ensures all file-based agents have corresponding database records.
    """
    logger.info("🔄 Starting agent discovery synchronization...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all discovered agents from the agent manager
            discovered_agents = agent_manager.get_available_agents()
            agent_descriptions = agent_manager.get_agent_descriptions()
            
            logger.info(f"📋 Found {len(discovered_agents)} dynamically discovered agents: {discovered_agents}")
            
            # Get existing agents from database
            result = await db.execute(select(Agent.agent_type))
            existing_agent_types = {row[0] for row in result.fetchall()}
            
            logger.info(f"📋 Found {len(existing_agent_types)} existing agents in database: {existing_agent_types}")
            
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
            else:
                logger.info("✅ All discovered agents already exist in database")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error synchronizing agents: {e}")
            await db.rollback()
            return False

async def fix_conversation_agents():
    """
    Fix existing ConversationAgent records that have agent_id=None
    by linking them to the proper Agent records.
    """
    logger.info("🔧 Fixing existing ConversationAgent records...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Find ConversationAgent records with agent_id=None
            result = await db.execute(
                select(ConversationAgent)
                .where(ConversationAgent.agent_id.is_(None))
            )
            broken_records = result.scalars().all()
            
            if not broken_records:
                logger.info("✅ No broken ConversationAgent records found")
                return True
            
            logger.info(f"🔍 Found {len(broken_records)} ConversationAgent records with agent_id=None")
            
            # Get all agents from database for lookup
            agent_result = await db.execute(select(Agent))
            agents_by_type = {agent.agent_type: agent.id for agent in agent_result.scalars().all()}
            
            fixed_count = 0
            for conv_agent in broken_records:
                if conv_agent.agent_type in agents_by_type:
                    conv_agent.agent_id = agents_by_type[conv_agent.agent_type]
                    fixed_count += 1
                    logger.info(f"🔗 Linked ConversationAgent {conv_agent.id} to Agent {conv_agent.agent_type}")
                else:
                    logger.warning(f"⚠️  No Agent record found for type: {conv_agent.agent_type}")
            
            if fixed_count > 0:
                await db.commit()
                logger.info(f"✅ Fixed {fixed_count} ConversationAgent records")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error fixing ConversationAgent records: {e}")
            await db.rollback()
            return False

async def verify_agent_system():
    """
    Verify that the agent system is working correctly after fixes.
    """
    logger.info("🔍 Verifying agent system integrity...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check that all discovered agents have database records
            discovered_agents = agent_manager.get_available_agents()
            
            for agent_type in discovered_agents:
                result = await db.execute(
                    select(Agent).where(Agent.agent_type == agent_type)
                )
                agent_record = result.scalar_one_or_none()
                
                if not agent_record:
                    logger.error(f"❌ Missing database record for agent: {agent_type}")
                    return False
                
                logger.info(f"✅ Agent {agent_type} has valid database record")
            
            # Check for ConversationAgent records with agent_id=None
            result = await db.execute(
                select(ConversationAgent)
                .where(ConversationAgent.agent_id.is_(None))
            )
            null_records = result.scalars().all()
            
            if null_records:
                logger.warning(f"⚠️  Found {len(null_records)} ConversationAgent records with agent_id=None")
                for record in null_records:
                    logger.warning(f"   - ConversationAgent {record.id} (type: {record.agent_type})")
                return False
            
            logger.info("✅ All ConversationAgent records have valid agent_id references")
            
            # Test agent discovery
            moderator_agent = agent_manager.get_agent("MODERATOR")
            if not moderator_agent:
                logger.error("❌ MODERATOR agent not found in discovery system")
                return False
            
            logger.info("✅ MODERATOR agent discovered successfully")
            
            logger.info("🎉 Agent system verification completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during verification: {e}")
            return False

async def create_database_if_needed():
    """Create database tables if they don't exist."""
    try:
        logger.info("📋 Ensuring database tables exist...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables ready")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        return False

async def main():
    """Main function to fix the agent discovery system."""
    logger.info("🚀 Starting Agent Discovery System Fix...")
    
    try:
        # Step 1: Ensure database is ready
        if not await create_database_if_needed():
            logger.error("❌ Failed to initialize database")
            return False
        
        # Step 2: Sync discovered agents to database
        if not await sync_agents_to_database():
            logger.error("❌ Failed to synchronize agents to database")
            return False
        
        # Step 3: Fix existing ConversationAgent records
        if not await fix_conversation_agents():
            logger.error("❌ Failed to fix ConversationAgent records")
            return False
        
        # Step 4: Verify the system is working
        if not await verify_agent_system():
            logger.error("❌ Agent system verification failed")
            return False
        
        logger.info("🎉 Agent Discovery System Fix completed successfully!")
        logger.info("")
        logger.info("✅ Summary of changes:")
        logger.info("   - Synced dynamically discovered agents to database")
        logger.info("   - Fixed ConversationAgent records with missing agent_id")
        logger.info("   - Verified system integrity")
        logger.info("")
        logger.info("🔄 The system now supports:")
        logger.info("   - Pure dynamic agent discovery from code")
        logger.info("   - Consistent database relationships")
        logger.info("   - Backward compatibility with existing data")
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)