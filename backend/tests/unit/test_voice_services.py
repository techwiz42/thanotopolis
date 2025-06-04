# tests/test_voice_services.py
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
from app.services.voice.deepgram_service import DeepgramService, LiveTranscriptionSession
from app.services.voice.elevenlabs_service import ElevenLabsService
from app.core.config import settings


class TestDeepgramService:
    """Unit tests for DeepgramService."""
    
    @pytest.fixture
    def deepgram_service(self):
        """Create a DeepgramService instance for testing."""
        with patch('app.services.voice.deepgram_service.settings') as mock_settings:
            mock_settings.DEEPGRAM_API_KEY = "test_key"
            mock_settings.DEEPGRAM_MODEL = "nova-2"
            mock_settings.DEEPGRAM_LANGUAGE = "en-US"
            
            with patch('app.services.voice.deepgram_service.DeepgramClient') as mock_client:
                service = DeepgramService()
                service.client = mock_client
                return service
    
    def test_is_available_with_key(self, deepgram_service):
        """Test service availability with valid API key."""
        assert deepgram_service.is_available() is True
    
    def test_is_available_without_key(self):
        """Test service availability without API key."""
        with patch('app.services.voice.deepgram_service.settings') as mock_settings:
            mock_settings.DEEPGRAM_API_KEY = "NOT_SET"
            service = DeepgramService()
            assert service.is_available() is False
    
    @pytest.mark.asyncio
    async def test_transcribe_file_success(self, deepgram_service):
        """Test successful file transcription."""
        # Mock response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Hello world",
                        "confidence": 0.95,
                        "words": [
                            {"word": "Hello", "start": 0.0, "end": 0.5, "confidence": 0.95},
                            {"word": "world", "start": 0.6, "end": 1.0, "confidence": 0.93}
                        ],
                        "paragraphs": {
                            "paragraphs": [{
                                "text": "Hello world",
                                "start": 0.0,
                                "end": 1.0
                            }]
                        }
                    }]
                }]
            }
        }
        
        # Mock client methods
        deepgram_service.client.listen.asyncprerecorded.v.return_value.transcribe_file = AsyncMock(
            return_value=mock_response
        )
        
        # Test transcription
        audio_data = b"fake_audio_data"
        result = await deepgram_service.transcribe_file(audio_data)
        
        assert result["success"] is True
        assert result["transcript"] == "Hello world"
        assert result["confidence"] == 0.95
        assert len(result["words"]) == 2
        assert len(result["paragraphs"]) == 1
    
    @pytest.mark.asyncio
    async def test_transcribe_file_error(self, deepgram_service):
        """Test file transcription with error."""
        # Mock client to raise exception
        deepgram_service.client.listen.asyncprerecorded.v.return_value.transcribe_file = AsyncMock(
            side_effect=Exception("API error")
        )
        
        audio_data = b"fake_audio_data"
        result = await deepgram_service.transcribe_file(audio_data)
        
        assert result["success"] is False
        assert "API error" in result["error"]
        assert result["transcript"] == ""
    
    @pytest.mark.asyncio
    async def test_start_live_transcription(self, deepgram_service):
        """Test starting live transcription session."""
        # Mock client
        mock_connection = Mock()
        deepgram_service.client.listen.asynclive.v.return_value = mock_connection
        
        # Mock callback
        on_message = Mock()
        
        # Start session
        session = await deepgram_service.start_live_transcription(on_message)
        
        assert isinstance(session, LiveTranscriptionSession)
        assert session.client == deepgram_service.client
        assert session.on_message == on_message


class TestLiveTranscriptionSession:
    """Unit tests for LiveTranscriptionSession."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Deepgram client."""
        return Mock()
    
    @pytest.fixture
    def mock_options(self):
        """Create mock live options."""
        return Mock()
    
    @pytest.fixture
    def session(self, mock_client, mock_options):
        """Create a LiveTranscriptionSession for testing."""
        on_message = Mock()
        return LiveTranscriptionSession(mock_client, mock_options, on_message)
    
    @pytest.mark.asyncio
    async def test_start_session_success(self, session, mock_client):
        """Test successful session start."""
        # Mock connection
        mock_connection = Mock()
        mock_connection.start = AsyncMock(return_value=True)
        mock_client.listen.asynclive.v.return_value = mock_connection
        
        await session.start()
        
        assert session.is_connected is True
        assert session.connection == mock_connection
    
    @pytest.mark.asyncio
    async def test_start_session_failure(self, session, mock_client):
        """Test session start failure."""
        # Mock connection
        mock_connection = Mock()
        mock_connection.start = AsyncMock(return_value=False)
        mock_client.listen.asynclive.v.return_value = mock_connection
        
        with pytest.raises(RuntimeError):
            await session.start()
    
    @pytest.mark.asyncio
    async def test_send_audio(self, session):
        """Test sending audio data."""
        # Setup session
        session.is_connected = True
        session.connection = Mock()
        session.connection.send = AsyncMock()
        
        audio_data = b"audio_chunk"
        await session.send_audio(audio_data)
        
        session.connection.send.assert_called_once_with(audio_data)
    
    @pytest.mark.asyncio
    async def test_send_audio_not_connected(self, session):
        """Test sending audio when not connected."""
        session.is_connected = False
        
        with pytest.raises(RuntimeError):
            await session.send_audio(b"audio")
    
    @pytest.mark.asyncio
    async def test_finish_session(self, session):
        """Test finishing transcription session."""
        # Setup session
        session.is_connected = True
        session.connection = Mock()
        session.connection.finish = AsyncMock()
        
        await session.finish()
        
        assert session.is_connected is False
        session.connection.finish.assert_called_once()
    
    def test_handle_transcript(self, session):
        """Test transcript message handling."""
        # Mock transcript data
        transcript_data = {
            "channel_index": 0,
            "duration": 2.5,
            "start": 0.0,
            "is_final": True,
            "speech_final": True,
            "channel": {
                "alternatives": [{
                    "transcript": "Test transcript",
                    "confidence": 0.9,
                    "words": []
                }]
            },
            "metadata": {}
        }
        
        session._handle_transcript(transcript_data)
        
        # Verify callback was called with formatted data
        session.on_message.assert_called_once()
        called_args = session.on_message.call_args[0][0]
        assert called_args["type"] == "transcript"
        assert called_args["transcript"] == "Test transcript"
        assert called_args["confidence"] == 0.9
        assert called_args["is_final"] is True


class TestElevenLabsService:
    """Unit tests for ElevenLabsService."""
    
    @pytest.fixture
    def elevenlabs_service(self):
        """Create an ElevenLabsService instance for testing."""
        with patch('app.services.voice.elevenlabs_service.settings') as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_key"
            mock_settings.ELEVENLABS_VOICE_ID = "test_voice"
            mock_settings.ELEVENLABS_MODEL = "eleven_turbo_v2_5"
            mock_settings.ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
            mock_settings.ELEVENLABS_OPTIMIZE_STREAMING_LATENCY = 3
            return ElevenLabsService()
    
    def test_is_available_with_key(self, elevenlabs_service):
        """Test service availability with valid API key."""
        assert elevenlabs_service.is_available() is True
    
    def test_is_available_without_key(self):
        """Test service availability without API key."""
        with patch('app.services.voice.elevenlabs_service.settings') as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "NOT_SET"
            service = ElevenLabsService()
            assert service.is_available() is False
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_voices_success(self, mock_session_class, elevenlabs_service):
        """Test successful voice retrieval."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "voices": [
                {"voice_id": "voice1", "name": "Voice 1"},
                {"voice_id": "voice2", "name": "Voice 2"}
            ]
        })
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        result = await elevenlabs_service.get_voices()
        
        assert result["success"] is True
        assert len(result["voices"]) == 2
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_voices_error(self, mock_session_class, elevenlabs_service):
        """Test voice retrieval with API error."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        result = await elevenlabs_service.get_voices()
        
        assert result["success"] is False
        assert "API error" in result["error"]
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_synthesize_speech_success(self, mock_session_class, elevenlabs_service):
        """Test successful speech synthesis."""
        # Mock response
        mock_audio_data = b"fake_audio_data"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=mock_audio_data)
        mock_response.headers = {"content-type": "audio/mpeg"}
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        result = await elevenlabs_service.synthesize_speech("Hello world")
        
        assert result["success"] is True
        assert result["audio_data"] == mock_audio_data
        assert result["content_type"] == "audio/mpeg"
        assert result["text"] == "Hello world"
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_synthesize_speech_error(self, mock_session_class, elevenlabs_service):
        """Test speech synthesis with API error."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad request")
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        result = await elevenlabs_service.synthesize_speech("Hello world")
        
        assert result["success"] is False
        assert "API error" in result["error"]
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_stream_speech_success(self, mock_session_class, elevenlabs_service):
        """Test successful speech streaming."""
        # Mock response chunks
        mock_chunks = [b"chunk1", b"chunk2", b"chunk3"]
        
        async def mock_iter_chunked(chunk_size):
            for chunk in mock_chunks:
                yield chunk
        
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.iter_chunked = mock_iter_chunked
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        # Collect streamed chunks
        chunks = []
        async for chunk in elevenlabs_service.stream_speech("Hello world"):
            chunks.append(chunk)
        
        assert chunks == mock_chunks
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_user_info_success(self, mock_session_class, elevenlabs_service):
        """Test successful user info retrieval."""
        # Mock response
        mock_user_info = {
            "subscription": {"tier": "starter"},
            "character_count": 1000,
            "character_limit": 10000
        }
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_user_info)
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        result = await elevenlabs_service.get_user_info()
        
        assert result["success"] is True
        assert result["user_info"] == mock_user_info
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_models_success(self, mock_session_class, elevenlabs_service):
        """Test successful models retrieval."""
        # Mock response
        mock_models = [
            {"model_id": "eleven_turbo_v2", "name": "Turbo v2"},
            {"model_id": "eleven_multilingual_v2", "name": "Multilingual v2"}
        ]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_models)
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        result = await elevenlabs_service.get_models()
        
        assert result["success"] is True
        assert result["models"] == mock_models


# Integration test fixtures and helpers
@pytest.fixture
def mock_audio_file():
    """Create a mock audio file for testing."""
    return b"fake_wav_audio_data"


@pytest.fixture
def mock_text():
    """Create mock text for TTS testing."""
    return "This is a test sentence for text-to-speech synthesis."


class TestVoiceServiceIntegration:
    """Integration tests for voice services."""
    
    @pytest.mark.asyncio
    async def test_full_stt_workflow(self):
        """Test complete STT workflow with mocked services."""
        with patch('app.services.voice.deepgram_service.DeepgramClient') as mock_client_class:
            # Mock client and response
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.to_dict.return_value = {
                "results": {
                    "channels": [{
                        "alternatives": [{
                            "transcript": "Integration test transcript",
                            "confidence": 0.9
                        }]
                    }]
                }
            }
            
            mock_client.listen.asyncprerecorded.v.return_value.transcribe_file = AsyncMock(
                return_value=mock_response
            )
            
            # Test service
            with patch('app.services.voice.deepgram_service.settings') as mock_settings:
                mock_settings.DEEPGRAM_API_KEY = "test_key"
                mock_settings.DEEPGRAM_MODEL = "nova-2"
                mock_settings.DEEPGRAM_LANGUAGE = "en-US"
                
                service = DeepgramService()
                
                # Test transcription
                result = await service.transcribe_file(b"fake_audio")
                
                assert result["success"] is True
                assert "Integration test transcript" in result["transcript"]
    
    @pytest.mark.asyncio
    async def test_full_tts_workflow(self):
        """Test complete TTS workflow with mocked services."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Mock response
            mock_audio_data = b"generated_audio_data"
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=mock_audio_data)
            mock_response.headers = {"content-type": "audio/mpeg"}
            
            # Mock session
            mock_session = AsyncMock()
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # Test service
            with patch('app.services.voice.elevenlabs_service.settings') as mock_settings:
                mock_settings.ELEVENLABS_API_KEY = "test_key"
                mock_settings.ELEVENLABS_VOICE_ID = "test_voice"
                mock_settings.ELEVENLABS_MODEL = "eleven_turbo_v2_5"
                mock_settings.ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
                mock_settings.ELEVENLABS_OPTIMIZE_STREAMING_LATENCY = 3
                
                service = ElevenLabsService()
                
                # Test synthesis
                result = await service.synthesize_speech("Test text")
                
                assert result["success"] is True
                assert result["audio_data"] == mock_audio_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
