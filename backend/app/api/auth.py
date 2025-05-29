# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from typing import List

from app.models.models import User, Tenant, RefreshToken
from app.db.database import get_db
from app.auth.auth import (
    AuthService,
    get_current_user,
    get_current_active_user,
    get_tenant_from_request
)
from app.schemas.schemas import (
    TenantCreate, TenantResponse,
    UserCreate, UserLogin, UserResponse,
    TokenResponse, RefreshTokenRequest
)

router = APIRouter()

# Tenant endpoints
@router.post("/tenants", response_model=TenantResponse, tags=["tenants"])
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant."""
    # Check if subdomain already exists
    result = await db.execute(
        select(Tenant).filter(
            Tenant.subdomain == tenant_data.subdomain
        )
    )
    existing = result.scalars().first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Subdomain already exists"
        )
    
    tenant = Tenant(
        name=tenant_data.name,
        subdomain=tenant_data.subdomain
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    return tenant

@router.get("/tenants/{subdomain}", response_model=TenantResponse, tags=["tenants"])
async def get_tenant_by_subdomain(
    subdomain: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tenant information by subdomain."""
    result = await db.execute(
        select(Tenant).filter(
            Tenant.subdomain == subdomain,
            Tenant.is_active == True
        )
    )
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found"
        )
    
    return tenant

# Auth endpoints
@router.post("/auth/register", response_model=UserResponse, tags=["auth"])
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user for a tenant."""
    # Get tenant from request
    tenant = await get_tenant_from_request(request, db)
    if not tenant:
        raise HTTPException(
            status_code=400,
            detail="Tenant not found. Please provide X-Tenant-ID header."
        )
    
    # Check if user already exists in this tenant
    result = await db.execute(
        select(User).filter(
            User.email == user_data.email,
            User.tenant_id == tenant.id
        )
    )
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered for this tenant"
        )
    
    # Check username uniqueness within tenant
    result = await db.execute(
        select(User).filter(
            User.username == user_data.username,
            User.tenant_id == tenant.id
        )
    )
    existing_username = result.scalars().first()
    
    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already taken for this tenant"
        )
    
    # Create user
    hashed_password = AuthService.get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        tenant_id=tenant.id
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user

@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access/refresh tokens."""
    # Get tenant
    result = await db.execute(
        select(Tenant).filter(
            Tenant.subdomain == login_data.tenant_subdomain,
            Tenant.is_active == True
        )
    )
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(
            status_code=400,
            detail="Invalid tenant"
        )
    
    # Get user
    result = await db.execute(
        select(User).filter(
            User.email == login_data.email,
            User.tenant_id == tenant.id
        )
    )
    user = result.scalars().first()
    
    if not user or not AuthService.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="User account is disabled"
        )
    
    # Create tokens
    access_token = AuthService.create_access_token(
        data={
            "sub": user.id,
            "tenant_id": tenant.id,
            "email": user.email,
            "role": user.role
        }
    )
    refresh_token = await AuthService.create_refresh_token(user.id, db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/auth/refresh", response_model=TokenResponse, tags=["auth"])
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    # Verify refresh token
    result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.token == refresh_data.refresh_token,
            RefreshToken.expires_at > datetime.utcnow()
        )
    )
    token = result.scalars().first()
    
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )
    
    # Get user
    await db.refresh(token, ["user"])
    user = token.user
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="User account is disabled"
        )
    
    # Delete old refresh token
    await db.delete(token)
    await db.commit()
    
    # Create new tokens
    access_token = AuthService.create_access_token(
        data={
            "sub": user.id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "role": user.role
        }
    )
    new_refresh_token = await AuthService.create_refresh_token(user.id, db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )

@router.post("/auth/logout", tags=["auth"])
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate all refresh tokens."""
    # Delete all refresh tokens for this user
    result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.user_id == current_user.id
        )
    )
    tokens = result.scalars().all()
    for token in tokens:
        await db.delete(token)
    await db.commit()
    
    return {"message": "Successfully logged out"}

# User endpoints
@router.get("/me", response_model=UserResponse, tags=["users"])
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current authenticated user information."""
    return current_user

@router.get("/users", response_model=List[UserResponse], tags=["users"])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users in the current tenant (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized. Admin access required."
        )
    
    result = await db.execute(
        select(User)
        .filter(User.tenant_id == current_user.tenant_id)
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()
    
    return users

@router.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific user information (admin only or own profile)."""
    # Users can view their own profile
    if current_user.id == user_id:
        return current_user
    
    # Otherwise, admin access required
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )
    
    result = await db.execute(
        select(User).filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    return user

@router.patch("/users/{user_id}/role", response_model=UserResponse, tags=["users"])
async def update_user_role(
    user_id: str,
    role: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user role (super_admin only)."""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Not authorized. Super admin access required."
        )
    
    if role not in ["user", "admin", "super_admin"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Must be one of: user, admin, super_admin"
        )
    
    result = await db.execute(
        select(User).filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    user.role = role
    await db.commit()
    await db.refresh(user)
    
    return user

@router.delete("/users/{user_id}", tags=["users"])
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user (admin only, cannot delete self)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized. Admin access required."
        )
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )
    
    result = await db.execute(
        select(User).filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Don't allow deleting super_admin unless you are super_admin
    if user.role == "super_admin" and current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Cannot delete super admin user"
        )
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}
