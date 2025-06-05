# tests/conftest_voice.py
"""
Pytest configuration and fixtures for voice service tests.
Updated for current voice services implementation.
"""
import pytest
import asyncio
import os
import io
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import tempfile
import wave
import struct
import json

from app.main import app
from app.auth.auth import get_current_active_user
from app.models.models import User
from app.services.voice import deepgram_service, elevenlabs_service
from app.services.voice.deepgram_service import DeepgramService, LiveTranscriptionSession
from app.services.voice.elevenlabs_service import ElevenLabsService


# Voice-specific user fixtures (extending main conftest fixtures)
@pytest.fixture
def voice_test_user():
    """Create a mock user specifically optimized for voice testing."""
    user = Mock(spec=User)
    user.id = "123e4567-e89b-12d3-a456-426614174000"
    user.email = "voiceuser@cyberiad.ai"
    user.username = "voicetest"
    user.first_name = "Voice"
    user.last_name = "Tester"
    user.tenant_id = "456e7890-e89b-12d3-a456-426614174001"
    user.role = "user"
    user.is_active = True
    user.is_verified = True
    
    # Voice-specific user preferences
    user.voice_settings = {
        "preferred_voice_id": "21m00Tcm4TlvDq8ikWAM",
        "preferred_model": "eleven_turbo_v2_5",
        "default_language": "en-US",
        "default_stability": 0.5,
        "default_similarity_boost": 0.5
    }
    
    return user


@pytest.fixture
def voice_admin_user():
    """Create a mock admin user for voice testing."""
    user = Mock(spec=User)
    user.id = "987e6543-e21b-12d3-a456-426614174999"
    user.email = "voiceadmin@cyberiad.ai"
    user.username = "voiceadmin"
    user.first_name = "Voice"
    user.last_name = "Admin"
    user.tenant_id = "456e7890-e89b-12d3-a456-426614174001"
    user.role = "admin"
    user.is_active = True
    user.is_verified = True
    
    # Admin can access all voice features
    user.voice_permissions = {
        "can_use_premium_voices": True,
        "can_access_analytics": True,
        "can_manage_voice_settings": True,
        "unlimited_usage": True
    }
    
    return user


# Voice service configuration fixtures
@pytest.fixture
def voice_test_config():
    """Comprehensive voice service test configuration."""
    return {
        # Deepgram settings
        "DEEPGRAM_API_KEY": "test_deepgram_key_12345",
        "DEEPGRAM_MODEL": "nova-2",
        "DEEPGRAM_LANGUAGE": "en-US",
        
        # ElevenLabs settings
        "ELEVENLABS_API_KEY": "test_elevenlabs_key_67890",
        "ELEVENLABS_VOICE_ID": "21m00Tcm4TlvDq8ikWAM",
        "ELEVENLABS_MODEL": "eleven_turbo_v2_5",
        "ELEVENLABS_OUTPUT_FORMAT": "mp3_44100_128",
        "ELEVENLABS_OPTIMIZE_STREAMING_LATENCY": 3,
        
        # WebSocket settings
        "WS_HEARTBEAT_INTERVAL": 30,
        "WS_CONNECTION_TIMEOUT": 3600,
        
        # API settings
        "API_VERSION": "1.0",
        "MAX_CONTEXT_MESSAGES": 25
    }


# Authentication fixtures for voice endpoints
@pytest.fixture
def client_with_voice_auth(voice_test_user):
    """Create a test client with voice user authentication override."""
    app.dependency_overrides[get_current_active_user] = lambda: voice_test_user
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_voice_admin_auth(voice_admin_user):
    """Create a test client with voice admin authentication override."""
    app.dependency_overrides[get_current_active_user] = lambda: voice_admin_user
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client_with_voice_auth(voice_test_user):
    """Create an async test client with voice user authentication override."""
    app.dependency_overrides[get_current_active_user] = lambda: voice_test_user
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# Audio file fixtures
@pytest.fixture
def mock_wav_file():
    """Create a realistic mock WAV audio file for testing."""
    # Create a temporary WAV file with actual audio data
    sample_rate = 16000
    duration = 2.0  # 2 seconds
    frequency = 440  # A4 note
    
    # Generate sine wave
    frames = int(duration * sample_rate)
    audio_samples = []
    
    for i in range(frames):
        # Generate a sine wave with some variation
        t = i / sample_rate
        amplitude = 16000 * 0.3
        sample = int(amplitude * 
                    (0.5 * (1 + (i / frames))) *  # Fade in
                    (1 if (i // (sample_rate // frequency)) % 2 == 0 else -1))  # Square wave
        audio_samples.append(struct.pack('<h', max(-32767, min(32767, sample))))
    
    # Create WAV file in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(audio_samples))
    
    wav_buffer.seek(0)
    audio_content = wav_buffer.read()
    
    return ("test_recording.wav", audio_content, "audio/wav")


@pytest.fixture
def mock_mp3_file():
    """Create a mock MP3 audio file for testing."""
    # Create a more realistic MP3 header and data
    mp3_header = b'\xff\xfb\x90\x00'  # MP3 frame header
    mp3_data = mp3_header + b'\x00' * 2048  # 2KB of MP3 data
    
    return ("test_audio.mp3", mp3_data, "audio/mpeg")


@pytest.fixture
def mock_flac_file():
    """Create a mock FLAC audio file for testing."""
    # FLAC file signature and minimal data
    flac_header = b'fLaC'
    flac_data = flac_header + b'\x00' * 1024  # Minimal FLAC data
    
    return ("test_audio.flac", flac_data, "audio/flac")


@pytest.fixture
def large_audio_file():
    """Create a larger mock audio file for performance testing."""
    # Simulate 30 seconds of 16kHz mono audio
    sample_rate = 16000
    duration = 30.0
    frames = int(duration * sample_rate)
    
    # Generate audio data (simple pattern to keep it fast)
    audio_data = b'\x00\x01\x02\x03' * (frames // 2)  # 2 bytes per sample
    
    return ("large_recording.wav", audio_data, "audio/wav")


# Voice service response fixtures
@pytest.fixture
def comprehensive_transcription_response():
    """Create a comprehensive transcription response with all fields."""
    return {
        "success": True,
        "transcript": "This is a comprehensive test transcription with multiple speakers and detailed timing information.",
        "confidence": 0.92,
        "words": [
            {"word": "This", "start": 0.0, "end": 0.25, "confidence": 0.95, "speaker": 0},
            {"word": "is", "start": 0.3, "end": 0.45, "confidence": 0.88, "speaker": 0},
            {"word": "a", "start": 0.5, "end": 0.6, "confidence": 0.91, "speaker": 0},
            {"word": "comprehensive", "start": 0.65, "end": 1.3, "confidence": 0.93, "speaker": 0},
            {"word": "test", "start": 1.35, "end": 1.6, "confidence": 0.94, "speaker": 0},
            {"word": "transcription", "start": 1.65, "end": 2.4, "confidence": 0.89, "speaker": 0},
            {"word": "with", "start": 2.45, "end": 2.7, "confidence": 0.96, "speaker": 0},
            {"word": "multiple", "start": 2.75, "end": 3.2, "confidence": 0.87, "speaker": 1},
            {"word": "speakers", "start": 3.25, "end": 3.8, "confidence": 0.92, "speaker": 1},
            {"word": "and", "start": 3.85, "end": 4.0, "confidence": 0.94, "speaker": 1},
            {"word": "detailed", "start": 4.05, "end": 4.5, "confidence": 0.88, "speaker": 1},
            {"word": "timing", "start": 4.55, "end": 4.9, "confidence": 0.91, "speaker": 1},
            {"word": "information", "start": 4.95, "end": 5.6, "confidence": 0.85, "speaker": 1}
        ],
        "speakers": [0, 1],
        "paragraphs": [
            {
                "text": "This is a comprehensive test transcription with multiple speakers and detailed timing information.",
                "start": 0.0,
                "end": 5.6,
                "speaker": 0
            }
        ],
        "raw_response": {
            "metadata": {
                "transaction_key": "deprecated",
                "request_id": "test-request-123",
                "sha256": "test-hash",
                "created": "2024-01-01T12:00:00.000Z",
                "duration": 5.6,
                "channels": 1,
                "models": ["nova-2"],
                "model_info": {
                    "nova-2": {
                        "name": "2-general-nova",
                        "canonical_name": "nova-2",
                        "architecture": "nova",
                        "languages": ["en"],
                        "version": "2024-01-09.29447",
                        "uuid": "test-uuid-123",
                        "batch": False,
                        "streaming": False
                    }
                }
            }
        }
    }


@pytest.fixture
def high_quality_synthesis_response():
    """Create a high-quality speech synthesis response."""
    # Generate more realistic audio data (larger file)
    fake_audio_data = b'\x00\x01\x02\x03\x04\x05\x06\x07' * 1024  # 8KB of fake audio
    
    return {
        "success": True,
        "audio_data": fake_audio_data,
        "content_type": "audio/mpeg",
        "text": "This is a high-quality test synthesis with advanced voice settings and premium features.",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128",
        "size_bytes": len(fake_audio_data)
    }


@pytest.fixture
def elevenlabs_voices_response():
    """Create a comprehensive ElevenLabs voices response."""
    return {
        "success": True,
        "voices": [
            {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Rachel",
                "samples": None,
                "category": "premade",
                "fine_tuning": {
                    "is_allowed_to_fine_tune": False,
                    "finetuning_state": "not_started"
                },
                "labels": {
                    "accent": "american",
                    "description": "calm",
                    "age": "young",
                    "gender": "female",
                    "use_case": "narration"
                },
                "description": "A calm, soothing voice perfect for narration and audiobooks.",
                "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/21m00Tcm4TlvDq8ikWAM/test.mp3",
                "available_for_tiers": ["free", "starter", "creator", "pro"],
                "settings": None,
                "sharing": None,
                "high_quality_base_model_ids": ["eleven_multilingual_v2"]
            },
            {
                "voice_id": "AZnzlk1XvdvUeBnXmlld",
                "name": "Domi",
                "samples": None,
                "category": "premade",
                "fine_tuning": {
                    "is_allowed_to_fine_tune": False,
                    "finetuning_state": "not_started"
                },
                "labels": {
                    "accent": "american",
                    "description": "strong",
                    "age": "young",
                    "gender": "female",
                    "use_case": "conversation"
                },
                "description": "A strong, confident voice ideal for conversational applications.",
                "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/AZnzlk1XvdvUeBnXmlld/test.mp3",
                "available_for_tiers": ["free", "starter", "creator", "pro"],
                "settings": None,
                "sharing": None,
                "high_quality_base_model_ids": ["eleven_multilingual_v2"]
            },
            {
                "voice_id": "custom_voice_123",
                "name": "Custom Business Voice",
                "samples": None,
                "category": "cloned",
                "fine_tuning": {
                    "is_allowed_to_fine_tune": True,
                    "finetuning_state": "fine_tuned"
                },
                "labels": {
                    "accent": "british",
                    "description": "professional",
                    "age": "middle_aged",
                    "gender": "male",
                    "use_case": "business"
                },
                "description": "A professional British male voice for business applications.",
                "preview_url": None,
                "available_for_tiers": ["pro"],
                "settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.85,
                    "style": 0.1,
                    "use_speaker_boost": True
                },
                "sharing": {
                    "status": "private",
                    "history_item_sample_id": None,
                    "original_voice_id": None,
                    "public_owner_id": None,
                    "liked_by_count": 0,
                    "cloned_by_count": 0
                },
                "high_quality_base_model_ids": ["eleven_multilingual_v2"]
            }
        ]
    }


@pytest.fixture
def elevenlabs_models_response():
    """Create a comprehensive ElevenLabs models response."""
    return {
        "success": True,
        "models": [
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
                "description": "Our fastest model, optimized for real-time applications with low latency.",
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
                "description": "Our most advanced model supporting 29 languages with the highest quality output.",
                "language": {
                    "language_id": "multi",
                    "name": "Multilingual"
                },
                "max_characters_request_free_user": 500,
                "max_characters_request_subscribed_user": 5000,
                "maximum_text_length_per_request": 5000
            },
            {
                "model_id": "eleven_turbo_v2",
                "name": "Turbo v2",
                "can_be_finetuned": False,
                "can_do_text_to_speech": True,
                "can_do_voice_conversion": False,
                "can_use_style": False,
                "can_use_speaker_boost": True,
                "serves_pro_voices": False,
                "token_cost_factor": 0.5,
                "description": "Fast and efficient model for basic text-to-speech applications.",
                "language": {
                    "language_id": "en",
                    "name": "English"
                },
                "max_characters_request_free_user": 1000,
                "max_characters_request_subscribed_user": 10000,
                "maximum_text_length_per_request": 10000
            }
        ]
    }


@pytest.fixture
def elevenlabs_user_info_response():
    """Create a comprehensive user info response from ElevenLabs."""
    return {
        "success": True,
        "user_info": {
            "subscription": {
                "tier": "creator",
                "character_count": 15432,
                "character_limit": 100000,
                "can_extend_character_limit": True,
                "allowed_to_extend_character_limit": True,
                "next_character_count_reset_unix": 1735689600,  # 2025-01-01
                "voice_limit": 30,
                "max_voice_add_edits": 50,
                "voice_add_edit_counter": 12,
                "professional_voice_limit": 5,
                "can_extend_voice_limit": True,
                "can_use_instant_voice_cloning": True,
                "can_use_professional_voice_cloning": True,
                "can_use_speech_to_speech": True,
                "can_use_voice_conversion": True,
                "currency": "usd",
                "status": "active",
                "billing_period": "monthly_period",
                "character_refresh_period": "monthly_period",
                "next_invoice_date": "2025-02-01",
                "invoice_total_characters": 100000
            },
            "is_new_user": False,
            "xi_api_key": "test_key_redacted",
            "can_use_delayed_payment_methods": True,
            "is_onboarding_completed": True,
            "is_onboarding_checklist_completed": True,
            "first_name": "Voice",
            "last_name": "Tester",
            "profile_picture_url": None
        }
    }


# Service mocking fixtures
@pytest.fixture
def mock_deepgram_service():
    """Create a comprehensive mock Deepgram service."""
    mock_service = Mock(spec=DeepgramService)
    mock_service.is_available.return_value = True
    
    # Mock file transcription
    mock_service.transcribe_file = AsyncMock(return_value={
        "success": True,
        "transcript": "Mock transcription result from Deepgram service",
        "confidence": 0.95,
        "words": [
            {"word": "Mock", "start": 0.0, "end": 0.3, "confidence": 0.95},
            {"word": "transcription", "start": 0.35, "end": 1.0, "confidence": 0.94},
            {"word": "result", "start": 1.05, "end": 1.4, "confidence": 0.96}
        ],
        "speakers": [],
        "paragraphs": [{
            "text": "Mock transcription result from Deepgram service",
            "start": 0.0,
            "end": 1.4
        }],
        "raw_response": {}
    })
    
    # Mock live transcription
    mock_session = Mock(spec=LiveTranscriptionSession)
    mock_session.start = AsyncMock()
    mock_session.send_audio = AsyncMock()
    mock_session.finish = AsyncMock()
    mock_session.is_connected = True
    
    mock_service.start_live_transcription = AsyncMock(return_value=mock_session)
    
    return mock_service


@pytest.fixture
def mock_elevenlabs_service():
    """Create a comprehensive mock ElevenLabs service."""
    mock_service = Mock(spec=ElevenLabsService)
    mock_service.is_available.return_value = True
    
    # Mock speech synthesis
    fake_audio_data = b"mock_audio_data" * 100
    mock_service.synthesize_speech = AsyncMock(return_value={
        "success": True,
        "audio_data": fake_audio_data,
        "content_type": "audio/mpeg",
        "text": "Mock synthesis text",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "model_id": "eleven_turbo_v2_5",
        "output_format": "mp3_44100_128",
        "size_bytes": len(fake_audio_data)
    })
    
    # Mock speech streaming
    async def mock_stream_speech(*args, **kwargs):
        chunks = [b"chunk1", b"chunk2", b"chunk3", b"final_chunk"]
        for chunk in chunks:
            yield chunk
    
    mock_service.stream_speech = mock_stream_speech
    
    # Mock metadata methods
    mock_service.get_voices = AsyncMock(return_value={
        "success": True,
        "voices": [{"voice_id": "test_voice", "name": "Test Voice"}]
    })
    
    mock_service.get_voice_info = AsyncMock(return_value={
        "success": True,
        "voice": {"voice_id": "test_voice", "name": "Test Voice"}
    })
    
    mock_service.get_models = AsyncMock(return_value={
        "success": True,
        "models": [{"model_id": "test_model", "name": "Test Model"}]
    })
    
    mock_service.get_user_info = AsyncMock(return_value={
        "success": True,
        "user_info": {"subscription": {"tier": "free"}}
    })
    
    return mock_service


@pytest.fixture
def mock_voice_services(mock_deepgram_service, mock_elevenlabs_service):
    """Mock both voice services together."""
    with patch('app.services.voice.deepgram_service', mock_deepgram_service), \
         patch('app.services.voice.elevenlabs_service', mock_elevenlabs_service):
        yield {
            'deepgram': mock_deepgram_service,
            'elevenlabs': mock_elevenlabs_service
        }


# WebSocket testing fixtures
@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection for testing."""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.send_bytes = AsyncMock()
    websocket.receive = AsyncMock()
    websocket.receive_json = AsyncMock()
    websocket.receive_bytes = AsyncMock()
    websocket.close = AsyncMock()
    
    # Add realistic message simulation
    websocket.messages = []
    
    def add_message(msg):
        websocket.messages.append(msg)
    
    websocket.add_test_message = add_message
    
    return websocket


@pytest.fixture
def websocket_auth_token(voice_test_user):
    """Create a valid WebSocket authentication token."""
    from app.auth.auth import AuthService
    
    token = AuthService.create_access_token(
        data={
            "sub": voice_test_user.id,
            "email": voice_test_user.email,
            "role": voice_test_user.role
        }
    )
    return token


# Performance testing fixtures
@pytest.fixture
def performance_text_samples():
    """Create text samples of various lengths for performance testing."""
    base_text = "This is a comprehensive performance test sentence with multiple words and complex punctuation. "
    
    return {
        "tiny": "Hello world!",
        "short": base_text,
        "medium": base_text * 5,    # ~500 characters
        "long": base_text * 20,     # ~2000 characters  
        "very_long": base_text * 50, # ~5000 characters
        "extreme": base_text * 100   # ~10000 characters
    }


# Error simulation fixtures
@pytest.fixture
def mock_api_errors():
    """Create various API error responses for testing error handling."""
    return {
        "network_error": Exception("Network connection failed"),
        "rate_limit": {
            "success": False,
            "error": "Rate limit exceeded. Please try again in 60 seconds."
        },
        "quota_exceeded": {
            "success": False,
            "error": "Monthly character quota exceeded. Please upgrade your plan."
        },
        "invalid_voice": {
            "success": False,
            "error": "Voice ID not found or not accessible with current subscription."
        },
        "audio_too_long": {
            "success": False,
            "error": "Audio file is too long. Maximum duration is 10 minutes."
        },
        "unsupported_format": {
            "success": False,
            "error": "Unsupported audio format. Please use WAV, MP3, or FLAC."
        },
        "api_key_invalid": {
            "success": False,
            "error": "Invalid API key. Please check your authentication credentials."
        }
    }


# Utility functions
def create_websocket_message(msg_type: str, data: dict = None, binary_data: bytes = None):
    """Helper function to create WebSocket test messages."""
    if binary_data:
        return {"type": "websocket.receive", "bytes": binary_data}
    
    message = {"type": msg_type}
    if data:
        message.update(data)
    
    return {"type": "websocket.receive", "text": json.dumps(message)}


def assert_voice_response_format(response_data: dict, response_type: str = "transcription"):
    """Helper function to assert voice response formats."""
    assert "success" in response_data
    
    if response_type == "transcription":
        if response_data["success"]:
            required_fields = ["transcript", "confidence", "words", "speakers", "paragraphs"]
            for field in required_fields:
                assert field in response_data
    
    elif response_type == "synthesis":
        if response_data["success"]:
            required_fields = ["audio_data", "content_type", "text", "voice_id", "model_id"]
            for field in required_fields:
                assert field in response_data
            assert len(response_data["audio_data"]) > 0


def create_realistic_audio_data(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Helper function to create realistic audio data for testing."""
    frames = int(duration_seconds * sample_rate)
    audio_samples = []
    
    for i in range(frames):
        # Simple sine wave
        t = i / sample_rate
        frequency = 440  # A4 note
        sample = int(16000 * 0.3 * (2 ** 0.5) * (1 + (i / frames)) * 
                    (1 if (i // (sample_rate // frequency)) % 2 == 0 else -1))
        audio_samples.append(struct.pack('<h', max(-32767, min(32767, sample))))
    
    return b''.join(audio_samples)


# Cleanup and teardown
@pytest.fixture(autouse=True)
async def voice_test_cleanup():
    """Automatically clean up voice test resources."""
    yield
    
    # Clean up any test files, connections, etc.
    try:
        # Clear any mock patches
        if hasattr(patch, '_active_patches'):
            for active_patch in patch._active_patches[:]:
                try:
                    active_patch.stop()
                except:
                    pass
    except:
        pass
