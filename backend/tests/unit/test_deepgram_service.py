"""
Tests for the Deepgram voice service.
Tests the critical Speech-to-Text functionality including language mapping,
model compatibility, file transcription, and live transcription sessions.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional
import asyncio

from app.services.voice.deepgram_service import (
    DeepgramService,
    LiveTranscriptionSession,
    map_language_code_to_deepgram,
    get_compatible_model_for_language,
    deepgram_service
)


class TestLanguageMapping:
    """Test language code mapping functionality."""
    
    def test_map_language_code_to_deepgram_common_mappings(self):
        """Test mapping of common language codes to Deepgram format."""
        # Test common mappings
        assert map_language_code_to_deepgram('fr-FR') == 'fr'
        assert map_language_code_to_deepgram('es-ES') == 'es'
        assert map_language_code_to_deepgram('de-DE') == 'de'
        assert map_language_code_to_deepgram('it-IT') == 'it'
        
        # Test codes that stay the same
        assert map_language_code_to_deepgram('en-US') == 'en-US'
        assert map_language_code_to_deepgram('en-GB') == 'en-GB'
        assert map_language_code_to_deepgram('pt-BR') == 'pt-BR'
        
    def test_map_language_code_to_deepgram_edge_cases(self):
        """Test edge cases for language mapping."""
        # Test None input
        assert map_language_code_to_deepgram(None) is None
        
        # Test empty string
        assert map_language_code_to_deepgram('') is None
        
        # Test unmapped language returns original
        assert map_language_code_to_deepgram('xx-XX') == 'xx-XX'
        
        # Test simple language code without region
        assert map_language_code_to_deepgram('en') == 'en'


class TestModelCompatibility:
    """Test model compatibility functionality."""
    
    def test_get_compatible_model_for_language_nova3_supported(self):
        """Test that Nova-3 supported languages stay with Nova-3."""
        # English variants should stay with nova-3
        assert get_compatible_model_for_language('en', 'nova-3') == 'nova-3'
        assert get_compatible_model_for_language('en-US', 'nova-3') == 'nova-3'
        assert get_compatible_model_for_language('en-GB', 'nova-3') == 'nova-3'
        
        # Spanish should stay with nova-3
        assert get_compatible_model_for_language('es', 'nova-3') == 'nova-3'
        assert get_compatible_model_for_language('es-ES', 'nova-3') == 'nova-3'
    
    def test_get_compatible_model_for_language_nova3_fallback(self):
        """Test that unsupported languages fallback from Nova-3 to Nova-2."""
        # French should fallback to nova-2
        assert get_compatible_model_for_language('fr', 'nova-3') == 'nova-2'
        
        # German should fallback to nova-2
        assert get_compatible_model_for_language('de', 'nova-3') == 'nova-2'
        
        # Italian should fallback to nova-2
        assert get_compatible_model_for_language('it', 'nova-3') == 'nova-2'
    
    def test_get_compatible_model_for_language_other_models(self):
        """Test that non-Nova-3 models are unchanged."""
        # Nova-2 should stay nova-2 regardless of language
        assert get_compatible_model_for_language('fr', 'nova-2') == 'nova-2'
        assert get_compatible_model_for_language('de', 'nova-2') == 'nova-2'
        
        # Base model should stay base
        assert get_compatible_model_for_language('fr', 'base') == 'base'
    
    def test_get_compatible_model_for_language_no_language(self):
        """Test behavior when no language is provided."""
        assert get_compatible_model_for_language(None, 'nova-3') == 'nova-3'
        assert get_compatible_model_for_language('', 'nova-3') == 'nova-3'


class TestDeepgramService:
    """Test DeepgramService functionality."""
    
    @pytest.fixture
    def mock_deepgram_client(self):
        """Create a mock Deepgram client."""
        mock_client = Mock()
        mock_client.listen = Mock()
        mock_client.listen.asyncrest = Mock()
        mock_client.listen.asyncrest.v = Mock()
        mock_client.listen.asyncwebsocket = Mock()
        return mock_client
    
    @pytest.fixture
    def deepgram_service_with_mock(self, mock_deepgram_client):
        """Create DeepgramService with mocked client."""
        service = DeepgramService()
        service.client = mock_deepgram_client
        return service
    
    @patch('app.services.voice.deepgram_service.settings')
    def test_init_with_api_key(self, mock_settings):
        """Test DeepgramService initialization with valid API key."""
        mock_settings.DEEPGRAM_API_KEY = "valid_api_key"
        
        with patch('app.services.voice.deepgram_service.DeepgramClient') as mock_client_class:
            mock_client_instance = Mock()
            mock_client_class.return_value = mock_client_instance
            
            service = DeepgramService()
            
            assert service.client == mock_client_instance
            mock_client_class.assert_called_once_with("valid_api_key")
    
    @patch('app.services.voice.deepgram_service.settings')
    def test_init_without_api_key(self, mock_settings):
        """Test DeepgramService initialization without API key."""
        mock_settings.DEEPGRAM_API_KEY = "NOT_SET"
        
        service = DeepgramService()
        
        assert service.client is None
    
    def test_is_available(self, deepgram_service_with_mock):
        """Test service availability check."""
        # With client
        assert deepgram_service_with_mock.is_available() is True
        
        # Without client
        deepgram_service_with_mock.client = None
        assert deepgram_service_with_mock.is_available() is False
    
    async def test_transcribe_file_success(self, deepgram_service_with_mock):
        """Test successful file transcription."""
        # Mock the response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Hello world",
                        "confidence": 0.95,
                        "words": [
                            {
                                "word": "Hello",
                                "start": 0.0,
                                "end": 0.5,
                                "confidence": 0.96
                            },
                            {
                                "word": "world",
                                "start": 0.5,
                                "end": 1.0,
                                "confidence": 0.94
                            }
                        ]
                    }]
                }]
            }
        }
        
        # Configure mock
        mock_transcribe = AsyncMock(return_value=mock_response)
        deepgram_service_with_mock.client.listen.asyncrest.v.return_value.transcribe_file = mock_transcribe
        
        # Test transcription
        audio_data = b"fake_audio_data"
        result = await deepgram_service_with_mock.transcribe_file(
            audio_data,
            language="en-US",
            model="nova-2"
        )
        
        # Verify result
        assert result["success"] is True
        assert result["transcript"] == "Hello world"
        assert result["confidence"] == 0.95
        assert len(result["words"]) == 2
        assert result["words"][0]["word"] == "Hello"
        assert result["words"][1]["word"] == "world"
    
    async def test_transcribe_file_service_unavailable(self):
        """Test file transcription when service is unavailable."""
        service = DeepgramService()
        service.client = None
        
        with pytest.raises(RuntimeError, match="Deepgram service not available"):
            await service.transcribe_file(b"audio_data")
    
    async def test_transcribe_file_with_language_mapping(self, deepgram_service_with_mock):
        """Test file transcription with language mapping."""
        # Mock successful response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Bonjour le monde",
                        "confidence": 0.90
                    }]
                }]
            }
        }
        
        mock_transcribe = AsyncMock(return_value=mock_response)
        deepgram_service_with_mock.client.listen.asyncrest.v.return_value.transcribe_file = mock_transcribe
        
        # Test with French locale that should be mapped
        result = await deepgram_service_with_mock.transcribe_file(
            b"audio_data",
            language="fr-FR",  # Should be mapped to 'fr'
            model="nova-2"
        )
        
        assert result["success"] is True
        assert result["transcript"] == "Bonjour le monde"
    
    async def test_transcribe_file_error_handling(self, deepgram_service_with_mock):
        """Test error handling in file transcription."""
        # Mock an exception
        mock_transcribe = AsyncMock(side_effect=Exception("API Error"))
        deepgram_service_with_mock.client.listen.asyncrest.v.return_value.transcribe_file = mock_transcribe
        
        result = await deepgram_service_with_mock.transcribe_file(b"audio_data")
        
        assert result["success"] is False
        assert "API Error" in result["error"]
        assert result["transcript"] == ""
        assert result["confidence"] == 0.0
    
    @patch('app.services.voice.deepgram_service.settings')
    async def test_start_live_transcription_success(self, mock_settings, deepgram_service_with_mock):
        """Test starting a live transcription session."""
        mock_settings.DEEPGRAM_MODEL = "nova-2"
        mock_settings.DEEPGRAM_LANGUAGE = "en-US"
        
        # Mock callback
        mock_callback = Mock()
        
        # Test starting live transcription
        session = await deepgram_service_with_mock.start_live_transcription(
            on_message=mock_callback,
            language="en-US",
            model="nova-2"
        )
        
        assert isinstance(session, LiveTranscriptionSession)
        assert session.on_message == mock_callback
    
    async def test_start_live_transcription_service_unavailable(self):
        """Test starting live transcription when service is unavailable."""
        service = DeepgramService()
        service.client = None
        
        with pytest.raises(RuntimeError, match="Deepgram service not available"):
            await service.start_live_transcription(Mock())


class TestLiveTranscriptionSession:
    """Test LiveTranscriptionSession functionality."""
    
    @pytest.fixture
    def mock_live_options(self):
        """Create mock LiveOptions."""
        mock_options = Mock()
        mock_options.model = "nova-2"
        mock_options.language = "en-US"
        mock_options.punctuate = True
        mock_options.interim_results = True
        mock_options.smart_format = True
        mock_options.encoding = "linear16"
        mock_options.sample_rate = 16000
        mock_options.channels = 1
        return mock_options
    
    @pytest.fixture
    def mock_deepgram_client(self):
        """Create mock Deepgram client for live session."""
        mock_client = Mock()
        mock_connection = Mock()
        mock_connection.start = AsyncMock(return_value=True)
        mock_connection.send = AsyncMock()
        mock_connection.finish = AsyncMock()
        mock_connection.on = Mock()
        
        mock_client.listen.asyncwebsocket.v.return_value = mock_connection
        return mock_client, mock_connection
    
    def test_live_session_initialization(self, mock_live_options):
        """Test LiveTranscriptionSession initialization."""
        mock_client, _ = Mock(), Mock()
        mock_callback = Mock()
        
        session = LiveTranscriptionSession(
            mock_client,
            mock_live_options,
            mock_callback
        )
        
        assert session.client == mock_client
        assert session.options == mock_live_options
        assert session.on_message == mock_callback
        assert session.connection is None
        assert session.is_connected is False
    
    async def test_live_session_start_success(self, mock_live_options):
        """Test successful start of live transcription session."""
        mock_client, mock_connection = self.mock_deepgram_client()
        mock_callback = Mock()
        
        session = LiveTranscriptionSession(
            mock_client,
            mock_live_options,
            mock_callback
        )
        
        await session.start()
        
        assert session.is_connected is True
        assert session.connection == mock_connection
        mock_connection.start.assert_called_once_with(mock_live_options)
    
    async def test_live_session_start_failure(self, mock_live_options):
        """Test failed start of live transcription session."""
        mock_client, mock_connection = self.mock_deepgram_client()
        mock_connection.start = AsyncMock(return_value=False)
        mock_callback = Mock()
        
        session = LiveTranscriptionSession(
            mock_client,
            mock_live_options,
            mock_callback
        )
        
        with pytest.raises(RuntimeError, match="Failed to start live transcription session"):
            await session.start()
    
    async def test_send_audio_success(self, mock_live_options):
        """Test successful audio sending."""
        mock_client, mock_connection = self.mock_deepgram_client()
        mock_callback = Mock()
        
        session = LiveTranscriptionSession(
            mock_client,
            mock_live_options,
            mock_callback
        )
        
        # Simulate successful start
        await session.start()
        
        # Test sending audio
        audio_data = b"audio_chunk"
        await session.send_audio(audio_data)
        
        mock_connection.send.assert_called_once_with(audio_data)
    
    async def test_send_audio_not_connected(self, mock_live_options):
        """Test sending audio when not connected."""
        mock_client, _ = Mock(), Mock()
        mock_callback = Mock()
        
        session = LiveTranscriptionSession(
            mock_client,
            mock_live_options,
            mock_callback
        )
        
        with pytest.raises(RuntimeError, match="Transcription session not connected"):
            await session.send_audio(b"audio_data")
    
    async def test_finish_session(self, mock_live_options):
        """Test finishing the transcription session."""
        mock_client, mock_connection = self.mock_deepgram_client()
        mock_callback = Mock()
        
        session = LiveTranscriptionSession(
            mock_client,
            mock_live_options,
            mock_callback
        )
        
        # Start and then finish
        await session.start()
        await session.finish()
        
        assert session.is_connected is False
        mock_connection.finish.assert_called_once()
    
    async def test_handle_transcript_data_success(self, mock_live_options):
        """Test handling transcript data."""
        mock_client, _ = Mock(), Mock()
        mock_callback = Mock()
        
        session = LiveTranscriptionSession(
            mock_client,
            mock_live_options,
            mock_callback
        )
        
        # Mock transcript data structure
        mock_result = Mock()
        mock_result.channel = Mock()
        mock_result.channel.alternatives = [Mock()]
        mock_result.channel.alternatives[0].transcript = "Hello world"
        mock_result.channel.alternatives[0].confidence = 0.95
        mock_result.channel.alternatives[0].words = []
        mock_result.is_final = True
        mock_result.speech_final = True
        mock_result.duration = 1.0
        mock_result.start = 0.0
        
        transcript_data = {"result": mock_result}
        
        await session._handle_transcript_data(transcript_data)
        
        # Verify callback was called with formatted data
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args[0][0]
        assert call_args["type"] == "transcript"
        assert call_args["transcript"] == "Hello world"
        assert call_args["confidence"] == 0.95
        assert call_args["is_final"] is True
    
    def mock_deepgram_client(self):
        """Helper method to create mock Deepgram client."""
        mock_client = Mock()
        mock_connection = Mock()
        mock_connection.start = AsyncMock(return_value=True)
        mock_connection.send = AsyncMock()
        mock_connection.finish = AsyncMock()
        mock_connection.on = Mock()
        
        mock_client.listen.asyncwebsocket.v.return_value = mock_connection
        return mock_client, mock_connection


class TestSingletonInstance:
    """Test the singleton deepgram_service instance."""
    
    def test_singleton_instance_exists(self):
        """Test that the singleton instance exists."""
        from app.services.voice.deepgram_service import deepgram_service
        
        assert deepgram_service is not None
        assert isinstance(deepgram_service, DeepgramService)
    
    def test_singleton_instance_is_consistent(self):
        """Test that multiple imports return the same instance."""
        from app.services.voice.deepgram_service import deepgram_service as instance1
        from app.services.voice.deepgram_service import deepgram_service as instance2
        
        assert instance1 is instance2


@pytest.mark.skip(reason="Integration test requiring complex fixtures")
class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""
    
    @patch('app.services.voice.deepgram_service.settings')
    async def test_full_transcription_workflow(self, mock_settings, deepgram_service_with_mock):
        """Test a complete transcription workflow with language mapping and model compatibility."""
        mock_settings.DEEPGRAM_MODEL = "nova-3"
        mock_settings.DEEPGRAM_LANGUAGE = "en-US"
        
        # Mock successful response for French audio (should fallback to nova-2)
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Bonjour tout le monde",
                        "confidence": 0.92,
                        "words": []
                    }]
                }]
            }
        }
        
        mock_transcribe = AsyncMock(return_value=mock_response)
        deepgram_service_with_mock.client.listen.asyncrest.v.return_value.transcribe_file = mock_transcribe
        
        # Test with French language (should map fr-FR -> fr and nova-3 -> nova-2)
        result = await deepgram_service_with_mock.transcribe_file(
            b"french_audio_data",
            language="fr-FR",
            model="nova-3"
        )
        
        assert result["success"] is True
        assert result["transcript"] == "Bonjour tout le monde"
        assert result["confidence"] == 0.92
