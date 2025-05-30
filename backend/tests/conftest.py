# backend/tests/conftest.py
import pytest
import asyncio
import asyncpg
import uuid
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
import os
import sys
from unittest.mock import patch, MagicMock

# Set test environment
os.environ["TESTING"] = "1"

from app.main import app
from app.db.database import Base, get_db
from app.models.models import User, Tenant
from app.auth.auth import AuthService
from app.core.config import settings

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_thanotopolis"


async def ensure_test_database_exists():
    """Ensure the test database exists before running tests."""
    db_user = "postgres"
    db_password = "postgres"
    db_host = "localhost"
    db_port = 5432
    test_db_name = "test_thanotopolis"
    
    # Connect to PostgreSQL server
    dsn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/postgres"
    
    try:
        conn = await asyncpg.connect(dsn)
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = $1)",
            test_db_name
        )
        
        if not exists:
            # Create database
            await conn.execute(f'CREATE DATABASE "{test_db_name}"')
            print(f"\nCreated test database '{test_db_name}'")
        
        await conn.close()
        
        # Create extensions in test database
        test_dsn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{test_db_name}"
        conn = await asyncpg.connect(test_dsn)
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        await conn.close()
        
    except Exception as e:
        print(f"\nError setting up test database: {e}")
        print("Make sure PostgreSQL is running and accessible.")
        sys.exit(1)


# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False  # Set to True for debugging SQL queries
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
    class_=AsyncSession
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def setup_test_database():
    """Ensure test database exists before any tests run."""
    await ensure_test_database_exists()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
        await session.close()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database dependency."""
    # Override the get_db dependency to use our test session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create async client with ASGI transport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    
    # Clear dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        name="Test Company",
        subdomain="test"
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=AuthService.get_password_hash("password123"),
        first_name="Test",
        last_name="User",
        tenant_id=test_tenant.id,
        is_active=True,
        is_verified=True,
        role="user"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create an admin user."""
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=AuthService.get_password_hash("admin123"),
        first_name="Admin",
        last_name="User",
        tenant_id=test_tenant.id,
        is_active=True,
        is_verified=True,
        role="admin"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def super_admin_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a super admin user."""
    user = User(
        email="superadmin@example.com",
        username="superadmin",
        hashed_password=AuthService.get_password_hash("super123"),
        first_name="Super",
        last_name="Admin",
        tenant_id=test_tenant.id,
        is_active=True,
        is_verified=True,
        role="super_admin"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(test_user: User, test_tenant: Tenant) -> dict:
    """Create authentication headers for a test user."""
    access_token = AuthService.create_access_token(
        data={
            "sub": str(test_user.id),
            "tenant_id": str(test_tenant.id),
            "email": test_user.email,
            "role": test_user.role
        }
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": test_tenant.subdomain
    }


@pytest.fixture
async def admin_auth_headers(admin_user: User, test_tenant: Tenant) -> dict:
    """Create authentication headers for an admin user."""
    access_token = AuthService.create_access_token(
        data={
            "sub": str(admin_user.id),
            "tenant_id": str(test_tenant.id),
            "email": admin_user.email,
            "role": admin_user.role
        }
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": test_tenant.subdomain
    }


@pytest.fixture
async def super_admin_auth_headers(super_admin_user: User, test_tenant: Tenant) -> dict:
    """Create authentication headers for a super admin user."""
    access_token = AuthService.create_access_token(
        data={
            "sub": str(super_admin_user.id),
            "tenant_id": str(test_tenant.id),
            "email": super_admin_user.email,
            "role": super_admin_user.role
        }
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": test_tenant.subdomain
    }
