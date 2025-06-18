# Integration test fixtures that use real database
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.models import Base, User, Tenant, RefreshToken
from app.db.database import get_db
from app.auth.auth import AuthService

# Test database URL (using actual PostgreSQL for integration tests)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_thanotopolis"

# Test engine and session
test_engine = None
TestSessionLocal = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def setup_test_db():
    """Set up test database engine and create tables."""
    global test_engine, TestSessionLocal
    
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    
    TestSessionLocal = async_sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield test_engine
    
    # Clean up
    await test_engine.dispose()


@pytest.fixture
async def db_session(setup_test_db):
    """Create a database session for testing."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


async def override_get_db():
    """Override the get_db dependency for testing."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
async def client(setup_test_db):
    """Create an HTTP client with test database."""
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_tenant(db_session: AsyncSession):
    """Create a real tenant in the test database."""
    tenant = Tenant(
        name="Sample Organization",
        subdomain="sampleorg",
        is_active=True
    )
    
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    
    return tenant


@pytest.fixture
async def sample_user(db_session: AsyncSession, sample_tenant: Tenant):
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


@pytest.fixture
async def inactive_user(db_session: AsyncSession, sample_tenant: Tenant):
    """Create an inactive user in the test database."""
    hashed_password = AuthService.get_password_hash("testpassword123")
    
    user = User(
        email="inactive@example.com",
        username="inactiveuser",
        hashed_password=hashed_password,
        first_name="Inactive",
        last_name="User",
        role="user",
        is_active=False,  # Inactive
        is_verified=True,
        tenant_id=sample_tenant.id
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession, sample_tenant: Tenant):
    """Create an admin user in the test database."""
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


@pytest.fixture
async def other_tenant(db_session: AsyncSession):
    """Create another tenant for testing isolation."""
    tenant = Tenant(
        name="Other Organization",
        subdomain="otherorg",
        is_active=True
    )
    
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    
    return tenant


@pytest.fixture
async def other_tenant_user(db_session: AsyncSession, other_tenant: Tenant):
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


@pytest.fixture
async def auth_headers(client: AsyncClient, sample_user: User):
    """Create authentication headers for testing."""
    # Login to get real token
    login_data = {
        "email": sample_user.email,
        "password": "testpassword123"
    }
    
    response = await client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200
    
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}