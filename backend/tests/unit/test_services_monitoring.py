import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4
import asyncio
import psutil

from app.services.monitoring_service import MonitoringService, monitoring_service, track_websocket_connection
from app.services.usage_service import usage_service
from sqlalchemy.ext.asyncio import AsyncSession


class TestMonitoringService:
    """Test suite for MonitoringService."""
    
    @pytest.fixture
    def monitoring_service_instance(self):
        """Create a test MonitoringService instance."""
        return MonitoringService()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.scalar = MagicMock()
        db.fetchall = MagicMock()
        return db
    
    @pytest.fixture
    def sample_connection_id(self):
        """Create a sample connection ID."""
        return str(uuid4())
    
    @pytest.fixture
    def sample_user_id(self):
        """Create a sample user ID."""
        return str(uuid4())
    
    @pytest.fixture
    def sample_tenant_id(self):
        """Create a sample tenant ID."""
        return str(uuid4())
    
    def test_monitoring_service_initialization(self, monitoring_service_instance):
        """Test MonitoringService initialization."""
        assert isinstance(monitoring_service_instance.active_websocket_connections, set)
        assert isinstance(monitoring_service_instance.connection_metrics, dict)
        assert len(monitoring_service_instance.active_websocket_connections) == 0
        assert len(monitoring_service_instance.connection_metrics) == 0
        assert monitoring_service_instance.last_metrics_update > 0
    
    def test_add_websocket_connection(self, monitoring_service_instance, sample_connection_id, sample_user_id, sample_tenant_id):
        """Test adding a WebSocket connection."""
        monitoring_service_instance.add_websocket_connection(
            connection_id=sample_connection_id,
            user_id=sample_user_id,
            tenant_id=sample_tenant_id
        )
        
        assert sample_connection_id in monitoring_service_instance.active_websocket_connections
        assert sample_connection_id in monitoring_service_instance.connection_metrics
        
        metrics = monitoring_service_instance.connection_metrics[sample_connection_id]
        assert metrics["user_id"] == sample_user_id
        assert metrics["tenant_id"] == sample_tenant_id
        assert isinstance(metrics["connected_at"], datetime)
        assert isinstance(metrics["last_activity"], datetime)
    
    def test_add_websocket_connection_optional_params(self, monitoring_service_instance, sample_connection_id):
        """Test adding a WebSocket connection with optional parameters."""
        monitoring_service_instance.add_websocket_connection(connection_id=sample_connection_id)
        
        assert sample_connection_id in monitoring_service_instance.active_websocket_connections
        
        metrics = monitoring_service_instance.connection_metrics[sample_connection_id]
        assert metrics["user_id"] is None
        assert metrics["tenant_id"] is None
        assert isinstance(metrics["connected_at"], datetime)
        assert isinstance(metrics["last_activity"], datetime)
    
    def test_remove_websocket_connection(self, monitoring_service_instance, sample_connection_id, sample_user_id):
        """Test removing a WebSocket connection."""
        # First add a connection
        monitoring_service_instance.add_websocket_connection(
            connection_id=sample_connection_id,
            user_id=sample_user_id
        )
        
        # Verify it was added
        assert sample_connection_id in monitoring_service_instance.active_websocket_connections
        assert sample_connection_id in monitoring_service_instance.connection_metrics
        
        # Remove the connection
        monitoring_service_instance.remove_websocket_connection(sample_connection_id)
        
        # Verify it was removed
        assert sample_connection_id not in monitoring_service_instance.active_websocket_connections
        assert sample_connection_id not in monitoring_service_instance.connection_metrics
    
    def test_remove_nonexistent_websocket_connection(self, monitoring_service_instance):
        """Test removing a WebSocket connection that doesn't exist."""
        fake_connection_id = str(uuid4())
        
        # Should not raise an exception
        monitoring_service_instance.remove_websocket_connection(fake_connection_id)
        
        # Should remain empty
        assert len(monitoring_service_instance.active_websocket_connections) == 0
        assert len(monitoring_service_instance.connection_metrics) == 0
    
    def test_update_websocket_activity(self, monitoring_service_instance, sample_connection_id, sample_user_id):
        """Test updating WebSocket activity timestamp."""
        # Add a connection
        monitoring_service_instance.add_websocket_connection(
            connection_id=sample_connection_id,
            user_id=sample_user_id
        )
        
        # Get initial activity timestamp
        initial_activity = monitoring_service_instance.connection_metrics[sample_connection_id]["last_activity"]
        
        # Wait a small amount and update activity
        import time
        time.sleep(0.01)
        monitoring_service_instance.update_websocket_activity(sample_connection_id)
        
        # Verify timestamp was updated
        updated_activity = monitoring_service_instance.connection_metrics[sample_connection_id]["last_activity"]
        assert updated_activity > initial_activity
    
    def test_update_websocket_activity_nonexistent(self, monitoring_service_instance):
        """Test updating activity for a nonexistent connection."""
        fake_connection_id = str(uuid4())
        
        # Should not raise an exception
        monitoring_service_instance.update_websocket_activity(fake_connection_id)
    
    def test_get_websocket_count(self, monitoring_service_instance, sample_user_id):
        """Test getting WebSocket connection count."""
        assert monitoring_service_instance.get_websocket_count() == 0
        
        # Add connections
        conn1 = str(uuid4())
        conn2 = str(uuid4())
        conn3 = str(uuid4())
        
        monitoring_service_instance.add_websocket_connection(conn1, sample_user_id)
        monitoring_service_instance.add_websocket_connection(conn2, sample_user_id)
        monitoring_service_instance.add_websocket_connection(conn3, sample_user_id)
        
        assert monitoring_service_instance.get_websocket_count() == 3
        
        # Remove one connection
        monitoring_service_instance.remove_websocket_connection(conn2)
        assert monitoring_service_instance.get_websocket_count() == 2
    
    def test_get_websocket_connections_by_tenant(self, monitoring_service_instance):
        """Test getting WebSocket connections grouped by tenant."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())
        user1 = str(uuid4())
        user2 = str(uuid4())
        
        # Add connections for different tenants
        monitoring_service_instance.add_websocket_connection(str(uuid4()), user1, tenant1)
        monitoring_service_instance.add_websocket_connection(str(uuid4()), user1, tenant1)
        monitoring_service_instance.add_websocket_connection(str(uuid4()), user2, tenant2)
        monitoring_service_instance.add_websocket_connection(str(uuid4()), user2, None)  # No tenant
        
        tenant_counts = monitoring_service_instance.get_websocket_connections_by_tenant()
        
        assert tenant_counts[tenant1] == 2
        assert tenant_counts[tenant2] == 1
        # Connection with no tenant should not be counted
        assert len(tenant_counts) == 2
    
    def test_get_websocket_connections_by_tenant_empty(self, monitoring_service_instance):
        """Test getting tenant connections when no connections exist."""
        tenant_counts = monitoring_service_instance.get_websocket_connections_by_tenant()
        assert tenant_counts == {}
    
    @pytest.mark.asyncio
    async def test_get_database_metrics_success(self, monitoring_service_instance, mock_db):
        """Test getting database metrics successfully."""
        # Mock database responses
        mock_active_result = MagicMock()
        mock_active_result.scalar.return_value = 5
        
        mock_size_result = MagicMock()
        mock_size_result.scalar.return_value = 1073741824  # 1GB
        
        mock_table_result = MagicMock()
        mock_table_row1 = MagicMock()
        mock_table_row1.schemaname = "public"
        mock_table_row1.tablename = "users"
        mock_table_row1.total_changes = 1500
        
        mock_table_row2 = MagicMock()
        mock_table_row2.schemaname = "public"
        mock_table_row2.tablename = "conversations"
        mock_table_row2.total_changes = 800
        
        mock_table_result.fetchall.return_value = [mock_table_row1, mock_table_row2]
        
        # Set up mock_db to return different results for different queries
        mock_db.execute.side_effect = [mock_active_result, mock_size_result, mock_table_result]
        
        result = await monitoring_service_instance.get_database_metrics(mock_db)
        
        assert result["active_connections"] == 5
        assert result["database_size_bytes"] == 1073741824
        assert len(result["table_activity"]) == 2
        assert result["table_activity"][0]["schema"] == "public"
        assert result["table_activity"][0]["table"] == "users"
        assert result["table_activity"][0]["total_changes"] == 1500
        assert result["table_activity"][1]["table"] == "conversations"
        assert result["table_activity"][1]["total_changes"] == 800
        
        # Verify execute was called 3 times
        assert mock_db.execute.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_database_metrics_error(self, monitoring_service_instance, mock_db):
        """Test getting database metrics with database error."""
        mock_db.execute.side_effect = Exception("Database connection error")
        
        result = await monitoring_service_instance.get_database_metrics(mock_db)
        
        assert "error" in result
        assert result["error"] == "Database connection error"
        assert result["active_connections"] == 0
    
    def test_get_system_metrics_success(self, monitoring_service_instance):
        """Test getting system metrics successfully."""
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock psutil responses
            mock_cpu.return_value = 75.5
            
            mock_memory_obj = MagicMock()
            mock_memory_obj.percent = 60.2
            mock_memory_obj.available = 8589934592  # 8GB
            mock_memory.return_value = mock_memory_obj
            
            mock_disk_obj = MagicMock()
            mock_disk_obj.percent = 45.7
            mock_disk_obj.free = 107374182400  # 100GB
            mock_disk.return_value = mock_disk_obj
            
            result = monitoring_service_instance.get_system_metrics()
            
            assert result["cpu_percent"] == 75.5
            assert result["memory_percent"] == 60.2
            assert abs(result["memory_available_gb"] - 8.0) < 0.1  # ~8GB
            assert result["disk_percent"] == 45.7
            assert abs(result["disk_free_gb"] - 100.0) < 0.1  # ~100GB
            assert isinstance(result["timestamp"], datetime)
            
            # Verify psutil was called with correct parameters
            mock_cpu.assert_called_once_with(interval=1)
            mock_memory.assert_called_once()
            mock_disk.assert_called_once_with('/')
    
    def test_get_system_metrics_error(self, monitoring_service_instance):
        """Test getting system metrics with psutil error."""
        with patch('psutil.cpu_percent', side_effect=Exception("System monitoring error")):
            result = monitoring_service_instance.get_system_metrics()
            
            assert "error" in result
            assert result["error"] == "System monitoring error"
            assert isinstance(result["timestamp"], datetime)
    
    @pytest.mark.asyncio
    async def test_record_periodic_metrics_success(self, monitoring_service_instance, mock_db):
        """Test recording periodic metrics successfully."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())
        
        # Add some WebSocket connections
        monitoring_service_instance.add_websocket_connection(str(uuid4()), str(uuid4()), tenant1)
        monitoring_service_instance.add_websocket_connection(str(uuid4()), str(uuid4()), tenant2)
        monitoring_service_instance.add_websocket_connection(str(uuid4()), str(uuid4()), tenant1)
        
        with patch.object(usage_service, 'record_system_metric', return_value=MagicMock()) as mock_record, \
             patch.object(monitoring_service_instance, 'get_database_metrics', return_value={"active_connections": 5, "database_size_bytes": 1000000}) as mock_db_metrics, \
             patch.object(monitoring_service_instance, 'get_system_metrics', return_value={"cpu_percent": 80, "memory_percent": 70}) as mock_sys_metrics:
            
            await monitoring_service_instance.record_periodic_metrics(mock_db)
            
            # Verify WebSocket metrics were recorded
            ws_call = None
            db_call = None
            cpu_call = None
            memory_call = None
            
            for call in mock_record.call_args_list:
                kwargs = call[1]
                if kwargs["metric_type"] == "ws_connections":
                    ws_call = kwargs
                elif kwargs["metric_type"] == "db_connections":
                    db_call = kwargs
                elif kwargs["metric_type"] == "cpu_usage":
                    cpu_call = kwargs
                elif kwargs["metric_type"] == "memory_usage":
                    memory_call = kwargs
            
            # Verify WebSocket connections metric
            assert ws_call is not None
            assert ws_call["value"] == 3
            assert tenant1 in ws_call["additional_data"]["tenant_breakdown"]
            assert tenant2 in ws_call["additional_data"]["tenant_breakdown"]
            assert ws_call["additional_data"]["tenant_breakdown"][tenant1] == 2
            assert ws_call["additional_data"]["tenant_breakdown"][tenant2] == 1
            
            # Verify database metrics
            assert db_call is not None
            assert db_call["value"] == 5
            
            # Verify system metrics
            assert cpu_call is not None
            assert cpu_call["value"] == 80
            assert memory_call is not None
            assert memory_call["value"] == 70
            
            # Verify all required calls were made
            assert mock_record.call_count == 4
    
    @pytest.mark.asyncio
    async def test_record_periodic_metrics_database_error(self, monitoring_service_instance, mock_db):
        """Test recording periodic metrics with database error."""
        with patch.object(monitoring_service_instance, 'get_database_metrics', return_value={"error": "DB error"}) as mock_db_metrics, \
             patch.object(monitoring_service_instance, 'get_system_metrics', return_value={"cpu_percent": 80, "memory_percent": 70}) as mock_sys_metrics, \
             patch.object(usage_service, 'record_system_metric', return_value=MagicMock()) as mock_record:
            
            await monitoring_service_instance.record_periodic_metrics(mock_db)
            
            # Should still record WebSocket and system metrics, but not database metrics
            metric_types = [call[1]["metric_type"] for call in mock_record.call_args_list]
            assert "ws_connections" in metric_types
            assert "cpu_usage" in metric_types
            assert "memory_usage" in metric_types
            assert "db_connections" not in metric_types
    
    @pytest.mark.asyncio
    async def test_record_periodic_metrics_system_error(self, monitoring_service_instance, mock_db):
        """Test recording periodic metrics with system monitoring error."""
        with patch.object(monitoring_service_instance, 'get_database_metrics', return_value={"active_connections": 5}) as mock_db_metrics, \
             patch.object(monitoring_service_instance, 'get_system_metrics', return_value={"error": "System error"}) as mock_sys_metrics, \
             patch.object(usage_service, 'record_system_metric', return_value=MagicMock()) as mock_record:
            
            await monitoring_service_instance.record_periodic_metrics(mock_db)
            
            # Should still record WebSocket and database metrics, but not system metrics
            metric_types = [call[1]["metric_type"] for call in mock_record.call_args_list]
            assert "ws_connections" in metric_types
            assert "db_connections" in metric_types
            assert "cpu_usage" not in metric_types
            assert "memory_usage" not in metric_types
    
    @pytest.mark.asyncio
    async def test_record_periodic_metrics_exception_handling(self, monitoring_service_instance, mock_db):
        """Test that record_periodic_metrics handles exceptions gracefully."""
        with patch.object(usage_service, 'record_system_metric', side_effect=Exception("Recording error")), \
             patch('builtins.print') as mock_print:
            
            # Should not raise an exception
            await monitoring_service_instance.record_periodic_metrics(mock_db)
            
            # Should print error message
            mock_print.assert_called_with("Error recording metrics: Recording error")
    
    @pytest.mark.asyncio
    async def test_start_monitoring_loop_single_iteration(self, monitoring_service_instance):
        """Test a single iteration of the monitoring loop."""
        mock_db_session = AsyncMock()
        
        # Create proper async context manager
        class MockAsyncContextManager:
            async def __aenter__(self):
                return mock_db_session
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        mock_session_factory = MagicMock(return_value=MockAsyncContextManager())
        
        # Create a simple mock that doesn't cause recursion
        mock_record_metrics = AsyncMock()
        
        # Cancel after first sleep to prevent infinite loop
        async def mock_sleep(duration):
            raise asyncio.CancelledError()
        
        with patch.object(monitoring_service_instance, 'record_periodic_metrics', mock_record_metrics), \
             patch('asyncio.sleep', side_effect=mock_sleep):
            
            try:
                await monitoring_service_instance.start_monitoring_loop(mock_session_factory, interval_seconds=1)
            except asyncio.CancelledError:
                pass  # Expected
            
            # Verify that record_periodic_metrics was called
            mock_record_metrics.assert_called_once_with(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_start_monitoring_loop_exception_handling(self, monitoring_service_instance):
        """Test that monitoring loop handles exceptions gracefully."""
        mock_session_factory = MagicMock()
        
        iteration_count = 0
        
        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 2:
                # Stop after two iterations (one error, one retry)
                raise asyncio.CancelledError()
        
        with patch.object(monitoring_service_instance, 'record_periodic_metrics', side_effect=Exception("Metrics error")), \
             patch('asyncio.sleep', side_effect=mock_sleep), \
             patch('builtins.print') as mock_print:
            
            try:
                await monitoring_service_instance.start_monitoring_loop(mock_session_factory, interval_seconds=1)
            except asyncio.CancelledError:
                pass  # Expected
            
            # Should print error message
            error_prints = [call for call in mock_print.call_args_list if "Error in monitoring loop" in str(call)]
            assert len(error_prints) > 0
    
    def test_concurrent_connection_management(self, monitoring_service_instance):
        """Test managing connections concurrently."""
        import threading
        import time
        
        connections_added = []
        connections_lock = threading.Lock()
        
        def add_connections():
            for i in range(10):
                conn_id = str(uuid4())
                monitoring_service_instance.add_websocket_connection(conn_id, str(uuid4()), str(uuid4()))
                with connections_lock:
                    connections_added.append(conn_id)
                time.sleep(0.001)  # Small delay to interleave operations
        
        def remove_connections():
            time.sleep(0.01)  # Let some connections be added first
            # Make a copy of the list to avoid modification during iteration
            while True:
                with connections_lock:
                    if not connections_added:
                        time.sleep(0.001)
                        continue
                    # Remove every other connection that exists
                    to_remove = []
                    for i, conn_id in enumerate(list(connections_added)):
                        if i % 2 == 0 and conn_id in monitoring_service_instance.active_websocket_connections:
                            to_remove.append(conn_id)
                    
                    if not to_remove and len(connections_added) >= 5:
                        break  # Exit if no more connections to remove and we have enough
                
                for conn_id in to_remove:
                    monitoring_service_instance.remove_websocket_connection(conn_id)
                    time.sleep(0.001)
                
                if len(connections_added) >= 10:
                    break
        
        # Run concurrent operations
        add_thread = threading.Thread(target=add_connections)
        remove_thread = threading.Thread(target=remove_connections)
        
        add_thread.start()
        remove_thread.start()
        
        add_thread.join()
        remove_thread.join()
        
        # Verify final state is consistent
        active_count = monitoring_service_instance.get_websocket_count()
        metrics_count = len(monitoring_service_instance.connection_metrics)
        
        assert active_count == metrics_count
        assert active_count >= 0  # Should never be negative
        
        # All tracked connections should have metrics
        for conn_id in monitoring_service_instance.active_websocket_connections:
            assert conn_id in monitoring_service_instance.connection_metrics


class TestMonitoringServiceSingleton:
    """Test the monitoring service singleton."""
    
    def test_singleton_exists(self):
        """Test that monitoring service singleton exists."""
        assert monitoring_service is not None
        assert isinstance(monitoring_service, MonitoringService)
    
    def test_singleton_initialization(self):
        """Test singleton initialization."""
        assert isinstance(monitoring_service.active_websocket_connections, set)
        assert isinstance(monitoring_service.connection_metrics, dict)
        assert monitoring_service.last_metrics_update > 0


class TestWebSocketTrackingDecorator:
    """Test the WebSocket connection tracking decorator."""
    
    @pytest.mark.asyncio
    async def test_track_websocket_connection_decorator(self):
        """Test the WebSocket tracking decorator."""
        user_id = str(uuid4())
        tenant_id = str(uuid4())
        
        # Track initial connection count
        initial_count = monitoring_service.get_websocket_count()
        
        @track_websocket_connection(user_id=user_id, tenant_id=tenant_id)
        async def mock_websocket_handler(*args, **kwargs):
            # During execution, connection should be tracked
            current_count = monitoring_service.get_websocket_count()
            assert current_count == initial_count + 1
            
            # Connection ID should be available in kwargs
            assert 'connection_id' in kwargs
            connection_id = kwargs['connection_id']
            assert connection_id in monitoring_service.active_websocket_connections
            
            # Verify connection metrics
            metrics = monitoring_service.connection_metrics[connection_id]
            assert metrics['user_id'] == user_id
            assert metrics['tenant_id'] == tenant_id
            
            return "test_result"
        
        # Execute the decorated function
        result = await mock_websocket_handler("test_arg", test_kwarg="test_value")
        
        # After execution, connection should be removed
        final_count = monitoring_service.get_websocket_count()
        assert final_count == initial_count
        assert result == "test_result"
    
    @pytest.mark.asyncio
    async def test_track_websocket_connection_decorator_with_exception(self):
        """Test that decorator cleans up connection even when function raises exception."""
        user_id = str(uuid4())
        
        initial_count = monitoring_service.get_websocket_count()
        
        @track_websocket_connection(user_id=user_id)
        async def failing_websocket_handler(*args, **kwargs):
            # During execution, connection should be tracked
            current_count = monitoring_service.get_websocket_count()
            assert current_count == initial_count + 1
            
            raise Exception("Handler failed")
        
        # Execute the decorated function and catch the exception
        with pytest.raises(Exception, match="Handler failed"):
            await failing_websocket_handler()
        
        # After exception, connection should still be removed
        final_count = monitoring_service.get_websocket_count()
        assert final_count == initial_count
    
    @pytest.mark.asyncio
    async def test_track_websocket_connection_decorator_optional_params(self):
        """Test decorator with optional parameters."""
        initial_count = monitoring_service.get_websocket_count()
        
        @track_websocket_connection()
        async def websocket_handler_no_params(*args, **kwargs):
            current_count = monitoring_service.get_websocket_count()
            assert current_count == initial_count + 1
            
            connection_id = kwargs['connection_id']
            metrics = monitoring_service.connection_metrics[connection_id]
            assert metrics['user_id'] is None
            assert metrics['tenant_id'] is None
            
            return "success"
        
        result = await websocket_handler_no_params()
        
        final_count = monitoring_service.get_websocket_count()
        assert final_count == initial_count
        assert result == "success"


class TestMonitoringServiceIntegration:
    """Integration tests for monitoring service components."""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """Test a complete monitoring workflow with multiple connections."""
        monitoring = MonitoringService()
        
        # Add multiple connections
        connections = []
        tenants = [str(uuid4()) for _ in range(3)]
        
        for i in range(5):
            conn_id = str(uuid4())
            user_id = str(uuid4())
            tenant_id = tenants[i % 3]  # Distribute across 3 tenants
            
            monitoring.add_websocket_connection(conn_id, user_id, tenant_id)
            connections.append(conn_id)
        
        # Verify connection count
        assert monitoring.get_websocket_count() == 5
        
        # Verify tenant distribution
        tenant_counts = monitoring.get_websocket_connections_by_tenant()
        assert len(tenant_counts) == 3
        assert sum(tenant_counts.values()) == 5
        
        # Update activity for some connections
        for conn_id in connections[:3]:
            monitoring.update_websocket_activity(conn_id)
        
        # Remove some connections
        for conn_id in connections[:2]:
            monitoring.remove_websocket_connection(conn_id)
        
        # Verify final state
        assert monitoring.get_websocket_count() == 3
        final_tenant_counts = monitoring.get_websocket_connections_by_tenant()
        assert sum(final_tenant_counts.values()) == 3
        
        # Verify remaining connections are tracked
        for conn_id in connections[2:]:
            assert conn_id in monitoring.active_websocket_connections
            assert conn_id in monitoring.connection_metrics
    
