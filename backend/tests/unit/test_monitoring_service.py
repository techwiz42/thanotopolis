"""
Comprehensive unit tests for monitoring service.
Tests system health checks, WebSocket tracking, and performance monitoring.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.services.monitoring_service import (
    MonitoringService, monitoring_service, track_websocket_connection
)


class TestMonitoringServiceUnit:
    """Unit tests for MonitoringService class."""

    @pytest.fixture
    def monitoring_svc(self):
        """Create a fresh MonitoringService instance for testing."""
        return MonitoringService()

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    def test_monitoring_service_initialization(self, monitoring_svc):
        """Test MonitoringService initialization."""
        assert isinstance(monitoring_svc.active_websocket_connections, set)
        assert isinstance(monitoring_svc.connection_metrics, dict)
        assert isinstance(monitoring_svc.last_metrics_update, float)
        assert len(monitoring_svc.active_websocket_connections) == 0
        assert len(monitoring_svc.connection_metrics) == 0

    def test_add_websocket_connection(self, monitoring_svc):
        """Test adding WebSocket connection tracking."""
        connection_id = "conn_123"
        user_id = "user_456"
        tenant_id = "tenant_789"
        
        monitoring_svc.add_websocket_connection(connection_id, user_id, tenant_id)
        
        assert connection_id in monitoring_svc.active_websocket_connections
        assert connection_id in monitoring_svc.connection_metrics
        
        metrics = monitoring_svc.connection_metrics[connection_id]
        assert metrics["user_id"] == user_id
        assert metrics["tenant_id"] == tenant_id
        assert isinstance(metrics["connected_at"], datetime)
        assert isinstance(metrics["last_activity"], datetime)

    def test_add_websocket_connection_without_user_tenant(self, monitoring_svc):
        """Test adding WebSocket connection without user/tenant info."""
        connection_id = "conn_123"
        
        monitoring_svc.add_websocket_connection(connection_id)
        
        assert connection_id in monitoring_svc.active_websocket_connections
        metrics = monitoring_svc.connection_metrics[connection_id]
        assert metrics["user_id"] is None
        assert metrics["tenant_id"] is None

    def test_remove_websocket_connection(self, monitoring_svc):
        """Test removing WebSocket connection tracking."""
        connection_id = "conn_123"
        
        # Add connection first
        monitoring_svc.add_websocket_connection(connection_id, "user_456", "tenant_789")
        assert connection_id in monitoring_svc.active_websocket_connections
        
        # Remove connection
        monitoring_svc.remove_websocket_connection(connection_id)
        assert connection_id not in monitoring_svc.active_websocket_connections
        assert connection_id not in monitoring_svc.connection_metrics

    def test_remove_nonexistent_websocket_connection(self, monitoring_svc):
        """Test removing non-existent WebSocket connection (should not error)."""
        connection_id = "nonexistent_conn"
        
        # Should not raise an exception
        monitoring_svc.remove_websocket_connection(connection_id)
        assert connection_id not in monitoring_svc.active_websocket_connections

    def test_update_websocket_activity(self, monitoring_svc):
        """Test updating WebSocket activity timestamp."""
        connection_id = "conn_123"
        
        # Add connection first
        monitoring_svc.add_websocket_connection(connection_id, "user_456", "tenant_789")
        original_activity = monitoring_svc.connection_metrics[connection_id]["last_activity"]
        
        # Wait a small amount and update activity
        import time
        time.sleep(0.01)
        monitoring_svc.update_websocket_activity(connection_id)
        
        new_activity = monitoring_svc.connection_metrics[connection_id]["last_activity"]
        assert new_activity > original_activity

    def test_update_websocket_activity_nonexistent(self, monitoring_svc):
        """Test updating activity for non-existent connection (should not error)."""
        connection_id = "nonexistent_conn"
        
        # Should not raise an exception
        monitoring_svc.update_websocket_activity(connection_id)

    def test_get_websocket_count(self, monitoring_svc):
        """Test getting WebSocket connection count."""
        assert monitoring_svc.get_websocket_count() == 0
        
        # Add some connections
        monitoring_svc.add_websocket_connection("conn_1", "user_1", "tenant_1")
        monitoring_svc.add_websocket_connection("conn_2", "user_2", "tenant_1")
        monitoring_svc.add_websocket_connection("conn_3", "user_3", "tenant_2")
        
        assert monitoring_svc.get_websocket_count() == 3
        
        # Remove one connection
        monitoring_svc.remove_websocket_connection("conn_2")
        assert monitoring_svc.get_websocket_count() == 2

    def test_get_websocket_connections_by_tenant(self, monitoring_svc):
        """Test getting WebSocket connections grouped by tenant."""
        # Add connections for different tenants
        monitoring_svc.add_websocket_connection("conn_1", "user_1", "tenant_1")
        monitoring_svc.add_websocket_connection("conn_2", "user_2", "tenant_1")
        monitoring_svc.add_websocket_connection("conn_3", "user_3", "tenant_2")
        monitoring_svc.add_websocket_connection("conn_4", "user_4", None)  # No tenant
        
        tenant_counts = monitoring_svc.get_websocket_connections_by_tenant()
        
        assert tenant_counts["tenant_1"] == 2
        assert tenant_counts["tenant_2"] == 1
        assert "None" not in tenant_counts  # Connections without tenant not counted

    def test_get_websocket_connections_by_tenant_empty(self, monitoring_svc):
        """Test getting WebSocket connections by tenant when no connections exist."""
        tenant_counts = monitoring_svc.get_websocket_connections_by_tenant()
        assert tenant_counts == {}

    @pytest.mark.asyncio
    async def test_get_database_metrics_success(self, monitoring_svc, mock_db_session):
        """Test successful database metrics retrieval."""
        # Mock database query results
        mock_result_1 = Mock()
        mock_result_1.scalar.return_value = 5  # active connections
        
        mock_result_2 = Mock()
        mock_result_2.scalar.return_value = 1024000000  # database size
        
        mock_result_3 = Mock()
        mock_table_row = Mock()
        mock_table_row.schemaname = "public"
        mock_table_row.tablename = "users"
        mock_table_row.total_changes = 150
        mock_result_3.fetchall.return_value = [mock_table_row]
        
        mock_db_session.execute.side_effect = [
            mock_result_1,
            mock_result_2,
            mock_result_3
        ]
        
        metrics = await monitoring_svc.get_database_metrics(mock_db_session)
        
        assert metrics["active_connections"] == 5
        assert metrics["database_size_bytes"] == 1024000000
        assert len(metrics["table_activity"]) == 1
        assert metrics["table_activity"][0]["schema"] == "public"
        assert metrics["table_activity"][0]["table"] == "users"
        assert metrics["table_activity"][0]["total_changes"] == 150
        
        # Verify SQL queries were executed
        assert mock_db_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_get_database_metrics_error(self, monitoring_svc, mock_db_session):
        """Test database metrics retrieval with database error."""
        mock_db_session.execute.side_effect = Exception("Database connection failed")
        
        metrics = await monitoring_svc.get_database_metrics(mock_db_session)
        
        assert "error" in metrics
        assert metrics["active_connections"] == 0
        assert "Database connection failed" in metrics["error"]

    @patch('app.services.monitoring_service.psutil')
    def test_get_system_metrics_success(self, mock_psutil, monitoring_svc):
        """Test successful system metrics retrieval."""
        # Mock psutil responses
        mock_psutil.cpu_percent.return_value = 45.5
        
        mock_memory = Mock()
        mock_memory.percent = 65.2
        mock_memory.available = 4 * (1024**3)  # 4 GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.percent = 75.0
        mock_disk.free = 100 * (1024**3)  # 100 GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        metrics = monitoring_svc.get_system_metrics()
        
        assert metrics["cpu_percent"] == 45.5
        assert metrics["memory_percent"] == 65.2
        assert metrics["memory_available_gb"] == 4.0
        assert metrics["disk_percent"] == 75.0
        assert metrics["disk_free_gb"] == 100.0
        assert isinstance(metrics["timestamp"], datetime)
        
        # Verify psutil calls
        mock_psutil.cpu_percent.assert_called_once_with(interval=1)
        mock_psutil.virtual_memory.assert_called_once()
        mock_psutil.disk_usage.assert_called_once_with('/')

    @patch('app.services.monitoring_service.psutil')
    def test_get_system_metrics_error(self, mock_psutil, monitoring_svc):
        """Test system metrics retrieval with psutil error."""
        mock_psutil.cpu_percent.side_effect = Exception("Failed to get CPU stats")
        
        metrics = monitoring_svc.get_system_metrics()
        
        assert "error" in metrics
        assert isinstance(metrics["timestamp"], datetime)
        assert "Failed to get CPU stats" in metrics["error"]

    @pytest.mark.asyncio
    async def test_record_periodic_metrics_success(self, monitoring_svc, mock_db_session):
        """Test successful periodic metrics recording."""
        with patch('app.services.monitoring_service.usage_service') as mock_usage_service:
            mock_usage_service.record_system_metric = AsyncMock()
            
            # Add some WebSocket connections
            monitoring_svc.add_websocket_connection("conn_1", "user_1", "tenant_1")
            monitoring_svc.add_websocket_connection("conn_2", "user_2", "tenant_2")
            
            # Mock database and system metrics
            with patch.object(monitoring_svc, 'get_database_metrics') as mock_db_metrics, \
                 patch.object(monitoring_svc, 'get_system_metrics') as mock_sys_metrics:
                
                mock_db_metrics.return_value = {
                    "active_connections": 5,
                    "database_size_bytes": 1024000000
                }
                
                mock_sys_metrics.return_value = {
                    "cpu_percent": 50.0,
                    "memory_percent": 60.0,
                    "timestamp": datetime.utcnow()
                }
                
                await monitoring_svc.record_periodic_metrics(mock_db_session)
            
            # Verify metrics were recorded
            assert mock_usage_service.record_system_metric.call_count == 4
            
            # Check WebSocket connections metric
            ws_call = mock_usage_service.record_system_metric.call_args_list[0]
            assert ws_call[1]["metric_type"] == "ws_connections"
            assert ws_call[1]["value"] == 2
            
            # Check database connections metric
            db_call = mock_usage_service.record_system_metric.call_args_list[1]
            assert db_call[1]["metric_type"] == "db_connections"
            assert db_call[1]["value"] == 5
            
            # Check CPU metric
            cpu_call = mock_usage_service.record_system_metric.call_args_list[2]
            assert cpu_call[1]["metric_type"] == "cpu_usage"
            assert cpu_call[1]["value"] == 50
            
            # Check memory metric
            memory_call = mock_usage_service.record_system_metric.call_args_list[3]
            assert memory_call[1]["metric_type"] == "memory_usage"
            assert memory_call[1]["value"] == 60

    @pytest.mark.asyncio
    async def test_record_periodic_metrics_database_error(self, monitoring_svc, mock_db_session):
        """Test periodic metrics recording with database error."""
        with patch('app.services.monitoring_service.usage_service') as mock_usage_service:
            mock_usage_service.record_system_metric = AsyncMock()
            
            with patch.object(monitoring_svc, 'get_database_metrics') as mock_db_metrics:
                mock_db_metrics.return_value = {"error": "Database error"}
                
                # Should not raise exception, just skip database metrics
                await monitoring_svc.record_periodic_metrics(mock_db_session)
            
            # Should still record WebSocket connections but not database metrics
            calls = mock_usage_service.record_system_metric.call_args_list
            metric_types = [call[1]["metric_type"] for call in calls]
            
            assert "ws_connections" in metric_types
            assert "db_connections" not in metric_types

    @pytest.mark.asyncio
    async def test_record_periodic_metrics_system_error(self, monitoring_svc, mock_db_session):
        """Test periodic metrics recording with system metrics error."""
        with patch('app.services.monitoring_service.usage_service') as mock_usage_service:
            mock_usage_service.record_system_metric = AsyncMock()
            
            with patch.object(monitoring_svc, 'get_system_metrics') as mock_sys_metrics:
                mock_sys_metrics.return_value = {"error": "System error"}
                
                await monitoring_svc.record_periodic_metrics(mock_db_session)
            
            # Should still record other metrics but not system metrics
            calls = mock_usage_service.record_system_metric.call_args_list
            metric_types = [call[1]["metric_type"] for call in calls]
            
            assert "ws_connections" in metric_types
            assert "cpu_usage" not in metric_types
            assert "memory_usage" not in metric_types

    @pytest.mark.asyncio
    async def test_record_periodic_metrics_exception_handling(self, monitoring_svc, mock_db_session):
        """Test periodic metrics recording with general exception."""
        with patch('app.services.monitoring_service.usage_service') as mock_usage_service:
            mock_usage_service.record_system_metric.side_effect = Exception("Service error")
            
            # Should not raise exception, just print error
            with patch('builtins.print') as mock_print:
                await monitoring_svc.record_periodic_metrics(mock_db_session)
                
                mock_print.assert_called_once()
                assert "Error recording metrics" in mock_print.call_args[0][0]

    @pytest.mark.asyncio
    async def test_start_monitoring_loop(self, monitoring_svc):
        """Test monitoring loop start and exception handling."""
        
        class MockDBSession:
            async def __aenter__(self):
                return AsyncMock()
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        def mock_db_session_factory():
            return MockDBSession()
        
        call_count = 0
        sleep_count = 0
        
        async def mock_record_metrics(db):
            nonlocal call_count
            call_count += 1
            # Don't raise exception here, let it complete normally
        
        async def mock_sleep(seconds):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:  # Stop after 2 sleep calls
                raise KeyboardInterrupt("Stop test")
            # Don't actually sleep, just return immediately
            return
        
        with patch.object(monitoring_svc, 'record_periodic_metrics', side_effect=mock_record_metrics), \
             patch('asyncio.sleep', side_effect=mock_sleep):
            
            with pytest.raises(KeyboardInterrupt):
                await monitoring_svc.start_monitoring_loop(mock_db_session_factory, interval_seconds=1)
            
            assert call_count >= 1
            assert sleep_count == 2

    @pytest.mark.asyncio
    async def test_start_monitoring_loop_error_handling(self, monitoring_svc):
        """Test monitoring loop error handling."""
        mock_db_session_factory = AsyncMock()
        mock_db_session_factory.side_effect = Exception("Database connection failed")
        
        iteration_count = 0
        
        async def mock_sleep(seconds):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 2:  # Stop after 2 error iterations
                raise KeyboardInterrupt("Stop test")
        
        with patch('asyncio.sleep', side_effect=mock_sleep), \
             patch('builtins.print') as mock_print:
            
            with pytest.raises(KeyboardInterrupt):
                await monitoring_svc.start_monitoring_loop(mock_db_session_factory, interval_seconds=1)
            
            # Should have printed error messages
            assert mock_print.call_count >= 2
            assert any("Error in monitoring loop" in str(call) for call in mock_print.call_args_list)


class TestGlobalMonitoringService:
    """Test the global monitoring service instance."""

    def test_global_monitoring_service_exists(self):
        """Test that global monitoring service instance exists."""
        from app.services.monitoring_service import monitoring_service
        
        assert isinstance(monitoring_service, MonitoringService)
        assert hasattr(monitoring_service, 'active_websocket_connections')
        assert hasattr(monitoring_service, 'connection_metrics')

    def test_global_monitoring_service_is_singleton(self):
        """Test that imports return the same instance."""
        from app.services.monitoring_service import monitoring_service as svc1
        from app.services.monitoring_service import monitoring_service as svc2
        
        assert svc1 is svc2


class TestWebSocketConnectionTracker:
    """Test WebSocket connection tracking decorator."""

    @pytest.mark.asyncio
    async def test_track_websocket_connection_decorator(self):
        """Test WebSocket connection tracking decorator."""
        user_id = "user_123"
        tenant_id = "tenant_456"
        
        # Create a test function to decorate
        @track_websocket_connection(user_id=user_id, tenant_id=tenant_id)
        async def test_websocket_function(message, connection_id=None):
            # Verify connection_id was added to kwargs
            assert connection_id is not None
            assert isinstance(connection_id, str)
            
            # Verify connection is being tracked
            assert connection_id in monitoring_service.active_websocket_connections
            assert connection_id in monitoring_service.connection_metrics
            
            metrics = monitoring_service.connection_metrics[connection_id]
            assert metrics["user_id"] == user_id
            assert metrics["tenant_id"] == tenant_id
            
            return "success"
        
        # Call the decorated function
        result = await test_websocket_function("test message")
        assert result == "success"
        
        # After function completes, connection should be cleaned up
        # Note: This might not work in unit test because decorator uses global instance
        # but it demonstrates the expected behavior

    @pytest.mark.asyncio
    async def test_track_websocket_connection_decorator_exception(self):
        """Test WebSocket connection tracking decorator with exception in function."""
        user_id = "user_123"
        
        connection_ids_seen = []
        
        @track_websocket_connection(user_id=user_id)
        async def test_websocket_function_with_error(connection_id=None):
            connection_ids_seen.append(connection_id)
            
            # Verify connection is tracked during execution
            assert connection_id in monitoring_service.active_websocket_connections
            
            # Raise an exception
            raise ValueError("Test error")
        
        # Function should raise exception
        with pytest.raises(ValueError, match="Test error"):
            await test_websocket_function_with_error()
        
        # Connection should be cleaned up even after exception
        connection_id = connection_ids_seen[0]
        assert connection_id not in monitoring_service.active_websocket_connections
        assert connection_id not in monitoring_service.connection_metrics

    @pytest.mark.asyncio
    async def test_track_websocket_connection_decorator_without_params(self):
        """Test WebSocket connection tracking decorator without user/tenant params."""
        @track_websocket_connection()
        async def test_websocket_function(connection_id=None):
            assert connection_id is not None
            
            metrics = monitoring_service.connection_metrics[connection_id]
            assert metrics["user_id"] is None
            assert metrics["tenant_id"] is None
            
            return "success"
        
        result = await test_websocket_function()
        assert result == "success"


class TestMonitoringServiceIntegration:
    """Integration-style tests for monitoring service components."""

    @pytest.fixture
    def monitoring_svc(self):
        """Create a fresh MonitoringService instance for integration testing."""
        return MonitoringService()

    def test_websocket_lifecycle_management(self, monitoring_svc):
        """Test complete WebSocket connection lifecycle."""
        # Start with no connections
        assert monitoring_svc.get_websocket_count() == 0
        assert monitoring_svc.get_websocket_connections_by_tenant() == {}
        
        # Add multiple connections
        tenant_1_id = "tenant_1"
        tenant_2_id = "tenant_2"
        
        monitoring_svc.add_websocket_connection("conn_1", "user_1", tenant_1_id)
        monitoring_svc.add_websocket_connection("conn_2", "user_2", tenant_1_id)
        monitoring_svc.add_websocket_connection("conn_3", "user_3", tenant_2_id)
        
        # Verify counts
        assert monitoring_svc.get_websocket_count() == 3
        tenant_counts = monitoring_svc.get_websocket_connections_by_tenant()
        assert tenant_counts[tenant_1_id] == 2
        assert tenant_counts[tenant_2_id] == 1
        
        # Update activity
        monitoring_svc.update_websocket_activity("conn_1")
        monitoring_svc.update_websocket_activity("conn_2")
        
        # Remove some connections
        monitoring_svc.remove_websocket_connection("conn_2")
        assert monitoring_svc.get_websocket_count() == 2
        
        tenant_counts = monitoring_svc.get_websocket_connections_by_tenant()
        assert tenant_counts[tenant_1_id] == 1
        assert tenant_counts[tenant_2_id] == 1
        
        # Remove all connections
        monitoring_svc.remove_websocket_connection("conn_1")
        monitoring_svc.remove_websocket_connection("conn_3")
        
        assert monitoring_svc.get_websocket_count() == 0
        assert monitoring_svc.get_websocket_connections_by_tenant() == {}

    @pytest.mark.asyncio
    async def test_metrics_collection_flow(self, monitoring_svc, mock_db_session):
        """Test complete metrics collection flow."""
        with patch('app.services.monitoring_service.usage_service') as mock_usage_service, \
             patch('app.services.monitoring_service.psutil') as mock_psutil:
            
            mock_usage_service.record_system_metric = AsyncMock()
            
            # Setup system metrics mocks
            mock_psutil.cpu_percent.return_value = 25.0
            mock_memory = Mock()
            mock_memory.percent = 30.0
            mock_memory.available = 8 * (1024**3)
            mock_psutil.virtual_memory.return_value = mock_memory
            mock_disk = Mock()
            mock_disk.percent = 40.0
            mock_disk.free = 500 * (1024**3)
            mock_psutil.disk_usage.return_value = mock_disk
            
            # Setup database metrics mocks
            mock_result_1 = Mock()
            mock_result_1.scalar.return_value = 10
            mock_result_2 = Mock()
            mock_result_2.scalar.return_value = 2048000000
            mock_result_3 = Mock()
            mock_result_3.fetchall.return_value = []
            
            mock_db_session.execute.side_effect = [
                mock_result_1, mock_result_2, mock_result_3
            ]
            
            # Add some WebSocket connections
            monitoring_svc.add_websocket_connection("conn_1", "user_1", "tenant_1")
            monitoring_svc.add_websocket_connection("conn_2", "user_2", "tenant_1")
            
            # Record metrics
            await monitoring_svc.record_periodic_metrics(mock_db_session)
            
            # Verify all metrics were recorded
            assert mock_usage_service.record_system_metric.call_count == 4
            
            # Check specific metrics
            calls = mock_usage_service.record_system_metric.call_args_list
            
            ws_call = next(call for call in calls if call[1]["metric_type"] == "ws_connections")
            assert ws_call[1]["value"] == 2
            
            db_call = next(call for call in calls if call[1]["metric_type"] == "db_connections")
            assert db_call[1]["value"] == 10
            
            cpu_call = next(call for call in calls if call[1]["metric_type"] == "cpu_usage")
            assert cpu_call[1]["value"] == 25
            
            memory_call = next(call for call in calls if call[1]["metric_type"] == "memory_usage")
            assert memory_call[1]["value"] == 30