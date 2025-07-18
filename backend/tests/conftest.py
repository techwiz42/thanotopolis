# tests/conftest.py
import pytest
import asyncio
import warnings
from unittest.mock import Mock, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from app.main import app
from app.models.models import User, Tenant

# Suppress warnings for testing
warnings.filterwarnings("ignore", category=DeprecationWarning, module="fastapi.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*TelephonyVoiceAgentHandler.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, module="_pytest.assertion.rewrite")


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test function to prevent cross-test pollution."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    
    # Cancel all remaining tasks
    try:
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending_tasks:
            for task in pending_tasks:
                task.cancel()
            # Wait for tasks to be cancelled
            loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
    except Exception:
        pass
    finally:
        loop.close()


@pytest.fixture
async def client():
    """Create an HTTP client for testing."""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
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


# Missing fixtures for billing and API tests
@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_tenant():
    """Create a sample tenant for testing."""
    tenant = Mock(spec=Tenant)
    tenant.id = uuid4()
    tenant.name = "Sample Organization"
    tenant.subdomain = "sampleorg"
    tenant.is_active = True
    tenant.created_at = datetime.now(timezone.utc)
    return tenant


@pytest.fixture
def sample_user(sample_tenant):
    """Create a sample user for testing."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.role = "user"
    user.is_active = True
    user.is_verified = True
    user.tenant_id = sample_tenant.id
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def sample_admin_user(sample_tenant):
    """Create a sample admin user for testing."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "admin@example.com"
    user.username = "adminuser"
    user.first_name = "Admin"
    user.last_name = "User"
    user.role = "admin"
    user.is_active = True
    user.is_verified = True
    user.tenant_id = sample_tenant.id
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def sample_org_admin_user(sample_tenant):
    """Create a sample org admin user for testing."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "orgadmin@example.com"
    user.username = "orgadminuser"
    user.first_name = "OrgAdmin"
    user.last_name = "User"
    user.role = "org_admin"
    user.is_active = True
    user.is_verified = True
    user.tenant_id = sample_tenant.id
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def sample_super_admin_user():
    """Create a sample super admin user for testing."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "superadmin@example.com"
    user.username = "superadmin"
    user.first_name = "Super"
    user.last_name = "Admin"
    user.role = "super_admin"
    user.is_active = True
    user.is_verified = True
    user.tenant_id = None  # Super admin not tied to specific tenant
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def authenticated_user(sample_user):
    """Create authenticated user context with headers."""
    return {
        "user": sample_user,
        "headers": {"Authorization": f"Bearer test_token_{sample_user.id}"}
    }


@pytest.fixture
def authenticated_admin(sample_admin_user):
    """Create authenticated admin context with headers."""
    return {
        "user": sample_admin_user,
        "headers": {"Authorization": f"Bearer test_token_{sample_admin_user.id}"}
    }


@pytest.fixture
def authenticated_org_admin(sample_org_admin_user):
    """Create authenticated org admin context with headers."""
    return {
        "user": sample_org_admin_user,
        "headers": {"Authorization": f"Bearer test_token_{sample_org_admin_user.id}"}
    }


@pytest.fixture
def authenticated_super_admin(sample_super_admin_user):
    """Create authenticated super admin context with headers."""
    return {
        "user": sample_super_admin_user,
        "headers": {"Authorization": f"Bearer test_token_{sample_super_admin_user.id}"}
    }


@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    
    # Mock the execute method to return a proper result
    def create_mock_result(return_value=None, scalar_value=None, scalars_all_value=None):
        mock_result = AsyncMock()
        if scalar_value is not None:
            mock_result.scalar_one_or_none.return_value = scalar_value
            mock_result.scalar_one.return_value = scalar_value
            mock_result.scalar.return_value = scalar_value
        if scalars_all_value is not None:
            mock_scalars = Mock()
            mock_scalars.all.return_value = scalars_all_value
            mock_result.scalars.return_value = mock_scalars
        elif return_value is not None:
            mock_scalars = Mock()
            mock_scalars.all.return_value = return_value
            mock_result.scalars.return_value = mock_scalars
        else:
            mock_scalars = Mock()
            mock_scalars.all.return_value = []
            mock_result.scalars.return_value = mock_scalars
        return mock_result
    
    # Default mock result
    session.execute.return_value = create_mock_result()
    session.add = Mock()  # Use regular Mock, not AsyncMock for non-async methods
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    
    # Store the create_mock_result function for tests to use
    session._create_mock_result = create_mock_result
    
    return session


@pytest.fixture
def other_user(sample_tenant):
    """Create another sample user for testing access control."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "other@example.com"
    user.username = "otheruser"
    user.first_name = "Other"
    user.last_name = "User"
    user.role = "user"
    user.is_active = True
    user.is_verified = True
    user.tenant_id = sample_tenant.id
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def inactive_user(sample_tenant):
    """Create an inactive sample user for testing."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "inactive@example.com"
    user.username = "inactiveuser"
    user.first_name = "Inactive"
    user.last_name = "User"
    user.role = "user"
    user.is_active = False  # This user is inactive
    user.is_verified = True
    user.tenant_id = sample_tenant.id
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def admin_user(sample_tenant):
    """Create an admin user for testing."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "admin@example.com"
    user.username = "adminuser"
    user.first_name = "Admin"
    user.last_name = "User"
    user.role = "admin"
    user.is_active = True
    user.is_verified = True
    user.tenant_id = sample_tenant.id
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def other_tenant():
    """Create another tenant for testing isolation."""
    tenant = Mock(spec=Tenant)
    tenant.id = uuid4()
    tenant.name = "Other Organization"
    tenant.subdomain = "otherorg"
    tenant.is_active = True
    tenant.created_at = datetime.now(timezone.utc)
    return tenant


@pytest.fixture
def other_tenant_user(other_tenant):
    """Create a user from another tenant for testing isolation."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "othertenant@example.com"
    user.username = "othertenantuser"
    user.first_name = "OtherTenant"
    user.last_name = "User"
    user.role = "user"
    user.is_active = True
    user.is_verified = True
    user.tenant_id = other_tenant.id
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def auth_headers(sample_user):
    """Create authentication headers for testing."""
    return {"Authorization": f"Bearer test_token_{sample_user.id}"}


@pytest.fixture(autouse=True, scope="function")
def reset_global_state():
    """Reset global state between tests to prevent pollution."""
    yield
    
    # Clean up after each test
    try:
        # Reset websocket globals
        import app.api.websockets as ws_module
        ws_module.active_connections.clear()
        ws_module.connection_stats = {
            "total": 0,
            "by_conversation": {},
            "by_user": {},
            "last_cleanup": None
        }
        
        # Cancel cleanup task if it exists
        if hasattr(ws_module, 'cleanup_task') and ws_module.cleanup_task is not None:
            if not ws_module.cleanup_task.done():
                ws_module.cleanup_task.cancel()
            ws_module.cleanup_task = None
            
    except ImportError:
        # Module not imported yet, nothing to clean
        pass
    except Exception:
        # Ignore cleanup errors
        pass
        
    try:
        # Reset buffer manager state
        from app.core.buffer_manager import buffer_manager
        if hasattr(buffer_manager, '_conversation_buffers'):
            buffer_manager._conversation_buffers.clear()
        if hasattr(buffer_manager, '_initialized'):
            buffer_manager._initialized = True
    except ImportError:
        pass
    except Exception:
        pass
        
    try:
        # Reset monitoring service state
        from app.services.monitoring_service import monitoring_service
        if hasattr(monitoring_service, 'websocket_connections'):
            monitoring_service.websocket_connections.clear()
        if hasattr(monitoring_service, 'active_conversations'):
            monitoring_service.active_conversations.clear()
    except ImportError:
        pass
    except Exception:
        pass
        
    try:
        # Reset database engine state and connection pools to prevent event loop conflicts
        import app.db.database as db_module
        # Force close any existing connections
        if hasattr(db_module, 'engine') and db_module.engine is not None:
            # Don't dispose the engine as it's session-scoped, but clear connection pools
            if hasattr(db_module.engine, 'pool'):
                try:
                    # Force close any hanging connections
                    db_module.engine.pool.checkedout()
                except:
                    pass
    except ImportError:
        pass
    except Exception:
        pass
        
    try:
        # Reset asyncio event loop state
        import asyncio
        # Get the current event loop and ensure it's properly closed for the next test
        try:
            current_loop = asyncio.get_running_loop()
            # Don't close the running loop, but clear any pending tasks
            for task in asyncio.all_tasks(current_loop):
                if not task.done() and not task.cancelled():
                    task.cancel()
        except RuntimeError:
            # No running loop, which is fine
            pass
    except Exception:
        pass
        
    try:
        # Clear FastAPI dependency overrides that might hold database references
        from app.main import app
        app.dependency_overrides.clear()
    except ImportError:
        pass
    except Exception:
        pass
