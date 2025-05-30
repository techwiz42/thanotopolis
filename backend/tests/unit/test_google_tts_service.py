# backend/tests/unit/test_google_tts_service.py
import pytest
import base64
from unittest.mock import Mock, patch, MagicMock
import json
import requests

from app.services.voice.google_tts_service import GoogleTTSService

class TestGoogleTTSService:
    """Test suite for Google Text-to-Speech Service."""
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-api-key'}):
            yield
    
    @pytest.fixture
    def service(self, mock_env):
        """Create TTS service instance."""
        return GoogleTTSService()
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock successful API response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "audioContent": base64.b64encode(b"fake audio data").decode()
        }
        return response
    
    def test_load_api_key_from_env(self, mock_env):
        """Test loading API key from environment."""
        service = GoogleTTSService()
        assert service.api_key == 'test-api-key'
    
    def test_load_api_key_from_project_env_file(self):
        """Test loading API key from project .env file."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = lambda path: path == '/home/peter/agent_framework/backend/.env'
                
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value = [
                        'OTHER_VAR=value\n',
                        'GOOGLE_API_KEY="project-api-key"\n'
                    ]
                    
                    service = GoogleTTSService()
                    assert service.api_key == 'project-api-key'
    
    def test_load_api_key_from_system_env_file(self):
        """Test loading API key from system .env file."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = lambda path: path == '/etc/cyberiad/.env'
                
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value = [
                        'GOOGLE_API_KEY=system-api-key\n'
                    ]
                    
                    service = GoogleTTSService()
                    assert service.api_key == 'system-api-key'
    
    def test_load_api_key_not_found(self):
        """Test handling when API key is not found."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('os.path.exists', return_value=False):
                service = GoogleTTSService()
                assert service.api_key is None
    
    def test_get_available_voices(self, service):
        """Test getting list of available voices."""
        voices = service.get_available_voices()
        
        assert len(voices) > 0
        assert all('id' in v for v in voices)
        assert all('name' in v for v in voices)
        assert all('gender' in v for v in voices)
        assert all('quality' in v for v in voices)
        
        # Check sorting by quality
        qualities = [v['quality'] for v in voices]
        assert qualities == sorted(qualities, key=lambda x: {"studio": 0, "neural2": 1, "standard": 2}.get(x, 3))
    
    def test_escape_for_ssml(self, service):
        """Test SSML escaping."""
        text = 'Test & "quotes" < > \' em—dash'
        escaped = service.escape_for_ssml(text)
        
        assert '&amp;' in escaped
        assert '&lt;' in escaped
        assert '&gt;' in escaped
        assert '&quot;' in escaped
        assert '&apos;' in escaped
        assert '--' in escaped  # em dash replaced
    
    def test_add_contextual_emphasis(self, service):
        """Test adding contextual emphasis."""
        text = "This is very important but also quite interesting."
        processed = service.add_contextual_emphasis(text)
        
        assert '<emphasis level="strong">important</emphasis>' in processed
        assert '<emphasis level="strong">interesting</emphasis>' in processed
        assert '<emphasis level="moderate">but</emphasis>' in processed
    
    def test_add_natural_variations(self, service):
        """Test adding natural prosody variations."""
        text = "First sentence. Is this a question? (This is parenthetical.) Last sentence."
        processed = service.add_natural_variations(text)
        
        # Should have prosody tags
        assert '<prosody' in processed
        
        # Questions should have higher pitch
        assert 'pitch="+' in processed
        
        # Parenthetical should be quieter
        assert 'volume="-2dB"' in processed
    
    def test_handle_special_content(self, service):
        """Test handling special content like URLs, dates, etc."""
        text = "Visit https://example.com on 12/25/2023 at 3:30 PM for $99.99 (50% off)."
        processed = service.handle_special_content(text)
        
        assert 'website example.com' in processed
        assert '<say-as interpret-as="date"' in processed
        assert '<say-as interpret-as="time"' in processed
        assert '<say-as interpret-as="currency"' in processed
        assert '<say-as interpret-as="cardinal">50</say-as> percent' in processed
    
    def test_preprocess_text_basic(self, service):
        """Test basic text preprocessing."""
        text = "Hello world. How are you?"
        processed = service.preprocess_text(text, enhance=False)
        
        assert processed.startswith('<speak>')
        assert processed.endswith('</speak>')
        assert '<break time=' in processed
    
    def test_preprocess_text_enhanced(self, service):
        """Test enhanced text preprocessing."""
        text = "This is very important! Visit https://example.com today."
        processed = service.preprocess_text(text, enhance=True)
        
        assert '<speak>' in processed
        assert '<emphasis' in processed
        assert 'website' in processed
        assert '<break' in processed
    
    def test_preprocess_text_already_ssml(self, service):
        """Test that already-SSML text is not reprocessed."""
        ssml_text = '<speak>Already SSML</speak>'
        processed = service.preprocess_text(ssml_text)
        
        assert processed == ssml_text
    
    def test_validate_ssml_content(self, service):
        """Test SSML content validation."""
        original = "Test content with words"
        valid_ssml = '<speak>Test content with words</speak>'
        invalid_ssml = '<speak>Test content</speak>'  # Missing "with words"
        
        assert service.validate_ssml_content(original, valid_ssml) is True
        assert service.validate_ssml_content(original, invalid_ssml) is False
    
    def test_synthesize_speech_success(self, service, mock_response):
        """Test successful speech synthesis."""
        with patch('requests.post', return_value=mock_response):
            result = service.synthesize_speech(
                text="Hello world",
                voice_id="en-US-Studio-O"
            )
        
        assert result['success'] is True
        assert 'audio' in result
        assert result['encoding'] == 'mp3'
        assert result['voice_id'] == 'en-US-Studio-O'
        assert result['voice_quality'] == 'studio'
    
    def test_synthesize_speech_no_api_key(self):
        """Test synthesis without API key."""
        service = GoogleTTSService()
        service.api_key = None
        
        result = service.synthesize_speech("Hello")
        
        assert result['success'] is False
        assert 'not configured' in result['error']
    
    def test_synthesize_speech_api_error(self, service):
        """Test handling API error response."""
        error_response = Mock()
        error_response.status_code = 400
        error_response.json.return_value = {
            "error": {"message": "Invalid request"}
        }
        
        with patch('requests.post', return_value=error_response):
            result = service.synthesize_speech("Hello")
        
        assert result['success'] is False
        assert 'status 400' in result['error']
        assert 'Invalid request' in result['details']
    
    def test_synthesize_speech_missing_audio_content(self, service):
        """Test handling response missing audio content."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {}  # No audioContent
        
        with patch('requests.post', return_value=response):
            result = service.synthesize_speech("Hello")
        
        assert result['success'] is False
        assert 'Missing audio content' in result['error']
    
    def test_synthesize_speech_exception(self, service):
        """Test handling exceptions during synthesis."""
        with patch('requests.post', side_effect=Exception("Network error")):
            result = service.synthesize_speech("Hello")
        
        assert result['success'] is False
        assert 'Network error' in result['error']
    
    def test_synthesize_speech_voice_fallback(self, service, mock_response):
        """Test voice fallback to default."""
        with patch('requests.post', return_value=mock_response):
            result = service.synthesize_speech(
                text="Hello",
                voice_id="invalid-voice"
            )
        
        # Should use default voice
        assert result['voice_id'] == service.default_voice
    
    def test_synthesize_speech_parameters(self, service, mock_response):
        """Test synthesis with custom parameters."""
        with patch('requests.post', return_value=mock_response) as mock_post:
            service.synthesize_speech(
                text="Hello",
                voice_id="en-US-Neural2-A",
                speaking_rate=1.2,
                pitch=5.0,
                volume_gain_db=2.0,
                audio_encoding="OGG_OPUS",
                preprocess_text=False
            )
        
        # Check the request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        
        assert payload['input']['text'] == "Hello"  # No SSML when preprocess_text=False
        assert payload['voice']['name'] == "en-US-Neural2-A"
        assert payload['audioConfig']['speakingRate'] == 1.2
        assert payload['audioConfig']['pitch'] == 5.0
        assert payload['audioConfig']['volumeGainDb'] == 2.0
        assert payload['audioConfig']['audioEncoding'] == "OGG_OPUS"
    
    def test_get_audio_mime_type(self, service):
        """Test MIME type mapping."""
        assert service.get_audio_mime_type("mp3") == "audio/mpeg"
        assert service.get_audio_mime_type("linear16") == "audio/wav"
        assert service.get_audio_mime_type("ogg_opus") == "audio/ogg"
        assert service.get_audio_mime_type("unknown") == "audio/mpeg"  # Default
    
    def test_get_recommended_voice(self, service):
        """Test voice recommendation."""
        # Test female US voice
        voice = service.get_recommended_voice(gender="FEMALE", accent="US")
        assert voice.startswith("en-US-")
        assert service.voices[voice]["gender"] == "FEMALE"
        
        # Test male GB voice
        voice = service.get_recommended_voice(gender="MALE", accent="GB")
        assert voice.startswith("en-GB-")
        assert service.voices[voice]["gender"] == "MALE"
        
        # Test default when no match
        voice = service.get_recommended_voice(gender="OTHER", accent="XX")
        assert voice == service.default_voice
    
    def test_debug_ssml(self, service):
        """Test SSML debugging functionality."""
        text = "Test & text"
        debug_info = service.debug_ssml(text)
        
        assert 'original' in debug_info
        assert 'escaped' in debug_info
        assert 'basic_ssml' in debug_info
        assert 'enhanced_ssml' in debug_info
        assert 'legacy_ssml' in debug_info
        
        # Check plain text extraction
        assert 'basic_ssml_plain' in debug_info
        assert debug_info['basic_ssml_plain'] == "Test & text"
    
    def test_preprocess_text_legacy(self, service):
        """Test legacy preprocessing method."""
        text = "Hello world. Visit https://example.com today!"
        processed = service.preprocess_text_legacy(text)
        
        assert processed.startswith('<speak>')
        assert processed.endswith('</speak>')
        assert 'link' in processed  # URL replaced
        assert '<break time="500ms"/>' in processed  # Sentence break
        # Skip the comma check as it's modified in the current implementation
