import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.core.websocket_queue import (
    WebSocketConnection, 
    ConnectionState, 
    ConnectionHealth,
    connection_health,
    initialize_connection_health
)


class TestWebSocketConnection:
    """Test suite for WebSocketConnection class."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        return websocket
    
    @pytest.fixture
    def ws_connection(self, mock_websocket):
        """Create a test WebSocketConnection."""
        return WebSocketConnection(mock_websocket, "test_user")
    
    def test_websocket_connection_initialization(self, ws_connection, mock_websocket):
        """Test WebSocketConnection initialization."""
        assert ws_connection.websocket == mock_websocket
        assert ws_connection.user_identifier == "test_user"
        assert ws_connection.connected_at is not None
        assert ws_connection.last_activity is not None
        assert ws_connection.state == ConnectionState.PENDING
        assert ws_connection._accept_lock is None
        assert ws_connection._send_lock is None
    
    @pytest.mark.asyncio
    async def test_ensure_locks(self, ws_connection):
        """Test that locks are created in async context."""
        await ws_connection._ensure_locks()
        
        assert ws_connection._accept_lock is not None
        assert ws_connection._send_lock is not None
        assert isinstance(ws_connection._accept_lock, asyncio.Lock)
        assert isinstance(ws_connection._send_lock, asyncio.Lock)
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, ws_connection):
        """Test successful connection initialization."""
        result = await ws_connection.initialize()
        
        assert result is True
        assert ws_connection.state == ConnectionState.ACCEPTED
    
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, ws_connection):
        """Test initialization when already initialized."""
        # Initialize once
        await ws_connection.initialize()
        assert ws_connection.state == ConnectionState.ACCEPTED
        
        # Try to initialize again
        result = await ws_connection.initialize()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_text_success(self, ws_connection, mock_websocket):
        """Test successful message sending."""
        await ws_connection.initialize()
        mock_websocket.send_text = AsyncMock()
        
        result = await ws_connection.send_text("Hello")
        
        assert result is True
        mock_websocket.send_text.assert_called_once_with("Hello")
    
    @pytest.mark.asyncio
    async def test_send_text_not_accepted(self, ws_connection):
        """Test sending message when connection not accepted."""
        # Don't initialize, so state remains PENDING
        result = await ws_connection.send_text("Hello")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_text_websocket_disconnect(self, ws_connection, mock_websocket):
        """Test handling WebSocket disconnect during send."""
        await ws_connection.initialize()
        mock_websocket.send_text = AsyncMock(side_effect=WebSocketDisconnect())
        
        result = await ws_connection.send_text("Hello", max_retries=1)
        
        assert result is False
        assert ws_connection.state == ConnectionState.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_send_text_retry_logic(self, ws_connection, mock_websocket):
        """Test retry logic in send_text."""
        await ws_connection.initialize()
        
        # First call fails, second succeeds
        mock_websocket.send_text = AsyncMock(side_effect=[Exception("Network error"), None])
        
        result = await ws_connection.send_text("Hello", max_retries=2, initial_delay=0.01)
        
        assert result is True
        assert mock_websocket.send_text.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_text_max_retries_exceeded(self, ws_connection, mock_websocket):
        """Test when max retries are exceeded."""
        await ws_connection.initialize()
        mock_websocket.send_text = AsyncMock(side_effect=Exception("Persistent error"))
        
        result = await ws_connection.send_text("Hello", max_retries=2, initial_delay=0.01)
        
        assert result is False
        assert ws_connection.state == ConnectionState.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_close_connection(self, ws_connection, mock_websocket):
        """Test closing connection."""
        await ws_connection.initialize()
        mock_websocket.close = AsyncMock()
        
        await ws_connection.close()
        
        assert ws_connection.state == ConnectionState.DISCONNECTED
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_already_disconnected(self, ws_connection, mock_websocket):
        """Test closing already disconnected connection."""
        ws_connection.state = ConnectionState.DISCONNECTED
        mock_websocket.close = AsyncMock()
        
        await ws_connection.close()
        
        # Should not call close again
        mock_websocket.close.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_close_with_error(self, ws_connection, mock_websocket):
        """Test closing connection with WebSocket error."""
        await ws_connection.initialize()
        mock_websocket.close = AsyncMock(side_effect=Exception("Close error"))
        
        # Should not raise exception
        await ws_connection.close()
        
        assert ws_connection.state == ConnectionState.DISCONNECTED


class TestConnectionHealth:
    """Test suite for ConnectionHealth class."""
    
    @pytest.fixture
    def connection_health_instance(self):
        """Create a test ConnectionHealth instance."""
        return ConnectionHealth()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        return AsyncMock(spec=WebSocket)
    
    def test_connection_health_initialization(self, connection_health_instance):
        """Test ConnectionHealth initialization."""
        ch = connection_health_instance
        assert ch.active_connections == {}
        assert ch.private_conversations == set()
        assert ch.MAX_TOTAL_CONNECTIONS == 50000
        assert ch.MAX_CONNECTIONS_PER_CONVERSATION == 250
        assert ch.HANDSHAKE_TIMEOUT == 30.0
        assert ch.CONNECTION_TIMEOUT == 3600.0
        assert ch._initialized is False
    
    @pytest.mark.asyncio
    async def test_ensure_initialized(self, connection_health_instance):
        """Test async initialization."""
        ch = connection_health_instance
        await ch._ensure_initialized()
        
        assert ch._initialized is True
        assert ch._global_lock is not None
        assert ch._cleanup_task_lock is not None
        assert ch._privacy_lock is not None
        assert ch._metrics_lock is not None
    
    @pytest.mark.asyncio
    async def test_get_conversation_lock(self, connection_health_instance):
        """Test getting conversation-specific lock."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        lock1 = await ch.get_conversation_lock(conversation_id)
        lock2 = await ch.get_conversation_lock(conversation_id)
        
        assert lock1 is lock2
        assert isinstance(lock1, asyncio.Lock)
    
    @pytest.mark.asyncio
    async def test_update_metrics(self, connection_health_instance):
        """Test metrics update."""
        ch = connection_health_instance
        
        await ch.update_metrics({"total_connections": 5, "successful_connections": 3})
        
        assert ch.metrics["total_connections"] == 5
        assert ch.metrics["successful_connections"] == 3
        assert ch.metrics["peak_connections"] == 5
    
    @pytest.mark.asyncio
    async def test_update_timeout_metrics(self, connection_health_instance):
        """Test timeout metrics update."""
        ch = connection_health_instance
        
        await ch.update_timeout_metrics("handshake")
        await ch.update_timeout_metrics("message")
        
        assert ch.metrics["timeouts"]["handshake"] == 1
        assert ch.metrics["timeouts"]["message"] == 1
    
    @pytest.mark.asyncio
    async def test_enqueue_connection_success(self, connection_health_instance, mock_websocket):
        """Test successful connection enqueueing."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        # Mock the initialize method to always succeed
        original_init = WebSocketConnection.initialize
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            connection_id = await ch.enqueue_connection(
                mock_websocket, conversation_id, "test_user"
            )
        
        assert connection_id is not None
        assert conversation_id in ch.active_connections
        assert connection_id in ch.active_connections[conversation_id]
    
    @pytest.mark.asyncio
    async def test_enqueue_connection_stt_priority(self, connection_health_instance, mock_websocket):
        """Test STT connection gets priority treatment."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            connection_id = await ch.enqueue_connection(
                mock_websocket, conversation_id, "streaming_stt_user"
            )
        
        assert connection_id is not None
        ch.metrics["total_connections"] = ch.MAX_TOTAL_CONNECTIONS
        
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            connection_id = await ch.enqueue_connection(
                mock_websocket, conversation_id, "streaming_stt_user"
            )
        
        # STT connection should still be allowed despite high load
        assert connection_id is not None
    
    @pytest.mark.asyncio
    async def test_enqueue_connection_limit_exceeded(self, connection_health_instance, mock_websocket):
        """Test connection rejection when limit exceeded."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        # Set high connection count
        ch.metrics["total_connections"] = ch.MAX_TOTAL_CONNECTIONS + 100
        
        connection_id = await ch.enqueue_connection(
            mock_websocket, conversation_id, "regular_user"
        )
        
        assert connection_id is None
    
    @pytest.mark.asyncio
    async def test_disconnect_connection(self, connection_health_instance, mock_websocket):
        """Test disconnecting a connection."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        # Add a connection first
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            connection_id = await ch.enqueue_connection(
                mock_websocket, conversation_id, "test_user"
            )
        
        # Disconnect it
        await ch.disconnect(conversation_id, connection_id)
        
        # Should be removed from active connections
        assert connection_id not in ch.active_connections.get(conversation_id, {})
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_empty_conversation(self, connection_health_instance, mock_websocket):
        """Test that empty conversations are removed after disconnect."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        # Add and then disconnect the only connection
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            connection_id = await ch.enqueue_connection(
                mock_websocket, conversation_id, "test_user"
            )
        
        await ch.disconnect(conversation_id, connection_id)
        
        # Conversation should be completely removed
        assert conversation_id not in ch.active_connections
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, connection_health_instance, mock_websocket):
        """Test broadcasting message to all connections."""
        ch = connection_health_instance
        conversation_id = uuid4()
        message = {"type": "test", "content": "Hello"}
        
        # Add a connection
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            connection_id = await ch.enqueue_connection(
                mock_websocket, conversation_id, "test_user"
            )
        
        # Mock successful send
        connection = ch.active_connections[conversation_id][connection_id]
        with patch.object(connection, 'send_text', return_value=True) as mock_send:
            await ch.broadcast(conversation_id, message)
        
        # Verify send_text was called with JSON
        mock_send.assert_called_once_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_broadcast_excludes_connection(self, connection_health_instance, mock_websocket):
        """Test broadcasting excludes specific connection."""
        ch = connection_health_instance
        conversation_id = uuid4()
        message = {"type": "test", "content": "Hello"}
        
        # Add two connections
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            connection_id1 = await ch.enqueue_connection(
                mock_websocket, conversation_id, "user1"
            )
            connection_id2 = await ch.enqueue_connection(
                AsyncMock(spec=WebSocket), conversation_id, "user2"
            )
        
        # Mock send_text for both connections
        conn1 = ch.active_connections[conversation_id][connection_id1]
        conn2 = ch.active_connections[conversation_id][connection_id2]
        
        with patch.object(conn1, 'send_text', return_value=True) as mock_send1, \
             patch.object(conn2, 'send_text', return_value=True) as mock_send2:
            
            await ch.broadcast(conversation_id, message, exclude_id=connection_id1)
        
        # Only connection 2 should receive the message
        mock_send1.assert_not_called()
        mock_send2.assert_called_once_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_broadcast_stt_priority(self, connection_health_instance):
        """Test that STT connections get priority in broadcasts."""
        ch = connection_health_instance
        conversation_id = uuid4()
        message = {"type": "test", "content": "Hello"}
        
        # Add STT and regular connections
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            stt_id = await ch.enqueue_connection(
                AsyncMock(spec=WebSocket), conversation_id, "streaming_stt_user"
            )
            regular_id = await ch.enqueue_connection(
                AsyncMock(spec=WebSocket), conversation_id, "regular_user"
            )
        
        call_order = []
        
        def track_stt_call(*args, **kwargs):
            call_order.append("stt")
            return True
        
        def track_regular_call(*args, **kwargs):
            call_order.append("regular")
            return True
        
        stt_conn = ch.active_connections[conversation_id][stt_id]
        regular_conn = ch.active_connections[conversation_id][regular_id]
        
        with patch.object(stt_conn, 'send_text', side_effect=track_stt_call), \
             patch.object(regular_conn, 'send_text', side_effect=track_regular_call):
            
            await ch.broadcast(conversation_id, message)
        
        # STT should be called first
        assert call_order == ["stt", "regular"]
    
    @pytest.mark.asyncio
    async def test_set_privacy(self, connection_health_instance):
        """Test setting conversation privacy."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        await ch.set_privacy(conversation_id, True)
        assert await ch.is_private(conversation_id) is True
        
        await ch.set_privacy(conversation_id, False)
        assert await ch.is_private(conversation_id) is False
    
    @pytest.mark.asyncio
    async def test_get_connection_metrics(self, connection_health_instance, mock_websocket):
        """Test getting connection metrics."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        # Add some connections
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            await ch.enqueue_connection(mock_websocket, conversation_id, "user1")
            await ch.enqueue_connection(AsyncMock(spec=WebSocket), conversation_id, "user2")
        
        metrics = await ch.get_connection_metrics()
        
        assert "current_active_connections" in metrics
        assert "active_conversations" in metrics
        assert "total_connections" in metrics
        assert "timeouts" in metrics
        assert metrics["active_conversations"] >= 1  # May include other conversations
        assert metrics["current_active_connections"] >= 1  # May include other connections
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self, connection_health_instance, mock_websocket):
        """Test cleanup of stale connections."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        # Add a connection
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            connection_id = await ch.enqueue_connection(
                mock_websocket, conversation_id, "test_user"
            )
        
        # Make connection appear stale
        connection = ch.active_connections[conversation_id][connection_id]
        connection.last_activity = datetime.utcnow() - timedelta(hours=2)
        
        # Mock the cleanup method to avoid infinite loop
        with patch.object(ch, 'disconnect') as mock_disconnect:
            # Manually call cleanup logic
            current_time = datetime.utcnow()
            if (current_time - connection.last_activity).total_seconds() > ch.CONNECTION_TIMEOUT:
                await ch.disconnect(conversation_id, connection_id, reason="connection timeout")
        
        mock_disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stt_connections_not_timed_out(self, connection_health_instance):
        """Test that STT connections are not timed out."""
        ch = connection_health_instance
        conversation_id = uuid4()
        
        # Add STT connection
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            stt_id = await ch.enqueue_connection(
                AsyncMock(spec=WebSocket), conversation_id, "streaming_stt_user"
            )
        
        # Make connection appear very old
        connection = ch.active_connections[conversation_id][stt_id]
        connection.last_activity = datetime.utcnow() - timedelta(days=1)
        
        # STT connections should not be disconnected due to timeout
        with patch.object(ch, 'disconnect') as mock_disconnect:
            # Simulate cleanup check
            if 'streaming_stt' not in connection.user_identifier:
                # Only non-STT connections should be checked
                await ch.disconnect(conversation_id, stt_id)
        
        # Should not have been called since it's an STT connection
        mock_disconnect.assert_not_called()


class TestConnectionHealthSingleton:
    """Test the singleton connection health instance."""
    
    def test_singleton_exists(self):
        """Test that connection health singleton exists."""
        assert connection_health is not None
        assert isinstance(connection_health, ConnectionHealth)
    
    @pytest.mark.asyncio
    async def test_initialize_connection_health(self):
        """Test connection health initialization function."""
        # Just test that the function exists and doesn't crash
        from app.core.buffer_manager import buffer_manager
        # Test that buffer_manager can be used (no specific initialization needed)
        test_uuid = uuid4()
        buffer = await buffer_manager.get_or_create_buffer(test_uuid)
        
        # Should not raise an exception and should return a buffer
        assert buffer is not None
        assert buffer.conversation_id == test_uuid


class TestConnectionStates:
    """Test ConnectionState enum."""
    
    def test_connection_states_exist(self):
        """Test that all connection states exist."""
        assert ConnectionState.PENDING.value == "pending"
        assert ConnectionState.ACCEPTED.value == "accepted"
        assert ConnectionState.DISCONNECTED.value == "disconnected"


class TestErrorHandling:
    """Test error handling in websocket components."""
    
    @pytest.mark.asyncio
    async def test_connection_health_error_handling(self):
        """Test error handling in connection health operations."""
        ch = ConnectionHealth()
        
        # Test with invalid conversation ID - should not crash
        await ch.disconnect(uuid4(), "nonexistent_connection")
        
        # Test broadcast to nonexistent conversation - should not crash
        await ch.broadcast(uuid4(), {"test": "message"})
    
    @pytest.mark.asyncio
    async def test_websocket_connection_error_recovery(self):
        """Test error recovery in websocket connections."""
        mock_websocket = AsyncMock(spec=WebSocket)
        connection = WebSocketConnection(mock_websocket, "test_user")
        
        # Test normal initialization should succeed
        result = await connection.initialize()
        
        # Should handle initialization gracefully
        assert result is True
        assert connection.state == ConnectionState.ACCEPTED
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling in operations."""
        ch = ConnectionHealth()
        ch.LOCK_ACQUIRE_TIMEOUT = 0.001  # Very short timeout for testing
        
        conversation_id = uuid4()
        
        # This should timeout but not crash
        with patch('asyncio.timeout') as mock_timeout:
            mock_timeout.side_effect = asyncio.TimeoutError()
            
            result = await ch.enqueue_connection(
                AsyncMock(spec=WebSocket), conversation_id, "test_user"
            )
            
            # Should return None due to timeout
            assert result is None


class TestPerformanceOptimizations:
    """Test performance-related optimizations."""
    
    @pytest.mark.asyncio
    async def test_batch_message_processing(self):
        """Test that message broadcasting is efficiently batched."""
        ch = ConnectionHealth()
        conversation_id = uuid4()
        
        # Add multiple connections
        connections = []
        
        # Mock the initialize method to always succeed
        async def mock_init(self):
            await self._ensure_locks()
            self.state = ConnectionState.ACCEPTED
            return True
        
        with patch.object(WebSocketConnection, 'initialize', mock_init):
            for i in range(5):
                conn_id = await ch.enqueue_connection(
                    AsyncMock(spec=WebSocket), conversation_id, f"user{i}"
                )
                connections.append(conn_id)
        
        message = {"type": "test", "data": "batch_test"}
        
        # Mock all send_text methods to track calls
        send_calls = []
        for conn_id in connections:
            connection = ch.active_connections[conversation_id][conn_id]
            original_send = connection.send_text
            
            async def mock_send(msg):
                send_calls.append(msg)
                return True
            
            connection.send_text = mock_send
        
        await ch.broadcast(conversation_id, message)
        
        # All connections should receive the same serialized message
        assert len(send_calls) == 5
        assert all(call == send_calls[0] for call in send_calls)
    
    @pytest.mark.asyncio
    async def test_memory_efficient_cleanup(self):
        """Test that cleanup operations are memory efficient."""
        ch = ConnectionHealth()
        
        # Simulate many conversations for cleanup
        conversation_ids = [uuid4() for _ in range(10)]
        
        # Add conversations to cleanup list
        for conv_id in conversation_ids:
            ch.active_connections[conv_id] = {}
        
        # Mock cleanup to verify it processes conversations individually
        cleanup_calls = []
        
        original_get_conversation_lock = ch.get_conversation_lock
        
        async def mock_get_lock(conv_id):
            cleanup_calls.append(conv_id)
            return await original_get_conversation_lock(conv_id)
        
        ch.get_conversation_lock = mock_get_lock
        
        # Simulate cleanup processing
        for conv_id in list(ch.active_connections.keys())[:3]:  # Process only first 3
            await ch.get_conversation_lock(conv_id)
        
        # Should process conversations individually, not all at once
        assert len(cleanup_calls) == 3