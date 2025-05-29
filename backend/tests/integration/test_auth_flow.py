# backend/tests/integration/test_auth_flow.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import User, Tenant, RefreshToken
from app.auth.auth import AuthService

class TestAuthenticationFlow:
    """Integration tests for complete authentication flows."""
    
    async def test_complete_registration_login_flow(self, client: AsyncClient, db_session: AsyncSession):
        """Test complete flow: create tenant -> register -> login -> access protected resource."""
        # Step 1: Create tenant
        tenant_response = await client.post(
            "/api/tenants",
            json={
                "name": "Flow Test Company",
                "subdomain": "flowtest"
            }
        )
        assert tenant_response.status_code == 200
        tenant_data = tenant_response.json()
        
        # Step 2: Register user
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "flowtest@example.com",
                "username": "flowuser",
                "password": "flowpass123",
                "first_name": "Flow",
                "last_name": "Test"
            },
            headers={"X-Tenant-ID": "flowtest"}
        )
        assert register_response.status_code == 200
        user_data = register_response.json()
        
        # Step 3: Login
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "flowtest@example.com",
                "password": "flowpass123",
                "tenant_subdomain": "flowtest"
            }
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        
        # Step 4: Access protected resource
        me_response = await client.get(
            "/api/me",
            headers={
                "Authorization": f"Bearer {tokens['access_token']}",
                "X-Tenant-ID": "flowtest"
            }
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == "flowtest@example.com"
        assert me_data["tenant_id"] == tenant_data["id"]
    
    async def test_token_refresh_flow(self, client: AsyncClient, test_tenant: Tenant, test_user: User):
        """Test complete token refresh flow."""
        # Login to get tokens
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
                "tenant_subdomain": test_tenant.subdomain
            }
        )
        assert login_response.status_code == 200
        initial_tokens = login_response.json()
        
        # Use refresh token to get new access token
        refresh_response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": initial_tokens["refresh_token"]}
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        
        # Verify new tokens are different
        assert new_tokens["access_token"] != initial_tokens["access_token"]
        assert new_tokens["refresh_token"] != initial_tokens["refresh_token"]
        
        # Use new access token
        me_response = await client.get(
            "/api/me",
            headers={
                "Authorization": f"Bearer {new_tokens['access_token']}",
                "X-Tenant-ID": test_tenant.subdomain
            }
        )
        assert me_response.status_code == 200
        
        # Verify old refresh token no longer works
        old_refresh_response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": initial_tokens["refresh_token"]}
        )
        assert old_refresh_response.status_code == 401
    
    async def test_logout_invalidates_tokens(self, client: AsyncClient, test_tenant: Tenant, test_user: User, db_session: AsyncSession):
        """Test that logout properly invalidates all refresh tokens."""
        # Login
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "password123",
                "tenant_subdomain": test_tenant.subdomain
            }
        )
        tokens = login_response.json()
        
        # Verify refresh token exists
        result = await db_session.execute(
            select(RefreshToken).filter(RefreshToken.user_id == test_user.id)
        )
        assert len(result.scalars().all()) > 0
        
        # Logout
        logout_response = await client.post(
            "/api/auth/logout",
            headers={
                "Authorization": f"Bearer {tokens['access_token']}",
                "X-Tenant-ID": test_tenant.subdomain
            }
        )
        assert logout_response.status_code == 200
        
        # Verify refresh tokens are deleted
        result = await db_session.execute(
            select(RefreshToken).filter(RefreshToken.user_id == test_user.id)
        )
        assert len(result.scalars().all()) == 0
        
        # Verify refresh token no longer works
        refresh_response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh_response.status_code == 401


class TestMultiTenantIsolation:
    """Integration tests for multi-tenant isolation."""
    
    async def test_tenant_user_isolation(self, client: AsyncClient, db_session: AsyncSession):
        """Test that users are properly isolated between tenants."""
        # Create two tenants
        tenant1 = Tenant(name="Company A", subdomain="companya")
        tenant2 = Tenant(name="Company B", subdomain="companyb")
        db_session.add_all([tenant1, tenant2])
        await db_session.commit()
        
        # Register same email in both tenants (should work)
        for tenant in [tenant1, tenant2]:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": "shared@example.com",
                    "username": f"user_{tenant.subdomain}",
                    "password": "password123"
                },
                headers={"X-Tenant-ID": tenant.subdomain}
            )
            assert response.status_code == 200
        
        # Login to tenant1
        login1 = await client.post(
            "/api/auth/login",
            json={
                "email": "shared@example.com",
                "password": "password123",
                "tenant_subdomain": tenant1.subdomain
            }
        )
        assert login1.status_code == 200
        tokens1 = login1.json()
        
        # Login to tenant2
        login2 = await client.post(
            "/api/auth/login",
            json={
                "email": "shared@example.com",
                "password": "password123",
                "tenant_subdomain": tenant2.subdomain
            }
        )
        assert login2.status_code == 200
        tokens2 = login2.json()
        
        # Verify tokens access correct tenant data
        me1 = await client.get(
            "/api/me",
            headers={
                "Authorization": f"Bearer {tokens1['access_token']}",
                "X-Tenant-ID": tenant1.subdomain
            }
        )
        me2 = await client.get(
            "/api/me",
            headers={
                "Authorization": f"Bearer {tokens2['access_token']}",
                "X-Tenant-ID": tenant2.subdomain
            }
        )
        
        assert me1.json()["tenant_id"] == tenant1.id
        assert me2.json()["tenant_id"] == tenant2.id
        assert me1.json()["username"] == f"user_{tenant1.subdomain}"
        assert me2.json()["username"] == f"user_{tenant2.subdomain}"
    
    async def test_cross_tenant_access_denied(self, client: AsyncClient, db_session: AsyncSession):
        """Test that users cannot access other tenants' resources."""
        # Create two tenants with admin users
        tenant1 = Tenant(name="Tenant 1", subdomain="tenant1")
        tenant2 = Tenant(name="Tenant 2", subdomain="tenant2")
        db_session.add_all([tenant1, tenant2])
        await db_session.commit()
        
        # Create admin in tenant1
        admin1 = User(
            email="admin1@example.com",
            username="admin1",
            hashed_password=AuthService.get_password_hash("admin123"),
            tenant_id=tenant1.id,
            role="admin",
            is_active=True
        )
        # Create user in tenant2
        user2 = User(
            email="user2@example.com",
            username="user2",
            hashed_password=AuthService.get_password_hash("user123"),
            tenant_id=tenant2.id,
            role="user",
            is_active=True
        )
        db_session.add_all([admin1, user2])
        await db_session.commit()
        
        # Get auth token for tenant1 admin
        token = AuthService.create_access_token({
            "sub": admin1.id,
            "tenant_id": tenant1.id,
            "email": admin1.email,
            "role": admin1.role
        })
        
        # Try to access tenant2 user (should fail)
        response = await client.get(
            f"/api/users/{user2.id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": tenant1.subdomain
            }
        )
        
        assert response.status_code == 404  # User not found (proper isolation)
    
    async def test_tenant_subdomain_uniqueness(self, client: AsyncClient, test_tenant: Tenant):
        """Test that tenant subdomains must be unique."""
        # Try to create tenant with same subdomain
        response = await client.post(
            "/api/tenants",
            json={
                "name": "Different Name",
                "subdomain": test_tenant.subdomain
            }
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
