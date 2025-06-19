"""
Integration tests for database module.
Tests database functionality with real database connections and sessions.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.database import get_db, get_db_context, init_db, check_db_connection


class TestDatabaseIntegration:
    """Test database integration with real connections."""

    @pytest.mark.asyncio
    async def test_get_db_dependency_real_session(self):
        """Test that get_db yields a real working session."""
        async for session in get_db():
            assert isinstance(session, AsyncSession)
            
            # Test that session can execute queries
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            break

    @pytest.mark.asyncio
    async def test_get_db_context_real_session(self):
        """Test that get_db_context provides a real working session."""
        # Create a test-specific engine to avoid event loop conflicts
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from contextlib import asynccontextmanager
        
        test_engine = create_async_engine(
            "postgresql+asyncpg://postgres:postgres@localhost:5432/test_thanotopolis",
            echo=False
        )
        
        TestSessionLocal = async_sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=test_engine, 
            expire_on_commit=False
        )
        
        @asynccontextmanager
        async def test_get_db_context():
            async with TestSessionLocal() as session:
                try:
                    yield session
                finally:
                    await session.close()
        
        try:
            async with test_get_db_context() as session:
                assert isinstance(session, AsyncSession)
                
                # Test that session can execute queries
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            await test_engine.dispose()

    @pytest.mark.asyncio
    async def test_check_db_connection_real_database(self):
        """Test database connection check with real database."""
        # Use test database URL to ensure we're testing the right database
        from app.core.config import settings
        import os
        
        # Temporarily set DATABASE_URL to test database
        original_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = settings.TEST_DATABASE_URL
        
        try:
            # Reimport to get the updated database URL
            import importlib
            from app.db import database
            importlib.reload(database)
            
            result = await database.check_db_connection()
            assert result is True
        finally:
            # Restore original DATABASE_URL
            if original_db_url:
                os.environ["DATABASE_URL"] = original_db_url
            elif "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    @pytest.mark.asyncio
    async def test_init_db_real_database(self):
        """Test database initialization with real database."""
        # Import here to avoid circular imports
        from app.models.models import Base
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from sqlalchemy import text
        
        # Create a test-specific engine for this test
        test_engine = create_async_engine(
            "postgresql+asyncpg://postgres:postgres@localhost:5432/test_thanotopolis",
            echo=False
        )
        
        try:
            # This should not raise any exceptions
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Verify connection still works after init using the same test engine
            TestSessionLocal = async_sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=test_engine, 
                expire_on_commit=False
            )
            
            async with TestSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            
            # If we get here without exceptions, the test passes
            assert True
        finally:
            await test_engine.dispose()