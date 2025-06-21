import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
import asyncio

from app.services.voice.soniox_service import (
    SonioxService, 
    soniox_service,
    LiveTranscriptionSession
)
from app.core.config import settings


class TestSonioxService:
    """Test suite for SonioxService."""
    
    @pytest.fixture
    def mock_soniox_client(self):
        """Create a mock Soniox client."""
        client = MagicMock()
        client.transcribe = MagicMock()
        return client
    
    @pytest.fixture
    def soniox_service_with_client(self, mock_soniox_client):
        """Create SonioxService with mock client."""
        with patch('app.services.voice.soniox_service.speech_service') as mock_speech_service:
            mock_speech_service.set_api_key = MagicMock()
            mock_speech_service.SpeechClient.return_value = mock_soniox_client
            
            service = SonioxService()
            service.available = True
            service._test_client = mock_soniox_client  # Store for test access
            return service
    
    @pytest.fixture
    def soniox_service_no_client(self):
        """Create SonioxService without client (API key not set)."""
        with patch.object(settings, 'SONIOX_API_KEY', 'NOT_SET'):
            return SonioxService()
    
    def test_soniox_service_initialization_with_api_key(self):
        """Test SonioxService initialization with valid API key."""
        with patch.object(settings, 'SONIOX_API_KEY', 'test_api_key'), \
             patch('app.services.voice.soniox_service.speech_service') as mock_speech_service:
            
            mock_speech_service.set_api_key = MagicMock()
            
            service = SonioxService()
            
            assert service.available is True
            mock_speech_service.set_api_key.assert_called_once_with('test_api_key')
    
    def test_soniox_service_initialization_no_api_key(self):
        """Test SonioxService initialization without API key."""
        with patch.object(settings, 'SONIOX_API_KEY', 'NOT_SET'):
            service = SonioxService()
            assert service.available is False
    
    def test_soniox_service_initialization_error(self):
        """Test SonioxService initialization with client creation error."""
        with patch.object(settings, 'SONIOX_API_KEY', 'test_api_key'), \
             patch('app.services.voice.soniox_service.speech_service.set_api_key', 
                   side_effect=Exception("Client creation failed")):
            
            service = SonioxService()
            assert service.available is False
    
    def test_is_available(self, soniox_service_with_client, soniox_service_no_client):
        """Test service availability check."""
        assert soniox_service_with_client.is_available() is True
        assert soniox_service_no_client.is_available() is False
    
    @pytest.mark.asyncio
    async def test_transcribe_file_success(self, soniox_service_with_client):
        """Test successful file transcription."""
        # Mock Soniox result
        mock_word1 = MagicMock()
        mock_word1.text = "Hello"
        mock_word1.start_ms = 0
        mock_word1.end_ms = 500
        mock_word1.confidence = 0.9
        
        mock_word2 = MagicMock()
        mock_word2.text = "world"
        mock_word2.start_ms = 600
        mock_word2.end_ms = 1000
        mock_word2.confidence = 0.95
        
        mock_result = MagicMock()
        mock_result.words = [mock_word1, mock_word2]
        
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            audio_data = b"fake_audio_data"
            result = await soniox_service_with_client.transcribe_file(
                audio_data=audio_data,
                content_type="audio/wav",
                language="en-US"
            )
            
            assert result["success"] is True
            assert result["transcript"] == "Hello world"
            assert len(result["words"]) == 2
            assert result["words"][0]["word"] == "Hello"
            assert result["words"][0]["start"] == 0.0
            assert result["words"][1]["word"] == "world"
            assert result["words"][1]["start"] == 0.6
            assert result["confidence"] > 0.9
    
    @pytest.mark.asyncio
    async def test_transcribe_file_service_unavailable(self, soniox_service_no_client):
        """Test transcription when service is unavailable."""
        with pytest.raises(RuntimeError, match="Soniox service not available"):
            await soniox_service_no_client.transcribe_file(b"audio_data")
    
    @pytest.mark.asyncio
    async def test_transcribe_file_with_diarization(self, soniox_service_with_client):
        """Test transcription with speaker diarization."""
        # Mock Soniox result with speaker information
        mock_word1 = MagicMock()
        mock_word1.text = "Speaker"
        mock_word1.start_ms = 0
        mock_word1.end_ms = 500
        mock_word1.confidence = 0.9
        mock_word1.speaker = 0
        
        mock_word2 = MagicMock()
        mock_word2.text = "one"
        mock_word2.start_ms = 600
        mock_word2.end_ms = 800
        mock_word2.confidence = 0.9
        mock_word2.speaker = 0
        
        mock_word3 = MagicMock()
        mock_word3.text = "Speaker"
        mock_word3.start_ms = 1000
        mock_word3.end_ms = 1500
        mock_word3.confidence = 0.9
        mock_word3.speaker = 1
        
        mock_word4 = MagicMock()
        mock_word4.text = "two"
        mock_word4.start_ms = 1600
        mock_word4.end_ms = 1800
        mock_word4.confidence = 0.9
        mock_word4.speaker = 1
        
        mock_result = MagicMock()
        mock_result.words = [mock_word1, mock_word2, mock_word3, mock_word4]
        
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            result = await soniox_service_with_client.transcribe_file(
                audio_data=b"audio_data",
                diarize=True
            )
            
            assert result["success"] is True
            assert len(result["speakers"]) == 2
            assert 0 in result["speakers"]
            assert 1 in result["speakers"]
            assert all(word.get("speaker") is not None for word in result["words"])
    
    @pytest.mark.asyncio
    async def test_transcribe_file_error(self, soniox_service_with_client):
        """Test transcription error handling."""
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.side_effect = Exception("Transcription failed")
            mock_client_class.return_value = mock_client
            
            result = await soniox_service_with_client.transcribe_file(b"audio_data")
            
            assert result["success"] is False
            assert "error" in result
            assert "Transcription failed" in result["error"]
            assert result["transcript"] == ""
            assert result["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_transcribe_file_empty_response(self, soniox_service_with_client):
        """Test handling of empty transcription response."""
        mock_result = MagicMock()
        mock_result.words = []
        
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            result = await soniox_service_with_client.transcribe_file(b"audio_data")
            
            assert result["success"] is True
            assert result["transcript"] == ""
            assert result["confidence"] == 0.0
            assert result["words"] == []
            assert result["speakers"] == []
    
    @pytest.mark.asyncio
    async def test_start_live_transcription_success(self, soniox_service_with_client):
        """Test starting live transcription session."""
        mock_on_message = MagicMock()
        mock_on_error = MagicMock()
        
        session = await soniox_service_with_client.start_live_transcription(
            on_message=mock_on_message,
            on_error=mock_on_error,
            language="en-US"
        )
        
        assert isinstance(session, LiveTranscriptionSession)
        assert session.on_message == mock_on_message
        assert session.on_error == mock_on_error
    
    @pytest.mark.asyncio
    async def test_start_live_transcription_service_unavailable(self, soniox_service_no_client):
        """Test starting live transcription when service unavailable."""
        with pytest.raises(RuntimeError, match="Soniox service not available"):
            await soniox_service_no_client.start_live_transcription(
                on_message=MagicMock()
            )
    
    @pytest.mark.asyncio
    async def test_start_live_transcription_with_auto_detection(self, soniox_service_with_client):
        """Test live transcription with language auto-detection."""
        session = await soniox_service_with_client.start_live_transcription(
            on_message=MagicMock(),
            detect_language=True
        )
        
        assert isinstance(session, LiveTranscriptionSession)
        # Config should not have specific language set when auto-detecting


class TestLiveTranscriptionSession:
    """Test suite for LiveTranscriptionSession."""
    
    @pytest.fixture
    def mock_transcription_config(self):
        """Create mock TranscriptionConfig."""
        with patch('app.services.voice.soniox_service.TranscriptionConfig') as mock_config_class:
            config = MagicMock()
            config.sample_rate_hertz = 16000
            config.num_audio_channels = 1
            config.include_nonfinal = True
            mock_config_class.return_value = config
            return config
    
    @pytest.fixture
    def live_session(self, mock_transcription_config):
        """Create a LiveTranscriptionSession for testing."""
        on_message = MagicMock()
        on_error = MagicMock()
        
        session = LiveTranscriptionSession(
            config=mock_transcription_config,
            on_message=on_message,
            on_error=on_error
        )
        
        return session
    
    def test_live_session_initialization(self, live_session, mock_transcription_config):
        """Test LiveTranscriptionSession initialization."""
        assert live_session.config == mock_transcription_config
        assert live_session.client is None
        assert live_session.is_connected is False
        assert live_session.on_message is not None
        assert live_session.on_error is not None
        assert live_session._running is False
    
    @pytest.mark.asyncio
    async def test_start_session_success(self, live_session):
        """Test starting live transcription session successfully."""
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value = mock_client
            
            await live_session.start()
            
            assert live_session.client is not None
            assert live_session.is_connected is True
            assert live_session._running is True
            assert live_session._process_task is not None
    
    @pytest.mark.asyncio
    async def test_start_session_exception(self, live_session):
        """Test handling exception during session start."""
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient', 
                   side_effect=Exception("Connection failed")):
            
            with pytest.raises(Exception, match="Connection failed"):
                await live_session.start()
            
            # Error handler should be called
            live_session.on_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_audio_success(self, live_session):
        """Test sending audio data successfully."""
        # Set up connected session
        live_session.is_connected = True
        live_session._audio_queue = AsyncMock()
        
        audio_data = b"test_audio_data"
        await live_session.send_audio(audio_data)
        
        live_session._audio_queue.put.assert_called_once_with(audio_data)
    
    @pytest.mark.asyncio
    async def test_send_audio_not_connected(self, live_session):
        """Test sending audio when not connected."""
        audio_data = b"test_audio_data"
        
        with pytest.raises(RuntimeError, match="Transcription session not connected"):
            await live_session.send_audio(audio_data)
    
    @pytest.mark.asyncio
    async def test_send_audio_error(self, live_session):
        """Test handling error during audio send."""
        live_session.is_connected = True
        live_session._audio_queue = AsyncMock()
        live_session._audio_queue.put.side_effect = Exception("Queue error")
        
        with pytest.raises(Exception, match="Queue error"):
            await live_session.send_audio(b"audio_data")
        
        live_session.on_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_finish_session(self, live_session):
        """Test finishing the transcription session."""
        live_session._running = True
        live_session._audio_queue = AsyncMock()
        live_session._process_task = AsyncMock()
        
        await live_session.finish()
        
        assert live_session._running is False
        assert live_session.is_connected is False
        live_session._audio_queue.put.assert_called_once_with(None)  # Stop signal
    
    @pytest.mark.asyncio
    async def test_finish_session_not_running(self, live_session):
        """Test finishing when not running."""
        # Should not raise an exception
        await live_session.finish()
    
    @pytest.mark.asyncio
    async def test_finish_session_error(self, live_session):
        """Test handling error during session finish."""
        live_session._running = True
        live_session._audio_queue = AsyncMock()
        live_session._audio_queue.put.side_effect = Exception("Finish failed")
        
        await live_session.finish()
        
        live_session.on_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transcribe_chunk_success(self, live_session):
        """Test transcribing an audio chunk successfully."""
        # Mock client and result
        mock_client = MagicMock()
        
        mock_word = MagicMock()
        mock_word.text = "test"
        mock_word.start_ms = 0
        mock_word.end_ms = 500
        mock_word.confidence = 0.9
        
        mock_result = MagicMock()
        mock_result.words = [mock_word]
        
        mock_client.transcribe.return_value = mock_result
        live_session.client = mock_client
        
        audio_data = b"test_audio_data" * 200  # Make it large enough
        await live_session._transcribe_chunk(audio_data)
        
        mock_client.transcribe.assert_called_once_with(audio_data, live_session.config)
    
    @pytest.mark.asyncio
    async def test_transcribe_chunk_too_small(self, live_session):
        """Test skipping transcription for tiny chunks."""
        mock_client = MagicMock()
        live_session.client = mock_client
        
        # Send tiny audio data
        tiny_audio = b"small"
        await live_session._transcribe_chunk(tiny_audio)
        
        # Should not call transcribe for tiny chunks
        mock_client.transcribe.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_transcribe_chunk_error(self, live_session):
        """Test handling error during chunk transcription."""
        mock_client = MagicMock()
        mock_client.transcribe.side_effect = Exception("Transcription error")
        live_session.client = mock_client
        
        audio_data = b"test_audio_data" * 200
        
        # Should not raise exception (errors are logged but not propagated)
        await live_session._transcribe_chunk(audio_data)
        
        # Error should not be propagated to avoid stopping the stream
        live_session.on_error.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_result_success(self, live_session):
        """Test handling a successful transcription result."""
        # Mock result with words
        mock_word1 = MagicMock()
        mock_word1.text = "Hello"
        mock_word1.start_ms = 0
        mock_word1.end_ms = 500
        mock_word1.confidence = 0.95
        
        mock_word2 = MagicMock()
        mock_word2.text = "world"
        mock_word2.start_ms = 600
        mock_word2.end_ms = 1000
        mock_word2.confidence = 0.90
        
        mock_result = MagicMock()
        mock_result.words = [mock_word1, mock_word2]
        
        await live_session._handle_result(mock_result)
        
        # Verify on_message was called
        live_session.on_message.assert_called_once()
        call_args = live_session.on_message.call_args[0][0]
        
        assert call_args["type"] == "transcript"
        assert call_args["transcript"] == "Hello world"
        assert call_args["is_final"] is True
        assert call_args["speech_final"] is True
        assert call_args["confidence"] == 0.925  # Average of 0.95 and 0.90
        assert len(call_args["words"]) == 2
        assert call_args["detected_language"] == "auto"
    
    @pytest.mark.asyncio
    async def test_handle_result_empty(self, live_session):
        """Test handling empty result."""
        mock_result = MagicMock()
        mock_result.words = []
        
        await live_session._handle_result(mock_result)
        
        # Should not call on_message for empty results
        live_session.on_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_result_no_result(self, live_session):
        """Test handling None result."""
        await live_session._handle_result(None)
        
        # Should not call on_message for None results
        live_session.on_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_result_exception(self, live_session):
        """Test handling exception during result processing."""
        # Create a result that will cause an exception
        mock_result = MagicMock()
        mock_word = MagicMock()
        # Make text property raise an exception when accessed
        type(mock_word).text = property(lambda self: exec('raise Exception("Processing error")'))
        mock_result.words = [mock_word]
        
        await live_session._handle_result(mock_result)
        
        # Error handler should be called
        live_session.on_error.assert_called_once()


class TestSonioxServiceSingleton:
    """Test the Soniox service singleton."""
    
    def test_singleton_exists(self):
        """Test that soniox service singleton exists."""
        assert soniox_service is not None
        assert isinstance(soniox_service, SonioxService)
    
    def test_singleton_availability_depends_on_config(self):
        """Test singleton availability depends on configuration."""
        # This test depends on actual settings, so we just verify the method exists
        availability = soniox_service.is_available()
        assert isinstance(availability, bool)


class TestSonioxServiceIntegration:
    """Integration tests for Soniox service components."""
    
    @pytest.mark.asyncio
    async def test_full_transcription_workflow(self):
        """Test a complete transcription workflow."""
        # Mock service
        service = SonioxService()
        service.available = True
        
        # Mock successful transcription response
        mock_word1 = MagicMock()
        mock_word1.text = "Complete"
        mock_word1.start_ms = 0
        mock_word1.end_ms = 800
        mock_word1.confidence = 0.9
        
        mock_word2 = MagicMock()
        mock_word2.text = "transcription"
        mock_word2.start_ms = 900
        mock_word2.end_ms = 1800
        mock_word2.confidence = 0.95
        
        mock_word3 = MagicMock()
        mock_word3.text = "test"
        mock_word3.start_ms = 1900
        mock_word3.end_ms = 2200
        mock_word3.confidence = 0.9
        
        mock_result = MagicMock()
        mock_result.words = [mock_word1, mock_word2, mock_word3]
        
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            # Test transcription with various options
            result = await service.transcribe_file(
                audio_data=b"test_audio_data",
                content_type="audio/wav",
                language="en-US",
                punctuate=True,
                diarize=False,
                smart_format=True
            )
            
            # Verify complete result structure
            assert result["success"] is True
            assert result["transcript"] == "Complete transcription test"
            assert result["confidence"] == 0.9166666666666666  # Average confidence
            assert len(result["words"]) == 3
            assert "raw_response" in result
            
            # Verify word-level data
            words = result["words"]
            assert words[0]["word"] == "Complete"
            assert words[1]["word"] == "transcription"
            assert words[2]["word"] == "test"
            
            # Verify timestamps (converted from ms to seconds)
            assert words[0]["start"] == 0.0
            assert words[2]["end"] == 2.2
    
    @pytest.mark.asyncio
    async def test_live_transcription_session_lifecycle(self):
        """Test complete live transcription session lifecycle."""
        service = SonioxService()
        service.available = True
        
        # Track messages
        received_messages = []
        
        def message_handler(data):
            received_messages.append(data)
        
        def error_handler(error):
            pytest.fail(f"Unexpected error: {error}")
        
        # Start session
        session = await service.start_live_transcription(
            on_message=message_handler,
            on_error=error_handler,
            language="en-US",
            interim_results=True
        )
        
        # Mock client for session start
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value = mock_client
            
            # Simulate session start
            await session.start()
            assert session.is_connected is True
            
            # Simulate sending audio data
            session._audio_queue = AsyncMock()
            audio_chunks = [b"chunk1", b"chunk2", b"chunk3"]
            for chunk in audio_chunks:
                await session.send_audio(chunk)
            
            # Verify all chunks were queued
            assert session._audio_queue.put.call_count == len(audio_chunks)
            
            # Simulate transcript reception
            mock_word = MagicMock()
            mock_word.text = "Live"
            mock_word.start_ms = 0
            mock_word.end_ms = 500
            mock_word.confidence = 0.88
            
            mock_word2 = MagicMock()
            mock_word2.text = "transcription"
            mock_word2.start_ms = 600
            mock_word2.end_ms = 1500
            mock_word2.confidence = 0.92
            
            mock_result = MagicMock()
            mock_result.words = [mock_word, mock_word2]
            
            await session._handle_result(mock_result)
            
            # Verify message was received
            assert len(received_messages) == 1
            assert received_messages[0]["transcript"] == "Live transcription"
            assert received_messages[0]["is_final"] is True
            
            # Finish session
            await session.finish()
            assert session.is_connected is False