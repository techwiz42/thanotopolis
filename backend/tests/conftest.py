# tests/conftest.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.models import User


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """Create an HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = "test_user_123"
    user.email = "test@example.com"
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_jwt_token():
    """Create a mock JWT token for testing."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXJfMTIzIiwiZXhwIjoxNjQwOTk1MjAwfQ.test_signature"


@pytest.fixture
def voice_test_audio_data():
    """Create mock audio data for voice testing."""
    # This would be actual audio bytes in a real scenario
    return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\x3e\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


@pytest.fixture
def voice_test_transcript():
    """Create mock transcript data for voice testing."""
    return {
        "success": True,
        "transcript": "This is a test transcription of audio content.",
        "confidence": 0.95,
        "words": [
            {"word": "This", "start": 0.0, "end": 0.2, "confidence": 0.95},
            {"word": "is", "start": 0.2, "end": 0.4, "confidence": 0.93},
            {"word": "a", "start": 0.4, "end": 0.5, "confidence": 0.92},
            {"word": "test", "start": 0.5, "end": 0.8, "confidence": 0.96},
            {"word": "transcription", "start": 0.8, "end": 1.5, "confidence": 0.94}
        ],
        "speakers": [],
        "paragraphs": [{
            "text": "This is a test transcription of audio content.",
            "start": 0.0,
            "end": 1.8,
            "speaker": None
        }],
        "raw_response": {}
    }


@pytest.fixture
def voice_test_synthesis_result():
    """Create mock synthesis result for voice testing."""
    mock_audio_data = b"fake_mp3_audio_data_" * 100  # Simulate larger audio file
    return {
        "success": True,
        "audio_data": mock_audio_data,
        "content_type": "audio/mpeg",
        "text": "This is a test of speech synthesis.",
        "voice_id": "test_voice_id",
        "model_id": "eleven_turbo_v2_5",
        "output_format": "mp3_44100_128",
        "size_bytes": len(mock_audio_data)
    }


@pytest.fixture
def mock_elevenlabs_voices():
    """Create mock ElevenLabs voices data."""
    return [
        {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "name": "Rachel",
            "samples": None,
            "category": "premade",
            "fine_tuning": {
                "language": None,
                "is_allowed_to_fine_tune": False,
                "fine_tuning_requested": False,
                "finetuning_state": "not_started",
                "verification_attempts": None,
                "verification_failures": [],
                "verification_attempts_count": 0,
                "slice_ids": None
            },
            "labels": {
                "accent": "american",
                "description": "calm",
                "age": "young",
                "gender": "female"
            },
            "description": None,
            "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/21m00Tcm4TlvDq8ikWAM/df6788f9-5c96-470d-8312-aab3b3d8f50a.mp3",
            "available_for_tiers": [],
            "settings": None,
            "sharing": None,
            "high_quality_base_model_ids": []
        },
        {
            "voice_id": "AZnzlk1XvdvUeBnXmlld",
            "name": "Domi",
            "samples": None,
            "category": "premade",
            "fine_tuning": {
                "language": None,
                "is_allowed_to_fine_tune": False,
                "fine_tuning_requested": False,
                "finetuning_state": "not_started",
                "verification_attempts": None,
                "verification_failures": [],
                "verification_attempts_count": 0,
                "slice_ids": None
            },
            "labels": {
                "accent": "american",
                "description": "strong",
                "age": "young",
                "gender": "female"
            },
            "description": None,
            "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/AZnzlk1XvdvUeBnXmlld/a8a3ff4e-4b43-4f17-ac52-3c8d7da2a9c4.mp3",
            "available_for_tiers": [],
            "settings": None,
            "sharing": None,
            "high_quality_base_model_ids": []
        }
    ]


@pytest.fixture
def mock_elevenlabs_models():
    """Create mock ElevenLabs models data."""
    return [
        {
            "model_id": "eleven_turbo_v2_5",
            "name": "Turbo v2.5",
            "can_be_finetuned": False,
            "can_do_text_to_speech": True,
            "can_do_voice_conversion": False,
            "can_use_style": True,
            "can_use_speaker_boost": True,
            "serves_pro_voices": False,
            "token_cost_factor": 1.0,
            "description": "Fastest model, ideal for applications where speed is crucial.",
            "language": {
                "language_id": "en",
                "name": "English"
            },
            "max_characters_request_free_user": 500,
            "max_characters_request_subscribed_user": 5000,
            "maximum_text_length_per_request": 5000
        },
        {
            "model_id": "eleven_multilingual_v2",
            "name": "Multilingual v2",
            "can_be_finetuned": True,
            "can_do_text_to_speech": True,
            "can_do_voice_conversion": True,
            "can_use_style": True,
            "can_use_speaker_boost": True,
            "serves_pro_voices": True,
            "token_cost_factor": 1.0,
            "description": "Cutting-edge model supporting 29 languages.",
            "language": {
                "language_id": "multi",
                "name": "Multilingual"
            },
            "max_characters_request_free_user": 500,
            "max_characters_request_subscribed_user": 5000,
            "maximum_text_length_per_request": 5000
        }
    ]


@pytest.fixture
def mock_deepgram_live_options():
    """Create mock Deepgram live options."""
    from deepgram import LiveOptions
    return LiveOptions(
        model="nova-2",
        language="en-US",
        punctuate=True,
        interim_results=True,
        smart_format=True,
        encoding="linear16",
        sample_rate=16000,
        channels=1
    )


@pytest.fixture
def mock_deepgram_prerecorded_options():
    """Create mock Deepgram prerecorded options."""
    from deepgram import PrerecordedOptions
    return PrerecordedOptions(
        model="nova-2",
        language="en-US",
        punctuate=True,
        diarize=False,
        smart_format=True,
        utterances=True,
        paragraphs=True
    )


# Utility functions for tests
def create_mock_websocket():
    """Create a mock WebSocket for testing."""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.send_bytes = AsyncMock()
    websocket.receive = AsyncMock()
    websocket.receive_json = AsyncMock()
    websocket.receive_bytes = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


def create_mock_file_upload(filename: str, content: bytes, content_type: str):
    """Create a mock file upload for testing."""
    from fastapi import UploadFile
    import io
    
    mock_file = UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers={"content-type": content_type}
    )
    return mock_file


# Async context managers for testing
class AsyncContextManager:
    """Helper class for async context managers in tests."""
    
    def __init__(self, return_value):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Custom assertions for voice testing
def assert_transcript_format(transcript_data):
    """Assert that transcript data has the correct format."""
    required_keys = ["success", "transcript", "confidence", "words", "speakers", "paragraphs"]
    for key in required_keys:
        assert key in transcript_data, f"Missing key: {key}"
    
    if transcript_data["success"]:
        assert isinstance(transcript_data["transcript"], str)
        assert isinstance(transcript_data["confidence"], (int, float))
        assert isinstance(transcript_data["words"], list)
        assert isinstance(transcript_data["speakers"], list)
        assert isinstance(transcript_data["paragraphs"], list)


def assert_synthesis_format(synthesis_data):
    """Assert that synthesis data has the correct format."""
    required_keys = ["success", "audio_data", "content_type", "text", "voice_id", "model_id"]
    for key in required_keys:
        assert key in synthesis_data, f"Missing key: {key}"
    
    if synthesis_data["success"]:
        assert isinstance(synthesis_data["audio_data"], bytes)
        assert isinstance(synthesis_data["content_type"], str)
        assert isinstance(synthesis_data["text"], str)
        assert isinstance(synthesis_data["voice_id"], str)
        assert isinstance(synthesis_data["model_id"], str)


# Configuration for pytest
def pytest_configure(config):
    """Configure pytest for voice service testing."""
    config.addinivalue_line(
        "markers", "voice: mark test as voice-related functionality"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "websocket: mark test as WebSocket-related"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Cleanup after tests
@pytest.fixture(autouse=True)
async def cleanup_connections():
    """Clean up any active connections after each test."""
    yield
    # This would clean up any global state if needed
    # For example, clearing connection managers, stopping background tasks, etc.
    pass
