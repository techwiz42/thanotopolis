"""
Tests for the database module.
Tests critical database functionality including connection management, session creation,
async context managers, and database initialization.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from contextlib import asynccontextmanager
import asyncio

from app.db.database import (
    get_db,
    get_db_context,
    init_db,
    check_db_connection,
    engine,
    AsyncSessionLocal
)


class TestDatabaseConfiguration:
    """Test database configuration and engine setup."""
    
    def test_engine_configuration(self):
        """Test that database engine is properly configured."""
        assert engine is not None
        assert engine.pool.size() == 50
        assert engine.pool._max_overflow == 100
        assert engine.pool._timeout == 30
        assert engine.pool._recycle == 3600
        assert engine.pool._pre_ping is True
    
    def test_async_session_local_configuration(self):
        """Test AsyncSessionLocal configuration."""
        assert AsyncSessionLocal is not None
        session_factory = AsyncSessionLocal
        
        # Check session factory configuration - modern async_sessionmaker uses different attributes
        # Check that the bind is the engine through the session_factory.kw
        kw = getattr(session_factory, 'kw', getattr(session_factory, '_class_kw', {}))
        assert kw.get('bind') is engine or getattr(session_factory, '_bind', None) is engine
        assert kw['autoflush'] is False
        assert kw['autocommit'] is False
        assert kw['expire_on_commit'] is False


class TestGetDbDependency:
    """Test the get_db dependency function."""
    
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test that get_db yields a valid AsyncSession."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            # Create mock session
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            # Test the generator
            db_generator = get_db()
            session = await db_generator.__anext__()
            
            assert session == mock_session
            
            # Test cleanup
            try:
                await db_generator.__anext__()
            except StopAsyncIteration:
                pass  # Expected when generator finishes
    
    @pytest.mark.asyncio
    async def test_get_db_closes_session_on_completion(self):
        """Test that get_db properly closes the session."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_session_local.return_value = mock_context_manager
            
            # Use the generator completely
            generator = get_db()
            session = await generator.__anext__()
            assert session == mock_session
            
            try:
                await generator.__anext__()
            except StopAsyncIteration:
                pass  # Expected when generator finishes
            
            # Verify session context manager was used properly
            mock_context_manager.__aenter__.assert_called_once()
            mock_context_manager.__aexit__.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_db_handles_exceptions(self):
        """Test that get_db handles exceptions and still closes session."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_session_local.return_value = mock_context_manager
            
            # Simulate an exception during session use
            generator = get_db()
            try:
                session = await generator.__anext__()
                raise RuntimeError("Test exception")
            except RuntimeError:
                pass
            finally:
                # Close the generator
                try:
                    await generator.__anext__()
                except StopAsyncIteration:
                    pass
            
            # Verify cleanup still happened
            mock_context_manager.__aenter__.assert_called_once()
            mock_context_manager.__aexit__.assert_called_once()


class TestGetDbContext:
    """Test the get_db_context async context manager."""
    
    @pytest.mark.asyncio
    async def test_get_db_context_returns_session(self):
        """Test that get_db_context returns a valid session."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_session_local.return_value = mock_context_manager
            
            async with get_db_context() as session:
                assert session == mock_session
            
            # Verify session was properly managed
            mock_context_manager.__aenter__.assert_called_once()
            mock_context_manager.__aexit__.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_db_context_closes_on_exception(self):
        """Test that get_db_context closes session even on exception."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_session_local.return_value = mock_context_manager
            
            try:
                async with get_db_context() as session:
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # Verify cleanup happened despite exception
            mock_context_manager.__aenter__.assert_called_once()
            mock_context_manager.__aexit__.assert_called_once()


class TestInitDb:
    """Test database initialization functionality."""
    
    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self):
        """Test that init_db creates all tables."""
        with patch('app.db.database.engine') as mock_engine:
            mock_connection = AsyncMock()
            mock_engine.begin.return_value.__aenter__.return_value = mock_connection
            mock_engine.begin.return_value.__aexit__.return_value = None
            
            # Mock Base.metadata.create_all
            with patch('app.db.database.Base') as mock_base:
                mock_metadata = Mock()
                mock_base.metadata = mock_metadata
                
                await init_db()
                
                # Verify that create_all was called
                mock_connection.run_sync.assert_called_once_with(mock_metadata.create_all)
    
    @pytest.mark.asyncio
    async def test_init_db_handles_connection_error(self):
        """Test that init_db handles connection errors gracefully."""
        with patch('app.db.database.engine') as mock_engine:
            mock_engine.begin.side_effect = OperationalError("Connection failed", None, None)
            
            with pytest.raises(OperationalError):
                await init_db()
    
    @pytest.mark.asyncio
    async def test_init_db_transaction_management(self):
        """Test that init_db properly manages transactions."""
        with patch('app.db.database.engine') as mock_engine:
            mock_connection = AsyncMock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_connection
            mock_context_manager.__aexit__.return_value = None
            mock_engine.begin.return_value = mock_context_manager
            
            with patch('app.db.database.Base') as mock_base:
                mock_base.metadata.create_all = Mock()
                
                await init_db()
                
                # Verify transaction context was used
                mock_engine.begin.assert_called_once()
                mock_context_manager.__aenter__.assert_called_once()
                mock_context_manager.__aexit__.assert_called_once()


class TestCheckDbConnection:
    """Test database connection checking functionality."""
    
    @pytest.mark.asyncio
    async def test_check_db_connection_success(self):
        """Test successful database connection check."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_session_local.return_value = mock_context_manager
            
            # Mock successful query execution
            mock_session.execute = AsyncMock()
            
            result = await check_db_connection()
            
            assert result is True
            mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_db_connection_failure(self):
        """Test database connection check failure."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_session_local.return_value = mock_context_manager
            
            # Mock failed query execution
            mock_session.execute = AsyncMock(side_effect=OperationalError("Connection failed", None, None))
            
            with patch('builtins.print') as mock_print:
                result = await check_db_connection()
                
                assert result is False
                mock_print.assert_called_once()
                assert "Database connection check failed" in mock_print.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_check_db_connection_various_exceptions(self):
        """Test database connection check with various exception types."""
        exceptions_to_test = [
            OperationalError("DB not available", None, None),
            SQLAlchemyError("General SQLAlchemy error"),
            ConnectionError("Network error"),
            Exception("Generic error")
        ]
        
        for exception in exceptions_to_test:
            with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__.return_value = mock_session
                mock_context_manager.__aexit__.return_value = None
                mock_session_local.return_value = mock_context_manager
                
                mock_session.execute = AsyncMock(side_effect=exception)
                
                with patch('builtins.print'):
                    result = await check_db_connection()
                    assert result is False
    
    @pytest.mark.asyncio
    async def test_check_db_connection_sql_query(self):
        """Test that check_db_connection executes the correct SQL query."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_session_local.return_value = mock_context_manager
            
            mock_session.execute = AsyncMock()
            
            await check_db_connection()
            
            # Verify the SQL query was correct
            call_args = mock_session.execute.call_args[0][0]
            # The query should be "SELECT 1"
            assert str(call_args).strip() == "SELECT 1"


class TestDatabaseUrlConfiguration:
    """Test database URL configuration logic."""
    
    @pytest.mark.skip(reason="Database integration test - depends on real environment")
    @patch.dict('os.environ', {}, clear=True)
    @patch('app.db.database.settings')
    def test_database_url_from_settings(self, mock_settings):
        """Test DATABASE_URL is taken from settings when available."""
        mock_settings.DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test"
        
        # Re-import to trigger URL configuration
        from importlib import reload
        import app.db.database as db_module
        reload(db_module)
        
        assert db_module.DATABASE_URL == "postgresql+asyncpg://test:test@localhost/test"
    
    @pytest.mark.skip(reason="Database integration test - depends on real environment")
    @patch.dict('os.environ', {'DATABASE_URL': 'postgresql+asyncpg://env:env@localhost/env'})
    @patch('app.db.database.settings')
    def test_database_url_from_environment(self, mock_settings):
        """Test DATABASE_URL falls back to environment variable."""
        # Simulate settings without DATABASE_URL attribute
        delattr(mock_settings, 'DATABASE_URL') if hasattr(mock_settings, 'DATABASE_URL') else None
        
        from importlib import reload
        import app.db.database as db_module
        reload(db_module)
        
        assert db_module.DATABASE_URL == "postgresql+asyncpg://env:env@localhost/env"
    
    @pytest.mark.skip(reason="Database integration test - depends on real environment")
    @patch.dict('os.environ', {}, clear=True)
    @patch('app.db.database.settings')
    def test_database_url_default_fallback(self, mock_settings):
        """Test DATABASE_URL uses default when neither settings nor env available."""
        # Simulate settings without DATABASE_URL attribute
        delattr(mock_settings, 'DATABASE_URL') if hasattr(mock_settings, 'DATABASE_URL') else None
        
        from importlib import reload
        import app.db.database as db_module
        reload(db_module)
        
        expected_default = "postgresql+asyncpg://user:password@localhost/thanotopolis"
        assert db_module.DATABASE_URL == expected_default


class TestConnectionPooling:
    """Test connection pooling configuration and behavior."""
    
    @pytest.mark.skip(reason="Database integration test - tests internal pool attributes")
    def test_pool_configuration_for_scale(self):
        """Test that connection pool is configured for 100+ concurrent users."""
        # Engine should be configured for high concurrency
        assert engine.pool_size == 50  # Base pool
        assert engine.pool._max_overflow == 100  # Additional connections
        
        # Total possible connections: pool_size + max_overflow = 150
        max_connections = engine.pool_size + engine.pool._max_overflow
        assert max_connections >= 100  # Should handle 100+ users
    
    def test_pool_timeout_configuration(self):
        """Test connection pool timeout configuration."""
        assert engine.pool._timeout == 30  # 30 second timeout
        assert engine.pool._recycle == 3600  # 1 hour recycle time
        assert engine.pool._pre_ping is True  # Connection validation enabled


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple database functions."""
    
    @pytest.mark.asyncio
    async def test_session_lifecycle_workflow(self):
        """Test complete session lifecycle from creation to cleanup."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_session_local.return_value = mock_context_manager
            
            # Test both dependency and context manager
            generator = get_db()
            session1 = await generator.__anext__()
            assert session1 == mock_session
            try:
                await generator.__anext__()
            except StopAsyncIteration:
                pass
            
            async with get_db_context() as session2:
                assert session2 == mock_session
            
            # Both should have used the session properly
            assert mock_context_manager.__aenter__.call_count == 2
            assert mock_context_manager.__aexit__.call_count == 2
    
    @pytest.mark.asyncio
    async def test_database_initialization_and_health_check(self):
        """Test database initialization followed by health check."""
        with patch('app.db.database.engine') as mock_engine:
            with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
                # Setup init_db mocks
                mock_connection = AsyncMock()
                mock_init_context = AsyncMock()
                mock_init_context.__aenter__.return_value = mock_connection
                mock_init_context.__aexit__.return_value = None
                mock_engine.begin.return_value = mock_init_context
                
                # Setup check_db_connection mocks
                mock_session = AsyncMock()
                mock_check_context = AsyncMock()
                mock_check_context.__aenter__.return_value = mock_session
                mock_check_context.__aexit__.return_value = None
                mock_session_local.return_value = mock_check_context
                mock_session.execute = AsyncMock()
                
                with patch('app.db.database.Base') as mock_base:
                    mock_base.metadata.create_all = Mock()
                    
                    # Test the workflow
                    await init_db()
                    health_check_result = await check_db_connection()
                    
                    assert health_check_result is True
                    mock_connection.run_sync.assert_called_once()
                    mock_session.execute.assert_called_once()


class TestErrorRecovery:
    """Test error recovery and resilience scenarios."""
    
    @pytest.mark.asyncio
    async def test_session_recovery_after_connection_loss(self):
        """Test that new sessions can be created after connection loss."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            # First call fails
            mock_session_local.side_effect = [
                OperationalError("Connection lost", None, None),
                AsyncMock()  # Second call succeeds
            ]
            
            # First attempt should fail
            with pytest.raises(OperationalError):
                async for session in get_db():
                    pass
            
            # Second attempt should succeed
            mock_session_local.side_effect = None
            mock_session = AsyncMock()
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_session_local.return_value = mock_context
            
            async for session in get_db():
                assert session == mock_session
                break
    
    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self):
        """Test handling of multiple concurrent sessions."""
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            sessions = []
            contexts = []
            
            # Create multiple mock sessions
            for i in range(5):
                mock_session = AsyncMock(spec=AsyncSession)
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value = mock_session
                mock_context.__aexit__.return_value = None
                sessions.append(mock_session)
                contexts.append(mock_context)
            
            mock_session_local.side_effect = contexts
            
            # Test concurrent access
            async def use_session(session_id):
                async with get_db_context() as session:
                    return session
            
            # Simulate concurrent usage
            results = await asyncio.gather(*[use_session(i) for i in range(5)])
            
            assert len(results) == 5
            assert all(result in sessions for result in results)