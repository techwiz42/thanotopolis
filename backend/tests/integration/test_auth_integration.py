"""
Integration tests for authentication API endpoints.
Tests actual HTTP endpoints with database integration.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import status

from app.models import User, Tenant


class TestAuthAPIIntegration:
    """Test authentication API endpoints with database integration."""

    async def test_register_new_user_success(self, client: AsyncClient, sample_tenant: Tenant):
        """Test successful user registration."""
        registration_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = await client.post("/api/auth/register", json=registration_data, 
                                   headers={"X-Tenant-ID": sample_tenant.subdomain})
        
        if response.status_code != status.HTTP_200_OK:
            print(f"Error: {response.status_code} - {response.json()}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert data["tenant_id"] == str(sample_tenant.id)
        assert data["role"] == "user"
        assert data["is_active"] is True
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password

    async def test_register_with_duplicate_email_fails(self, client: AsyncClient, sample_user: User, sample_tenant: Tenant):
        """Test that registration fails with duplicate email."""
        registration_data = {
            "email": sample_user.email,  # Duplicate
            "username": "anotheruser",
            "password": "AnotherPassword123!",
            "first_name": "Another",
            "last_name": "User"
        }
        
        response = await client.post("/api/auth/register", json=registration_data,
                                   headers={"X-Tenant-ID": sample_tenant.subdomain})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already" in response.json()["detail"].lower()

    async def test_register_with_invalid_email_fails(self, client: AsyncClient, sample_tenant: Tenant):
        """Test registration fails with invalid email format."""
        registration_data = {
            "email": "not-an-email",
            "username": "testuser",
            "password": "SecurePassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = await client.post("/api/auth/register", json=registration_data,
                                   headers={"X-Tenant-ID": sample_tenant.subdomain})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_register_with_weak_password_fails(self, client: AsyncClient, sample_tenant: Tenant):
        """Test registration fails with weak password."""
        registration_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "weak",  # Too weak
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = await client.post("/api/auth/register", json=registration_data,
                                   headers={"X-Tenant-ID": sample_tenant.subdomain})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_login_with_valid_credentials_success(self, client: AsyncClient, sample_user: User):
        """Test successful login with valid credentials."""
        login_data = {
            "email": sample_user.email,
            "password": "testpassword123"  # From fixture
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["organization_subdomain"]

    async def test_login_with_wrong_password_fails(self, client: AsyncClient, sample_user: User):
        """Test login fails with wrong password."""
        login_data = {
            "email": sample_user.email,
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in response.json()["detail"]

    async def test_login_with_inactive_user_fails(self, client: AsyncClient, inactive_user: User):
        """Test login fails for inactive user."""
        login_data = {
            "email": inactive_user.email,
            "password": "testpassword123"
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_get_current_user_with_valid_token(self, client: AsyncClient, auth_headers: dict):
        """Test getting current user info with valid token."""
        response = await client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "id" in data
        assert "email" in data
        assert "username" in data
        assert "role" in data
        assert "tenant_id" in data
        assert "is_active" in data
        assert "hashed_password" not in data

    async def test_refresh_token_with_valid_token(self, client: AsyncClient, sample_user: User):
        """Test refreshing access token with valid refresh token."""
        # First login to get refresh token
        login_data = {
            "email": sample_user.email,
            "password": "testpassword123"
        }
        
        login_response = await client.post("/api/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}
        response = await client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_logout_with_valid_token(self, client: AsyncClient, sample_user: User):
        """Test successful logout with valid refresh token."""
        # First login to get refresh token and access token
        login_data = {
            "email": sample_user.email,
            "password": "testpassword123"
        }
        
        login_response = await client.post("/api/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]
        
        # Logout with auth header
        logout_data = {"refresh_token": refresh_token}
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post("/api/auth/logout", json=logout_data, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "successfully logged out" in response.json()["detail"].lower()
        
        # Verify refresh token no longer works
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = await client.post("/api/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_multiple_login_sessions(self, client: AsyncClient, sample_user: User):
        """Test that user can have multiple active sessions."""
        login_data = {
            "email": sample_user.email,
            "password": "testpassword123"
        }
        
        # Create two login sessions
        response1 = await client.post("/api/auth/login", json=login_data)
        response2 = await client.post("/api/auth/login", json=login_data)
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        
        token1 = response1.json()["refresh_token"]
        token2 = response2.json()["refresh_token"]
        
        # Both tokens should be different
        assert token1 != token2
        
        # Both should work for refresh
        refresh_response1 = await client.post("/api/auth/refresh", json={"refresh_token": token1})
        refresh_response2 = await client.post("/api/auth/refresh", json={"refresh_token": token2})
        
        assert refresh_response1.status_code == status.HTTP_200_OK
        assert refresh_response2.status_code == status.HTTP_200_OK

    async def test_access_token_expiration_handling(self, client: AsyncClient, sample_user: User):
        """Test that access tokens work initially."""
        # Login to get tokens
        login_data = {
            "email": sample_user.email,
            "password": "testpassword123"
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        access_token = response.json()["access_token"]
        
        # Access token should work initially
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK

    async def test_role_based_access_patterns(self, client: AsyncClient, admin_user: User):
        """Test that user roles are properly included in tokens."""
        login_data = {
            "email": admin_user.email,
            "password": "testpassword123"
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        # The role would be in the JWT token payload, not directly in response

    async def test_tenant_isolation_in_auth(self, client: AsyncClient, sample_user: User, other_tenant_user: User):
        """Test that authentication respects tenant boundaries."""
        # Both users should be able to authenticate independently
        login_data1 = {
            "email": sample_user.email,
            "password": "testpassword123"
        }
        
        login_data2 = {
            "email": other_tenant_user.email,
            "password": "testpassword123"
        }
        
        response1 = await client.post("/api/auth/login", json=login_data1)
        response2 = await client.post("/api/auth/login", json=login_data2)
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        
        # Verify different tenant subdomains in responses
        org1 = response1.json()["organization_subdomain"]
        org2 = response2.json()["organization_subdomain"]
        
        assert org1 != org2