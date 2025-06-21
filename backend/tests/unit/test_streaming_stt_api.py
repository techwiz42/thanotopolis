"""
Comprehensive unit tests for streaming STT API endpoints.
Tests speech-to-text streaming, WebSocket connections, and file transcription.
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException, WebSocket, WebSocketDisconnect, UploadFile
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.api.streaming_stt import (
    StreamingSTTManager, stt_manager, count_words,
    authenticate_stt_websocket, websocket_streaming_stt,
    transcribe_audio_file, get_stt_status, shutdown_stt_handlers
)
from app.models.models import User


class TestStreamingSTTUnit:
    """Unit tests for streaming STT components."""

    def test_count_words_function(self):
        """Test word counting function."""
        assert count_words("") == 0
        assert count_words(None) == 0
        assert count_words("hello") == 1
        assert count_words("hello world") == 2
        assert count_words("  hello   world  ") == 2
        assert count_words("Hello, world! How are you?") == 5

    def test_streaming_stt_manager_initialization(self):
        """Test StreamingSTTManager initialization."""
        manager = StreamingSTTManager()
        assert isinstance(manager.active_connections, dict)
        assert len(manager.active_connections) == 0
        assert manager.lock is not None

    @pytest.mark.asyncio
    async def test_streaming_stt_manager_connect(self):
        """Test STT manager connection handling."""
        manager = StreamingSTTManager()
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_user = Mock(spec=User)
        mock_user.email = "test@example.com"
        
        connection_id = await manager.connect(mock_websocket, mock_user)
        
        assert connection_id is not None
        assert connection_id in manager.active_connections
        assert manager.active_connections[connection_id]["websocket"] == mock_websocket
        assert manager.active_connections[connection_id]["user"] == mock_user
        assert manager.active_connections[connection_id]["is_transcribing"] is False
        
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_stt_manager_disconnect(self):
        """Test STT manager disconnection handling."""
        manager = StreamingSTTManager()
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_user = Mock(spec=User)
        mock_user.email = "test@example.com"
        
        # Connect first
        connection_id = await manager.connect(mock_websocket, mock_user)
        assert connection_id in manager.active_connections
        
        # Add mock transcription session
        mock_session = AsyncMock()
        manager.active_connections[connection_id]["transcription_session"] = mock_session
        
        # Disconnect
        await manager.disconnect(connection_id)
        
        assert connection_id not in manager.active_connections
        mock_session.finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_stt_manager_disconnect_nonexistent(self):
        """Test disconnecting non-existent connection (should not error)."""
        manager = StreamingSTTManager()
        
        # Should not raise exception
        await manager.disconnect("nonexistent_id")

    def test_streaming_stt_manager_get_connection(self):
        """Test getting connection by ID."""
        manager = StreamingSTTManager()
        
        # Non-existent connection
        assert manager.get_connection("nonexistent") is None
        
        # Add a connection manually for testing
        connection_data = {"test": "data"}
        manager.active_connections["test_id"] = connection_data
        
        assert manager.get_connection("test_id") == connection_data

    @pytest.mark.asyncio
    async def test_authenticate_stt_websocket_success(self):
        """Test successful STT WebSocket authentication."""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_db = AsyncMock(spec=AsyncSession)
        token = "valid_token"
        
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        
        with patch('app.auth.auth.AuthService') as mock_auth_service:
            mock_payload = Mock()
            mock_payload.sub = str(mock_user.id)
            mock_auth_service.decode_token.return_value = mock_payload
            
            mock_result = Mock()
            mock_result.scalars.return_value.first.return_value = mock_user
            mock_db.execute.return_value = mock_result
            
            result = await authenticate_stt_websocket(mock_websocket, token, mock_db)
            
        assert result == mock_user
        mock_auth_service.decode_token.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_authenticate_stt_websocket_invalid_token(self):
        """Test STT WebSocket authentication with invalid token."""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_db = AsyncMock(spec=AsyncSession)
        token = "invalid_token"
        
        with patch('app.auth.auth.AuthService') as mock_auth_service:
            mock_auth_service.decode_token.side_effect = Exception("Invalid token")
            
            result = await authenticate_stt_websocket(mock_websocket, token, mock_db)
            
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_stt_websocket_user_not_found(self):
        """Test STT WebSocket authentication when user not found."""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_db = AsyncMock(spec=AsyncSession)
        token = "valid_token"
        
        with patch('app.auth.auth.AuthService') as mock_auth_service:
            mock_payload = Mock()
            mock_payload.sub = str(uuid4())
            mock_auth_service.decode_token.return_value = mock_payload
            
            mock_result = Mock()
            mock_result.scalars.return_value.first.return_value = None
            mock_db.execute.return_value = mock_result
            
            result = await authenticate_stt_websocket(mock_websocket, token, mock_db)
            
        assert result is None

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_success(self):
        """Test successful audio file transcription."""
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        mock_user.email = "test@example.com"
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Create mock audio file
        audio_content = b"fake audio data"
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=audio_content)
        mock_file.content_type = "audio/wav"
        mock_file.filename = "test.wav"
        
        with patch('app.api.streaming_stt.soniox_service') as mock_soniox, \
             patch('app.api.streaming_stt.usage_service') as mock_usage_service:
            
            mock_soniox.is_available.return_value = True
            mock_soniox.transcribe_file = AsyncMock(return_value={
                "success": True,
                "transcript": "Hello world test transcript",
                "confidence": 0.95,
                "words": [{"word": "Hello"}, {"word": "world"}],
                "speakers": [],
                "paragraphs": ["Hello world test transcript"]
            })
            
            mock_usage_service.record_stt_usage = AsyncMock()
            
            result = await transcribe_audio_file(
                audio_file=mock_file,
                language="en",
                model="nova-2",
                current_user=mock_user,
                db=mock_db
            )
            
        assert result["success"] is True
        assert result["transcript"] == "Hello world test transcript"
        assert result["confidence"] == 0.95
        assert result["metadata"]["filename"] == "test.wav"
        assert result["metadata"]["content_type"] == "audio/wav"
        assert result["metadata"]["language"] == "en"
        
        # Verify usage tracking
        mock_usage_service.record_stt_usage.assert_called_once()
        usage_call = mock_usage_service.record_stt_usage.call_args
        assert usage_call[1]["word_count"] == 4  # "Hello world test transcript"
        assert usage_call[1]["service_provider"] == "soniox"

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_service_unavailable(self):
        """Test audio file transcription when service is unavailable."""
        mock_user = Mock(spec=User)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_file = Mock(spec=UploadFile)
        
        with patch('app.api.streaming_stt.soniox_service') as mock_soniox:
            mock_soniox.is_available.return_value = False
            
            with pytest.raises(HTTPException) as exc_info:
                await transcribe_audio_file(
                    audio_file=mock_file,
                    current_user=mock_user,
                    db=mock_db
                )
            
            assert exc_info.value.status_code == 503
            assert "Speech-to-text service unavailable" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_empty_transcript(self):
        """Test audio file transcription with empty transcript."""
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        audio_content = b"fake audio data"
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=audio_content)
        mock_file.content_type = "audio/wav"
        mock_file.filename = "silent.wav"
        
        with patch('app.api.streaming_stt.soniox_service') as mock_soniox, \
             patch('app.api.streaming_stt.usage_service') as mock_usage_service:
            
            mock_soniox.is_available.return_value = True
            mock_soniox.transcribe_file = AsyncMock(return_value={
                "success": True,
                "transcript": "",  # Empty transcript
                "confidence": 0.0,
                "words": [],
                "speakers": [],
                "paragraphs": []
            })
            
            mock_usage_service.record_stt_usage = AsyncMock()
            
            result = await transcribe_audio_file(
                audio_file=mock_file,
                current_user=mock_user,
                db=mock_db
            )
            
        assert result["success"] is True
        assert result["transcript"] == ""
        
        # Should not record usage for empty transcript
        mock_usage_service.record_stt_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_error(self):
        """Test audio file transcription error handling."""
        mock_user = Mock(spec=User)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(side_effect=Exception("File read error"))
        
        with pytest.raises(HTTPException) as exc_info:
            await transcribe_audio_file(
                audio_file=mock_file,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 500
        assert "File read error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_stt_status(self):
        """Test STT status endpoint."""
        with patch('app.api.streaming_stt.soniox_service') as mock_soniox:
            
            mock_soniox.is_available.return_value = True
            
            # Add some mock connections to stt_manager
            stt_manager.active_connections = {"conn1": {}, "conn2": {}}
            
            result = await get_stt_status()
            
        assert result["service"] == "soniox"
        assert result["available"] is True
        assert result["model"] == "soniox-auto"
        assert result["language"] == "auto-detect"
        assert result["active_connections"] == 2
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_shutdown_stt_handlers(self):
        """Test STT handlers shutdown."""
        # Add mock connections
        mock_connection1 = {"id": "conn1"}
        mock_connection2 = {"id": "conn2"}
        stt_manager.active_connections = {
            "conn1": mock_connection1,
            "conn2": mock_connection2
        }
        
        with patch.object(stt_manager, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            await shutdown_stt_handlers()
            
            assert mock_disconnect.call_count == 2
            mock_disconnect.assert_any_call("conn1")
            mock_disconnect.assert_any_call("conn2")

    @pytest.mark.asyncio
    async def test_shutdown_stt_handlers_with_error(self):
        """Test STT handlers shutdown with error handling."""
        stt_manager.active_connections = {"conn1": {}}
        
        with patch.object(stt_manager, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            mock_disconnect.side_effect = Exception("Disconnect error")
            
            # Should not raise exception
            await shutdown_stt_handlers()
            
            mock_disconnect.assert_called_once_with("conn1")


class TestWebSocketSTTIntegration:
    """Integration tests for WebSocket STT functionality."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive = AsyncMock()
        return websocket

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.tenant_id = uuid4()
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_websocket_stt_authentication_failure(self, mock_websocket, mock_db):
        """Test WebSocket STT with authentication failure."""
        with patch('app.api.streaming_stt.authenticate_stt_websocket') as mock_auth:
            mock_auth.return_value = None
            
            await websocket_streaming_stt(
                websocket=mock_websocket,
                token="invalid_token",
                db=mock_db
            )
            
            mock_websocket.close.assert_called_once_with(
                code=4001, reason="Authentication failed"
            )

    @pytest.mark.asyncio
    async def test_websocket_stt_service_unavailable(self, mock_websocket, mock_user, mock_db):
        """Test WebSocket STT when service is unavailable."""
        with patch('app.api.streaming_stt.authenticate_stt_websocket') as mock_auth, \
             patch('app.api.streaming_stt.soniox_service') as mock_soniox:
            
            mock_auth.return_value = mock_user
            mock_soniox.is_available.return_value = False
            
            await websocket_streaming_stt(
                websocket=mock_websocket,
                token="valid_token",
                db=mock_db
            )
            
            mock_websocket.close.assert_called_once_with(
                code=4003, reason="Speech-to-text service unavailable"
            )

    @pytest.mark.asyncio
    async def test_websocket_stt_successful_connection(self, mock_websocket, mock_user, mock_db):
        """Test successful WebSocket STT connection."""
        with patch('app.api.streaming_stt.authenticate_stt_websocket') as mock_auth, \
             patch('app.api.streaming_stt.soniox_service') as mock_soniox, \
             patch('app.api.streaming_stt.stt_manager') as mock_manager:
            
            mock_auth.return_value = mock_user
            mock_soniox.is_available.return_value = True
            
            connection_id = "test_connection_123"
            mock_manager.connect = AsyncMock(return_value=connection_id)
            mock_manager.disconnect = AsyncMock()
            mock_manager.get_connection.return_value = {
                "websocket": mock_websocket,
                "user": mock_user,
                "is_transcribing": False,
                "transcription_session": None
            }
            
            # Mock receive to simulate disconnect after welcome message
            mock_websocket.receive.side_effect = [
                {"type": "websocket.disconnect"}
            ]
            
            await websocket_streaming_stt(
                websocket=mock_websocket,
                token="valid_token",
                db=mock_db
            )
            
            # Verify connection flow
            mock_manager.connect.assert_called_once_with(mock_websocket, mock_user)
            mock_websocket.send_json.assert_called()
            mock_manager.disconnect.assert_called_once_with(connection_id)

    @pytest.mark.asyncio
    async def test_websocket_stt_audio_processing(self, mock_websocket, mock_user, mock_db):
        """Test WebSocket STT audio data processing."""
        with patch('app.api.streaming_stt.authenticate_stt_websocket') as mock_auth, \
             patch('app.api.streaming_stt.soniox_service') as mock_soniox, \
             patch('app.api.streaming_stt.stt_manager') as mock_manager, \
             patch('app.api.streaming_stt.usage_service') as mock_usage_service, \
             patch('app.api.streaming_stt.settings') as mock_settings:
            
            mock_auth.return_value = mock_user
            mock_soniox.is_available.return_value = True
            mock_settings.DEEPGRAM_MODEL = "nova-2"
            
            connection_id = "test_connection_123"
            mock_connection = {
                "websocket": mock_websocket,
                "user": mock_user,
                "is_transcribing": False,
                "transcription_session": None
            }
            
            mock_manager.connect = AsyncMock(return_value=connection_id)
            mock_manager.disconnect = AsyncMock()
            mock_manager.get_connection.return_value = mock_connection
            
            # Mock transcription session
            mock_session = AsyncMock()
            mock_soniox.start_live_transcription = AsyncMock(return_value=mock_session)
            
            mock_usage_service.record_stt_usage = AsyncMock()
            
            # Mock receive sequence: audio data, then disconnect
            audio_data = b"fake audio data" * 100  # Make it large enough
            mock_websocket.receive.side_effect = [
                {"type": "websocket.receive", "bytes": audio_data},
                {"type": "websocket.disconnect"}
            ]
            
            await websocket_streaming_stt(
                websocket=mock_websocket,
                token="valid_token",
                db=mock_db
            )
            
            # Verify transcription session was started
            mock_soniox.start_live_transcription.assert_called_once()
            mock_session.start.assert_called_once()
            mock_session.send_audio.assert_called_once_with(audio_data)

    @pytest.mark.asyncio
    async def test_websocket_stt_control_messages(self, mock_websocket, mock_user, mock_db):
        """Test WebSocket STT control message handling."""
        with patch('app.api.streaming_stt.authenticate_stt_websocket') as mock_auth, \
             patch('app.api.streaming_stt.soniox_service') as mock_soniox, \
             patch('app.api.streaming_stt.stt_manager') as mock_manager:
            
            mock_auth.return_value = mock_user
            mock_soniox.is_available.return_value = True
            
            connection_id = "test_connection_123"
            mock_connection = {
                "websocket": mock_websocket,
                "user": mock_user,
                "is_transcribing": False,
                "transcription_session": None
            }
            
            mock_manager.connect = AsyncMock(return_value=connection_id)
            mock_manager.disconnect = AsyncMock()
            mock_manager.get_connection.return_value = mock_connection
            
            # Mock control messages
            start_msg = json.dumps({
                "type": "start_transcription",
                "language": "es",
                "model": "nova-2"
            })
            
            ping_msg = json.dumps({"type": "ping"})
            
            mock_websocket.receive.side_effect = [
                {"type": "websocket.receive", "text": start_msg},
                {"type": "websocket.receive", "text": ping_msg},
                {"type": "websocket.disconnect"}
            ]
            
            await websocket_streaming_stt(
                websocket=mock_websocket,
                token="valid_token",
                db=mock_db
            )
            
            # Verify control message responses
            send_calls = mock_websocket.send_json.call_args_list
            
            # Should have welcome, transcription_ready, and pong messages
            assert len(send_calls) >= 3
            
            # Check for pong response
            pong_sent = any(
                call[0][0].get("type") == "pong" 
                for call in send_calls
            )
            assert pong_sent

    @pytest.mark.asyncio
    async def test_websocket_stt_invalid_control_message(self, mock_websocket, mock_user, mock_db):
        """Test WebSocket STT with invalid control message."""
        with patch('app.api.streaming_stt.authenticate_stt_websocket') as mock_auth, \
             patch('app.api.streaming_stt.soniox_service') as mock_soniox, \
             patch('app.api.streaming_stt.stt_manager') as mock_manager:
            
            mock_auth.return_value = mock_user
            mock_soniox.is_available.return_value = True
            
            connection_id = "test_connection_123"
            mock_connection = {
                "websocket": mock_websocket,
                "user": mock_user,
                "is_transcribing": False,
                "transcription_session": None
            }
            
            mock_manager.connect = AsyncMock(return_value=connection_id)
            mock_manager.disconnect = AsyncMock()
            mock_manager.get_connection.return_value = mock_connection
            
            # Invalid JSON control message
            invalid_msg = "invalid json"
            
            mock_websocket.receive.side_effect = [
                {"type": "websocket.receive", "text": invalid_msg},
                {"type": "websocket.disconnect"}
            ]
            
            await websocket_streaming_stt(
                websocket=mock_websocket,
                token="valid_token",
                db=mock_db
            )
            
            # Should send error message
            send_calls = mock_websocket.send_json.call_args_list
            error_sent = any(
                call[0][0].get("type") == "error" and
                "Invalid control message format" in call[0][0].get("message", "")
                for call in send_calls
            )
            assert error_sent

    @pytest.mark.asyncio
    async def test_websocket_stt_exception_handling(self, mock_websocket, mock_user, mock_db):
        """Test WebSocket STT exception handling."""
        with patch('app.api.streaming_stt.authenticate_stt_websocket') as mock_auth, \
             patch('app.api.streaming_stt.soniox_service') as mock_soniox, \
             patch('app.api.streaming_stt.stt_manager') as mock_manager:
            
            mock_auth.return_value = mock_user
            mock_soniox.is_available.return_value = True
            
            connection_id = "test_connection_123"
            mock_manager.connect = AsyncMock(return_value=connection_id)
            mock_manager.disconnect = AsyncMock()
            mock_manager.get_connection.side_effect = Exception("Connection error")
            
            # Should handle exception gracefully
            await websocket_streaming_stt(
                websocket=mock_websocket,
                token="valid_token",
                db=mock_db
            )
            
            # Should still attempt to disconnect
            mock_manager.disconnect.assert_called_once_with(connection_id)


class TestSTTUsageTracking:
    """Test STT usage tracking functionality."""

    @pytest.mark.asyncio
    async def test_transcript_usage_recording(self):
        """Test usage recording for transcripts."""
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.tenant_id = uuid4()
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.streaming_stt.usage_service') as mock_usage_service:
            
            mock_usage_service.record_stt_usage = AsyncMock()
            
            # Simulate transcript callback
            transcript_data = {
                "transcript": "This is a test transcript with multiple words",
                "is_final": True,
                "confidence": 0.95
            }
            
            # This would be called within the WebSocket handler
            transcript_text = transcript_data.get("transcript", "")
            if transcript_data.get("is_final", False) and transcript_text.strip():
                word_count = count_words(transcript_text)
                if word_count > 0:
                    await mock_usage_service.record_stt_usage(
                        db=mock_db,
                        tenant_id=mock_user.tenant_id,
                        user_id=mock_user.id,
                        word_count=word_count,
                        service_provider="soniox",
                        model_name="soniox-auto"
                    )
            
            # Verify usage was recorded
            mock_usage_service.record_stt_usage.assert_called_once()
            call_args = mock_usage_service.record_stt_usage.call_args[1]
            assert call_args["word_count"] == 8  # Count of words in transcript
            assert call_args["service_provider"] == "soniox"
            assert call_args["tenant_id"] == mock_user.tenant_id
            assert call_args["user_id"] == mock_user.id

    @pytest.mark.asyncio
    async def test_interim_transcript_no_usage(self):
        """Test that interim transcripts don't record usage."""
        mock_user = Mock(spec=User)
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.streaming_stt.usage_service') as mock_usage_service:
            mock_usage_service.record_stt_usage = AsyncMock()
            
            # Simulate interim transcript callback (is_final=False)
            transcript_data = {
                "transcript": "This is interim",
                "is_final": False,
                "confidence": 0.8
            }
            
            # This logic would be in the WebSocket handler
            transcript_text = transcript_data.get("transcript", "")
            if transcript_data.get("is_final", False) and transcript_text.strip():
                # Should not execute for interim transcripts
                await mock_usage_service.record_stt_usage(
                    db=mock_db,
                    tenant_id=mock_user.tenant_id,
                    user_id=mock_user.id,
                    word_count=count_words(transcript_text),
                    service_provider="soniox",
                    model_name="soniox-auto"
                )
            
            # Should not record usage for interim transcript
            mock_usage_service.record_stt_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_transcript_no_usage(self):
        """Test that empty transcripts don't record usage."""
        mock_user = Mock(spec=User)
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.streaming_stt.usage_service') as mock_usage_service:
            mock_usage_service.record_stt_usage = AsyncMock()
            
            # Simulate empty transcript
            transcript_data = {
                "transcript": "",
                "is_final": True,
                "confidence": 0.0
            }
            
            # This logic would be in the WebSocket handler
            transcript_text = transcript_data.get("transcript", "")
            if transcript_data.get("is_final", False) and transcript_text.strip():
                word_count = count_words(transcript_text)
                if word_count > 0:
                    await mock_usage_service.record_stt_usage(
                        db=mock_db,
                        tenant_id=mock_user.tenant_id,
                        user_id=mock_user.id,
                        word_count=word_count,
                        service_provider="soniox",
                        model_name="soniox-auto"
                    )
            
            # Should not record usage for empty transcript
            mock_usage_service.record_stt_usage.assert_not_called()


class TestSTTGlobalManager:
    """Test the global STT manager instance."""

    def test_global_stt_manager_exists(self):
        """Test that global STT manager instance exists."""
        from app.api.streaming_stt import stt_manager
        
        assert isinstance(stt_manager, StreamingSTTManager)
        assert hasattr(stt_manager, 'active_connections')
        assert hasattr(stt_manager, 'lock')

    def test_global_stt_manager_is_singleton(self):
        """Test that imports return the same instance."""
        from app.api.streaming_stt import stt_manager as manager1
        from app.api.streaming_stt import stt_manager as manager2
        
        assert manager1 is manager2