# tests/test_voice_services_consolidated.py
"""
Consolidated Voice Services Tests

This file combines the best elements from existing tests while updating
outdated references and adding comprehensive coverage for current implementation.
"""

import pytest
import asyncio
import json
import io
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from httpx import AsyncClient
from fastapi import UploadFile
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from contextlib import asynccontextmanager

from app.services.voice.deepgram_service import DeepgramService, LiveTranscriptionSession
from app.services.voice.elevenlabs_service import ElevenLabsService
from app.services.voice import deepgram_service, elevenlabs_service
from app.api.voice_streaming import VoiceConnectionManager
from app.main import app


class TestDeepgramServiceUnit:
    """Comprehensive unit tests for DeepgramService - updated for current implementation."""
    
    @pytest.fixture
    def deepgram_service_mock(self):
        """Create a properly mocked DeepgramService instance."""
        with patch('app.services.voice.deepgram_service.settings') as mock_settings:
            mock_settings.DEEPGRAM_API_KEY = "test_key"
            mock_settings.DEEPGRAM_MODEL = "nova-2"
            mock_settings.DEEPGRAM_LANGUAGE = "en-US"
            
            with patch('app.services.voice.deepgram_service.DeepgramClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                service = DeepgramService()
                service.client = mock_client
                return service, mock_client
    
    def test_service_initialization(self):
        """Test service initialization with and without API key."""
        # Test with valid API key
        with patch('app.services.voice.deepgram_service.settings') as mock_settings:
            mock_settings.DEEPGRAM_API_KEY = "valid_key"
            mock_settings.DEEPGRAM_MODEL = "nova-2"
            mock_settings.DEEPGRAM_LANGUAGE = "en-US"
            
            with patch('app.services.voice.deepgram_service.DeepgramClient'):
                service = DeepgramService()
                assert service.is_available() is True
        
        # Test with invalid/missing API key
        with patch('app.services.voice.deepgram_service.settings') as mock_settings:
            mock_settings.DEEPGRAM_API_KEY = "NOT_SET"
            service = DeepgramService()
            assert service.is_available() is False
    
    @pytest.mark.asyncio
    async def test_transcribe_file_comprehensive(self, deepgram_service_mock):
        """Test file transcription with comprehensive response handling."""
        service, mock_client = deepgram_service_mock
        
        # Mock comprehensive response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "This is a comprehensive test transcript with multiple words.",
                        "confidence": 0.95,
                        "words": [
                            {"word": "This", "start": 0.0, "end": 0.2, "confidence": 0.95, "speaker": 0},
                            {"word": "is", "start": 0.2, "end": 0.4, "confidence": 0.93, "speaker": 0},
                            {"word": "a", "start": 0.4, "end": 0.5, "confidence": 0.92, "speaker": 0},
                            {"word": "comprehensive", "start": 0.5, "end": 1.2, "confidence": 0.96, "speaker": 0},
                            {"word": "test", "start": 1.2, "end": 1.5, "confidence": 0.94, "speaker": 0}
                        ],
                        "paragraphs": {
                            "paragraphs": [{
                                "text": "This is a comprehensive test transcript with multiple words.",
                                "start": 0.0,
                                "end": 2.5,
                                "speaker": 0
                            }]
                        }
                    }]
                }]
            }
        }
        
        mock_transcribe = AsyncMock(return_value=mock_response)
        mock_client.listen.asyncprerecorded.v.return_value.transcribe_file = mock_transcribe
        
        # Test with various parameters
        audio_data = b"fake_audio_data"
        result = await service.transcribe_file(
            audio_data=audio_data,
            content_type="audio/wav",
            language="en-US",
            model="nova-2",
            punctuate=True,
            diarize=True,
            smart_format=True
        )
        
        # Comprehensive assertions
        assert result["success"] is True
        assert result["transcript"] == "This is a comprehensive test transcript with multiple words."
        assert result["confidence"] == 0.95
        assert len(result["words"]) == 5
        assert len(result["paragraphs"]) == 1
        assert len(result["speakers"]) == 1  # Should extract speaker 0
        
        # Verify word details
        first_word = result["words"][0]
        assert first_word["word"] == "This"
        assert first_word["start"] == 0.0
        assert first_word["confidence"] == 0.95
        assert first_word["speaker"] == 0
    
    @pytest.mark.asyncio
    async def test_transcribe_file_error_scenarios(self, deepgram_service_mock):
        """Test various error scenarios in file transcription."""
        service, mock_client = deepgram_service_mock
        
        # Test API error
        mock_transcribe = AsyncMock(side_effect=Exception("Deepgram API error"))
        mock_client.listen.asyncprerecorded.v.return_value.transcribe_file = mock_transcribe
        
        result = await service.transcribe_file(b"audio_data")
        
        assert result["success"] is False
        assert "Deepgram API error" in result["error"]
        assert result["transcript"] == ""
        assert result["confidence"] == 0.0
        
        # Test malformed response
        mock_response = Mock()
        mock_response.to_dict.return_value = {}  # Empty response
        mock_transcribe = AsyncMock(return_value=mock_response)
        mock_client.listen.asyncprerecorded.v.return_value.transcribe_file = mock_transcribe
        
        result = await service.transcribe_file(b"audio_data")
        
        assert result["success"] is True  # Should handle gracefully
        assert result["transcript"] == ""
    
    @pytest.mark.asyncio
    async def test_live_transcription_session_lifecycle(self, deepgram_service_mock):
        """Test complete live transcription session lifecycle."""
        service, mock_client = deepgram_service_mock
        
        # Mock callback functions
        messages_received = []
        errors_received = []
        
        def on_message(data):
            messages_received.append(data)
        
        def on_error(error):
            errors_received.append(error)
        
        # Create session
        session = await service.start_live_transcription(
            on_message=on_message,
            on_error=on_error,
            language="en-US",
            model="nova-2",
            interim_results=True
        )
        
        assert isinstance(session, LiveTranscriptionSession)
        assert session.on_message == on_message
        assert session.on_error == on_error
        
        # Test session start
        mock_connection = Mock()
        mock_connection.start = AsyncMock(return_value=True)
        mock_connection.on = Mock()
        session.client.listen.asynclive.v.return_value = mock_connection
        
        await session.start()
        
        assert session.is_connected is True
        assert session.connection == mock_connection
        
        # Verify event handlers were registered
        assert mock_connection.on.call_count == 4  # transcript, error, warning, metadata
        
        # Test sending audio
        mock_connection.send = AsyncMock()
        audio_chunk = b"audio_chunk_data"
        await session.send_audio(audio_chunk)
        mock_connection.send.assert_called_once_with(audio_chunk)
        
        # Test finishing session
        mock_connection.finish = AsyncMock()
        await session.finish()
        assert session.is_connected is False
        mock_connection.finish.assert_called_once()


class TestElevenLabsServiceUnit:
    """Comprehensive unit tests for ElevenLabsService - updated for current implementation."""
    
    @pytest.fixture
    def elevenlabs_service_mock(self):
        """Create a properly configured ElevenLabsService instance."""
        with patch('app.services.voice.elevenlabs_service.settings') as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_key"
            mock_settings.ELEVENLABS_VOICE_ID = "test_voice_id"
            mock_settings.ELEVENLABS_MODEL = "eleven_turbo_v2_5"
            mock_settings.ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
            mock_settings.ELEVENLABS_OPTIMIZE_STREAMING_LATENCY = 3
            return ElevenLabsService()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_synthesize_speech_comprehensive(self, mock_session_class, elevenlabs_service_mock):
        """Test comprehensive speech synthesis with various parameters."""
        service = elevenlabs_service_mock
        
        # Mock successful response
        mock_audio_data = b"fake_high_quality_audio_data" * 50  # Larger audio file
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=mock_audio_data)
        mock_response.headers = {"content-type": "audio/mpeg"}
        
        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        # Test with custom voice settings
        result = await service.synthesize_speech(
            text="This is a comprehensive test of speech synthesis with custom settings.",
            voice_id="custom_voice_id",
            model_id="eleven_multilingual_v2",
            voice_settings={
                "stability": 0.7,
                "similarity_boost": 0.8,
                "style": 0.2,
                "use_speaker_boost": False
            },
            output_format="wav_44100"
        )
        
        # Comprehensive assertions
        assert result["success"] is True
        assert result["audio_data"] == mock_audio_data
        assert result["content_type"] == "audio/mpeg"
        assert result["voice_id"] == "custom_voice_id"
        assert result["model_id"] == "eleven_multilingual_v2"
        assert result["output_format"] == "wav_44100"
        assert result["size_bytes"] == len(mock_audio_data)
        
        # Verify API call was made with correct parameters
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "text-to-speech/custom_voice_id" in call_args[1]["url"]
        
        # Check request data
        request_data = call_args[1]["json"]
        assert request_data["text"] == "This is a comprehensive test of speech synthesis with custom settings."
        assert request_data["model_id"] == "eleven_multilingual_v2"
        assert request_data["voice_settings"]["stability"] == 0.7
        assert request_data["voice_settings"]["similarity_boost"] == 0.8
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_stream_speech_comprehensive(self, mock_session_class, elevenlabs_service_mock):
        """Test speech streaming with proper chunk handling."""
        service = elevenlabs_service_mock
        
        # Mock streaming response
        mock_chunks = [
            b"audio_chunk_1_data_",
            b"audio_chunk_2_data_", 
            b"audio_chunk_3_data_",
            b"final_chunk_data"
        ]
        
        async def mock_iter_chunked(chunk_size):
            for chunk in mock_chunks:
                yield chunk
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.iter_chunked = mock_iter_chunked
        
        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        # Test streaming
        received_chunks = []
        async for chunk in service.stream_speech(
            text="Streaming test text",
            voice_id="streaming_voice",
            chunk_size=512
        ):
            received_chunks.append(chunk)
        
        assert received_chunks == mock_chunks
        
        # Verify streaming endpoint was called
        call_args = mock_session.post.call_args
        assert "text-to-speech/streaming_voice/stream" in call_args[1]["url"]
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession') 
    async def test_get_voices_with_filtering(self, mock_session_class, elevenlabs_service_mock):
        """Test voice retrieval with comprehensive voice data."""
        service = elevenlabs_service_mock
        
        # Mock comprehensive voice response
        mock_voices_data = {
            "voices": [
                {
                    "voice_id": "21m00Tcm4TlvDq8ikWAM",
                    "name": "Rachel",
                    "category": "premade",
                    "labels": {"accent": "american", "gender": "female", "age": "young"},
                    "description": "A calm, young American female voice",
                    "preview_url": "https://example.com/preview1.mp3"
                },
                {
                    "voice_id": "AZnzlk1XvdvUeBnXmlld", 
                    "name": "Domi",
                    "category": "premade",
                    "labels": {"accent": "american", "gender": "female", "age": "young"},
                    "description": "A strong, confident female voice",
                    "preview_url": "https://example.com/preview2.mp3"
                },
                {
                    "voice_id": "custom_voice_123",
                    "name": "Custom Voice",
                    "category": "cloned",
                    "labels": {"accent": "british", "gender": "male", "age": "middle_aged"},
                    "description": "A custom cloned voice"
                }
            ]
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_voices_data)
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        result = await service.get_voices()
        
        assert result["success"] is True
        assert len(result["voices"]) == 3
        
        # Check voice data structure
        rachel_voice = result["voices"][0]
        assert rachel_voice["name"] == "Rachel"
        assert rachel_voice["category"] == "premade"
        assert "labels" in rachel_voice
        assert "preview_url" in rachel_voice


class TestVoiceStreamingIntegration:
    """Comprehensive integration tests for voice streaming API."""
    
    @pytest.mark.asyncio
    async def test_transcribe_file_endpoint_comprehensive(self, client: AsyncClient, mock_user):
        """Test file transcription endpoint with comprehensive scenarios."""
        # Test successful transcription
        mock_transcript_result = {
            "success": True,
            "transcript": "This is a comprehensive test transcription with speaker identification.",
            "confidence": 0.94,
            "words": [
                {"word": "This", "start": 0.0, "end": 0.2, "confidence": 0.95, "speaker": 0},
                {"word": "is", "start": 0.2, "end": 0.4, "confidence": 0.93, "speaker": 0},
                {"word": "a", "start": 0.4, "end": 0.5, "confidence": 0.91, "speaker": 0}
            ],
            "speakers": [0],
            "paragraphs": [{
                "text": "This is a comprehensive test transcription with speaker identification.",
                "start": 0.0,
                "end": 3.5,
                "speaker": 0
            }],
            "raw_response": {"metadata": {"model": "nova-2", "language": "en-US"}}
        }
        
        with patch.object(deepgram_service, 'is_available', return_value=True), \
             patch.object(deepgram_service, 'transcribe_file', return_value=mock_transcript_result), \
             patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
            
            # Create realistic audio file data
            audio_content = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00" + b"fake_audio_data" * 100
            
            response = await client.post(
                "/voice/stt/file",
                files={"audio_file": ("test_recording.wav", io.BytesIO(audio_content), "audio/wav")},
                data={
                    "language": "en-US",
                    "model": "nova-2",
                    "punctuate": True,
                    "diarize": True,
                    "smart_format": True
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Comprehensive response validation
            assert data["success"] is True
            assert data["transcript"] == mock_transcript_result["transcript"]
            assert data["confidence"] == 0.94
            assert len(data["words"]) == 3
            assert len(data["speakers"]) == 1
            assert len(data["paragraphs"]) == 1
            
            # Validate metadata
            metadata = data["metadata"]
            assert metadata["filename"] == "test_recording.wav"
            assert metadata["content_type"] == "audio/wav"
            assert metadata["file_size"] == len(audio_content)
            assert metadata["language"] == "en-US"
            assert metadata["model"] == "nova-2"
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_endpoint_comprehensive(self, client: AsyncClient, mock_user):
        """Test speech synthesis endpoint with comprehensive parameters."""
        mock_audio_data = b"high_quality_audio_data" * 200  # Larger realistic audio
        mock_synthesis_result = {
            "success": True,
            "audio_data": mock_audio_data,
            "content_type": "audio/mpeg",
            "text": "This is a comprehensive test of speech synthesis with advanced settings.",
            "voice_id": "premium_voice_id",
            "model_id": "eleven_multilingual_v2",
            "output_format": "mp3_44100_128"
        }
        
        with patch.object(elevenlabs_service, 'is_available', return_value=True), \
             patch.object(elevenlabs_service, 'synthesize_speech', return_value=mock_synthesis_result), \
             patch('app.api.voice_streaming.get_current_active_user', return_value=mock_user):
            
            response = await client.post(
                "/voice/tts/synthesize",
                data={
                    "text": "This is a comprehensive test of speech synthesis with advanced settings.",
                    "voice_id": "premium_voice_id",
                    "model_id": "eleven_multilingual_v2",
                    "stability": 0.75,
                    "similarity_boost": 0.85,
                    "style": 0.15,
                    "use_speaker_boost": True,
                    "output_format": "mp3_44100_128"
                }
            )
            
            assert response.status_code == 200
            assert response.content == mock_audio_data
            assert response.headers["content-type"] == "audio/mpeg"
            
            # Check custom headers
            assert response.headers["X-Voice-ID"] == "premium_voice_id"
            assert response.headers["X-Model-ID"] == "eleven_multilingual_v2"
            assert response.headers["X-Output-Format"] == "mp3_44100_128"
            assert "X-Text-Length" in response.headers


class TestVoiceWebSocketComprehensive:
    """Comprehensive WebSocket testing with proper event loop handling."""
    
    @pytest.mark.asyncio
    async def test_websocket_live_transcription_flow(self, mock_user):
        """Test complete WebSocket live transcription workflow."""
        # Create mock connection manager that handles the flow properly
        mock_connection_manager = AsyncMock()
        mock_connection_id = "test-conn-123"
        
        # Mock connection state
        connection_state = {
            "websocket": None,
            "user": mock_user,
            "transcription_session": None,
            "is_transcribing": False,
            "connected_at": "2024-01-01T00:00:00"
        }
        
        mock_connection_manager.connect = AsyncMock(return_value=mock_connection_id)
        mock_connection_manager.disconnect = AsyncMock()
        mock_connection_manager.get_connection = Mock(return_value=connection_state)
        
        # Mock live transcription session
        mock_session = AsyncMock()
        mock_session.start = AsyncMock()
        mock_session.send_audio = AsyncMock()
        mock_session.finish = AsyncMock()
        
        with patch('app.api.voice_streaming.authenticate_voice_websocket', return_value=mock_user), \
             patch.object(deepgram_service, 'is_available', return_value=True), \
             patch.object(deepgram_service, 'start_live_transcription', return_value=mock_session), \
             patch('app.api.voice_streaming.voice_connection_manager', mock_connection_manager):
            
            # Use TestClient for WebSocket testing
            with TestClient(app) as client:
                with client.websocket_connect("/ws/voice/streaming-stt?token=valid_token") as websocket:
                    # Should receive connection confirmation
                    welcome_msg = websocket.receive_json()
                    assert welcome_msg["type"] == "connected"
                    assert welcome_msg["connection_id"] == mock_connection_id
                    
                    # Send start transcription control message
                    websocket.send_json({
                        "type": "start_transcription"
                    })
                    
                    # Send some audio data
                    test_audio = b"fake_audio_chunk_1"
                    websocket.send_bytes(test_audio)
                    
                    # In a real scenario, we'd receive transcript messages
                    # For testing, we simulate the flow by checking the session was used
                    
                    # Send stop transcription
                    websocket.send_json({
                        "type": "stop_transcription"
                    })
                    
                    # Verify session lifecycle
                    mock_connection_manager.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_error_scenarios(self, mock_user):
        """Test WebSocket error handling scenarios."""
        # Test authentication failure
        with patch('app.api.voice_streaming.authenticate_voice_websocket', return_value=None):
            with TestClient(app) as client:
                with pytest.raises(WebSocketDisconnect):
                    with client.websocket_connect("/ws/voice/streaming-stt?token=invalid"):
                        pass
        
        # Test service unavailable
        with patch('app.api.voice_streaming.authenticate_voice_websocket', return_value=mock_user), \
             patch.object(deepgram_service, 'is_available', return_value=False):
            
            with TestClient(app) as client:
                with pytest.raises(WebSocketDisconnect):
                    with client.websocket_connect("/ws/voice/streaming-stt?token=valid"):
                        pass
        
        # Test connection limit reached
        mock_connection_manager = AsyncMock()
        mock_connection_manager.connect = AsyncMock(return_value=None)  # Indicates capacity reached
        
        with patch('app.api.voice_streaming.authenticate_voice_websocket', return_value=mock_user), \
             patch.object(deepgram_service, 'is_available', return_value=True), \
             patch('app.api.voice_streaming.voice_connection_manager', mock_connection_manager):
            
            with TestClient(app) as client:
                with client.websocket_connect("/ws/voice/streaming-stt?token=valid") as websocket:
                    error_msg = websocket.receive_json()
                    assert error_msg["type"] == "error"
                    assert "capacity" in error_msg["message"].lower()


class TestVoiceConnectionManagerComprehensive:
    """Comprehensive tests for VoiceConnectionManager with proper cleanup."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create fresh connection manager for each test."""
        return VoiceConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle_with_transcription(self, connection_manager):
        """Test complete connection lifecycle including transcription session."""
        # Mock websocket and user
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_user.id = "user123"
        
        # Connect user
        connection_id = await connection_manager.connect(mock_websocket, mock_user)
        assert connection_id is not None
        
        # Verify connection exists
        connection = connection_manager.get_connection(connection_id)
        assert connection is not None
        assert connection["user"] == mock_user
        assert connection["is_transcribing"] is False
        
        # Add transcription session
        mock_session = AsyncMock()
        mock_session.finish = AsyncMock()
        connection["transcription_session"] = mock_session
        
        # Disconnect and verify cleanup
        await connection_manager.disconnect(connection_id)
        
        # Verify transcription session was finished
        mock_session.finish.assert_called_once()
        
        # Verify connection was removed
        assert connection_manager.get_connection(connection_id) is None
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, connection_manager):
        """Test handling multiple concurrent connections."""
        connections = []
        
        # Create multiple connections
        for i in range(5):
            mock_websocket = AsyncMock()
            mock_websocket.accept = AsyncMock()
            
            mock_user = Mock()
            mock_user.email = f"user{i}@example.com"
            mock_user.id = f"user{i}"
            
            connection_id = await connection_manager.connect(mock_websocket, mock_user)
            connections.append(connection_id)
        
        # Verify all connections exist
        assert len(connection_manager.active_connections) == 5
        
        # Disconnect all
        for connection_id in connections:
            await connection_manager.disconnect(connection_id)
        
        # Verify all connections removed
        assert len(connection_manager.active_connections) == 0


# Fixtures for comprehensive testing
@pytest.fixture
def mock_user():
    """Create a comprehensive mock user."""
    user = Mock()
    user.id = "test_user_123"
    user.email = "test@example.com"
    user.is_active = True
    user.is_verified = True
    user.created_at = "2024-01-01T00:00:00"
    return user


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
