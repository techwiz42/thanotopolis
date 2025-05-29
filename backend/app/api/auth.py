# backend/app/api/auth.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.db.database import get_db
from app.models.models import User, Tenant, RefreshToken
from app.schemas.schemas import (
    UserRegister, 
    UserLogin, 
    TokenResponse, 
    RefreshTokenRequest,
    UserResponse
)
from app.auth.auth import (
    AuthService, 
    get_current_user, 
    get_current_active_user,
    get_tenant_from_request
)

router = APIRouter()

@router.post("/auth/register", response_model=TokenResponse, tags=["auth"])
async def register(
    register_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user in an existing organization."""
    # Verify organization exists and access code is valid
    result = await db.execute(
        select(Tenant).filter(
            Tenant.subdomain == register_data.organization_subdomain,
            Tenant.is_active == True
        )
    )
    organization = result.scalars().first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if organization.access_code != register_data.access_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid access code"
        )
    
    # Check if email already exists in the organization
    result = await db.execute(
        select(User).filter(
            User.email == register_data.email,
            User.tenant_id == organization.id
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
            User.tenant_id == organization.id
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
        tenant_id=organization.id,
        role="user",
        is_active=True,
        is_verified=False  # User needs to verify email
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create tokens
    access_token = AuthService.create_access_token(
        data={
            "sub": str(new_user.id),
            "tenant_id": str(organization.id),
            "email": new_user.email,
            "role": new_user.role
        }
    )
    refresh_token = await AuthService.create_refresh_token(str(new_user.id), db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        organization_subdomain=organization.subdomain
    )

@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access/refresh tokens."""
    # Find user by email across all organizations
    result = await db.execute(
        select(User).filter(
            User.email == login_data.email
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