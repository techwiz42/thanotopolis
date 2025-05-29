# backend/tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
import os

# Set test environment
os.environ["TESTING"] = "1"

from app.main import app
from app.db.database import Base, get_db
from app.models.models import User, Tenant
from app.auth.auth import AuthService
from app.core.config import settings

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_thanotopolis"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
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
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database dependency."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
    
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
            "sub": test_user.id,
            "tenant_id": test_tenant.id,
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
            "sub": admin_user.id,
            "tenant_id": test_tenant.id,
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
            "sub": super_admin_user.id,
            "tenant_id": test_tenant.id,
            "email": super_admin_user.email,
            "role": super_admin_user.role
        }
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": test_tenant.subdomain
    }
