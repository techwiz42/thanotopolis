# backend/tests/integration/test_websockets.py
import pytest
import asyncio
import json
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from starlette.testclient import TestClient
from fastapi.testclient import TestClient as FastAPITestClient

from app.main import app
from app.models.models import User
from app.auth.auth import AuthService


class TestWebSocketEndpoints:
    """Integration tests for WebSocket endpoints"""
    
    @pytest.fixture
    def test_conversation_id(self):
        """Generate a test conversation ID"""
        return uuid4()
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing"""
        return User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            hashed_password="hashed",
            tenant_id=uuid4(),
            is_active=True,
            is_verified=True,
            role="user"
        )
    
    @pytest.fixture
    def auth_token(self, mock_user):
        """Generate an auth token for the mock user"""
        return AuthService.create_access_token({
            "sub": str(mock_user.id),
            "tenant_id": str(mock_user.tenant_id),
            "email": mock_user.email,
            "role": mock_user.role
        })
    
    def test_websocket_connection_success(self, test_conversation_id, auth_token, mock_user):
        """Test successful WebSocket connection"""
        with TestClient(app) as client:
            # Mock authentication
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = mock_user
                
                # Connect to WebSocket
                with client.websocket_connect(
                    f"/api/ws/conversations/{test_conversation_id}?token={auth_token}"
                ) as websocket:
                    # Should receive welcome message
                    data = websocket.receive_json()
                    assert data["type"] == "system"
                    assert "Welcome" in data["content"]
                    
                    # Should receive user joined message
                    data = websocket.receive_json()
                    assert data["type"] == "user_joined"
                    assert data["email"] == mock_user.email
    
    def test_websocket_authentication_failure(self, test_conversation_id):
        """Test WebSocket connection with invalid token"""
        with TestClient(app) as client:
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = None
                
                with client.websocket_connect(
                    f"/api/ws/conversations/{test_conversation_id}?token=invalid"
                ) as websocket:
                    # Should receive error message
                    data = websocket.receive_json()
                    assert data["type"] == "error"
                    assert "Authentication failed" in data["content"]
    
    def test_websocket_message_handling(self, test_conversation_id, auth_token, mock_user):
        """Test sending and receiving messages"""
        with TestClient(app) as client:
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = mock_user
                
                with client.websocket_connect(
                    f"/api/ws/conversations/{test_conversation_id}?token={auth_token}"
                ) as websocket:
                    # Skip welcome messages
                    websocket.receive_json()  # Welcome
                    websocket.receive_json()  # User joined
                    
                    # Send a message
                    test_message = "Hello, WebSocket!"
                    websocket.send_json({
                        "type": "message",
                        "content": test_message
                    })
                    
                    # Should receive the broadcasted message
                    data = websocket.receive_json()
                    assert data["type"] == "message"
                    assert data["content"] == test_message
                    assert data["email"] == mock_user.email
                    assert data["is_owner"] is True
    
    def test_websocket_typing_indicator(self, test_conversation_id, auth_token, mock_user):
        """Test typing status functionality"""
        with TestClient(app) as client:
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = mock_user
                
                with client.websocket_connect(
                    f"/api/ws/conversations/{test_conversation_id}?token={auth_token}"
                ) as websocket:
                    # Skip welcome messages
                    websocket.receive_json()
                    websocket.receive_json()
                    
                    # Send typing status
                    websocket.send_json({
                        "type": "typing_status",
                        "is_typing": True
                    })
                    
                    # Should receive typing status broadcast
                    data = websocket.receive_json()
                    assert data["type"] == "typing_status"
                    assert data["is_typing"] is True
                    assert data["identifier"] == mock_user.email
    
    def test_websocket_help_command(self, test_conversation_id, auth_token, mock_user):
        """Test help command"""
        with TestClient(app) as client:
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = mock_user
                
                with client.websocket_connect(
                    f"/api/ws/conversations/{test_conversation_id}?token={auth_token}"
                ) as websocket:
                    # Skip welcome messages
                    websocket.receive_json()
                    websocket.receive_json()
                    
                    # Send help command
                    websocket.send_json({
                        "type": "message",
                        "content": "?"
                    })
                    
                    # Should receive help message
                    data = websocket.receive_json()
                    assert data["type"] == "message"
                    assert "Available Commands" in data["content"]
                    assert data["identifier"] == "system"
    
    def test_websocket_status_command(self, test_conversation_id, auth_token, mock_user):
        """Test status command"""
        with TestClient(app) as client:
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = mock_user
                
                with client.websocket_connect(
                    f"/api/ws/conversations/{test_conversation_id}?token={auth_token}"
                ) as websocket:
                    # Skip welcome messages
                    websocket.receive_json()
                    websocket.receive_json()
                    
                    # Send status command
                    websocket.send_json({
                        "type": "message",
                        "content": "/status"
                    })
                    
                    # Should receive status message
                    data = websocket.receive_json()
                    assert data["type"] == "message"
                    assert "Connection active" in data["content"]
                    assert str(test_conversation_id) in data["content"]
    
    def test_websocket_ping_pong(self, test_conversation_id, auth_token, mock_user):
        """Test ping/pong keepalive"""
        with TestClient(app) as client:
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = mock_user
                
                with client.websocket_connect(
                    f"/api/ws/conversations/{test_conversation_id}?token={auth_token}"
                ) as websocket:
                    # Skip welcome messages
                    websocket.receive_json()
                    websocket.receive_json()
                    
                    # Send ping
                    websocket.send_json({
                        "type": "ping"
                    })
                    
                    # Should receive pong
                    data = websocket.receive_json()
                    assert data["type"] == "pong"
    
    def test_websocket_disconnect_notification(self, test_conversation_id, auth_token, mock_user):
        """Test that disconnect sends leave notification"""
        with TestClient(app) as client:
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = mock_user
                
                # Create two connections
                with client.websocket_connect(
                    f"/api/ws/conversations/{test_conversation_id}?token={auth_token}"
                ) as ws1:
                    # Skip welcome messages for first connection
                    ws1.receive_json()
                    ws1.receive_json()
                    
                    with client.websocket_connect(
                        f"/api/ws/conversations/{test_conversation_id}?token={auth_token}"
                    ) as ws2:
                        # Skip messages for second connection
                        ws2.receive_json()
                        ws2.receive_json()
                        
                        # First connection should receive join notification for second
                        data = ws1.receive_json()
                        assert data["type"] == "user_joined"
                    
                    # After ws2 closes, ws1 should receive leave notification
                    data = ws1.receive_json()
                    assert data["type"] == "user_left"
                    assert data["email"] == mock_user.email
    
    @pytest.mark.asyncio
    async def test_notification_websocket(self, auth_token, mock_user):
        """Test notification WebSocket endpoint"""
        # This requires async test client
        from httpx import AsyncClient
        from app.main import app
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.api.websockets.authenticate_websocket') as mock_auth:
                mock_auth.return_value = mock_user
                
                # Note: httpx doesn't support WebSocket, so we'd need a different approach
                # This is a placeholder showing the test structure
                pass
    
    def test_get_active_users_endpoint(self, client, test_conversation_id, auth_headers):
        """Test getting active users in a conversation"""
        # This would be a regular HTTP endpoint test
        # Requires proper auth setup from conftest.py
        pass


class TestConnectionManager:
    """Unit tests for ConnectionManager"""
    
    @pytest.mark.asyncio
    async def test_connection_manager_connect(self):
        """Test connection registration"""
        from app.api.websockets import ConnectionManager
        
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        conversation_id = uuid4()
        user_email = "test@example.com"
        
        # Connect
        conn_id = await manager.connect(mock_ws, conversation_id, user_email)
        
        assert conn_id is not None
        assert conversation_id in manager.active_connections
        assert conn_id in manager.active_connections[conversation_id]
        assert user_email in manager.user_connections
        assert conversation_id in manager.user_connections[user_email]
    
    @pytest.mark.asyncio
    async def test_connection_manager_disconnect(self):
        """Test connection removal"""
        from app.api.websockets import ConnectionManager
        
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        conversation_id = uuid4()
        user_email = "test@example.com"
        
        # Connect then disconnect
        conn_id = await manager.connect(mock_ws, conversation_id, user_email)
        await manager.disconnect(conversation_id, conn_id, user_email)
        
        # Should be cleaned up
        assert conversation_id not in manager.active_connections
        assert user_email not in manager.user_connections
    
    @pytest.mark.asyncio
    async def test_connection_manager_broadcast(self):
        """Test message broadcasting"""
        from app.api.websockets import ConnectionManager
        
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        conversation_id = uuid4()
        
        # Connect two clients
        await manager.connect(mock_ws1, conversation_id, "user1@example.com")
        await manager.connect(mock_ws2, conversation_id, "user2@example.com")
        
        # Broadcast message
        test_message = {"type": "test", "content": "Hello"}
        await manager.broadcast(conversation_id, test_message)
        
        # Both should receive the message
        mock_ws1.send_json.assert_called_once_with(test_message)
        mock_ws2.send_json.assert_called_once_with(test_message)
    
    @pytest.mark.asyncio
    async def test_connection_manager_send_to_user(self):
        """Test sending message to specific user"""
        from app.api.websockets import ConnectionManager
        
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        conversation_id1 = uuid4()
        conversation_id2 = uuid4()
        user_email = "test@example.com"
        
        # User connected to two conversations
        await manager.connect(mock_ws, conversation_id1, user_email)
        await manager.connect(mock_ws, conversation_id2, user_email)
        
        # Send message to user
        test_message = {"type": "notification", "content": "Test"}
        await manager.send_to_user(user_email, test_message)
        
        # Should receive message for both conversations
        assert mock_ws.send_json.call_count == 2
