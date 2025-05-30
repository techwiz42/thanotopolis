# backend/tests/unit/test_user_management.py
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import User, Tenant

class TestUserManagement:
    """Test suite for user management endpoints."""
    
    async def test_list_users_as_admin(self, client: AsyncClient, admin_auth_headers: dict, test_tenant: Tenant, db_session: AsyncSession):
        """Test listing users as admin."""
        # Create additional users one by one to avoid bulk insert issues
        users = []
        for i in range(3):
            user = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                hashed_password="hashed",
                tenant_id=test_tenant.id
            )
            db_session.add(user)
            await db_session.flush()  # Flush to get the ID
            users.append(user)
        
        await db_session.commit()
        
        response = await client.get(
            "/api/users",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 4  # 3 created + admin user
        
        # Verify all users belong to same tenant
        for user in data:
            assert user["tenant_id"] == str(test_tenant.id)
    
    async def test_list_users_as_regular_user(self, client: AsyncClient, auth_headers: dict):
        """Test that regular users cannot list all users."""
        response = await client.get(
            "/api/users",
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]
    
    async def test_list_users_pagination(self, client: AsyncClient, admin_auth_headers: dict):
        """Test user list pagination."""
        response = await client.get(
            "/api/users?skip=0&limit=2",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2
    
    async def test_get_user_own_profile(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """Test users can view their own profile."""
        response = await client.get(
            f"/api/users/{test_user.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
    
    async def test_get_other_user_as_admin(self, client: AsyncClient, admin_auth_headers: dict, test_user: User):
        """Test admin can view other users."""
        response = await client.get(
            f"/api/users/{test_user.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
    
    async def test_get_other_user_as_regular_user(self, client: AsyncClient, auth_headers: dict, admin_user: User):
        """Test regular user cannot view other users."""
        response = await client.get(
            f"/api/users/{admin_user.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]
    
    async def test_get_user_different_tenant(self, client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession):
        """Test admin cannot view users from different tenant."""
        # Create another tenant and user
        other_tenant = Tenant(name="Other Company", subdomain="other")
        db_session.add(other_tenant)
        await db_session.commit()
        await db_session.refresh(other_tenant)
        
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password="hashed",
            tenant_id=other_tenant.id
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)
        
        response = await client.get(
            f"/api/users/{other_user.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    async def test_update_user_role_as_super_admin(self, client: AsyncClient, super_admin_auth_headers: dict, test_user: User):
        """Test super admin can update user roles."""
        response = await client.patch(
            f"/api/users/{test_user.id}/role",
            headers=super_admin_auth_headers,
            params={"role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
    
    async def test_update_user_role_as_admin(self, client: AsyncClient, admin_auth_headers: dict, super_admin_user: User):
        """Test regular admin cannot update super admin's role."""
        response = await client.patch(
            f"/api/users/{super_admin_user.id}/role",
            headers=admin_auth_headers,
            params={"role": "user"}
        )
        
        assert response.status_code == 403
        assert "Super admin access required" in response.json()["detail"]
    
    async def test_update_user_role_invalid(self, client: AsyncClient, super_admin_auth_headers: dict, test_user: User):
        """Test updating user with invalid role."""
        response = await client.patch(
            f"/api/users/{test_user.id}/role",
            headers=super_admin_auth_headers,
            params={"role": "invalid_role"}
        )
        
        assert response.status_code == 400
        assert "Invalid role" in response.json()["detail"]
    
    async def test_delete_user_as_admin(self, client: AsyncClient, admin_auth_headers: dict, test_user: User, db_session: AsyncSession):
        """Test admin can delete regular users."""
        user_id = test_user.id
        
        response = await client.delete(
            f"/api/users/{user_id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify user is deleted
        result = await db_session.execute(
            select(User).filter(User.id == user_id)
        )
        deleted_user = result.scalars().first()
        assert deleted_user is None
    
    async def test_delete_self(self, client: AsyncClient, admin_user: User, admin_auth_headers: dict):
        """Test users cannot delete themselves."""
        response = await client.delete(
            f"/api/users/{admin_user.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]
    
    async def test_delete_super_admin_as_admin(self, client: AsyncClient, admin_auth_headers: dict, super_admin_user: User):
        """Test regular admin cannot delete super admin."""
        response = await client.delete(
            f"/api/users/{super_admin_user.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 403
        assert "Cannot delete super admin" in response.json()["detail"]
    
    async def test_delete_user_as_regular_user(self, client: AsyncClient, auth_headers: dict, admin_user: User):
        """Test regular user cannot delete others."""
        response = await client.delete(
            f"/api/users/{admin_user.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]
