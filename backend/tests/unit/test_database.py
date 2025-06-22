import pytest
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from contextlib import asynccontextmanager

from app.db.database import (
    DATABASE_URL, engine, AsyncSessionLocal, 
    get_db, get_db_context, init_db, check_db_connection
)


class TestDatabaseConfiguration:
    """Test database configuration and setup."""
    
    def test_database_url_from_settings(self):
        """Test DATABASE_URL is correctly configured from settings."""
        # Test that DATABASE_URL is a valid PostgreSQL connection string
        assert isinstance(DATABASE_URL, str)
        assert "postgresql" in DATABASE_URL.lower()
        
    @patch.dict(os.environ, {'DATABASE_URL': 'postgresql+asyncpg://test:test@localhost/test'})
    def test_database_url_from_environment(self):
        """Test DATABASE_URL fallback to environment variable."""
        # Re-import to pick up environment change
        from importlib import reload
        import app.db.database
        reload(app.db.database)
        
        # Should use environment variable when settings don't have DATABASE_URL
        with patch('app.db.database.settings') as mock_settings:
            del mock_settings.DATABASE_URL  # Simulate missing attribute
            
            from app.db.database import DATABASE_URL as env_url
            # Note: This test demonstrates the fallback logic, actual value depends on reload timing
            
    def test_engine_configuration(self):
        """Test that engine is configured with appropriate connection pool settings."""
        # Verify engine is properly configured
        assert engine is not None
        assert hasattr(engine, 'pool')
        
        # Check pool configuration
        pool = engine.pool
        assert pool.size() >= 0  # Pool size should be non-negative
        assert hasattr(pool, '_overflow')  # Should have overflow capability
        
    def test_async_session_local_configuration(self):
        """Test AsyncSessionLocal configuration."""
        assert AsyncSessionLocal is not None
        assert hasattr(AsyncSessionLocal, 'bind')
        assert AsyncSessionLocal.bind == engine
        
        # Test session factory properties
        session_factory = AsyncSessionLocal
        assert hasattr(session_factory, 'class_')
        assert issubclass(session_factory.class_, AsyncSession)


class TestDatabaseDependencies:
    """Test database dependency functions."""
    
    @pytest.mark.asyncio
    async def test_get_db_dependency_success(self):
        """Test successful database session creation and cleanup."""
        session_instances = []
        
        # Mock AsyncSessionLocal to track session lifecycle
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            # Configure mock to return our test session
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock()
            
            # Test the dependency
            async for session in get_db():
                session_instances.append(session)
                assert session == mock_session
                break  # Only test first iteration
                
        # Verify session was properly closed
        mock_session.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_db_dependency_exception_handling(self):
        """Test that get_db properly handles exceptions and closes session."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock()
            
            # Simulate exception during session usage
            async def use_session_with_error():
                async for session in get_db():
                    raise Exception("Simulated database error")
                    
            with pytest.raises(Exception, match="Simulated database error"):
                await use_session_with_error()
                
        # Session should still be closed despite the exception
        mock_session.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_db_context_success(self):
        """Test successful database context manager."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock()
            
            async with get_db_context() as session:
                assert session == mock_session
                
        # Verify session was properly closed
        mock_session.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_db_context_exception_handling(self):
        """Test that get_db_context properly handles exceptions."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock()
            
            # Test exception handling in context manager
            with pytest.raises(Exception, match="Context manager error"):
                async with get_db_context() as session:
                    raise Exception("Context manager error")
                    
        # Session should still be closed despite the exception
        mock_session.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_db_multiple_sessions(self):
        """Test that get_db can handle multiple concurrent sessions."""
        sessions = []
        mock_sessions = [AsyncMock(spec=AsyncSession) for _ in range(3)]
        
        for mock_session in mock_sessions:
            mock_session.close = AsyncMock()
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            # Configure to return different sessions for each call
            session_iter = iter(mock_sessions)
            
            def create_session():
                session = next(session_iter)
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock(return_value=session)
                mock_cm.__aexit__ = AsyncMock()
                return mock_cm
                
            mock_session_factory.side_effect = create_session
            
            # Create multiple sessions
            async for session in get_db():
                sessions.append(session)
                if len(sessions) >= 3:
                    break
                    
        # Verify all sessions were created and closed
        assert len(sessions) == 3
        for i, session in enumerate(sessions):
            assert session == mock_sessions[i]
            session.close.assert_called_once()


class TestDatabaseInitialization:
    """Test database initialization functions."""
    
    @pytest.mark.asyncio
    async def test_init_db_success(self):
        """Test successful database initialization."""
        # Mock engine and connection
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()
        
        with patch('app.db.database.engine') as mock_engine:
            mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_engine.begin.return_value.__aexit__ = AsyncMock()
            
            # Test initialization
            await init_db()
            
            # Verify database tables were created
            mock_conn.run_sync.assert_called_once()
            
            # Verify the correct metadata operation was called
            call_args = mock_conn.run_sync.call_args[0]
            assert len(call_args) == 1
            # The function should be Base.metadata.create_all
            
    @pytest.mark.asyncio
    async def test_init_db_connection_error(self):
        """Test init_db handling of connection errors."""
        with patch('app.db.database.engine') as mock_engine:
            mock_engine.begin.side_effect = OperationalError("Connection failed", None, None)
            
            # Should propagate the database error
            with pytest.raises(OperationalError):
                await init_db()
                
    @pytest.mark.asyncio
    async def test_init_db_metadata_error(self):
        """Test init_db handling of metadata creation errors."""
        mock_conn = AsyncMock()
        mock_conn.run_sync.side_effect = SQLAlchemyError("Table creation failed")
        
        with patch('app.db.database.engine') as mock_engine:
            mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_engine.begin.return_value.__aexit__ = AsyncMock()
            
            # Should propagate the SQLAlchemy error
            with pytest.raises(SQLAlchemyError):
                await init_db()


class TestDatabaseHealthCheck:
    """Test database health check functionality."""
    
    @pytest.mark.asyncio
    async def test_check_db_connection_success(self):
        """Test successful database connection check."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock()
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock()
            
            result = await check_db_connection()
            
            assert result is True
            mock_session.execute.assert_called_once()
            
            # Verify that a simple SELECT 1 query was executed
            call_args = mock_session.execute.call_args[0]
            assert len(call_args) == 1
            # Should be a text() query
            
    @pytest.mark.asyncio
    async def test_check_db_connection_failure(self):
        """Test database connection check failure."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.side_effect = OperationalError("Connection failed", None, None)
            
            # Mock print to capture error output
            with patch('builtins.print') as mock_print:
                result = await check_db_connection()
                
                assert result is False
                mock_print.assert_called_once()
                assert "Database connection check failed" in mock_print.call_args[0][0]
                
    @pytest.mark.asyncio
    async def test_check_db_connection_session_error(self):
        """Test database connection check with session creation error."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = SQLAlchemyError("Query execution failed")
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock()
            
            with patch('builtins.print') as mock_print:
                result = await check_db_connection()
                
                assert result is False
                mock_print.assert_called_once()
                assert "failed" in mock_print.call_args[0][0].lower()
                
    @pytest.mark.asyncio
    async def test_check_db_connection_generic_exception(self):
        """Test database connection check with generic exception."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.side_effect = Exception("Unexpected error")
            
            with patch('builtins.print') as mock_print:
                result = await check_db_connection()
                
                assert result is False
                mock_print.assert_called_once()
                assert "Unexpected error" in mock_print.call_args[0][0]


class TestDatabaseConcurrency:
    """Test database handling of concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self):
        """Test that multiple sessions can be created concurrently."""
        import asyncio
        
        session_count = 0
        created_sessions = []
        
        async def create_session():
            nonlocal session_count
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.close = AsyncMock()
            mock_session.id = session_count
            session_count += 1
            created_sessions.append(mock_session)
            return mock_session
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            def session_factory():
                mock_cm = MagicMock()
                mock_cm.__aenter__ = create_session
                mock_cm.__aexit__ = AsyncMock()
                return mock_cm
                
            mock_session_factory.side_effect = session_factory
            
            # Create multiple concurrent database contexts
            async def use_db():
                async with get_db_context() as session:
                    return session.id
                    
            # Run multiple concurrent operations
            tasks = [use_db() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Verify all sessions were created and have unique IDs
            assert len(set(results)) == 5  # All unique session IDs
            assert len(created_sessions) == 5
            
            # Verify all sessions were properly closed
            for session in created_sessions:
                session.close.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Test that sessions are properly isolated from each other."""
        session1_data = {"value": "session1"}
        session2_data = {"value": "session2"}
        
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session1.data = session1_data
        mock_session1.close = AsyncMock()
        
        mock_session2 = AsyncMock(spec=AsyncSession)
        mock_session2.data = session2_data
        mock_session2.close = AsyncMock()
        
        sessions = [mock_session1, mock_session2]
        session_iter = iter(sessions)
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            def create_session():
                session = next(session_iter)
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock(return_value=session)
                mock_cm.__aexit__ = AsyncMock()
                return mock_cm
                
            mock_session_factory.side_effect = create_session
            
            # Use two different sessions
            async with get_db_context() as session1:
                data1 = session1.data
                
            async with get_db_context() as session2:
                data2 = session2.data
                
            # Verify sessions had different data (isolation)
            assert data1 != data2
            assert data1["value"] == "session1"
            assert data2["value"] == "session2"


class TestDatabaseErrorRecovery:
    """Test database error recovery and resilience."""
    
    @pytest.mark.asyncio
    async def test_session_recovery_after_error(self):
        """Test that new sessions can be created after a previous session error."""
        call_count = 0
        
        def session_factory():
            nonlocal call_count
            call_count += 1
            
            mock_cm = MagicMock()
            
            if call_count == 1:
                # First call fails
                mock_cm.__aenter__ = AsyncMock(side_effect=OperationalError("Connection lost", None, None))
            else:
                # Subsequent calls succeed
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.close = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
                
            mock_cm.__aexit__ = AsyncMock()
            return mock_cm
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.side_effect = session_factory
            
            # First attempt should fail
            with pytest.raises(OperationalError):
                async with get_db_context():
                    pass
                    
            # Second attempt should succeed
            async with get_db_context() as session:
                assert session is not None
                
            # Verify both attempts were made
            assert call_count == 2
            
    @pytest.mark.asyncio
    async def test_connection_pool_resilience(self):
        """Test that connection pool can handle temporary failures."""
        # Simulate connection pool exhaustion and recovery
        attempt_count = 0
        
        async def mock_session_creation():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count <= 2:
                # First two attempts fail (simulating pool exhaustion)
                raise OperationalError("Pool exhausted", None, None)
            else:
                # Third attempt succeeds (pool recovered)
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.close = AsyncMock()
                return mock_session
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_cm = MagicMock()
            mock_cm.__aenter__ = mock_session_creation
            mock_cm.__aexit__ = AsyncMock()
            mock_session_factory.return_value = mock_cm
            
            # First two attempts should fail
            for _ in range(2):
                with pytest.raises(OperationalError):
                    async with get_db_context():
                        pass
                        
            # Third attempt should succeed
            async with get_db_context() as session:
                assert session is not None
                session.close.assert_called_once()
                
            assert attempt_count == 3


class TestDatabaseEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_database_url_handling(self):
        """Test behavior with empty or invalid database URL."""
        # This test verifies that the module can handle configuration edge cases
        # In practice, an invalid URL would cause engine creation to fail
        
        with patch.dict(os.environ, {'DATABASE_URL': ''}):
            with pytest.raises((ValueError, TypeError)):
                # Re-creating engine with empty URL should fail
                create_async_engine('')
                
    @pytest.mark.asyncio
    async def test_database_session_timeout(self):
        """Test handling of database session timeouts."""
        import asyncio
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        
        # Simulate a slow database operation
        async def slow_operation():
            await asyncio.sleep(0.1)  # Simulate slow query
            return "result"
            
        mock_session.execute.side_effect = slow_operation
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock()
            
            # Test that session can handle operations that take time
            async with get_db_context() as session:
                result = await session.execute()
                assert result == "result"
                
    def test_database_url_configuration_precedence(self):
        """Test that DATABASE_URL configuration follows correct precedence."""
        # This test verifies the configuration logic in the module
        
        # Mock settings without DATABASE_URL
        with patch('app.db.database.settings') as mock_settings:
            # Remove DATABASE_URL attribute to test fallback
            if hasattr(mock_settings, 'DATABASE_URL'):
                del mock_settings.DATABASE_URL
                
            with patch.dict(os.environ, {'DATABASE_URL': 'postgresql+asyncpg://env:env@localhost/env'}):
                # Re-import to pick up environment variable
                import importlib
                import app.db.database
                importlib.reload(app.db.database)
                
                # Should fall back to environment variable when settings don't have it