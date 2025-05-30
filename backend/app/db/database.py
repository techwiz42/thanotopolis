# backend/app/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator

from app.core.config import settings
from app.models.models import Base

# Use settings from config or fallback to environment variable
DATABASE_URL = settings.DATABASE_URL if hasattr(settings, 'DATABASE_URL') else os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://user:password@localhost/thanotopolis"
)

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Create all tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def check_db_connection():
    """Check if database connection is working."""
    try:
        # Try to execute a simple query
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection check failed: {e}")
        return False
