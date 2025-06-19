import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
import asyncio

from app.services.voice.deepgram_service import (
    DeepgramService, 
    deepgram_service,
    map_language_code_to_deepgram,
    get_compatible_model_for_language,
    LiveTranscriptionSession
)
from app.core.config import settings


class TestLanguageMappingUtils:
    """Test utility functions for language mapping."""
    
    def test_map_language_code_to_deepgram_basic_mappings(self):
        """Test basic language code mappings."""
        test_cases = [
            ('fr-FR', 'fr'),
            ('en-US', 'en-US'),
            ('en-GB', 'en-GB'),
            ('es-ES', 'es'),
            ('de-DE', 'de'),
            ('ja-JP', 'ja'),
            ('zh-CN', 'zh-CN'),
            ('pt-BR', 'pt-BR'),
        ]
        
        for input_lang, expected_output in test_cases:
            result = map_language_code_to_deepgram(input_lang)
            assert result == expected_output, f"Expected {input_lang} -> {expected_output}, got {result}"
    
    def test_map_language_code_to_deepgram_unmapped(self):
        """Test language codes that don't have specific mappings."""
        unmapped_codes = ['xx-XX', 'unknown', 'custom-locale']
        
        for lang_code in unmapped_codes:
            result = map_language_code_to_deepgram(lang_code)
            assert result == lang_code, f"Unmapped code {lang_code} should return itself"
    
    def test_map_language_code_to_deepgram_edge_cases(self):
        """Test edge cases for language mapping."""
        assert map_language_code_to_deepgram(None) is None
        assert map_language_code_to_deepgram('') is None
        assert map_language_code_to_deepgram('en') == 'en'
        assert map_language_code_to_deepgram('fr') == 'fr'
    
    def test_get_compatible_model_for_language_nova3_supported(self):
        """Test nova-3 compatibility with supported languages."""
        supported_languages = ['en', 'en-US', 'en-GB', 'es', 'es-ES']
        
        for lang in supported_languages:
            result = get_compatible_model_for_language(lang, 'nova-3')
            assert result == 'nova-3', f"Nova-3 should support {lang}"
    
    def test_get_compatible_model_for_language_nova3_fallback(self):
        """Test nova-3 fallback to nova-2 for unsupported languages."""
        unsupported_languages = ['fr', 'de', 'ja', 'zh-CN', 'pt-BR']
        
        for lang in unsupported_languages:
            result = get_compatible_model_for_language(lang, 'nova-3')
            assert result == 'nova-2', f"Nova-3 should fallback to nova-2 for {lang}"
    
    def test_get_compatible_model_for_language_other_models(self):
        """Test that non-nova-3 models pass through unchanged."""
        models = ['nova-2', 'base', 'enhanced', 'custom-model']
        languages = ['fr', 'de', 'ja', 'en']
        
        for model in models:
            for lang in languages:
                result = get_compatible_model_for_language(lang, model)
                assert result == model, f"Model {model} should pass through unchanged for {lang}"
    
    def test_get_compatible_model_for_language_no_language(self):
        """Test model compatibility when no language specified."""
        result = get_compatible_model_for_language(None, 'nova-3')
        assert result == 'nova-3'
        
        result = get_compatible_model_for_language('', 'nova-3')
        assert result == 'nova-3'


class TestDeepgramService:
    """Test suite for DeepgramService."""
    
    @pytest.fixture
    def mock_deepgram_client(self):
        """Create a mock Deepgram client."""
        client = MagicMock()
        client.listen = MagicMock()
        client.listen.asyncrest = MagicMock()
        client.listen.asyncrest.v.return_value = MagicMock()
        client.listen.asyncwebsocket = MagicMock()
        client.listen.asyncwebsocket.v.return_value = MagicMock()
        return client
    
    @pytest.fixture
    def deepgram_service_with_client(self, mock_deepgram_client):
        """Create DeepgramService with mock client."""
        service = DeepgramService()
        service.client = mock_deepgram_client
        return service
    
    @pytest.fixture
    def deepgram_service_no_client(self):
        """Create DeepgramService without client (API key not set)."""
        with patch.object(settings, 'DEEPGRAM_API_KEY', 'NOT_SET'):
            return DeepgramService()
    
    def test_deepgram_service_initialization_with_api_key(self):
        """Test DeepgramService initialization with valid API key."""
        with patch.object(settings, 'DEEPGRAM_API_KEY', 'test_api_key'), \
             patch('app.services.voice.deepgram_service.DeepgramClient') as mock_client_class:
            
            mock_client_instance = MagicMock()
            mock_client_class.return_value = mock_client_instance
            
            service = DeepgramService()
            
            assert service.client == mock_client_instance
            mock_client_class.assert_called_once_with('test_api_key')
    
    def test_deepgram_service_initialization_no_api_key(self):
        """Test DeepgramService initialization without API key."""
        with patch.object(settings, 'DEEPGRAM_API_KEY', 'NOT_SET'):
            service = DeepgramService()
            assert service.client is None
    
    def test_deepgram_service_initialization_error(self):
        """Test DeepgramService initialization with client creation error."""
        with patch.object(settings, 'DEEPGRAM_API_KEY', 'test_api_key'), \
             patch('app.services.voice.deepgram_service.DeepgramClient', side_effect=Exception("Client creation failed")):
            
            service = DeepgramService()
            assert service.client is None
    
    def test_is_available(self, deepgram_service_with_client, deepgram_service_no_client):
        """Test service availability check."""
        assert deepgram_service_with_client.is_available() is True
        assert deepgram_service_no_client.is_available() is False
    
    @pytest.mark.asyncio
    async def test_transcribe_file_success(self, deepgram_service_with_client):
        """Test successful file transcription."""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Hello world test transcript",
                        "confidence": 0.95,
                        "words": [
                            {"word": "Hello", "start": 0.0, "end": 0.5, "confidence": 0.9},
                            {"word": "world", "start": 0.6, "end": 1.0, "confidence": 0.95}
                        ],
                        "paragraphs": {
                            "paragraphs": [{
                                "text": "Hello world test transcript",
                                "start": 0.0,
                                "end": 1.0
                            }]
                        }
                    }]
                }]
            }
        }
        
        deepgram_service_with_client.client.listen.asyncrest.v.return_value.transcribe_file = AsyncMock(return_value=mock_response)
        
        audio_data = b"fake_audio_data"
        result = await deepgram_service_with_client.transcribe_file(
            audio_data=audio_data,
            content_type="audio/wav",
            language="en-US",
            model="nova-2"
        )
        
        assert result["success"] is True
        assert result["transcript"] == "Hello world test transcript"
        assert result["confidence"] == 0.95
        assert len(result["words"]) == 2
        assert result["words"][0]["word"] == "Hello"
        assert result["words"][1]["word"] == "world"
        assert len(result["paragraphs"]) == 1
        assert result["paragraphs"][0]["text"] == "Hello world test transcript"
    
    @pytest.mark.asyncio
    async def test_transcribe_file_service_unavailable(self, deepgram_service_no_client):
        """Test transcription when service is unavailable."""
        with pytest.raises(RuntimeError, match="Deepgram service not available"):
            await deepgram_service_no_client.transcribe_file(b"audio_data")
    
    @pytest.mark.asyncio
    async def test_transcribe_file_with_language_mapping(self, deepgram_service_with_client):
        """Test transcription with language code mapping."""
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Bonjour le monde",
                        "confidence": 0.9
                    }]
                }]
            }
        }
        
        deepgram_service_with_client.client.listen.asyncrest.v.return_value.transcribe_file = AsyncMock(return_value=mock_response)
        
        # Test French language mapping (fr-FR -> fr)
        with patch('app.services.voice.deepgram_service.map_language_code_to_deepgram', return_value='fr') as mock_map, \
             patch('app.services.voice.deepgram_service.get_compatible_model_for_language', return_value='nova-2') as mock_compat:
            
            result = await deepgram_service_with_client.transcribe_file(
                audio_data=b"audio_data",
                language="fr-FR",
                model="nova-3"
            )
            
            mock_map.assert_called_once_with("fr-FR")
            mock_compat.assert_called_once_with('fr', 'nova-3')
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_transcribe_file_with_detect_language(self, deepgram_service_with_client):
        """Test transcription with language detection enabled."""
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Test transcript",
                        "confidence": 0.9
                    }]
                }]
            }
        }
        
        mock_transcribe = AsyncMock(return_value=mock_response)
        deepgram_service_with_client.client.listen.asyncrest.v.return_value.transcribe_file = mock_transcribe
        
        result = await deepgram_service_with_client.transcribe_file(
            audio_data=b"audio_data",
            detect_language=True
        )
        
        assert result["success"] is True
        # Verify transcribe_file was called
        mock_transcribe.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transcribe_file_error(self, deepgram_service_with_client):
        """Test transcription error handling."""
        deepgram_service_with_client.client.listen.asyncrest.v.return_value.transcribe_file = AsyncMock(
            side_effect=Exception("Transcription failed")
        )
        
        result = await deepgram_service_with_client.transcribe_file(b"audio_data")
        
        assert result["success"] is False
        assert "error" in result
        assert "Transcription failed" in result["error"]
        assert result["transcript"] == ""
        assert result["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_transcribe_file_empty_response(self, deepgram_service_with_client):
        """Test handling of empty transcription response."""
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"results": {}}
        
        deepgram_service_with_client.client.listen.asyncrest.v.return_value.transcribe_file = AsyncMock(return_value=mock_response)
        
        result = await deepgram_service_with_client.transcribe_file(b"audio_data")
        
        assert result["success"] is True
        assert result["transcript"] == ""
        assert result["confidence"] == 0.0
        assert result["words"] == []
        assert result["paragraphs"] == []
    
    @pytest.mark.asyncio
    async def test_transcribe_file_with_diarization(self, deepgram_service_with_client):
        """Test transcription with speaker diarization."""
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Speaker one. Speaker two.",
                        "confidence": 0.9,
                        "words": [
                            {"word": "Speaker", "start": 0.0, "end": 0.5, "confidence": 0.9, "speaker": 0},
                            {"word": "one", "start": 0.6, "end": 0.8, "confidence": 0.9, "speaker": 0},
                            {"word": "Speaker", "start": 1.0, "end": 1.5, "confidence": 0.9, "speaker": 1},
                            {"word": "two", "start": 1.6, "end": 1.8, "confidence": 0.9, "speaker": 1}
                        ]
                    }]
                }]
            }
        }
        
        deepgram_service_with_client.client.listen.asyncrest.v.return_value.transcribe_file = AsyncMock(return_value=mock_response)
        
        result = await deepgram_service_with_client.transcribe_file(
            audio_data=b"audio_data",
            diarize=True
        )
        
        assert result["success"] is True
        assert len(result["speakers"]) == 2
        assert 0 in result["speakers"]
        assert 1 in result["speakers"]
        assert all(word.get("speaker") is not None for word in result["words"])
    
    @pytest.mark.asyncio
    async def test_start_live_transcription_success(self, deepgram_service_with_client):
        """Test starting live transcription session."""
        mock_on_message = MagicMock()
        mock_on_error = MagicMock()
        
        session = await deepgram_service_with_client.start_live_transcription(
            on_message=mock_on_message,
            on_error=mock_on_error,
            language="en-US",
            model="nova-2"
        )
        
        assert isinstance(session, LiveTranscriptionSession)
        assert session.client == deepgram_service_with_client.client
        assert session.on_message == mock_on_message
        assert session.on_error == mock_on_error
    
    @pytest.mark.asyncio
    async def test_start_live_transcription_service_unavailable(self, deepgram_service_no_client):
        """Test starting live transcription when service unavailable."""
        with pytest.raises(RuntimeError, match="Deepgram service not available"):
            await deepgram_service_no_client.start_live_transcription(
                on_message=MagicMock()
            )
    
    @pytest.mark.asyncio
    async def test_start_live_transcription_with_language_mapping(self, deepgram_service_with_client):
        """Test live transcription with language mapping and model compatibility."""
        with patch('app.services.voice.deepgram_service.map_language_code_to_deepgram', return_value='es') as mock_map, \
             patch('app.services.voice.deepgram_service.get_compatible_model_for_language', return_value='nova-2') as mock_compat:
            
            session = await deepgram_service_with_client.start_live_transcription(
                on_message=MagicMock(),
                language="es-ES",
                model="nova-3"
            )
            
            mock_map.assert_called_once_with("es-ES")
            mock_compat.assert_called_once_with('es', 'nova-3')
            assert isinstance(session, LiveTranscriptionSession)
    
    @pytest.mark.asyncio
    async def test_start_live_transcription_detect_language(self, deepgram_service_with_client):
        """Test live transcription with language detection."""
        session = await deepgram_service_with_client.start_live_transcription(
            on_message=MagicMock(),
            detect_language=True
        )
        
        assert isinstance(session, LiveTranscriptionSession)
        # When detect_language=True, no specific language should be set
        # This would be verified by checking the LiveOptions passed to the session


class TestLiveTranscriptionSession:
    """Test suite for LiveTranscriptionSession."""
    
    @pytest.fixture
    def mock_deepgram_client(self):
        """Create a mock Deepgram client for live sessions."""
        client = MagicMock()
        mock_connection = MagicMock()
        mock_connection.start = AsyncMock(return_value=True)
        mock_connection.send = AsyncMock()
        mock_connection.finish = AsyncMock()
        mock_connection.on = MagicMock()
        
        client.listen.asyncwebsocket.v.return_value = mock_connection
        return client
    
    @pytest.fixture
    def mock_live_options(self):
        """Create mock LiveOptions."""
        options = MagicMock()
        options.model = "nova-2"
        options.language = "en-US"
        options.punctuate = True
        options.interim_results = True
        return options
    
    @pytest.fixture
    def live_session(self, mock_deepgram_client, mock_live_options):
        """Create a LiveTranscriptionSession for testing."""
        on_message = MagicMock()
        on_error = MagicMock()
        
        session = LiveTranscriptionSession(
            client=mock_deepgram_client,
            options=mock_live_options,
            on_message=on_message,
            on_error=on_error
        )
        
        return session
    
    def test_live_session_initialization(self, live_session, mock_deepgram_client, mock_live_options):
        """Test LiveTranscriptionSession initialization."""
        assert live_session.client == mock_deepgram_client
        assert live_session.options == mock_live_options
        assert live_session.connection is None
        assert live_session.is_connected is False
        assert live_session.on_message is not None
        assert live_session.on_error is not None
    
    @pytest.mark.asyncio
    async def test_start_session_success(self, live_session):
        """Test starting live transcription session successfully."""
        await live_session.start()
        
        assert live_session.connection is not None
        assert live_session.is_connected is True
        
        # Verify connection setup
        live_session.connection.start.assert_called_once_with(live_session.options)
        assert live_session.connection.on.call_count == 2  # Transcript and Error handlers
    
    @pytest.mark.asyncio
    async def test_start_session_connection_failure(self, live_session):
        """Test handling connection start failure."""
        # Mock the client to return a connection that fails to start
        mock_connection = MagicMock()
        mock_connection.start = AsyncMock(return_value=False)
        mock_connection.on = MagicMock()
        
        live_session.client.listen.asyncwebsocket.v.return_value = mock_connection
        
        with pytest.raises(RuntimeError, match="Failed to start live transcription session"):
            await live_session.start()
        
        assert live_session.is_connected is False
    
    @pytest.mark.asyncio
    async def test_start_session_exception(self, live_session):
        """Test handling exception during session start."""
        # Make the client throw an exception
        live_session.client.listen.asyncwebsocket.v.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await live_session.start()
        
        # Error handler should be called
        live_session.on_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_audio_success(self, live_session):
        """Test sending audio data successfully."""
        # Set up connected session
        live_session.connection = MagicMock()
        live_session.connection.send = AsyncMock()
        live_session.is_connected = True
        
        audio_data = b"test_audio_data"
        await live_session.send_audio(audio_data)
        
        live_session.connection.send.assert_called_once_with(audio_data)
    
    @pytest.mark.asyncio
    async def test_send_audio_not_connected(self, live_session):
        """Test sending audio when not connected."""
        audio_data = b"test_audio_data"
        
        with pytest.raises(RuntimeError, match="Transcription session not connected"):
            await live_session.send_audio(audio_data)
    
    @pytest.mark.asyncio
    async def test_send_audio_error(self, live_session):
        """Test handling error during audio send."""
        live_session.connection = MagicMock()
        live_session.connection.send = AsyncMock(side_effect=Exception("Send failed"))
        live_session.is_connected = True
        
        with pytest.raises(Exception, match="Send failed"):
            await live_session.send_audio(b"audio_data")
        
        live_session.on_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_finish_session(self, live_session):
        """Test finishing the transcription session."""
        live_session.connection = MagicMock()
        live_session.connection.finish = AsyncMock()
        live_session.is_connected = True
        
        await live_session.finish()
        
        live_session.connection.finish.assert_called_once()
        assert live_session.is_connected is False
    
    @pytest.mark.asyncio
    async def test_finish_session_not_connected(self, live_session):
        """Test finishing when not connected."""
        # Should not raise an exception
        await live_session.finish()
    
    @pytest.mark.asyncio
    async def test_finish_session_error(self, live_session):
        """Test handling error during session finish."""
        live_session.connection = MagicMock()
        live_session.connection.finish = AsyncMock(side_effect=Exception("Finish failed"))
        live_session.is_connected = True
        
        await live_session.finish()
        
        live_session.on_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_transcript_data(self, live_session):
        """Test handling transcript data."""
        # Mock transcript data structure
        mock_result = MagicMock()
        mock_result.is_final = True
        mock_result.speech_final = False
        mock_result.duration = 2.5
        mock_result.start = 0.0
        mock_result.language = "en-US"
        
        mock_alternative = MagicMock()
        mock_alternative.transcript = "Hello world"
        mock_alternative.confidence = 0.95
        mock_alternative.words = []
        
        mock_channel = MagicMock()
        mock_channel.alternatives = [mock_alternative]
        
        mock_result.channel = mock_channel
        
        transcript_data = {"result": mock_result}
        
        await live_session._handle_transcript_data(transcript_data)
        
        # Verify on_message was called with formatted data
        live_session.on_message.assert_called_once()
        call_args = live_session.on_message.call_args[0][0]
        
        assert call_args["type"] == "transcript"
        assert call_args["transcript"] == "Hello world"
        assert call_args["confidence"] == 0.95
        assert call_args["is_final"] is True
        assert call_args["detected_language"] == "en-US"
    
    @pytest.mark.asyncio
    async def test_handle_transcript_data_with_words(self, live_session):
        """Test handling transcript data with word-level timestamps."""
        # Mock word data
        mock_word1 = MagicMock()
        mock_word1.word = "Hello"
        mock_word1.start = 0.0
        mock_word1.end = 0.5
        mock_word1.confidence = 0.9
        mock_word1.punctuated_word = "Hello"
        mock_word1.speaker = None
        
        mock_word2 = MagicMock()
        mock_word2.word = "world"
        mock_word2.start = 0.6
        mock_word2.end = 1.0
        mock_word2.confidence = 0.95
        mock_word2.punctuated_word = "world"
        mock_word2.speaker = None
        
        mock_alternative = MagicMock()
        mock_alternative.transcript = "Hello world"
        mock_alternative.confidence = 0.93
        mock_alternative.words = [mock_word1, mock_word2]
        
        mock_channel = MagicMock()
        mock_channel.alternatives = [mock_alternative]
        
        mock_result = MagicMock()
        mock_result.channel = mock_channel
        mock_result.is_final = False
        mock_result.speech_final = False
        
        transcript_data = {"result": mock_result}
        
        await live_session._handle_transcript_data(transcript_data)
        
        live_session.on_message.assert_called_once()
        call_args = live_session.on_message.call_args[0][0]
        
        assert len(call_args["words"]) == 2
        assert call_args["words"][0]["word"] == "Hello"
        assert call_args["words"][0]["start"] == 0.0
        assert call_args["words"][1]["word"] == "world"
        assert call_args["words"][1]["start"] == 0.6
    
    @pytest.mark.asyncio
    async def test_handle_transcript_data_empty_transcript(self, live_session):
        """Test handling empty transcript data."""
        mock_alternative = MagicMock()
        mock_alternative.transcript = ""
        mock_alternative.confidence = 0.0
        
        mock_channel = MagicMock()
        mock_channel.alternatives = [mock_alternative]
        
        mock_result = MagicMock()
        mock_result.channel = mock_channel
        mock_result.is_final = False
        
        transcript_data = {"result": mock_result}
        
        await live_session._handle_transcript_data(transcript_data)
        
        # Should not call on_message for empty transcripts
        live_session.on_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_transcript_data_exception(self, live_session):
        """Test handling exception in transcript processing."""
        # Invalid transcript data structure
        transcript_data = {"invalid": "structure"}
        
        await live_session._handle_transcript_data(transcript_data)
        
        # Should not crash, and should not call on_message
        live_session.on_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_error_data(self, live_session):
        """Test handling error data."""
        error_data = {"error": "Connection timeout", "code": 1000}
        
        await live_session._handle_error_data(error_data)
        
        live_session.on_error.assert_called_once()
        error_arg = live_session.on_error.call_args[0][0]
        assert isinstance(error_arg, Exception)
        assert "Connection timeout" in str(error_arg)


class TestDeepgramServiceSingleton:
    """Test the Deepgram service singleton."""
    
    def test_singleton_exists(self):
        """Test that deepgram service singleton exists."""
        assert deepgram_service is not None
        assert isinstance(deepgram_service, DeepgramService)
    
    def test_singleton_availability_depends_on_config(self):
        """Test singleton availability depends on configuration."""
        # This test depends on actual settings, so we just verify the method exists
        availability = deepgram_service.is_available()
        assert isinstance(availability, bool)


class TestDeepgramServiceIntegration:
    """Integration tests for Deepgram service components."""
    
    @pytest.mark.asyncio
    async def test_full_transcription_workflow(self):
        """Test a complete transcription workflow."""
        # Mock service with client
        service = DeepgramService()
        service.client = MagicMock()
        
        # Mock successful transcription response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "results": {
                "channels": [{
                    "alternatives": [{
                        "transcript": "Complete transcription test",
                        "confidence": 0.92,
                        "words": [
                            {"word": "Complete", "start": 0.0, "end": 0.8, "confidence": 0.9},
                            {"word": "transcription", "start": 0.9, "end": 1.8, "confidence": 0.95},
                            {"word": "test", "start": 1.9, "end": 2.2, "confidence": 0.9}
                        ],
                        "paragraphs": {
                            "paragraphs": [{
                                "text": "Complete transcription test",
                                "start": 0.0,
                                "end": 2.2
                            }]
                        }
                    }]
                }]
            }
        }
        
        service.client.listen.asyncrest.v.return_value.transcribe_file = AsyncMock(return_value=mock_response)
        
        # Test transcription with various options
        result = await service.transcribe_file(
            audio_data=b"test_audio_data",
            content_type="audio/wav",
            language="en-US",
            model="nova-2",
            punctuate=True,
            diarize=False,
            smart_format=True
        )
        
        # Verify complete result structure
        assert result["success"] is True
        assert result["transcript"] == "Complete transcription test"
        assert result["confidence"] == 0.92
        assert len(result["words"]) == 3
        assert len(result["paragraphs"]) == 1
        assert "raw_response" in result
        
        # Verify word-level data
        words = result["words"]
        assert words[0]["word"] == "Complete"
        assert words[1]["word"] == "transcription"
        assert words[2]["word"] == "test"
        
        # Verify timestamps
        assert words[0]["start"] == 0.0
        assert words[2]["end"] == 2.2
    
    @pytest.mark.asyncio
    async def test_live_transcription_session_lifecycle(self):
        """Test complete live transcription session lifecycle."""
        service = DeepgramService()
        service.client = MagicMock()
        
        # Mock connection
        mock_connection = MagicMock()
        mock_connection.start = AsyncMock(return_value=True)
        mock_connection.send = AsyncMock()
        mock_connection.finish = AsyncMock()
        mock_connection.on = MagicMock()
        
        service.client.listen.asyncwebsocket.v.return_value = mock_connection
        
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
            model="nova-2",
            interim_results=True
        )
        
        # Simulate session start
        await session.start()
        assert session.is_connected is True
        
        # Simulate sending audio data
        audio_chunks = [b"chunk1", b"chunk2", b"chunk3"]
        for chunk in audio_chunks:
            await session.send_audio(chunk)
        
        # Verify all chunks were sent
        assert mock_connection.send.call_count == len(audio_chunks)
        
        # Simulate transcript reception
        mock_result = MagicMock()
        mock_result.is_final = True
        mock_result.speech_final = True
        
        mock_alternative = MagicMock()
        mock_alternative.transcript = "Live transcription test"
        mock_alternative.confidence = 0.88
        mock_alternative.words = []
        
        mock_channel = MagicMock()
        mock_channel.alternatives = [mock_alternative]
        mock_result.channel = mock_channel
        
        transcript_data = {"result": mock_result}
        await session._handle_transcript_data(transcript_data)
        
        # Verify message was received
        assert len(received_messages) == 1
        assert received_messages[0]["transcript"] == "Live transcription test"
        assert received_messages[0]["is_final"] is True
        
        # Finish session
        await session.finish()
        assert session.is_connected is False
        mock_connection.finish.assert_called_once()