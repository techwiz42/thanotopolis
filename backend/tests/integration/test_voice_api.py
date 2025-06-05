# tests/test_voice_streaming.py
import pytest
import asyncio
import json
import io
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from httpx import AsyncClient
from fastapi import UploadFile
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.services.voice import deepgram_service, elevenlabs_service
from app.api.voice_streaming import VoiceConnectionManager


class TestVoiceStreamingAPI:
    """Tests for voice streaming API endpoints."""
    
    @pytest.mark.asyncio
    async def test_stt_status_endpoint(self, client: AsyncClient):
        """Test the STT status endpoint."""
        with patch.object(deepgram_service, 'is_available', return_value=True):
            response = await client.get("/voice/stt/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["service"] == "deepgram"
            assert data["available"] is True
            assert "model" in data
            assert "language" in data
    
    @pytest.mark.asyncio
    async def test_tts_status_endpoint(self, client: AsyncClient):
        """Test the TTS status endpoint."""
        with patch.object(elevenlabs_service, 'is_available', return_value=True):
            response = await client.get("/voice/tts/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["service"] == "elevenlabs"
            assert data["available"] is True
            assert "model" in data
            assert "voice_id" in data
    
    @pytest.mark.asyncio
    async def test_voice_status_endpoint(self, client: AsyncClient):
        """Test the combined voice status endpoint."""
        with patch.object(deepgram_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'get_user_info', return_value={"success": True, "user_info": {"tier": "free"}}):
            
            response = await client.get("/voice/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "stt" in data
            assert "tts" in data
            assert "active_connections" in data
            assert data["stt"]["available"] is True
            assert data["tts"]["available"] is True


class TestVoiceFileEndpoints:
    """Tests for voice file processing endpoints."""
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_file_success(self, client: AsyncClient, mock_user):
        """Test successful audio file transcription."""
        # Mock Deepgram service
        with patch.object(deepgram_service, 'is_available', return_value=True), \
             patch.object(deepgram_service, 'transcribe_file') as mock_transcribe:
            
            mock_transcribe.return_value = {
                "success": True,
                "transcript": "Hello world",
                "confidence": 0.95,
                "words": [],
                "speakers": [],
                "paragraphs": []
            }
            
            # Create mock audio file
            audio_content = b"fake_audio_data"
            
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                response = await client.post(
                    "/voice/stt/file",
                    files={"audio_file": ("test.wav", io.BytesIO(audio_content), "audio/wav")},
                    data={
                        "language": "en-US",
                        "model": "nova-2",
                        "punctuate": True,
                        "diarize": False,
                        "smart_format": True
                    }
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["transcript"] == "Hello world"
            assert data["confidence"] == 0.95
            assert "metadata" in data
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_file_service_unavailable(self, client: AsyncClient, mock_user):
        """Test audio transcription when service is unavailable."""
        with patch.object(deepgram_service, 'is_available', return_value=False):
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                audio_content = b"fake_audio_data"
                response = await client.post(
                    "/voice/stt/file",
                    files={"audio_file": ("test.wav", io.BytesIO(audio_content), "audio/wav")}
                )
            
            assert response.status_code == 503
            assert "unavailable" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_success(self, client: AsyncClient, mock_user):
        """Test successful speech synthesis."""
        # Mock ElevenLabs service
        with patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'synthesize_speech') as mock_synthesize:
            
            mock_audio_data = b"fake_audio_data"
            mock_synthesize.return_value = {
                "success": True,
                "audio_data": mock_audio_data,
                "content_type": "audio/mpeg",
                "voice_id": "test_voice",
                "model_id": "eleven_turbo_v2_5",
                "output_format": "mp3_44100_128"
            }
            
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                response = await client.post(
                    "/voice/tts/synthesize",
                    data={
                        "text": "Hello world",
                        "voice_id": "test_voice",
                        "stability": 0.5,
                        "similarity_boost": 0.5
                    }
                )
            
            assert response.status_code == 200
            assert response.content == mock_audio_data
            assert response.headers["content-type"] == "audio/mpeg"
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_service_unavailable(self, client: AsyncClient, mock_user):
        """Test speech synthesis when service is unavailable."""
        with patch.object(elevenlabs_service, 'is_available', return_value=False):
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                response = await client.post(
                    "/voice/tts/synthesize",
                    data={"text": "Hello world"}
                )
            
            assert response.status_code == 503
            assert "unavailable" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_stream_speech_success(self, client: AsyncClient, mock_user):
        """Test successful speech streaming."""
        # Mock ElevenLabs service
        async def mock_stream_generator():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"
        
        with patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'stream_speech', return_value=mock_stream_generator()):
            
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                response = await client.post(
                    "/voice/tts/stream",
                    data={"text": "Hello world"}
                )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/mpeg"
            content = response.content
            assert content == b"chunk1chunk2chunk3"


class TestVoiceMetadataEndpoints:
    """Tests for voice metadata endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_voices_success(self, client: AsyncClient, mock_user):
        """Test getting available voices."""
        mock_voices = [
            {"voice_id": "voice1", "name": "Voice 1"},
            {"voice_id": "voice2", "name": "Voice 2"}
        ]
        
        with patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'get_voices') as mock_get_voices:
            
            mock_get_voices.return_value = {
                "success": True,
                "voices": mock_voices
            }
            
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                response = await client.get("/voice/tts/voices")
            
            assert response.status_code == 200
            assert response.json() == mock_voices
    
    @pytest.mark.asyncio
    async def test_get_voice_info_success(self, client: AsyncClient, mock_user):
        """Test getting specific voice info."""
        mock_voice_info = {
            "voice_id": "test_voice",
            "name": "Test Voice",
            "category": "premade"
        }
        
        with patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'get_voice_info') as mock_get_voice_info:
            
            mock_get_voice_info.return_value = {
                "success": True,
                "voice": mock_voice_info
            }
            
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                response = await client.get("/voice/tts/voice/test_voice")
            
            assert response.status_code == 200
            assert response.json() == mock_voice_info
    
    @pytest.mark.asyncio
    async def test_get_voice_info_not_found(self, client: AsyncClient, mock_user):
        """Test getting voice info for non-existent voice."""
        with patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'get_voice_info') as mock_get_voice_info:
            
            mock_get_voice_info.return_value = {
                "success": False,
                "error": "Voice not found"
            }
            
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                response = await client.get("/voice/tts/voice/nonexistent")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_models_success(self, client: AsyncClient, mock_user):
        """Test getting available models."""
        mock_models = [
            {"model_id": "eleven_turbo_v2", "name": "Turbo v2"},
            {"model_id": "eleven_multilingual_v2", "name": "Multilingual v2"}
        ]
        
        with patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'get_models') as mock_get_models:
            
            mock_get_models.return_value = {
                "success": True,
                "models": mock_models
            }
            
            # Mock authentication
            with patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
                response = await client.get("/voice/tts/models")
            
            assert response.status_code == 200
            assert response.json() == mock_models


class TestVoiceWebSocket:
    """Tests for voice WebSocket endpoints."""
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_failure(self):
        """Test WebSocket connection with invalid authentication."""
        with patch('app.api.voice_streaming.authenticate_voice_websocket', return_value=None):
            with TestClient(app) as client:
                with pytest.raises(WebSocketDisconnect):
                    with client.websocket_connect("/ws/voice/streaming-stt?token=invalid"):
                        pass
    
    @pytest.mark.asyncio
    async def test_websocket_service_unavailable(self, mock_user):
        """Test WebSocket connection when Deepgram service is unavailable."""
        with patch('app.api.voice_streaming.authenticate_voice_websocket', return_value=mock_user), \
             patch.object(deepgram_service, 'is_available', return_value=False):
            
            with TestClient(app) as client:
                with pytest.raises(WebSocketDisconnect):
                    with client.websocket_connect("/ws/voice/streaming-stt?token=valid"):
                        pass
    
    @pytest.mark.asyncio
    async def test_websocket_successful_connection(self, mock_user):
        """Test successful WebSocket connection and basic flow."""
        # Mock the voice connection manager
        mock_connection_manager = Mock()
        mock_connection_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_connection_manager.disconnect = AsyncMock()
        mock_connection_manager.get_connection = Mock(return_value={
            "websocket": Mock(),
            "user": mock_user,
            "transcription_session": None,
            "is_transcribing": False
        })
        
        with patch('app.api.voice_streaming.authenticate_voice_websocket', return_value=mock_user), \
             patch.object(deepgram_service, 'is_available', return_value=True), \
             patch('app.api.voice_streaming.voice_connection_manager', mock_connection_manager):
            
            with TestClient(app) as client:
                with client.websocket_connect("/ws/voice/streaming-stt?token=valid") as websocket:
                    # Should receive welcome message
                    message = websocket.receive_json()
                    assert message["type"] == "connected"
                    assert message["connection_id"] == "test-connection-id"


class TestVoiceConnectionManager:
    """Tests for VoiceConnectionManager."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create a VoiceConnectionManager for testing."""
        return VoiceConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        return websocket
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = Mock()
        user.email = "test@example.com"
        user.id = "user123"
        return user
    
    @pytest.mark.asyncio
    async def test_connect_user(self, connection_manager, mock_websocket, mock_user):
        """Test connecting a user."""
        connection_id = await connection_manager.connect(mock_websocket, mock_user)
        
        assert connection_id is not None
        assert connection_id in connection_manager.active_connections
        
        connection = connection_manager.get_connection(connection_id)
        assert connection["user"] == mock_user
        assert connection["websocket"] == mock_websocket
        assert connection["is_transcribing"] is False
        
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_user(self, connection_manager, mock_websocket, mock_user):
        """Test disconnecting a user."""
        # First connect
        connection_id = await connection_manager.connect(mock_websocket, mock_user)
        assert connection_id in connection_manager.active_connections
        
        # Then disconnect
        await connection_manager.disconnect(connection_id)
        assert connection_id not in connection_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_disconnect_with_active_transcription(self, connection_manager, mock_websocket, mock_user):
        """Test disconnecting with active transcription session."""
        # Connect and add mock transcription session
        connection_id = await connection_manager.connect(mock_websocket, mock_user)
        
        mock_transcription_session = AsyncMock()
        mock_transcription_session.finish = AsyncMock()
        
        connection_manager.active_connections[connection_id]["transcription_session"] = mock_transcription_session
        
        # Disconnect
        await connection_manager.disconnect(connection_id)
        
        # Verify transcription session was finished
        mock_transcription_session.finish.assert_called_once()
        assert connection_id not in connection_manager.active_connections
    
    def test_get_nonexistent_connection(self, connection_manager):
        """Test getting a connection that doesn't exist."""
        connection = connection_manager.get_connection("nonexistent")
        assert connection is None


class TestVoiceStreamingIntegration:
    """Integration tests for voice streaming functionality."""
    
    @pytest.mark.asyncio
    async def test_complete_transcription_workflow(self, mock_user):
        """Test complete file transcription workflow."""
        mock_transcript_result = {
            "success": True,
            "transcript": "This is a test transcription",
            "confidence": 0.95,
            "words": [
                {"word": "This", "start": 0.0, "end": 0.2, "confidence": 0.95},
                {"word": "is", "start": 0.2, "end": 0.4, "confidence": 0.93}
            ],
            "speakers": [],
            "paragraphs": [{"text": "This is a test transcription", "start": 0.0, "end": 2.0}]
        }
        
        with patch.object(deepgram_service, 'is_available', return_value=True), \
             patch.object(deepgram_service, 'transcribe_file', return_value=mock_transcript_result), \
             patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                audio_content = b"fake_audio_data"
                response = await client.post(
                    "/voice/stt/file",
                    files={"audio_file": ("test.wav", io.BytesIO(audio_content), "audio/wav")},
                    data={"language": "en-US", "model": "nova-2"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is True
                assert data["transcript"] == "This is a test transcription"
                assert len(data["words"]) == 2
                assert len(data["paragraphs"]) == 1
    
    @pytest.mark.asyncio
    async def test_complete_synthesis_workflow(self, mock_user):
        """Test complete speech synthesis workflow."""
        mock_audio_data = b"generated_speech_audio"
        mock_synthesis_result = {
            "success": True,
            "audio_data": mock_audio_data,
            "content_type": "audio/mpeg",
            "voice_id": "test_voice",
            "model_id": "eleven_turbo_v2_5",
            "output_format": "mp3_44100_128"
        }
        
        with patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'synthesize_speech', return_value=mock_synthesis_result), \
             patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/voice/tts/synthesize",
                    data={
                        "text": "Hello, this is a test of speech synthesis.",
                        "voice_id": "test_voice",
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                )
                
                assert response.status_code == 200
                assert response.content == mock_audio_data
                assert response.headers["content-type"] == "audio/mpeg"
                assert "X-Voice-ID" in response.headers
                assert "X-Model-ID" in response.headers


# Test fixtures
@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock()
    user.id = "test_user_123"
    user.email = "test@example.com"
    return user


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
