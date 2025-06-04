# tests/conftest_voice.py
"""
Pytest configuration and fixtures for voice service tests.
"""
import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import tempfile
import wave
import struct

from app.main import app
from app.auth.auth import get_current_active_user
from app.models.models import User


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_user():
    """Create a comprehensive mock user for testing."""
    user = Mock(spec=User)
    user.id = "123e4567-e89b-12d3-a456-426614174000"
    user.email = "test@cyberiad.ai"
    user.username = "voicetest"
    user.first_name = "Voice"
    user.last_name = "Tester"
    user.tenant_id = "456e7890-e89b-12d3-a456-426614174001"
    user.role = "user"
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for testing."""
    user = Mock(spec=User)
    user.id = "987e6543-e21b-12d3-a456-426614174999"
    user.email = "admin@cyberiad.ai"
    user.username = "voiceadmin"
    user.first_name = "Voice"
    user.last_name = "Admin"
    user.tenant_id = "456e7890-e89b-12d3-a456-426614174001"
    user.role = "admin"
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture
def test_settings():
    """Create test settings for voice services."""
    return {
        "DEEPGRAM_API_KEY": "test_deepgram_key_12345",
        "DEEPGRAM_MODEL": "nova-2",
        "DEEPGRAM_LANGUAGE": "en-US",
        "ELEVENLABS_API_KEY": "test_elevenlabs_key_67890",
        "ELEVENLABS_VOICE_ID": "21m00Tcm4TlvDq8ikWAM",
        "ELEVENLABS_MODEL": "eleven_turbo_v2_5",
        "ELEVENLABS_OUTPUT_FORMAT": "mp3_44100_128",
        "ELEVENLABS_OPTIMIZE_STREAMING_LATENCY": 3
    }


@pytest.fixture
def client_with_auth(mock_user):
    """Create a test client with authentication override."""
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_admin_auth(mock_admin_user):
    """Create a test client with admin authentication override."""
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client_with_auth(mock_user):
    """Create an async test client with authentication override."""
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_wav_file():
    """Create a mock WAV audio file for testing."""
    # Create a temporary WAV file with sine wave
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        # WAV file parameters
        sample_rate = 16000
        duration = 1.0  # 1 second
        frequency = 440  # A4 note
        
        # Generate sine wave
        frames = int(duration * sample_rate)
        audio_data = []
        for i in range(frames):
            sample = int(32767 * 0.3 * (2 ** 0.5) * 
                        (1 + (i / frames)) * 
                        (1 if (i // (sample_rate // frequency)) % 2 == 0 else -1))
            audio_data.append(struct.pack('<h', sample))
        
        # Create WAV file
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(audio_data))
        
        # Read the file content
        temp_file.seek(0)
        audio_content = temp_file.read()
        
        # Clean up
        os.unlink(temp_file.name)
        
        return ("test_audio.wav", audio_content, "audio/wav")


@pytest.fixture
def mock_mp3_file():
    """Create a mock MP3 audio file for testing."""
    # Simple MP3 header + fake data for testing
    mp3_header = b'\xff\xfb\x90\x00'  # Basic MP3 frame header
    fake_mp3_data = mp3_header + b'\x00' * 1024  # 1KB of fake MP3 data
    
    return ("test_audio.mp3", fake_mp3_data, "audio/mpeg")


@pytest.fixture
def sample_transcription_response():
    """Create a sample successful transcription response."""
    return {
        "success": True,
        "transcript": "This is a sample transcription of the audio file.",
        "confidence": 0.92,
        "words": [
            {"word": "This", "start": 0.0, "end": 0.2, "confidence": 0.95},
            {"word": "is", "start": 0.25, "end": 0.35, "confidence": 0.88},
            {"word": "a", "start": 0.4, "end": 0.45, "confidence": 0.91},
            {"word": "sample", "start": 0.5, "end": 0.8, "confidence": 0.93},
            {"word": "transcription", "start": 0.85, "end": 1.4, "confidence": 0.89},
            {"word": "of", "start": 1.45, "end": 1.55, "confidence": 0.96},
            {"word": "the", "start": 1.6, "end": 1.7, "confidence": 0.94},
            {"word": "audio", "start": 1.75, "end": 2.0, "confidence": 0.87},
            {"word": "file", "start": 2.05, "end": 2.3, "confidence": 0.92}
        ],
        "speakers": [],
        "paragraphs": [{
            "text": "This is a sample transcription of the audio file.",
            "start": 0.0,
            "end": 2.3,
            "speaker": None
        }]
    }


@pytest.fixture
def sample_synthesis_response():
    """Create a sample successful speech synthesis response."""
    fake_audio_data = b'\x00\x01\x02\x03' * 256  # 1KB of fake audio data
    
    return {
        "success": True,
        "audio_data": fake_audio_data,
        "content_type": "audio/mpeg",
        "text": "This is test text for speech synthesis.",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "model_id": "eleven_turbo_v2_5",
        "output_format": "mp3_44100_128",
        "size_bytes": len(fake_audio_data)
    }


@pytest.fixture
def sample_voices_response():
    """Create a sample voices list response."""
    return {
        "success": True,
        "voices": [
            {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Rachel",
                "category": "premade",
                "gender": "female",
                "age": "young_adult",
                "accent": "american",
                "use_case": "narration"
            },
            {
                "voice_id": "AZnzlk1XvdvUeBnXmlld",
                "name": "Domi",
                "category": "premade",
                "gender": "female",
                "age": "young_adult",
                "accent": "american",
                "use_case": "conversation"
            },
            {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",
                "name": "Bella",
                "category": "premade",
                "gender": "female",
                "age": "young_adult",
                "accent": "american",
                "use_case": "narration"
            }
        ]
    }


@pytest.fixture
def sample_models_response():
    """Create a sample models list response."""
    return {
        "success": True,
        "models": [
            {
                "model_id": "eleven_turbo_v2",
                "name": "Turbo v2",
                "description": "Fastest model, optimized for real-time applications",
                "languages": ["en"],
                "max_characters": 500
            },
            {
                "model_id": "eleven_turbo_v2_5",
                "name": "Turbo v2.5",
                "description": "Enhanced version with better quality",
                "languages": ["en"],
                "max_characters": 500
            },
            {
                "model_id": "eleven_multilingual_v2",
                "name": "Multilingual v2",
                "description": "Supports multiple languages",
                "languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hi", "ko"],
                "max_characters": 500
            }
        ]
    }


@pytest.fixture
def sample_user_info_response():
    """Create a sample user info response from ElevenLabs."""
    return {
        "success": True,
        "user_info": {
            "subscription": {
                "tier": "starter",
                "character_count": 1500,
                "character_limit": 10000,
                "can_extend_character_limit": True,
                "allowed_to_extend_character_limit": True,
                "next_character_count_reset_unix": 1703980800,
                "voice_limit": 10,
                "max_voice_add_edits": 10,
                "voice_add_edit_counter": 0,
                "professional_voice_limit": 1,
                "can_extend_voice_limit": False,
                "can_use_instant_voice_cloning": True,
                "can_use_professional_voice_cloning": True,
                "currency": "usd",
                "status": "active"
            },
            "is_new_user": False,
            "xi_api_key": "redacted",
            "can_use_delayed_payment_methods": False
        }
    }


@pytest.fixture
def mock_deepgram_client():
    """Create a mock Deepgram client for testing."""
    client = Mock()
    
    # Mock prerecorded transcription
    mock_prerecorded = Mock()
    mock_response = Mock()
    mock_response.to_dict.return_value = {
        "results": {
            "channels": [{
                "alternatives": [{
                    "transcript": "Mock transcription result",
                    "confidence": 0.95,
                    "words": []
                }]
            }]
        }
    }
    mock_prerecorded.transcribe_file = AsyncMock(return_value=mock_response)
    client.listen.asyncprerecorded.v.return_value = mock_prerecorded
    
    # Mock live transcription
    mock_live_connection = Mock()
    mock_live_connection.start = AsyncMock(return_value=True)
    mock_live_connection.send = AsyncMock()
    mock_live_connection.finish = AsyncMock()
    mock_live_connection.on = Mock()
    client.listen.asynclive.v.return_value = mock_live_connection
    
    return client


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session for ElevenLabs testing."""
    session = AsyncMock()
    
    # Mock successful responses
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"success": True})
    mock_response.read = AsyncMock(return_value=b"fake_audio_data")
    mock_response.text = AsyncMock(return_value="Success")
    mock_response.headers = {"content-type": "audio/mpeg"}
    
    # Mock streaming response
    async def mock_iter_chunked(chunk_size):
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        for chunk in chunks:
            yield chunk
    
    mock_response.content.iter_chunked = mock_iter_chunked
    
    session.get.return_value.__aenter__.return_value = mock_response
    session.post.return_value.__aenter__.return_value = mock_response
    
    return session


# Parametrized test fixtures
@pytest.fixture(params=[
    ("audio/wav", "audio/wav"),
    ("audio/mp3", "audio/mpeg"),
    ("audio/mpeg", "audio/mpeg"),
    ("audio/flac", "audio/flac"),
    ("audio/ogg", "audio/ogg")
])
def audio_format_params(request):
    """Parametrized fixture for different audio formats."""
    return request.param


@pytest.fixture(params=[
    {"stability": 0.5, "similarity_boost": 0.5, "style": 0.0, "use_speaker_boost": True},
    {"stability": 0.8, "similarity_boost": 0.7, "style": 0.2, "use_speaker_boost": False},
    {"stability": 0.3, "similarity_boost": 0.3, "style": 0.5, "use_speaker_boost": True},
    {"stability": 1.0, "similarity_boost": 1.0, "style": 1.0, "use_speaker_boost": False}
])
def voice_settings_params(request):
    """Parametrized fixture for different voice settings."""
    return request.param


@pytest.fixture(params=[
    "mp3_44100_128",
    "mp3_44100_64",
    "mp3_22050_32",
    "pcm_16000",
    "pcm_22050",
    "pcm_24000",
    "pcm_44100"
])
def output_format_params(request):
    """Parametrized fixture for different output formats."""
    return request.param


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically clean up any test files created during testing."""
    yield
    # Cleanup code would go here if needed
    pass


# Performance testing fixtures
@pytest.fixture
def performance_test_text():
    """Create text of various lengths for performance testing."""
    base_text = "This is a test sentence for performance evaluation. "
    return {
        "short": base_text,
        "medium": base_text * 10,  # ~500 characters
        "long": base_text * 50,    # ~2500 characters
        "very_long": base_text * 100  # ~5000 characters
    }


@pytest.fixture
def large_audio_file():
    """Create a larger mock audio file for performance testing."""
    # Simulate 10 seconds of audio data
    sample_rate = 16000
    duration = 10.0
    frames = int(duration * sample_rate)
    
    # Generate basic audio data
    audio_data = b'\x00\x01' * frames  # Simple pattern
    
    return ("large_audio.wav", audio_data, "audio/wav")


# Error simulation fixtures
@pytest.fixture
def mock_network_error():
    """Create a mock network error for testing error handling."""
    import aiohttp
    return aiohttp.ClientError("Network connection failed")


@pytest.fixture
def mock_api_rate_limit_error():
    """Create a mock API rate limit error."""
    return {
        "success": False,
        "error": "Rate limit exceeded. Please try again later."
    }


@pytest.fixture
def mock_api_quota_error():
    """Create a mock API quota exceeded error."""
    return {
        "success": False,
        "error": "Character quota exceeded for this month."
    }


# Utility functions for tests
def create_mock_websocket_message(message_type: str, data: dict = None):
    """Helper function to create mock WebSocket messages."""
    message = {"type": message_type}
    if data:
        message.update(data)
    return message


def assert_audio_response_headers(response, expected_content_type: str = "audio/mpeg"):
    """Helper function to assert audio response headers."""
    assert response.headers["content-type"] == expected_content_type
    assert "content-length" in response.headers or "transfer-encoding" in response.headers
    
    # Check for custom headers
    custom_headers = ["X-Text-Length", "X-Voice-ID", "X-Model-ID", "X-Output-Format"]
    for header in custom_headers:
        if header in response.headers:
            assert response.headers[header] is not None


def assert_transcription_response(response_data: dict):
    """Helper function to assert transcription response structure."""
    required_fields = ["success", "transcript", "confidence", "words", "speakers", "paragraphs"]
    for field in required_fields:
        assert field in response_data
    
    if response_data["success"]:
        assert isinstance(response_data["transcript"], str)
        assert isinstance(response_data["confidence"], (int, float))
        assert isinstance(response_data["words"], list)
        assert isinstance(response_data["speakers"], list)
        assert isinstance(response_data["paragraphs"], list)


def assert_synthesis_response(response_data: dict):
    """Helper function to assert synthesis response structure."""
    required_fields = ["success", "audio_data", "content_type", "text", "voice_id", "model_id"]
    for field in required_fields:
        assert field in response_data
    
    if response_data["success"]:
        assert isinstance(response_data["audio_data"], bytes)
        assert len(response_data["audio_data"]) > 0
        assert response_data["content_type"].startswith("audio/")


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "voice: mark test as a voice service test"
    )
    config.addinivalue_line(
        "markers", "stt: mark test as a speech-to-text test"
    )
    config.addinivalue_line(
        "markers", "tts: mark test as a text-to-speech test"
    )
    config.addinivalue_line(
        "markers", "websocket: mark test as a WebSocket test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
