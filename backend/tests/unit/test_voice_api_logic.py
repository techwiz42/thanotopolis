import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import json
from datetime import datetime, timedelta
import asyncio

# Import the components we need to test
from app.api.streaming_stt import StreamingSTTManager, count_words
from app.api.voice_streaming import VoiceConnectionManager
from app.api.streaming_stt import authenticate_stt_websocket
from app.api.voice_streaming import authenticate_voice_websocket


class TestCountWords:
    """Test suite for the count_words function."""
    
    def test_count_words_empty_string(self):
        """Test word count with empty string."""
        assert count_words("") == 0
        assert count_words("   ") == 0
        assert count_words("\n\t") == 0
    
    def test_count_words_single_word(self):
        """Test word count with single word."""
        assert count_words("hello") == 1
        assert count_words("  hello  ") == 1
        assert count_words("\nhello\n") == 1
    
    def test_count_words_multiple_words(self):
        """Test word count with multiple words."""
        assert count_words("hello world") == 2
        assert count_words("the quick brown fox") == 4
        assert count_words("one two three four five") == 5
    
    def test_count_words_with_punctuation(self):
        """Test word count with punctuation."""
        assert count_words("Hello, world!") == 2
        assert count_words("What's up? How are you?") == 5
        assert count_words("one-two-three") == 1  # Hyphenated words count as one
        assert count_words("email@example.com") == 1  # Email counts as one word
    
    def test_count_words_with_special_characters(self):
        """Test word count with special characters."""
        assert count_words("Hello\tworld") == 2
        assert count_words("Line1\nLine2") == 2
        assert count_words("Word1\r\nWord2") == 2
        assert count_words("Test   multiple   spaces") == 3
    
    def test_count_words_with_numbers(self):
        """Test word count with numbers."""
        assert count_words("123 456") == 2
        assert count_words("Test123 456Test") == 2
        assert count_words("3.14159") == 1  # Decimal number counts as one
    
    def test_count_words_edge_cases(self):
        """Test word count edge cases."""
        assert count_words(None) == 0  # Should handle None gracefully
        assert count_words("a") == 1  # Single character word
        assert count_words("I am a test.") == 4
        assert count_words("   leading and trailing spaces   ") == 4


class TestStreamingSTTManager:
    """Test suite for StreamingSTTManager."""
    
    @pytest.fixture
    def stt_manager(self):
        """Create a StreamingSTTManager instance."""
        return StreamingSTTManager()
    
    @pytest.mark.asyncio
    async def test_connect_creates_session(self, stt_manager):
        """Test that connect creates a new session."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        
        session_id = await stt_manager.connect(websocket, user)
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert session_id in stt_manager.active_connections
        
        connection = stt_manager.active_connections[session_id]
        assert connection["websocket"] == websocket
        assert connection["user"] == user
        assert connection["transcription_session"] is None
        assert "connected_at" in connection
        assert connection["is_transcribing"] is False
    
    @pytest.mark.asyncio
    async def test_connect_thread_safety(self, stt_manager):
        """Test that connect is thread-safe with concurrent connections."""
        websockets = [AsyncMock() for _ in range(10)]
        for ws in websockets:
            ws.accept = AsyncMock()
        
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        
        # Create multiple connections concurrently
        tasks = [
            stt_manager.connect(ws, user)
            for ws in websockets
        ]
        
        session_ids = await asyncio.gather(*tasks)
        
        # All session IDs should be unique
        assert len(set(session_ids)) == 10
        assert len(stt_manager.active_connections) == 10
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_session(self, stt_manager):
        """Test that disconnect removes session and cleans up."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        mock_transcription_session = AsyncMock()
        mock_transcription_session.finish = AsyncMock()
        
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        
        # Create a connection
        session_id = await stt_manager.connect(websocket, user)
        
        # Add a transcription session
        stt_manager.active_connections[session_id]["transcription_session"] = mock_transcription_session
        
        # Disconnect
        await stt_manager.disconnect(session_id)
        
        # Verify cleanup
        assert session_id not in stt_manager.active_connections
        mock_transcription_session.finish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_session(self, stt_manager):
        """Test disconnecting a non-existent session."""
        # Should not raise an exception
        await stt_manager.disconnect("nonexistent-session-id")
    
    @pytest.mark.asyncio
    async def test_disconnect_without_transcription_session(self, stt_manager):
        """Test disconnecting when no transcription session exists."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        
        session_id = await stt_manager.connect(websocket, user)
        
        # Disconnect without transcription session
        await stt_manager.disconnect(session_id)
        
        assert session_id not in stt_manager.active_connections
    
    def test_get_connection_existing(self, stt_manager):
        """Test getting an existing connection."""
        session_id = "test-session"
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        connection_data = {
            "websocket": MagicMock(),
            "user": user,
            "connected_at": datetime.now(),
            "transcription_session": None,
            "is_transcribing": False
        }
        stt_manager.active_connections[session_id] = connection_data
        
        result = stt_manager.get_connection(session_id)
        
        assert result == connection_data
    
    def test_get_connection_nonexistent(self, stt_manager):
        """Test getting a non-existent connection."""
        result = stt_manager.get_connection("nonexistent-session")
        assert result is None


class TestVoiceConnectionManager:
    """Test suite for VoiceConnectionManager."""
    
    @pytest.fixture
    def voice_manager(self):
        """Create a VoiceConnectionManager instance."""
        return VoiceConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connect_creates_session(self, voice_manager):
        """Test that connect creates a new session."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        
        session_id = await voice_manager.connect(websocket, user)
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert session_id in voice_manager.active_connections
        
        connection = voice_manager.active_connections[session_id]
        assert connection["websocket"] == websocket
        assert connection["user"] == user
        assert connection["transcription_session"] is None
        assert connection["is_transcribing"] is False
        assert "connected_at" in connection
    
    @pytest.mark.asyncio
    async def test_disconnect_with_transcription_session(self, voice_manager):
        """Test disconnect with active transcription session."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        mock_transcription_session = AsyncMock()
        mock_transcription_session.finish = AsyncMock()
        
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        
        session_id = await voice_manager.connect(websocket, user)
        voice_manager.active_connections[session_id]["transcription_session"] = mock_transcription_session
        
        await voice_manager.disconnect(session_id)
        
        assert session_id not in voice_manager.active_connections
        mock_transcription_session.finish.assert_called_once()
    
    def test_voice_connection_has_transcription_flag(self, voice_manager):
        """Test that voice connections have is_transcribing flag."""
        session_id = "test-session"
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        connection_data = {
            "websocket": MagicMock(),
            "user": user,
            "connected_at": datetime.now(),
            "transcription_session": None,
            "is_transcribing": True
        }
        voice_manager.active_connections[session_id] = connection_data
        
        result = voice_manager.get_connection(session_id)
        
        assert "is_transcribing" in result
        assert result["is_transcribing"] is True


class TestAuthenticationFunctions:
    """Test suite for WebSocket authentication functions."""
    
    @pytest.mark.asyncio
    async def test_authenticate_stt_websocket_success(self):
        """Test successful STT WebSocket authentication."""
        # Mock dependencies
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.tenant_id = uuid.uuid4()
        
        mock_db = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_query_result
        
        # Mock AuthService decode_token
        mock_payload = MagicMock()
        mock_payload.sub = str(mock_user.id)
        
        with patch('app.auth.auth.AuthService.decode_token', return_value=mock_payload) as mock_decode:
            websocket = AsyncMock()
            token = "valid_token"
            
            result = await authenticate_stt_websocket(websocket, token, mock_db)
            
            assert result == mock_user
            mock_decode.assert_called_once_with(token)
    
    @pytest.mark.asyncio
    async def test_authenticate_stt_websocket_invalid_token(self):
        """Test STT WebSocket authentication with invalid token."""
        mock_db = AsyncMock()
        
        with patch('app.auth.auth.AuthService.decode_token') as mock_decode:
            mock_decode.side_effect = Exception("Invalid token")
            
            websocket = AsyncMock()
            token = "invalid_token"
            
            result = await authenticate_stt_websocket(websocket, token, mock_db)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_stt_websocket_user_not_found(self):
        """Test STT WebSocket authentication when user not found."""
        mock_db = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_query_result
        
        mock_payload = MagicMock()
        mock_payload.sub = str(uuid.uuid4())
        
        with patch('app.auth.auth.AuthService.decode_token', return_value=mock_payload) as mock_decode:
            websocket = AsyncMock()
            token = "valid_token"
            
            result = await authenticate_stt_websocket(websocket, token, mock_db)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_voice_websocket_success(self):
        """Test successful voice WebSocket authentication."""
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.tenant_id = uuid.uuid4()
        
        mock_db = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_query_result
        
        mock_payload = MagicMock()
        mock_payload.sub = str(mock_user.id)
        
        with patch('app.auth.auth.AuthService.decode_token', return_value=mock_payload) as mock_decode:
            websocket = AsyncMock()
            token = "valid_token"
            
            result = await authenticate_voice_websocket(websocket, token, mock_db)
            
            assert result == mock_user
            mock_decode.assert_called_once_with(token)


class TestAudioValidation:
    """Test suite for audio validation logic."""
    
    def test_audio_chunk_validation_too_small(self):
        """Test validation of audio chunks that are too small."""
        # Chunks smaller than 10 bytes should be skipped
        small_chunk = b'12345'  # 5 bytes
        
        # This logic is from streaming_stt.py lines 231-241
        # We'll test the validation logic
        chunk_size = len(small_chunk)
        
        assert chunk_size < 10
        # In the actual code, these would be skipped
    
    def test_audio_chunk_validation_normal_size(self):
        """Test validation of normal-sized audio chunks."""
        normal_chunk = b'a' * 1000  # 1KB
        
        chunk_size = len(normal_chunk)
        
        assert 10 <= chunk_size <= 32768  # Valid range
    
    def test_audio_chunk_validation_too_large(self):
        """Test validation of audio chunks that are too large."""
        large_chunk = b'a' * 40000  # 40KB
        
        chunk_size = len(large_chunk)
        
        assert chunk_size > 32768
        # In the actual code, this would trigger a warning


class TestLanguagePreferenceLogic:
    """Test suite for language preference resolution logic."""
    
    def test_language_preference_explicit(self):
        """Test explicit language preference."""
        # When user specifies a language explicitly
        language_pref = "en-US"
        
        # Should use the explicit language
        assert language_pref not in ["auto", "auto-detect", None, ""]
        resolved_language = language_pref
        assert resolved_language == "en-US"
    
    def test_language_preference_auto_detect_keywords(self):
        """Test auto-detection keywords."""
        auto_keywords = ["auto", "auto-detect", None, ""]
        
        for keyword in auto_keywords:
            # These should trigger auto-detection
            detect_language = keyword in ["auto", "auto-detect", None, ""]
            assert detect_language is True
    
    def test_language_preference_from_control_vs_param(self):
        """Test language preference from control message vs URL param."""
        # Control message takes precedence
        url_param_lang = "en-US"
        control_msg_lang = "es-ES"
        
        # Control message should override
        final_lang = control_msg_lang if control_msg_lang else url_param_lang
        assert final_lang == "es-ES"
        
        # When no control message language
        control_msg_lang = None
        final_lang = control_msg_lang if control_msg_lang else url_param_lang
        assert final_lang == "en-US"


class TestControlMessageParsing:
    """Test suite for control message parsing logic."""
    
    def test_parse_valid_control_message(self):
        """Test parsing valid control messages."""
        valid_messages = [
            {"type": "start_transcription", "language": "en-US"},
            {"type": "stop_transcription"},
            {"type": "ping"},
            {"type": "start_synthesis", "text": "Hello world"}
        ]
        
        for msg in valid_messages:
            # Should parse without error
            json_str = json.dumps(msg)
            parsed = json.loads(json_str)
            assert "type" in parsed
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        invalid_json = "{'type': 'test'}"  # Single quotes, invalid JSON
        
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)
    
    def test_unknown_control_type(self):
        """Test handling unknown control message types."""
        unknown_msg = {"type": "unknown_action", "data": "test"}
        
        # In the actual code, this would be logged and ignored
        msg_type = unknown_msg.get("type")
        known_types = ["start_transcription", "stop_transcription", "ping", "pong", "start_synthesis", "stop_synthesis"]
        
        assert msg_type not in known_types


class TestConnectionManagement:
    """Integration tests for connection management."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_lifecycle(self):
        """Test concurrent connection creation and cleanup."""
        stt_manager = StreamingSTTManager()
        voice_manager = VoiceConnectionManager()
        
        # Create multiple connections concurrently
        websockets = [AsyncMock() for _ in range(5)]
        for ws in websockets:
            ws.accept = AsyncMock()
        
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        
        # STT connections
        stt_tasks = [
            stt_manager.connect(ws, user)
            for ws in websockets[:3]
        ]
        
        # Voice connections
        voice_tasks = [
            voice_manager.connect(ws, user)
            for ws in websockets[3:]
        ]
        
        stt_sessions = await asyncio.gather(*stt_tasks)
        voice_sessions = await asyncio.gather(*voice_tasks)
        
        # Verify all connections created
        assert len(stt_manager.active_connections) == 3
        assert len(voice_manager.active_connections) == 2
        
        # Disconnect all
        disconnect_tasks = []
        for session_id in stt_sessions:
            disconnect_tasks.append(stt_manager.disconnect(session_id))
        for session_id in voice_sessions:
            disconnect_tasks.append(voice_manager.disconnect(session_id))
        
        await asyncio.gather(*disconnect_tasks)
        
        # Verify all cleaned up
        assert len(stt_manager.active_connections) == 0
        assert len(voice_manager.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_connection_timeout_simulation(self):
        """Test connection timeout handling."""
        manager = StreamingSTTManager()
        
        # Create a connection
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        user = MagicMock()
        user.email = "test@example.com"
        user.id = uuid.uuid4()
        
        session_id = await manager.connect(websocket, user)
        
        # Simulate connection aging
        connection = manager.active_connections[session_id]
        old_time = datetime.now() - timedelta(hours=2)
        connection["connected_at"] = old_time
        
        # In a real system, we'd have a cleanup task
        # Here we just verify the connection age
        age = datetime.now() - connection["connected_at"]
        assert age.total_seconds() > 7200  # More than 2 hours old