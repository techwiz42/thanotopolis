#!/usr/bin/env python3
"""
Minimal test to verify integration test setup works.
"""
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Set up the integration fixtures
pytest_plugins = ["tests.conftest_integration"]


async def test_basic_integration():
    """Test that we can create basic database records."""
    print("🔧 Testing integration setup...")
    
    # This would normally be handled by pytest fixtures
    from tests.conftest_integration import setup_test_db, TestSessionLocal
    
    try:
        # Setup test database
        await setup_test_db().__anext__()
        
        # Create a session
        async with TestSessionLocal() as session:
            # Import models
            from app.models.models import Tenant, User
            from app.auth.auth import AuthService
            
            # Create a tenant
            tenant = Tenant(
                name="Test Organization",
                subdomain="testorg",
                is_active=True
            )
            
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            
            print(f"✅ Created tenant: {tenant.id} - {tenant.subdomain}")
            
            # Create a user
            hashed_password = AuthService.get_password_hash("testpassword123")
            
            user = User(
                email="test@example.com",
                username="testuser",
                hashed_password=hashed_password,
                first_name="Test",
                last_name="User",
                role="user",
                is_active=True,
                is_verified=True,
                tenant_id=tenant.id
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            print(f"✅ Created user: {user.id} - {user.email}")
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_basic_integration())