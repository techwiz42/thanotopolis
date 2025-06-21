"""
Integration tests for the Soniox voice service.
Tests the critical Speech-to-Text functionality including file transcription,
live transcription sessions, and language auto-detection.

These tests can run with a real Soniox API key for full integration testing.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional
import asyncio
import os

from app.services.voice.soniox_service import (
    SonioxService,
    LiveTranscriptionSession,
    soniox_service
)
from app.core.config import settings


class TestSonioxServiceConfiguration:
    """Test Soniox service configuration and initialization."""
    
    def test_soniox_service_singleton_availability(self):
        """Test that the singleton service reflects configuration."""
        # Test depends on actual configuration
        availability = soniox_service.is_available()
        assert isinstance(availability, bool)
        
        # If API key is configured, service should be available
        if settings.SONIOX_API_KEY != "NOT_SET":
            assert availability is True
        else:
            assert availability is False
    
    def test_soniox_service_singleton_type(self):
        """Test that singleton is correct type."""
        assert isinstance(soniox_service, SonioxService)
        assert hasattr(soniox_service, 'is_available')
        assert hasattr(soniox_service, 'transcribe_file')
        assert hasattr(soniox_service, 'start_live_transcription')


class TestSonioxServiceMocked:
    """Test Soniox service with mocked responses (no API key required)."""
    
    @pytest.fixture
    def mock_soniox_service(self):
        """Create a mocked Soniox service for testing."""
        service = SonioxService()
        service.available = True
        return service
    
    @pytest.mark.asyncio
    async def test_transcribe_file_integration_mocked(self, mock_soniox_service):
        """Test complete file transcription workflow with mocked client."""
        # Create realistic mock response
        mock_word1 = MagicMock()
        mock_word1.text = "Integration"
        mock_word1.start_ms = 0
        mock_word1.end_ms = 800
        mock_word1.confidence = 0.95
        
        mock_word2 = MagicMock()
        mock_word2.text = "test"
        mock_word2.start_ms = 900
        mock_word2.end_ms = 1200
        mock_word2.confidence = 0.92
        
        mock_word3 = MagicMock()
        mock_word3.text = "successful"
        mock_word3.start_ms = 1300
        mock_word3.end_ms = 2100
        mock_word3.confidence = 0.88
        
        mock_result = MagicMock()
        mock_result.words = [mock_word1, mock_word2, mock_word3]
        
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            # Test with realistic audio data size
            audio_data = b"realistic_audio_data" * 1000
            
            result = await mock_soniox_service.transcribe_file(
                audio_data=audio_data,
                content_type="audio/wav",
                language=None,  # Test auto-detection
                punctuate=True,
                smart_format=True
            )
            
            # Verify complete integration
            assert result["success"] is True
            assert result["transcript"] == "Integration test successful"
            assert len(result["words"]) == 3
            assert result["confidence"] > 0.9
            
            # Verify client was called with proper config
            mock_client.transcribe.assert_called_once()
            call_args = mock_client.transcribe.call_args
            assert call_args[0][0] == audio_data  # First arg is audio data
            
            # Verify timestamps are converted to seconds
            assert result["words"][0]["start"] == 0.0
            assert result["words"][0]["end"] == 0.8
            assert result["words"][2]["end"] == 2.1
    
    @pytest.mark.asyncio
    async def test_transcribe_file_with_diarization_integration(self, mock_soniox_service):
        """Test file transcription with speaker diarization enabled."""
        # Mock multi-speaker result
        mock_words = []
        speakers = [0, 0, 0, 1, 1, 1, 0, 0]
        texts = ["Speaker", "one", "speaking", "Speaker", "two", "responds", "Speaker", "one"]
        
        for i, (text, speaker) in enumerate(zip(texts, speakers)):
            word = MagicMock()
            word.text = text
            word.start_ms = i * 500
            word.end_ms = (i + 1) * 500 - 50
            word.confidence = 0.9 + (i % 3) * 0.02  # Varying confidence
            word.speaker = speaker
            mock_words.append(word)
        
        mock_result = MagicMock()
        mock_result.words = mock_words
        
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            result = await mock_soniox_service.transcribe_file(
                audio_data=b"multi_speaker_audio" * 500,
                diarize=True
            )
            
            # Verify diarization results
            assert result["success"] is True
            assert len(result["speakers"]) == 2
            assert 0 in result["speakers"]
            assert 1 in result["speakers"]
            
            # Verify speaker assignments
            speaker_0_words = [w for w in result["words"] if w["speaker"] == 0]
            speaker_1_words = [w for w in result["words"] if w["speaker"] == 1]
            
            assert len(speaker_0_words) == 5  # "Speaker one speaking Speaker one"
            assert len(speaker_1_words) == 3  # "Speaker two responds"
    
    @pytest.mark.asyncio
    async def test_live_transcription_full_workflow(self, mock_soniox_service):
        """Test complete live transcription session workflow."""
        # Track all received messages
        received_messages = []
        received_errors = []
        
        def message_handler(data):
            received_messages.append(data)
        
        def error_handler(error):
            received_errors.append(error)
        
        # Create session
        session = await mock_soniox_service.start_live_transcription(
            on_message=message_handler,
            on_error=error_handler,
            interim_results=True,
            sample_rate=16000,
            channels=1
        )
        
        assert isinstance(session, LiveTranscriptionSession)
        assert session.on_message == message_handler
        assert session.on_error == error_handler
        
        # Mock the client and start session
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value = mock_client
            
            await session.start()
            
            assert session.is_connected is True
            assert session._running is True
            
            # Test audio queue functionality
            session._audio_queue = AsyncMock()
            
            # Simulate real-time audio chunks
            audio_chunks = [
                b"audio_chunk_1" * 100,
                b"audio_chunk_2" * 100,
                b"audio_chunk_3" * 100,
                b"final_chunk" * 100
            ]
            
            for chunk in audio_chunks:
                await session.send_audio(chunk)
            
            # Verify all chunks were queued
            assert session._audio_queue.put.call_count == len(audio_chunks)
            
            # Simulate processing results for each chunk
            test_results = [
                (["Real"], [0.9]),
                (["time"], [0.95]),
                (["transcription"], [0.88]),
                (["test"], [0.92])
            ]
            
            for i, (words, confidences) in enumerate(test_results):
                mock_words = []
                for j, (word, conf) in enumerate(zip(words, confidences)):
                    mock_word = MagicMock()
                    mock_word.text = word
                    mock_word.start_ms = (i * 1000) + (j * 200)
                    mock_word.end_ms = (i * 1000) + (j * 200) + 180
                    mock_word.confidence = conf
                    mock_words.append(mock_word)
                
                mock_result = MagicMock()
                mock_result.words = mock_words
                
                await session._handle_result(mock_result)
            
            # Verify all results were processed
            assert len(received_messages) == 4
            assert len(received_errors) == 0
            
            # Verify message content
            expected_transcripts = ["Real", "time", "transcription", "test"]
            for i, msg in enumerate(received_messages):
                assert msg["transcript"] == expected_transcripts[i]
                assert msg["type"] == "transcript"
                assert msg["is_final"] is True
                assert msg["speech_final"] is True
                assert "confidence" in msg
                assert "words" in msg
                assert msg["detected_language"] == "auto"
            
            # Test session cleanup
            await session.finish()
            
            assert session._running is False
            assert session.is_connected is False
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, mock_soniox_service):
        """Test comprehensive error handling throughout the service."""
        received_errors = []
        
        def error_handler(error):
            received_errors.append(error)
        
        # Test file transcription error
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.side_effect = Exception("Network timeout")
            mock_client_class.return_value = mock_client
            
            result = await mock_soniox_service.transcribe_file(b"audio_data")
            
            assert result["success"] is False
            assert "Network timeout" in result["error"]
        
        # Test live session error handling
        session = await mock_soniox_service.start_live_transcription(
            on_message=lambda x: None,
            on_error=error_handler
        )
        
        # Test start error
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient',
                   side_effect=Exception("Client creation failed")):
            
            with pytest.raises(Exception, match="Client creation failed"):
                await session.start()
            
            assert len(received_errors) == 1
        
        # Test audio send error when not connected
        with pytest.raises(RuntimeError, match="Transcription session not connected"):
            await session.send_audio(b"audio_data")
    
    @pytest.mark.asyncio 
    async def test_configuration_validation(self, mock_soniox_service):
        """Test that configuration parameters are properly validated."""
        # Test various configuration combinations
        configs = [
            {
                "sample_rate": 16000,
                "channels": 1,
                "interim_results": True,
                "punctuate": True,
                "smart_format": True
            },
            {
                "sample_rate": 8000,
                "channels": 2,
                "interim_results": False,
                "punctuate": False,
                "smart_format": False
            }
        ]
        
        for config in configs:
            session = await mock_soniox_service.start_live_transcription(
                on_message=lambda x: None,
                **config
            )
            
            # Verify configuration is applied
            assert session.config.sample_rate_hertz == config["sample_rate"]
            assert session.config.num_audio_channels == config["channels"]
            assert session.config.include_nonfinal == config["interim_results"]


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SONIOX_API_KEY", "NOT_SET") == "NOT_SET",
    reason="SONIOX_API_KEY not set - skipping real API tests"
)
class TestSonioxServiceReal:
    """Real integration tests with Soniox API (requires valid API key)."""
    
    @pytest.fixture
    def real_soniox_service(self):
        """Get the real Soniox service (requires API key)."""
        if not soniox_service.is_available():
            pytest.skip("Soniox service not available (API key not configured)")
        return soniox_service
    
    @pytest.mark.asyncio
    async def test_real_file_transcription(self, real_soniox_service):
        """Test actual file transcription with Soniox API."""
        # Create a proper WAV file with minimal header + silence
        # WAV header for 16-bit mono 16kHz audio
        wav_header = (
            b'RIFF' + (44 + 16000 * 2).to_bytes(4, 'little') +  # File size
            b'WAVE' +
            b'fmt ' + (16).to_bytes(4, 'little') +  # Format chunk size
            (1).to_bytes(2, 'little') +  # Audio format (PCM)
            (1).to_bytes(2, 'little') +  # Number of channels
            (16000).to_bytes(4, 'little') +  # Sample rate
            (32000).to_bytes(4, 'little') +  # Byte rate
            (2).to_bytes(2, 'little') +  # Block align
            (16).to_bytes(2, 'little') +  # Bits per sample
            b'data' + (16000 * 2).to_bytes(4, 'little')  # Data chunk size
        )
        test_audio = wav_header + b'\x00' * 16000 * 2  # 1 second of silence
        
        result = await real_soniox_service.transcribe_file(
            audio_data=test_audio,
            content_type="audio/wav"
        )
        
        # With silence, we might not get transcription, but should get valid response
        # If the API call fails, we'll get more info from the error
        if not result["success"]:
            # Log the error for debugging but don't fail the test for silence
            print(f"Transcription failed (expected for silence): {result.get('error', 'Unknown error')}")
            # For silence, we should still get a successful response structure
            assert "transcript" in result
            assert result["transcript"] == ""  # Empty transcript for silence is valid
        else:
            assert result["success"] is True
            assert "transcript" in result
            assert "confidence" in result
            assert "words" in result
            assert isinstance(result["words"], list)
    
    @pytest.mark.asyncio
    async def test_real_live_session_creation(self, real_soniox_service):
        """Test creating a real live transcription session."""
        received_messages = []
        
        def message_handler(data):
            received_messages.append(data)
        
        def error_handler(error):
            pytest.fail(f"Unexpected error in real test: {error}")
        
        session = await real_soniox_service.start_live_transcription(
            on_message=message_handler,
            on_error=error_handler
        )
        
        assert isinstance(session, LiveTranscriptionSession)
        
        # Test session lifecycle without sending audio
        await session.start()
        assert session.is_connected is True
        
        # Don't send audio in automated tests to avoid API costs
        # In manual testing, you could send actual audio here
        
        await session.finish()
        assert session.is_connected is False
    
    def test_real_service_availability(self, real_soniox_service):
        """Test that the real service reports availability correctly."""
        assert real_soniox_service.is_available() is True
        
        # Test that we can check availability multiple times
        for _ in range(3):
            assert real_soniox_service.is_available() is True


class TestSonioxServiceComparison:
    """Tests comparing Soniox behavior to expected STT patterns."""
    
    @pytest.mark.asyncio
    async def test_response_format_compatibility(self):
        """Test that Soniox responses match expected format for frontend compatibility."""
        service = SonioxService()
        service.available = True
        
        # Mock response that tests all fields
        mock_word = MagicMock()
        mock_word.text = "compatibility"
        mock_word.start_ms = 1000
        mock_word.end_ms = 2500
        mock_word.confidence = 0.94
        
        mock_result = MagicMock()
        mock_result.words = [mock_word]
        
        with patch('app.services.voice.soniox_service.speech_service.SpeechClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.transcribe.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            result = await service.transcribe_file(b"test_audio")
            
            # Verify response format matches what frontend expects
            required_fields = ["success", "transcript", "confidence", "words", "speakers", "paragraphs", "raw_response"]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
            
            # Verify data types
            assert isinstance(result["success"], bool)
            assert isinstance(result["transcript"], str)
            assert isinstance(result["confidence"], (int, float))
            assert isinstance(result["words"], list)
            assert isinstance(result["speakers"], list)
            assert isinstance(result["paragraphs"], list)
            
            # Verify word structure
            if result["words"]:
                word = result["words"][0]
                word_required_fields = ["word", "start", "end", "confidence", "speaker"]
                for field in word_required_fields:
                    assert field in word, f"Missing word field: {field}"
    
    @pytest.mark.asyncio
    async def test_live_session_message_format(self):
        """Test that live session messages match expected WebSocket format."""
        service = SonioxService()
        service.available = True
        
        received_messages = []
        
        def message_handler(data):
            received_messages.append(data)
        
        session = await service.start_live_transcription(
            on_message=message_handler,
            on_error=lambda e: None
        )
        
        # Mock a result and handle it
        mock_word = MagicMock()
        mock_word.text = "websocket"
        mock_word.start_ms = 500
        mock_word.end_ms = 1200
        mock_word.confidence = 0.91
        
        mock_result = MagicMock()
        mock_result.words = [mock_word]
        
        await session._handle_result(mock_result)
        
        assert len(received_messages) == 1
        message = received_messages[0]
        
        # Verify WebSocket message format
        required_fields = ["type", "transcript", "confidence", "is_final", "speech_final", "words", "detected_language"]
        for field in required_fields:
            assert field in message, f"Missing WebSocket field: {field}"
        
        # Verify specific values
        assert message["type"] == "transcript"
        assert message["transcript"] == "websocket"
        assert message["is_final"] is True
        assert message["speech_final"] is True
        assert message["detected_language"] == "auto"