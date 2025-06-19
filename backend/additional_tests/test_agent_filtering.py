#!/usr/bin/env python3
"""
Test script to verify agent filtering by organization.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db_context
from app.models.models import User, Tenant
from app.agents.tenant_aware_agent_manager import tenant_aware_agent_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_agent_filtering():
    """Test that users from different organizations see different agents."""
    
    async with get_db_context() as db:
        # Get users from different organizations
        demo_user_result = await db.execute(
            select(User).join(Tenant).where(
                Tenant.subdomain == "demo",
                User.is_active == True
            ).limit(1)
        )
        demo_user = demo_user_result.scalar_one_or_none()
        
        acme_user_result = await db.execute(
            select(User).join(Tenant).where(
                Tenant.subdomain == "acme", 
                User.is_active == True
            ).limit(1)
        )
        acme_user = acme_user_result.scalar_one_or_none()
        
        if not demo_user:
            logger.error("No active user found for demo organization")
            return
            
        if not acme_user:
            logger.error("No active user found for acme organization")
            return
        
        logger.info(f"Testing with demo user: {demo_user.email}")
        logger.info(f"Testing with acme user: {acme_user.email}")
        
        # Get available agents for demo user
        demo_agents = await tenant_aware_agent_manager.get_available_agents_for_user(demo_user, db)
        logger.info(f"\nAgents available to demo user: {demo_agents}")
        
        # Get available agents for acme user
        acme_agents = await tenant_aware_agent_manager.get_available_agents_for_user(acme_user, db)
        logger.info(f"\nAgents available to acme user: {acme_agents}")
        
        # Check if STOCK_INVESTMENT_ADVISOR is properly filtered
        if "STOCK_INVESTMENT_ADVISOR" in demo_agents:
            logger.info("✅ STOCK_INVESTMENT_ADVISOR correctly available to demo org")
        else:
            logger.error("❌ STOCK_INVESTMENT_ADVISOR missing for demo org")
            
        if "STOCK_INVESTMENT_ADVISOR" not in acme_agents:
            logger.info("✅ STOCK_INVESTMENT_ADVISOR correctly filtered out for acme org")
        else:
            logger.error("❌ STOCK_INVESTMENT_ADVISOR incorrectly available to acme org")
        
        # Show the difference
        demo_only = set(demo_agents) - set(acme_agents)
        acme_only = set(acme_agents) - set(demo_agents)
        common = set(demo_agents) & set(acme_agents)
        
        logger.info(f"\nAgents exclusive to demo: {demo_only}")
        logger.info(f"Agents exclusive to acme: {acme_only}")
        logger.info(f"Common agents (free agents): {common}")


if __name__ == "__main__":
    asyncio.run(test_agent_filtering())