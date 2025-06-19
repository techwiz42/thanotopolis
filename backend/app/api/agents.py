# backend/app/api/agents.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List
from uuid import UUID

from app.db.database import get_db
from app.models.models import Agent, User
from app.schemas.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AvailableAgentsResponse
)
from app.auth.auth import get_current_user

router = APIRouter(prefix="/api/agents", tags=["agents"])

async def is_org_admin(current_user: User = Depends(get_current_user)) -> User:
    """Check if user is organization admin or higher"""
    if current_user.role not in ["org_admin", "admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can perform this action"
        )
    return current_user

@router.get("/", response_model=AvailableAgentsResponse)
async def list_available_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all agents available to the current user's organization"""
    from app.agents.tenant_aware_agent_manager import tenant_aware_agent_manager
    
    # Get available agent types for this user
    available_agent_types = await tenant_aware_agent_manager.get_available_agents_for_user(current_user, db)
    
    # Build list of agent responses
    agents = []
    for agent_type in available_agent_types:
        # Get agent instance to check properties
        agent_instance = tenant_aware_agent_manager.get_agent(agent_type)
        if agent_instance:
            from app.agents.base_agent import BaseAgent
            
            # Check agent properties
            is_free_agent = True
            owner_tenant_id = None
            description = getattr(agent_instance, 'description', f"{agent_type} agent")
            capabilities = getattr(agent_instance, 'capabilities', [])
            
            if isinstance(agent_instance, BaseAgent):
                is_free_agent = getattr(agent_instance.__class__, 'IS_FREE_AGENT', True)
                owner_domain = getattr(agent_instance.__class__, 'OWNER_DOMAIN', None)
                
                # Get tenant ID from domain if proprietary
                if not is_free_agent and owner_domain:
                    tenant_result = await db.execute(
                        select(Agent.owner_tenant_id).join(Tenant).where(Tenant.subdomain == owner_domain)
                    )
                    result = tenant_result.scalar_one_or_none()
                    if result:
                        owner_tenant_id = result
            
            # Check if agent exists in database
            agent_result = await db.execute(
                select(Agent).where(Agent.agent_type == agent_type)
            )
            agent_record = agent_result.scalar_one_or_none()
            
            if agent_record:
                agents.append(agent_record)
            else:
                # Create a temporary agent response object
                from app.schemas.schemas import AgentResponse
                from datetime import datetime, timezone
                agents.append(AgentResponse(
                    id=UUID('00000000-0000-0000-0000-000000000000'),  # Placeholder ID
                    agent_type=agent_type,
                    name=agent_type.replace('_', ' ').title() + " Agent",
                    description=description if isinstance(description, str) else f"{agent_type} agent",
                    is_free_agent=is_free_agent,
                    owner_tenant_id=owner_tenant_id,
                    owner_domain=owner_domain if not is_free_agent else None,
                    is_enabled=True,
                    capabilities=capabilities if isinstance(capabilities, list) else [],
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=None
                ))
    
    # Import Tenant model locally to avoid circular imports
    from app.models.models import Tenant
    
    return AvailableAgentsResponse(agents=agents)

@router.post("/", response_model=AgentResponse)
async def create_proprietary_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a proprietary agent for the organization (org_admin or higher required)"""
    # Check if agent_type already exists
    result = await db.execute(
        select(Agent).where(Agent.agent_type == agent_data.agent_type)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent type already exists"
        )
    
    # Create agent
    agent = Agent(
        agent_type=agent_data.agent_type,
        name=agent_data.name,
        description=agent_data.description,
        is_free_agent=agent_data.is_free_agent,
        owner_tenant_id=current_user.tenant_id if not agent_data.is_free_agent else None,
        capabilities=agent_data.capabilities,
        is_active=True
    )
    
    # Only super_admin can create free agents
    if agent_data.is_free_agent and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create free agents"
        )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    return agent

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent details"""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check access permissions
    if not agent.is_free_agent and agent.owner_tenant_id != current_user.tenant_id:
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this agent"
            )
    
    return agent

@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    update_data: AgentUpdate,
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update agent configuration (org_admin or higher required)"""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check ownership
    if agent.is_free_agent:
        # Only super_admin can update free agents
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can update free agents"
            )
    else:
        # Org admins can only update their own agents
        if agent.owner_tenant_id != current_user.tenant_id and current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update agents owned by your organization"
            )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(agent, field, value)
    
    await db.commit()
    await db.refresh(agent)
    
    return agent

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a proprietary agent (org_admin or higher required)"""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check ownership
    if agent.is_free_agent:
        # Only super_admin can delete free agents
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can delete free agents"
            )
    else:
        # Org admins can only delete their own agents
        if agent.owner_tenant_id != current_user.tenant_id and current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete agents owned by your organization"
            )
    
    # Soft delete - just mark as inactive
    agent.is_active = False
    
    await db.commit()
    
    return {"message": "Agent deactivated successfully"}