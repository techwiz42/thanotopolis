# backend/tests/unit/test_auth_endpoints.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import User, Tenant, RefreshToken
from app.auth.auth import AuthService

class TestAuthEndpoints:
    """Test suite for authentication endpoints."""
    
    async def test_create_tenant(self, client: AsyncClient):
        """Test tenant creation endpoint."""
        response = await client.post(
            "/api/tenants",
            json={
                "name": "New Company",
                "subdomain": "newcompany"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Company"
        assert data["subdomain"] == "newcompany"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
    
    async def test_create_duplicate_tenant(self, client: AsyncClient, test_tenant: Tenant):
        """Test creating tenant with duplicate subdomain."""
        response = await client.post(
            "/api/tenants",
            json={
                "name": "Duplicate Company",
                "subdomain": test_tenant.subdomain
            }
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    async def test_get_tenant_by_subdomain(self, client: AsyncClient, test_tenant: Tenant):
        """Test getting tenant by subdomain."""
        response = await client.get(f"/api/tenants/{test_tenant.subdomain}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_tenant.id
        assert data["subdomain"] == test_tenant.subdomain
    
    async def test_get_nonexistent_tenant(self, client: AsyncClient):
        """Test getting non-existent tenant."""
        response = await client.get("/api/tenants/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    async def test_register_user(self, client: AsyncClient, test_tenant: Tenant):
        """Test user registration."""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "password123",
                "first_name": "New",
                "last_name": "User"
            },
            headers={"X-Tenant-ID": test_tenant.subdomain}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert data["tenant_id"] == test_tenant.id
        assert data["role"] == "user"
        assert data["is_active"] is True
        assert data["is_verified"] is False
    
    async def test_register_duplicate_email(self, client: AsyncClient, test_tenant: Tenant, test_user: User):
        """Test registering with duplicate email in same tenant."""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "username": "different_username",
                "password": "password123"
            },
            headers={"X-Tenant-ID": test_tenant.subdomain}
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    async def test_register_duplicate_username(self, client: AsyncClient, test_tenant: Tenant, test_user: User):
        """Test registering with duplicate username in same tenant."""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "password123"
            },
            headers={"X-Tenant-ID": test_tenant.subdomain}
        )
        
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]
    
    async def test_register_without_tenant(self, client: AsyncClient):
        """Test registration without tenant header."""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "password123"
            }
        )
        
        assert response.status_code == 400
        assert "Tenant not found" in response.json()["detail"]
    
    async def test_login_success(self, client: AsyncClient, test_tenant: Tenant, test_user: User):
        """Test successful login."""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
                "tenant_subdomain": test_tenant.subdomain
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify tokens are valid
        payload = AuthService.verify_token(data["access_token"])
        assert payload["sub"] == test_user.id
        assert payload["tenant_id"] == test_tenant.id
    
    async def test_login_wrong_password(self, client: AsyncClient, test_tenant: Tenant, test_user: User):
        """Test login with wrong password."""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
                "tenant_subdomain": test_tenant.subdomain
            }
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    async def test_login_wrong_tenant(self, client: AsyncClient, test_user: User):
        """Test login with wrong tenant."""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
                "tenant_subdomain": "wrongtenant"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid tenant" in response.json()["detail"]
    
    async def test_login_inactive_user(self, client: AsyncClient, test_tenant: Tenant, test_user: User, db_session: AsyncSession):
        """Test login with inactive user."""
        # Deactivate user
        test_user.is_active = False
        await db_session.commit()
        
        response = await client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
                "tenant_subdomain": test_tenant.subdomain
            }
        )
        
        assert response.status_code == 400
        assert "disabled" in response.json()["detail"]
    
    async def test_refresh_token(self, client: AsyncClient, test_tenant: Tenant, test_user: User, db_session: AsyncSession):
        """Test token refresh."""
        # Create refresh token
        refresh_token = await AuthService.create_refresh_token(test_user.id, db_session)
        
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != refresh_token  # New refresh token
        
        # Verify old refresh token is deleted
        result = await db_session.execute(
            select(RefreshToken).filter(RefreshToken.token == refresh_token)
        )
        assert result.scalars().first() is None
    
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]
    
    async def test_logout(self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession):
        """Test logout endpoint."""
        # Create some refresh tokens
        token1 = await AuthService.create_refresh_token(test_user.id, db_session)
        token2 = await AuthService.create_refresh_token(test_user.id, db_session)
        
        response = await client.post(
            "/api/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify all refresh tokens are deleted
        result = await db_session.execute(
            select(RefreshToken).filter(RefreshToken.user_id == test_user.id)
        )
        assert len(result.scalars().all()) == 0
    
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """Test getting current user info."""
        response = await client.get(
            "/api/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
    
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without auth."""
        response = await client.get("/api/me")
        
        assert response.status_code == 403  # HTTPBearer returns 403 for missing auth
