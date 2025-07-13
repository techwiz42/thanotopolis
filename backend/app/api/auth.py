# backend/app/api/auth.py
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
import secrets
import logging

logger = logging.getLogger(__name__)

from app.db.database import get_db
from app.models.models import User, Tenant, RefreshToken, PasswordResetToken
# Import schemas
from app.schemas.schemas import (
    UserRegister, 
    UserLogin, 
    TokenResponse, 
    RefreshTokenRequest,
    UserResponse,
    OrganizationCreate,
    OrganizationResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordResponse
)
from app.auth.auth import (
    AuthService, 
    get_current_user, 
    get_current_active_user,
    get_tenant_from_request
)
from app.services.email_service import email_service

router = APIRouter()

# Schema definitions (these would normally be in schemas.py)
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional

class OrganizationCreate(BaseModel):
    name: str
    subdomain: str

class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    subdomain: str
    access_code: str
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    access_code: Optional[str] = None  # Organization access code (optional)

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    tenant_subdomain: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    tenant_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    organization_subdomain: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/tenants", response_model=OrganizationResponse, tags=["organizations"])
@router.post("/organizations", response_model=OrganizationResponse, tags=["organizations"])
async def create_organization(
    org_data: OrganizationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization."""
    # Check if subdomain already exists
    result = await db.execute(
        select(Tenant).filter(Tenant.subdomain == org_data.subdomain)
    )
    existing = result.scalars().first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization subdomain already exists"
        )
    
    # Create new organization
    new_org = Tenant(
        name=org_data.name,
        subdomain=org_data.subdomain
    )
    
    db.add(new_org)
    await db.commit()
    await db.refresh(new_org)
    
    return new_org

@router.get("/organizations/{access_code}/info", tags=["organizations"])
async def get_organization_by_access_code(
    access_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Get organization info by access code (for registration flow)."""
    result = await db.execute(
        select(Tenant).filter(
            Tenant.access_code == access_code,
            Tenant.is_active == True
        )
    )
    organization = result.scalars().first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid access code or organization not found"
        )
    
    return {
        "name": organization.name,
        "subdomain": organization.subdomain
    }

@router.get("/tenants/{subdomain}", response_model=OrganizationResponse, tags=["organizations"])
async def get_tenant_by_subdomain(
    subdomain: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tenant by subdomain."""
    result = await db.execute(
        select(Tenant).filter(Tenant.subdomain == subdomain)
    )
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return tenant

@router.post("/auth/register", response_model=UserResponse, tags=["auth"])
async def register(
    register_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Try to get tenant from request header or use access code
    tenant = await get_tenant_from_request(request, db)
    
    if not tenant and hasattr(register_data, 'access_code'):
        # Find organization by access code
        result = await db.execute(
            select(Tenant).filter(
                Tenant.access_code == register_data.access_code,
                Tenant.is_active == True
            )
        )
        tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant not found"
        )
    
    # Check if email already exists in the organization
    result = await db.execute(
        select(User).filter(
            User.email == register_data.email,
            User.tenant_id == tenant.id
        )
    )
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered in this organization"
        )
    
    # Check if username already exists in the organization
    result = await db.execute(
        select(User).filter(
            User.username == register_data.username,
            User.tenant_id == tenant.id
        )
    )
    existing_username = result.scalars().first()
    
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken in this organization"
        )
    
    # Create new user
    hashed_password = AuthService.get_password_hash(register_data.password)
    
    new_user = User(
        email=register_data.email,
        username=register_data.username,
        hashed_password=hashed_password,
        first_name=register_data.first_name,
        last_name=register_data.last_name,
        tenant_id=tenant.id,
        role="user",
        is_active=True,
        is_verified=False  # User needs to verify email
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user

@router.post("/auth/register/token", response_model=TokenResponse, tags=["auth"])
async def register_and_get_token(
    register_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user and return tokens."""
    # First register the user
    new_user = await register(register_data, request, db)
    
    # Get the tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == new_user.tenant_id)
    )
    tenant = result.scalar_one()
    
    # Create tokens
    access_token = AuthService.create_access_token(
        data={
            "sub": str(new_user.id),
            "tenant_id": str(tenant.id),
            "email": new_user.email,
            "role": new_user.role
        }
    )
    refresh_token = await AuthService.create_refresh_token(str(new_user.id), db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        organization_subdomain=tenant.subdomain
    )

@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access/refresh tokens."""
    # If tenant_subdomain is provided, find the tenant
    tenant = None
    if login_data.tenant_subdomain:
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
    
    # Find user by email
    query = select(User).filter(User.email == login_data.email)
    if tenant:
        query = query.filter(User.tenant_id == tenant.id)
    
    result = await db.execute(query)
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
    
    # Get the user's organization
    await db.refresh(user, ["tenant"])
    organization = user.tenant
    
    if not organization.is_active:
        raise HTTPException(
            status_code=400,
            detail="Organization is not active"
        )
    
    # Create tokens
    access_token = AuthService.create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(organization.id),
            "email": user.email,
            "role": user.role
        }
    )
    refresh_token = await AuthService.create_refresh_token(str(user.id), db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        organization_subdomain=organization.subdomain
    )

@router.post("/auth/refresh", response_model=TokenResponse, tags=["auth"])
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    # Find the refresh token
    result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.token == refresh_request.refresh_token
        )
    )
    token_record = result.scalars().first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if token is expired
    if token_record.expires_at < datetime.now(timezone.utc):
        # Delete expired token
        await db.delete(token_record)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    
    # Get user
    result = await db.execute(
        select(User).filter(
            User.id == token_record.user_id,
            User.is_active == True
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Get organization
    await db.refresh(user, ["tenant"])
    organization = user.tenant
    
    if not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization is inactive"
        )
    
    # Create new tokens
    access_token = AuthService.create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(organization.id),
            "email": user.email,
            "role": user.role
        }
    )
    
    # Delete old refresh token and create a new one
    await db.delete(token_record)
    new_refresh_token = await AuthService.create_refresh_token(str(user.id), db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        organization_subdomain=organization.subdomain
    )

@router.get("/auth/me", response_model=UserResponse, tags=["auth"])
@router.get("/me", response_model=UserResponse, tags=["auth"])
async def get_user_info(current_user: User = Depends(get_current_active_user)):
    """Get information about the currently logged in user."""
    return current_user

@router.post("/auth/logout", tags=["auth"])
async def logout(
    refresh_request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout user by invalidating the refresh token."""
    # Find and delete the refresh token
    result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.token == refresh_request.refresh_token,
            RefreshToken.user_id == current_user.id
        )
    )
    token_record = result.scalars().first()
    
    if token_record:
        await db.delete(token_record)
        await db.commit()
    
    return {"detail": "Successfully logged out"}

@router.post("/auth/logout/all", tags=["auth"])
async def logout_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout user from all sessions by invalidating all refresh tokens."""
    # Delete all refresh tokens for the user
    result = await db.execute(
        select(RefreshToken).filter(RefreshToken.user_id == current_user.id)
    )
    tokens = result.scalars().all()
    
    for token in tokens:
        await db.delete(token)
    
    await db.commit()
    
    return {"detail": "Successfully logged out from all sessions"}

# User Management Endpoints
def require_admin():
    """Dependency to require admin role."""
    async def admin_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user
    return admin_checker

def require_super_admin():
    """Dependency to require super admin role."""
    async def super_admin_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )
        return current_user
    return super_admin_checker

@router.get("/users", response_model=list[UserResponse], tags=["users"])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin())
):
    """List all users in the current tenant (admin only)."""
    result = await db.execute(
        select(User).filter(User.tenant_id == current_user.tenant_id)
    )
    users = result.scalars().all()
    return users

@router.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a user by ID."""
    # Regular users can only view their own profile
    if current_user.role not in ["admin", "super_admin"] and str(current_user.id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Get user from database
    result = await db.execute(
        select(User).filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.put("/users/{user_id}/role", response_model=UserResponse, tags=["users"])
@router.patch("/users/{user_id}/role", response_model=UserResponse, tags=["users"])
async def update_user_role(
    user_id: UUID,
    role: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Check if user is admin
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    """Update a user's role (admin only)."""
    # Check if role is valid
    if role not in ["user", "admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    # Super admin required to promote to super_admin
    if role == "super_admin" and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can promote to super admin"
        )
    
    # Get user to update
    result = await db.execute(
        select(User).filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Regular admins cannot modify super admins
    if user.role == "super_admin" and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    
    # Update role
    user.role = role
    await db.commit()
    await db.refresh(user)
    
    return user

@router.delete("/users/{user_id}", tags=["users"])
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin())
):
    """Delete a user (admin only)."""
    # Check if user is trying to delete self
    if str(current_user.id) == str(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Get user to delete
    result = await db.execute(
        select(User).filter(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Regular admins cannot delete super admins
    if user.role == "super_admin" and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete super admin"
        )
    
    # Delete user
    await db.delete(user)
    await db.commit()
    
    return {"detail": "User deleted successfully"}

@router.post("/auth/forgot-password", response_model=ForgotPasswordResponse, tags=["auth"])
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send password reset email."""
    # Find user by email
    result = await db.execute(
        select(User).filter(User.email == request.email)
    )
    user = result.scalars().first()
    
    # Always return success to prevent email enumeration
    if not user:
        return ForgotPasswordResponse(message="If an account with that email exists, you will receive a password reset link.")
    
    # Delete any existing password reset tokens for this user
    result = await db.execute(
        select(PasswordResetToken).filter(PasswordResetToken.user_id == user.id)
    )
    existing_tokens = result.scalars().all()
    for token in existing_tokens:
        await db.delete(token)
    
    # Generate secure reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry
    
    # Create password reset token record
    password_reset_token = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=expires_at
    )
    db.add(password_reset_token)
    await db.commit()
    
    # Get user's organization for email context
    await db.refresh(user, ["tenant"])
    organization_name = user.tenant.name if user.tenant else "Thanotopolis"
    
    # Send password reset email
    try:
        user_name = f"{user.first_name} {user.last_name}".strip() or user.username
        await email_service.send_password_reset_email(
            to_email=user.email,
            user_name=user_name,
            reset_token=reset_token,
            organization_name=organization_name
        )
        logger.info(f"Password reset email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        # Don't fail the request if email fails - the token is still valid
    
    return ForgotPasswordResponse(message="If an account with that email exists, you will receive a password reset link.")

@router.post("/auth/reset-password", response_model=ResetPasswordResponse, tags=["auth"])
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using reset token."""
    # Find password reset token
    result = await db.execute(
        select(PasswordResetToken).filter(
            PasswordResetToken.token == request.token,
            PasswordResetToken.is_used == False
        )
    )
    reset_token = result.scalars().first()
    
    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )
    
    # Check if token is expired
    if reset_token.expires_at < datetime.now(timezone.utc):
        # Delete expired token
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail="Reset token has expired"
        )
    
    # Get user
    result = await db.execute(
        select(User).filter(User.id == reset_token.user_id)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = AuthService.get_password_hash(request.new_password)
    
    # Mark token as used
    reset_token.is_used = True
    
    # Revoke all existing refresh tokens for security
    result = await db.execute(
        select(RefreshToken).filter(RefreshToken.user_id == user.id)
    )
    refresh_tokens = result.scalars().all()
    for token in refresh_tokens:
        await db.delete(token)
    
    await db.commit()
    
    return ResetPasswordResponse(message="Password reset successfully")
