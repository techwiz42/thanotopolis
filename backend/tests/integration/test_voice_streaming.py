# backend/tests/integration/test_voice_streaming.py
import pytest
import asyncio
import json
from unittest.mock import patch, Mock, AsyncMock
from httpx import AsyncClient
from fastapi import WebSocket
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.services.voice.deepgram_stt_service import deepgram_stt_service


class TestVoiceStreamingEndpoints:
    """Integration tests for voice streaming endpoints"""
    
    @pytest.mark.asyncio
    async def test_stt_status_endpoint(self, client: AsyncClient):
        """Test the STT status endpoint"""
        with patch.object(deepgram_stt_service, 'api_key', 'test_key'):
            with patch.object(deepgram_stt_service, 'verify_api_key', 
                            return_value=(True, None)) as mock_verify:
                
                response = await client.get("/api/voice/stt/status")
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["service"] == "deepgram_stt"
                assert data["api_key_configured"] is True
                assert data["api_key_valid"] is True
                assert data["error"] is None
                assert "supported_models" in data
                
                mock_verify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stt_status_no_api_key(self, client: AsyncClient):
        """Test STT status when API key is not configured"""
        with patch.object(deepgram_stt_service, 'api_key', None):
            response = await client.get("/api/voice/stt/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["api_key_configured"] is False
            assert data["api_key_valid"] is False
            assert data["error"] == "API key not configured"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_success(self):
        """Test successful WebSocket connection and configuration"""
        with TestClient(app) as client:
            # Mock the Deepgram service
            with patch('app.api.voice_streaming.deepgram_stt_service') as mock_service:
                mock_service.api_key = "test_key"
                
                # Mock the handler
                with patch('app.api.voice_streaming.DeepgramStreamingHandler') as MockHandler:
                    mock_handler = AsyncMock()
                    mock_handler.run = AsyncMock()
                    MockHandler.return_value = mock_handler
                    
                    # Connect to WebSocket
                    with client.websocket_connect("/api/ws/voice/streaming-stt") as websocket:
                        # Send config
                        websocket.send_json({
                            "type": "config",
                            "config": {
                                "model": "nova-2",
                                "language": "en-US"
                            }
                        })
                        
                        # Give async tasks time to run
                        import time
                        time.sleep(0.1)
                        
                        # Verify handler was created and run
                        MockHandler.assert_called_once()
                        mock_handler.run.assert_called_once()
    
    @pytest.mark.skip(reason="Test causes DB connection issues in integration suite")
    @pytest.mark.asyncio
    async def test_websocket_invalid_config(self):
        """Test WebSocket with invalid configuration"""
        # Patch database initialization
        with patch('app.db.database.init_db'):
            # Mock the connection_health manager to prevent database access
            with patch('app.api.voice_streaming.connection_health') as mock_health:
                # Mock the enqueue_connection to return a valid connection ID
                mock_health._ensure_initialized = AsyncMock()
                mock_health.enqueue_connection = AsyncMock(return_value="test-connection-id")
                mock_health.disconnect = AsyncMock()
                
                with TestClient(app) as client:
                    with client.websocket_connect("/api/ws/voice/streaming-stt") as websocket:
                        # Send invalid config message
                        websocket.send_json({
                            "type": "invalid",
                            "data": "test"
                        })
                        
                        # Should receive error
                        response = websocket.receive_json()
                        assert response["type"] == "error"
                        assert "Expected config message" in response["message"]
    
    @pytest.mark.skip(reason="Test causes DB connection issues in integration suite")
    @pytest.mark.asyncio
    async def test_websocket_timeout_waiting_for_config(self):
        """Test WebSocket timeout when no config is sent"""
        # Patch database initialization
        with patch('app.db.database.init_db'):
            # Mock the connection_health manager to prevent database access
            with patch('app.api.voice_streaming.connection_health') as mock_health:
                # Mock the enqueue_connection to return a valid connection ID
                mock_health._ensure_initialized = AsyncMock()
                mock_health.enqueue_connection = AsyncMock(return_value="test-connection-id")
                mock_health.disconnect = AsyncMock()
                
                with TestClient(app) as client:
                    # Reduce timeout for faster test
                    with patch('app.api.voice_streaming.asyncio.wait_for') as mock_wait_for:
                        mock_wait_for.side_effect = asyncio.TimeoutError()
                        
                        with client.websocket_connect("/api/ws/voice/streaming-stt") as websocket:
                            response = websocket.receive_json()
                            assert response["type"] == "error"
                            assert "Timeout" in response["message"]
    
    @pytest.mark.skip(reason="Test causes DB connection issues in integration suite")
    @pytest.mark.asyncio
    async def test_websocket_audio_streaming_flow(self):
        """Test complete audio streaming flow"""
        # Patch database initialization
        with patch('app.db.database.init_db'):
            # Mock the connection_health manager to prevent database access
            with patch('app.api.voice_streaming.connection_health') as mock_health:
                # Mock the enqueue_connection to return a valid connection ID
                mock_health._ensure_initialized = AsyncMock()
                mock_health.enqueue_connection = AsyncMock(return_value="test-connection-id")
                mock_health.disconnect = AsyncMock()
                
                with TestClient(app) as client:
                    # Mock the entire handler to simulate streaming
                    with patch('app.api.voice_streaming.DeepgramStreamingHandler') as MockHandler:
                        mock_handler = AsyncMock()
                        
                        # Simulate the handler sending transcription results
                        async def mock_run(config):
                            # Send ready message
                            await mock_handler.client_ws.send_json({
                                "type": "ready",
                                "message": "Connected to Deepgram"
                            })
                            
                            # Simulate receiving audio and sending transcription
                            await asyncio.sleep(0.1)
                            
                            await mock_handler.client_ws.send_json({
                                "type": "transcription",
                                "transcript": "Hello world",
                                "is_final": True,
                                "speech_final": True
                            })
                        
                        mock_handler.run = mock_run
                        mock_handler.stop = AsyncMock()
                        MockHandler.return_value = mock_handler
                        
                        with client.websocket_connect("/api/ws/voice/streaming-stt") as websocket:
                            # Inject the websocket into our mock
                            mock_handler.client_ws = websocket
                            
                            # Send config
                            websocket.send_json({
                                "type": "config",
                                "config": {"model": "nova-2"}
                            })
                            
                            # Receive ready message
                            response = websocket.receive_json()
                            assert response["type"] == "ready"
                            
                            # Send audio data
                            websocket.send_bytes(b"fake_audio_data")
                            
                            # Receive transcription
                            response = websocket.receive_json()
                            assert response["type"] == "transcription"
                            assert response["transcript"] == "Hello world"
    
    @pytest.mark.skip(reason="Test causes DB connection issues in integration suite")
    @pytest.mark.asyncio
    async def test_websocket_connection_limit(self):
        """Test connection limit handling"""
        # Patch database initialization
        with patch('app.db.database.init_db'):
            with TestClient(app) as client:
                # Mock connection health to simulate at capacity
                with patch('app.api.voice_streaming.connection_health') as mock_health:
                    mock_health._ensure_initialized = AsyncMock()
                    mock_health.enqueue_connection = AsyncMock(return_value=None)
                    mock_health.disconnect = AsyncMock()
                    
                    with client.websocket_connect("/api/ws/voice/streaming-stt") as websocket:
                        response = websocket.receive_json()
                        assert response["type"] == "error"
                        assert "capacity" in response["message"].lower()
    
    @pytest.mark.asyncio
    async def test_websocket_graceful_shutdown(self):
        """Test graceful shutdown of handlers"""
        from app.api.voice_streaming import ACTIVE_HANDLERS, shutdown_all_handlers
        
        # Create mock handlers
        mock_handler1 = AsyncMock()
        mock_handler1.stop = AsyncMock()
        mock_handler2 = AsyncMock()
        mock_handler2.stop = AsyncMock()
        
        ACTIVE_HANDLERS.add(mock_handler1)
        ACTIVE_HANDLERS.add(mock_handler2)
        
        # Shutdown all handlers
        await shutdown_all_handlers()
        
        # Verify all handlers were stopped
        mock_handler1.stop.assert_called_once()
        mock_handler2.stop.assert_called_once()
        assert len(ACTIVE_HANDLERS) == 0


class TestDeepgramIntegration:
    """Test actual Deepgram integration (requires valid API key)"""
    
    @pytest.mark.skip(reason="Requires valid Deepgram API key")
    @pytest.mark.asyncio
    async def test_real_deepgram_connection(self):
        """Test real connection to Deepgram (manual test)"""
        # This test requires a valid DEEPGRAM_API_KEY in environment
        # Run manually with: pytest -k test_real_deepgram_connection -s
        
        from app.services.voice.deepgram_stt_service import DeepgramSTTService
        
        service = DeepgramSTTService()
        if not service.api_key:
            pytest.skip("No Deepgram API key configured")
        
        is_valid, error = await service.verify_api_key()
        assert is_valid is True
        assert error is None
        
        # Test creating a handler and connecting
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        from app.services.voice.deepgram_stt_service import DeepgramStreamingHandler
        handler = DeepgramStreamingHandler(mock_ws, service)
        
        # Try to connect
        connected = await handler.connect_to_deepgram({"model": "nova-2"})
        assert connected is True
        
        # Clean up
        await handler.stop()
