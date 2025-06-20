# Simple integration test fixtures that avoid scope issues
# IMPORTANT: These fixtures have priority over mock fixtures in conftest.py
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from uuid import uuid4
from datetime import datetime, timezone
import random
import string

from app.main import app
from app.models import Base, User, Tenant, RefreshToken, Conversation
from app.db.database import get_db
from app.auth.auth import AuthService

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_thanotopolis"


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_db_engine):
    """Create database session."""
    SessionLocal = async_sessionmaker(
        test_db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with SessionLocal() as session:
        yield session
        
        # Clean up all data after each test
        await session.execute(text("TRUNCATE TABLE messages CASCADE"))
        await session.execute(text("TRUNCATE TABLE conversations CASCADE"))
        await session.execute(text("TRUNCATE TABLE refresh_tokens CASCADE"))
        await session.execute(text("TRUNCATE TABLE usage_records CASCADE"))
        await session.execute(text("TRUNCATE TABLE system_metrics CASCADE"))
        await session.execute(text("TRUNCATE TABLE users CASCADE"))
        await session.execute(text("TRUNCATE TABLE agents CASCADE"))
        await session.execute(text("TRUNCATE TABLE tenants CASCADE"))
        await session.commit()


@pytest_asyncio.fixture
async def client(test_db_engine):
    """Create HTTP client with test database."""
    # Create a new sessionmaker for the app
    SessionLocal = async_sessionmaker(
        test_db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    # Override database dependency to use our test database
    async def override_get_db():
        async with SessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(name="sample_tenant")
async def db_sample_tenant(db_session: AsyncSession):
    """Create a real tenant in the test database."""
    # Generate unique subdomain to avoid conflicts
    random_suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
    
    tenant = Tenant(
        name=f"Sample Organization {random_suffix}",
        subdomain=f"sampleorg{random_suffix}",
        is_active=True
    )
    
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    
    return tenant


@pytest_asyncio.fixture(name="sample_user")
async def db_sample_user(db_session: AsyncSession, sample_tenant: Tenant):
    """Create a real user in the test database."""
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
        tenant_id=sample_tenant.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture(name="inactive_user")
async def db_inactive_user(db_session: AsyncSession, sample_tenant: Tenant):
    """Create an inactive user."""
    hashed_password = AuthService.get_password_hash("testpassword123")
    
    user = User(
        email="inactive@example.com",
        username="inactiveuser",
        hashed_password=hashed_password,
        first_name="Inactive",
        last_name="User",
        role="user",
        is_active=False,
        is_verified=True,
        tenant_id=sample_tenant.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture(name="admin_user")
async def db_admin_user(db_session: AsyncSession, sample_tenant: Tenant):
    """Create an admin user."""
    hashed_password = AuthService.get_password_hash("testpassword123")
    
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=hashed_password,
        first_name="Admin",
        last_name="User",
        role="admin",
        is_active=True,
        is_verified=True,
        tenant_id=sample_tenant.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture(name="other_tenant")
async def db_other_tenant(db_session: AsyncSession):
    """Create another tenant."""
    # Generate unique subdomain to avoid conflicts
    random_suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
    
    tenant = Tenant(
        name=f"Other Organization {random_suffix}",
        subdomain=f"otherorg{random_suffix}",
        is_active=True
    )
    
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    
    return tenant


@pytest_asyncio.fixture(name="other_tenant_user")
async def db_other_tenant_user(db_session: AsyncSession, other_tenant: Tenant):
    """Create a user from another tenant."""
    hashed_password = AuthService.get_password_hash("testpassword123")
    
    user = User(
        email="othertenant@example.com",
        username="othertenantuser",
        hashed_password=hashed_password,
        first_name="OtherTenant",
        last_name="User",
        role="user",
        is_active=True,
        is_verified=True,
        tenant_id=other_tenant.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture(name="auth_headers")
async def db_auth_headers(sample_user: User, db_session: AsyncSession):
    """Create authentication headers with real JWT token."""
    # Create access token for the user with all required fields
    access_token = AuthService.create_access_token(
        data={
            "sub": str(sample_user.id),
            "tenant_id": str(sample_user.tenant_id),
            "email": sample_user.email,
            "role": sample_user.role
        }
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture(name="other_user")
async def db_other_user(db_session: AsyncSession, sample_tenant: Tenant):
    """Create another user in the same tenant."""
    hashed_password = AuthService.get_password_hash("testpassword123")
    
    user = User(
        email="other@example.com",
        username="otheruser",
        hashed_password=hashed_password,
        first_name="Other",
        last_name="User",
        role="user",
        is_active=True,
        is_verified=True,
        tenant_id=sample_tenant.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture(name="authenticated_user")
async def db_authenticated_user(sample_user: User, db_session: AsyncSession):
    """Create authenticated user context with headers."""
    # Create access token for the user with all required fields
    access_token = AuthService.create_access_token(
        data={
            "sub": str(sample_user.id),
            "tenant_id": str(sample_user.tenant_id),
            "email": sample_user.email,
            "role": sample_user.role
        }
    )
    return {
        "user": sample_user,
        "headers": {"Authorization": f"Bearer {access_token}"}
    }


@pytest_asyncio.fixture(name="sample_conversation")
async def db_sample_conversation(db_session: AsyncSession, sample_tenant: Tenant):
    """Create a sample conversation."""
    conversation = Conversation(
        title="Test Conversation",
        tenant_id=sample_tenant.id,
        status="active"
    )
    
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    
    return conversation


@pytest_asyncio.fixture(name="async_client")
async def db_async_client(test_db_engine):
    """Create async HTTP client with test database."""
    # Create a new sessionmaker for the app
    SessionLocal = async_sessionmaker(
        test_db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    # Override database dependency to use our test database
    async def override_get_db():
        async with SessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()