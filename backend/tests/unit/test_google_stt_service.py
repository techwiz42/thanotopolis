# backend/tests/unit/test_google_stt_service.py
import pytest
import base64
from unittest.mock import Mock, patch, MagicMock
import json
import requests

from app.services.voice.google_stt_service import GoogleSTTService, stt_service

class TestGoogleSTTService:
    """Test suite for Google Speech-to-Text Service."""
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-api-key'}):
            yield
    
    @pytest.fixture
    def service(self, mock_env):
        """Create STT service instance."""
        return GoogleSTTService()
    
    @pytest.fixture
    def mock_audio_content(self):
        """Create mock audio content."""
        return b"fake audio bytes"
    
    @pytest.fixture
    def mock_successful_response(self):
        """Create a mock successful API response with transcription."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "results": [
                {
                    "alternatives": [
                        {
                            "transcript": "Hello world",
                            "confidence": 0.95
                        }
                    ]
                }
            ]
        }
        return response
    
    @pytest.fixture
    def mock_no_speech_response(self):
        """Create a mock response for no speech detected."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "totalBilledTime": "15s"
        }
        return response
    
    def test_initialization(self, service):
        """Test service initialization."""
        assert service.api_key == 'test-api-key'
        assert service.base_url == "https://speech.googleapis.com/v1/speech:recognize"
        assert len(service.supported_encodings) > 0
        assert len(service.supported_languages) > 0
    
    def test_load_api_key_from_env(self, mock_env):
        """Test loading API key from environment."""
        service = GoogleSTTService()
        assert service.api_key == 'test-api-key'
    
    def test_load_api_key_not_found(self):
        """Test handling when API key is not found."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('os.path.exists', return_value=False):
                service = GoogleSTTService()
                assert service.api_key is None
    
    def test_get_supported_languages(self, service):
        """Test getting supported languages."""
        languages = service.get_supported_languages()
        
        assert len(languages) > 0
        assert all('code' in lang for lang in languages)
        assert all('name' in lang for lang in languages)
        
        # Check some expected languages
        codes = [lang['code'] for lang in languages]
        assert 'en-US' in codes
        assert 'es-ES' in codes
    
    def test_get_supported_encodings(self, service):
        """Test getting supported encodings."""
        encodings = service.get_supported_encodings()
        
        assert len(encodings) > 0
        assert 'LINEAR16' in encodings
        assert 'WEBM_OPUS' in encodings
        assert 'MP3' in encodings
    
    async def test_transcribe_audio_success(self, service, mock_audio_content, mock_successful_response):
        """Test successful audio transcription."""
        with patch('requests.post', return_value=mock_successful_response):
            result = service.transcribe_audio(
                audio_content=mock_audio_content,
                language_code="en-US",
                encoding="LINEAR16",
                sample_rate_hertz=16000
            )
        
        assert result['success'] is True
        assert result['transcript'] == "Hello world"
        assert result['confidence'] == 0.95
    
    async def test_transcribe_audio_no_api_key(self, mock_audio_content):
        """Test transcription without API key."""
        service = GoogleSTTService()
        service.api_key = None
        
        result = service.transcribe_audio(mock_audio_content)
        
        assert result['success'] is False
        assert 'not configured' in result['error']
    
    async def test_transcribe_audio_webm_opus(self, service, mock_audio_content, mock_successful_response):
        """Test WebM/OPUS encoding forces 48000 Hz sample rate."""
        with patch('requests.post', return_value=mock_successful_response) as mock_post:
            service.transcribe_audio(
                audio_content=mock_audio_content,
                encoding="WEBM_OPUS",
                sample_rate_hertz=16000  # Should be overridden
            )
        
        # Check the request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        
        assert payload['config']['sampleRateHertz'] == 48000
    
    async def test_transcribe_audio_invalid_encoding(self, service, mock_audio_content, mock_successful_response):
        """Test handling of invalid encoding."""
        with patch('requests.post', return_value=mock_successful_response) as mock_post:
            service.transcribe_audio(
                audio_content=mock_audio_content,
                encoding="INVALID_ENCODING"
            )
        
        # Should fallback to LINEAR16
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['config']['encoding'] == "LINEAR16"
    
    async def test_transcribe_audio_invalid_sample_rate(self, service, mock_audio_content, mock_successful_response):
        """Test handling of invalid sample rate."""
        with patch('requests.post', return_value=mock_successful_response) as mock_post:
            service.transcribe_audio(
                audio_content=mock_audio_content,
                encoding="LINEAR16",
                sample_rate_hertz=12345  # Invalid rate
            )
        
        # Should adjust to closest valid rate
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['config']['sampleRateHertz'] in [8000, 12000, 16000, 22050, 24000, 32000, 44100, 48000]
    
    async def test_transcribe_audio_no_speech_detected(self, service, mock_audio_content, mock_no_speech_response):
        """Test handling when no speech is detected."""
        with patch('requests.post', return_value=mock_no_speech_response):
            result = service.transcribe_audio(
                audio_content=mock_audio_content,
                encoding="WEBM_OPUS"
            )
        
        assert result['success'] is True
        assert result['transcript'] == ""
        assert result['confidence'] == 0
        assert result['message'] == "No speech detected"
        assert 'audio_info' in result
    
    async def test_transcribe_audio_no_results(self, service, mock_audio_content):
        """Test handling when API returns no results."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {}  # No results field
        
        with patch('requests.post', return_value=response):
            result = service.transcribe_audio(mock_audio_content)
        
        assert result['success'] is False
        assert 'No transcription result' in result['error']
    
    async def test_transcribe_audio_api_error(self, service, mock_audio_content):
        """Test handling API error response."""
        error_response = Mock()
        error_response.status_code = 400
        error_response.json.return_value = {
            "error": {"message": "Invalid audio data"}
        }
        
        with patch('requests.post', return_value=error_response):
            result = service.transcribe_audio(mock_audio_content)
        
        assert result['success'] is False
        assert 'status 400' in result['error']
        assert 'Invalid audio data' in result['details']
    
    async def test_transcribe_audio_exception(self, service, mock_audio_content):
        """Test handling exceptions during transcription."""
        with patch('requests.post', side_effect=Exception("Network error")):
            result = service.transcribe_audio(mock_audio_content)
        
        assert result['success'] is False
        assert 'Network error' in result['error']
    
    async def test_transcribe_audio_full_config(self, service, mock_audio_content, mock_successful_response):
        """Test transcription with full configuration."""
        with patch('requests.post', return_value=mock_successful_response) as mock_post:
            service.transcribe_audio(
                audio_content=mock_audio_content,
                language_code="es-US",
                sample_rate_hertz=44100,
                encoding="MP3",
                model="video",
                enhanced=False
            )
        
        # Check the request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        config = payload['config']
        
        assert config['languageCode'] == "es-US"
        assert config['sampleRateHertz'] == 44100
        assert config['encoding'] == "MP3"
        assert config['model'] == "video"
        assert config['useEnhanced'] is False
        assert config['enableAutomaticPunctuation'] is True
        assert config['enableWordTimeOffsets'] is True
        assert 'speechContexts' in config
    
    async def test_transcribe_audio_no_sample_rate(self, service, mock_audio_content, mock_successful_response):
        """Test transcription without specifying sample rate."""
        with patch('requests.post', return_value=mock_successful_response) as mock_post:
            service.transcribe_audio(
                audio_content=mock_audio_content,
                encoding="FLAC"
            )
        
        # Should not include sampleRateHertz in config
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert 'sampleRateHertz' not in payload['config']
    
    async def test_encoding_normalization(self, service, mock_audio_content, mock_successful_response):
        """Test encoding is normalized to uppercase."""
        with patch('requests.post', return_value=mock_successful_response) as mock_post:
            service.transcribe_audio(
                audio_content=mock_audio_content,
                encoding="webm_opus"  # lowercase
            )
        
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['config']['encoding'] == "WEBM_OPUS"
    
    async def test_transcribe_audio_empty_alternatives(self, service, mock_audio_content):
        """Test handling when results have no alternatives."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "results": [
                {
                    "alternatives": []  # Empty alternatives
                }
            ]
        }
        
        with patch('requests.post', return_value=response):
            result = service.transcribe_audio(mock_audio_content)
        
        assert result['success'] is False
        assert 'No transcription result' in result['error']
    
    def test_singleton_instance(self):
        """Test that stt_service is a singleton instance."""
        assert hasattr(stt_service, 'api_key')
        assert hasattr(stt_service, 'transcribe_audio')
        assert hasattr(stt_service, 'get_supported_languages')
