# backend/app/api/organizations.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Dict, Any
from uuid import UUID
import secrets
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.models import Tenant, User, Agent, Conversation, Contact, PhoneCall, TelephonyConfiguration
from app.schemas.schemas import (
    OrganizationResponse, 
    OrganizationUpdate,
    OrganizationRegisterRequest,
    OrganizationRegisterResponse,
    UserResponse,
    UserUpdate,
    AdminUserUpdate
)
from app.auth.auth import get_current_user, get_password_hash, create_tokens
from app.core.config import settings

router = APIRouter(prefix="/api/organizations", tags=["organizations"])

async def is_org_admin(current_user: User = Depends(get_current_user)) -> User:
    """Check if user is organization admin or higher"""
    if current_user.role not in ["org_admin", "admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can perform this action"
        )
    return current_user

@router.post("/register", response_model=OrganizationRegisterResponse)
async def register_organization(
    request: OrganizationRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new organization with admin user"""
    # Check if subdomain already exists
    result = await db.execute(
        select(Tenant).where(Tenant.subdomain == request.subdomain)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subdomain already exists"
        )
    
    # Check if admin email already exists
    result = await db.execute(
        select(User).where(User.email == request.admin_email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization
    org = Tenant(
        name=request.name,
        subdomain=request.subdomain,
        full_name=request.full_name,
        address=request.address,
        phone=request.phone,
        organization_email=request.organization_email,
        access_code=secrets.token_urlsafe(8)
    )
    db.add(org)
    await db.flush()  # Get org.id without committing
    
    # Create admin user
    admin_user = User(
        email=request.admin_email,
        username=request.admin_username,
        hashed_password=get_password_hash(request.admin_password),
        first_name=request.admin_first_name,
        last_name=request.admin_last_name,
        role="org_admin",
        tenant_id=org.id,
        is_active=True,
        is_verified=True  # Auto-verify org admins
    )
    db.add(admin_user)
    
    await db.commit()
    await db.refresh(org)
    await db.refresh(admin_user)
    
    # Create tokens for immediate login
    access_token, refresh_token = await create_tokens(admin_user, db)
    
    return OrganizationRegisterResponse(
        organization=org,
        admin_user=admin_user,
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's organization details"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not belong to any organization"
        )
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return org

@router.patch("/current", response_model=OrganizationResponse)
async def update_current_organization(
    update_data: OrganizationUpdate,
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's organization details (org_admin or higher required)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not belong to any organization"
        )
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(org, field, value)
    
    await db.commit()
    await db.refresh(org)
    
    return org

@router.get("/stats", response_model=Dict[str, Any])
async def get_organization_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization statistics (admin or higher required)"""
    # Check if user has admin access
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access organization statistics"
        )
    
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not belong to any organization"
        )
    
    # Get organization
    org_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    org = org_result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Count total users
    users_result = await db.execute(
        select(User).where(User.tenant_id == current_user.tenant_id)
    )
    total_users = len(users_result.scalars().all())
    
    # Count total conversations
    conversations_result = await db.execute(
        select(Conversation).where(Conversation.tenant_id == current_user.tenant_id)
    )
    total_conversations = len(conversations_result.scalars().all())
    
    # Count total contacts
    contacts_result = await db.execute(
        select(Contact).where(Contact.tenant_id == current_user.tenant_id)
    )
    total_contacts = len(contacts_result.scalars().all())
    
    # Count total phone calls
    telephony_config_result = await db.execute(
        select(TelephonyConfiguration).where(TelephonyConfiguration.tenant_id == current_user.tenant_id)
    )
    telephony_config = telephony_config_result.scalar_one_or_none()
    
    total_calls = 0
    if telephony_config:
        calls_result = await db.execute(
            select(PhoneCall).where(PhoneCall.telephony_config_id == telephony_config.id)
        )
        total_calls = len(calls_result.scalars().all())
    
    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_activity = []
    
    # Recent conversations
    recent_conversations_result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.tenant_id == current_user.tenant_id,
                Conversation.created_at >= thirty_days_ago
            )
        ).order_by(Conversation.created_at.desc()).limit(5)
    )
    recent_conversations = recent_conversations_result.scalars().all()
    
    for conv in recent_conversations:
        recent_activity.append({
            "id": str(conv.id),
            "type": "conversation",
            "description": f"New conversation started",
            "timestamp": conv.created_at.isoformat()
        })
    
    # Recent contacts
    recent_contacts_result = await db.execute(
        select(Contact).where(
            and_(
                Contact.tenant_id == current_user.tenant_id,
                Contact.created_at >= thirty_days_ago
            )
        ).order_by(Contact.created_at.desc()).limit(5)
    )
    recent_contacts = recent_contacts_result.scalars().all()
    
    for contact in recent_contacts:
        recent_activity.append({
            "id": str(contact.id),
            "type": "contact",
            "description": f"New contact added: {contact.business_name}",
            "timestamp": contact.created_at.isoformat()
        })
    
    # Recent phone calls
    if telephony_config:
        recent_calls_result = await db.execute(
            select(PhoneCall).where(
                and_(
                    PhoneCall.telephony_config_id == telephony_config.id,
                    PhoneCall.created_at >= thirty_days_ago
                )
            ).order_by(PhoneCall.created_at.desc()).limit(5)
        )
        recent_calls = recent_calls_result.scalars().all()
        
        for call in recent_calls:
            recent_activity.append({
                "id": str(call.id),
                "type": "call",
                "description": f"Phone call from {call.customer_phone_number}",
                "timestamp": call.created_at.isoformat()
            })
    
    # Sort all activity by timestamp (most recent first)
    recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "total_users": total_users,
        "total_conversations": total_conversations,
        "total_contacts": total_contacts,
        "total_calls": total_calls,
        "recent_activity": recent_activity[:10]  # Limit to 10 most recent items
    }

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization details"""
    # Users can only view their own organization unless they're super_admin
    if str(current_user.tenant_id) != str(org_id) and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own organization"
        )
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return org

@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    update_data: OrganizationUpdate,
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update organization details (org_admin or higher required)"""
    # Org admins can only update their own org, unless super_admin
    if str(current_user.tenant_id) != str(org_id) and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own organization"
        )
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(org, field, value)
    
    await db.commit()
    await db.refresh(org)
    
    return org

@router.get("/{org_id}/users", response_model=List[UserResponse])
async def list_organization_users(
    org_id: UUID,
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users in an organization (org_admin or higher required)"""
    # Org admins can only list users in their own org
    if str(current_user.tenant_id) != str(org_id) and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only list users in your own organization"
        )
    
    result = await db.execute(
        select(User).where(User.tenant_id == org_id)
    )
    users = result.scalars().all()
    
    return users

@router.patch("/{org_id}/users/{user_id}", response_model=UserResponse)
async def update_organization_user(
    org_id: UUID,
    user_id: UUID,
    update_data: AdminUserUpdate,
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user status/role (org_admin or higher required)"""
    # Org admins can only update users in their own org
    if str(current_user.tenant_id) != str(org_id) and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update users in your own organization"
        )
    
    # Prevent self-demotion
    if str(current_user.id) == str(user_id) and update_data.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role"
        )
    
    result = await db.execute(
        select(User).where(and_(User.id == user_id, User.tenant_id == org_id))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization"
        )
    
    # Org admins can only promote to org_admin or below
    if update_data.role and current_user.role == "org_admin":
        if update_data.role in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot promote users to admin or super_admin"
            )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user

@router.delete("/{org_id}/users/{user_id}")
async def deactivate_organization_user(
    org_id: UUID,
    user_id: UUID,
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a user (org_admin or higher required)"""
    # Org admins can only deactivate users in their own org
    if str(current_user.tenant_id) != str(org_id) and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only deactivate users in your own organization"
        )
    
    # Prevent self-deactivation
    if str(current_user.id) == str(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate yourself"
        )
    
    result = await db.execute(
        select(User).where(and_(User.id == user_id, User.tenant_id == org_id))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization"
        )
    
    # Deactivate user instead of hard delete
    user.is_active = False
    
    await db.commit()
    
    return {"message": "User deactivated successfully"}

@router.post("/current/regenerate-access-code", response_model=OrganizationResponse)
async def regenerate_organization_access_code(
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate organization access code (org_admin or higher required)"""
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not belong to any organization"
        )
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Generate new access code
    org.access_code = secrets.token_urlsafe(8)
    
    await db.commit()
    await db.refresh(org)
    
    return org