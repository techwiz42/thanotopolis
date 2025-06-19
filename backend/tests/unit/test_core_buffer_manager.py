import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
import json
from app.core.buffer_manager import ConversationBuffer, BufferManager, buffer_manager


class TestConversationBuffer:
    """Test suite for ConversationBuffer class."""
    
    @pytest.fixture
    def conversation_buffer(self):
        """Create a test conversation buffer."""
        return ConversationBuffer(uuid4(), max_tokens=1000)
    
    def test_conversation_buffer_initialization(self, conversation_buffer):
        """Test ConversationBuffer initialization."""
        assert conversation_buffer.conversation_id is not None
        assert conversation_buffer.max_tokens == 1000
        assert conversation_buffer.messages == []
        assert conversation_buffer.summary is None
        assert conversation_buffer.last_updated is not None
        assert conversation_buffer.encoding is not None
        assert conversation_buffer._lock is not None
    
    def test_count_tokens_normal_text(self, conversation_buffer):
        """Test token counting with normal text."""
        text = "Hello, this is a test message."
        token_count = conversation_buffer.count_tokens(text)
        
        assert isinstance(token_count, int)
        assert token_count > 0
    
    def test_count_tokens_empty_text(self, conversation_buffer):
        """Test token counting with empty text."""
        token_count = conversation_buffer.count_tokens("")
        assert token_count == 0
    
    def test_count_tokens_fallback_on_error(self, conversation_buffer):
        """Test token counting fallback when encoding fails."""
        with patch.object(conversation_buffer.encoding, 'encode', side_effect=Exception("Encoding error")):
            text = "Test message that causes encoding error"
            token_count = conversation_buffer.count_tokens(text)
            
            # Should fallback to length // 4
            expected_count = len(text) // 4
            assert token_count == expected_count
    
    def test_add_message_basic(self, conversation_buffer):
        """Test adding a basic message."""
        conversation_buffer.add_message(
            message="Hello world",
            sender_id="user123",
            sender_type="user"
        )
        
        assert len(conversation_buffer.messages) == 1
        msg = conversation_buffer.messages[0]
        assert msg["content"] == "Hello world"
        assert msg["sender_id"] == "user123"
        assert msg["sender_type"] == "user"
        assert "timestamp" in msg
        assert msg["metadata"] == {}
    
    def test_add_message_with_metadata(self, conversation_buffer):
        """Test adding a message with metadata."""
        metadata = {"type": "voice", "duration": 5.2}
        conversation_buffer.add_message(
            message="Voice message content",
            sender_id="agent1",
            sender_type="agent",
            metadata=metadata
        )
        
        assert len(conversation_buffer.messages) == 1
        msg = conversation_buffer.messages[0]
        assert msg["metadata"] == metadata
    
    def test_add_multiple_messages(self, conversation_buffer):
        """Test adding multiple messages updates last_updated."""
        initial_time = conversation_buffer.last_updated
        
        conversation_buffer.add_message("Message 1", "user1", "user")
        first_update = conversation_buffer.last_updated
        
        conversation_buffer.add_message("Message 2", "agent1", "agent")
        second_update = conversation_buffer.last_updated
        
        assert first_update > initial_time
        assert second_update > first_update
        assert len(conversation_buffer.messages) == 2
    
    def test_get_formatted_context_no_summary(self, conversation_buffer):
        """Test formatted context without summary."""
        conversation_buffer.add_message("Hello", "user1", "user")
        conversation_buffer.add_message("Hi there", "agent1", "agent")
        
        context = conversation_buffer.get_formatted_context()
        
        assert "CONVERSATION HISTORY:" in context
        assert "] [USER]: Hello" in context  # Updated to include timestamp format
        assert "] [agent1]: Hi there" in context  # Updated to include timestamp format
        assert "CONVERSATION SUMMARY:" not in context
    
    def test_get_formatted_context_with_summary(self, conversation_buffer):
        """Test formatted context with summary."""
        conversation_buffer.summary = "Previous conversation about weather"
        conversation_buffer.add_message("What's the temperature?", "user1", "user")
        
        context = conversation_buffer.get_formatted_context()
        
        assert "CONVERSATION SUMMARY:" in context
        assert "Previous conversation about weather" in context
        assert "RECENT CONVERSATION:" in context
        assert "] [USER]: What's the temperature?" in context  # Updated to include timestamp format
    
    def test_get_formatted_context_different_sender_types(self, conversation_buffer):
        """Test formatted context with different sender types."""
        conversation_buffer.add_message("User message", "user1", "user")
        conversation_buffer.add_message("Agent response", "agent1", "agent")
        conversation_buffer.add_message("System notification", "sys", "system")
        conversation_buffer.add_message("Participant input", "part1", "participant")
        
        context = conversation_buffer.get_formatted_context()
        
        assert "] [USER]: User message" in context  # Updated to include timestamp format
        assert "] [agent1]: Agent response" in context  # Updated to include timestamp format
        assert "] [SYSTEM]: System notification" in context  # Updated to include timestamp format
        assert "] [PARTICIPANT]: Participant input" in context  # Updated to include timestamp format
    
    @pytest.mark.asyncio
    async def test_check_and_summarize_under_limit(self, conversation_buffer):
        """Test that summarization doesn't occur when under token limit."""
        # Add a few short messages
        for i in range(5):
            conversation_buffer.add_message(f"Short message {i}", f"user{i}", "user")
        
        await conversation_buffer._check_and_summarize()
        
        # Should not have summary since we're under the token limit
        assert conversation_buffer.summary is None
        assert len(conversation_buffer.messages) == 5
    
    @pytest.mark.asyncio
    async def test_summarize_older_messages_few_messages(self, conversation_buffer):
        """Test that summarization doesn't occur with few messages."""
        # Add only 10 messages (less than 20 threshold)
        for i in range(10):
            conversation_buffer.add_message(f"Message {i}", f"user{i}", "user")
        
        await conversation_buffer._summarize_older_messages()
        
        # Should not summarize with few messages
        assert conversation_buffer.summary is None
        assert len(conversation_buffer.messages) == 10
    
    @pytest.mark.asyncio
    @patch('openai.AsyncOpenAI')
    async def test_create_summary_success(self, mock_openai, conversation_buffer):
        """Test successful summary creation."""
        # Mock OpenAI response
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "Summary of the conversation"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        messages = [
            {"sender_type": "user", "sender_id": "user1", "content": "Hello"},
            {"sender_type": "agent", "sender_id": "agent1", "content": "Hi there"},
        ]
        
        summary = await conversation_buffer._create_summary(messages)
        
        assert summary == "Summary of the conversation"
        mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('openai.AsyncOpenAI')
    async def test_create_summary_error(self, mock_openai, conversation_buffer):
        """Test summary creation with API error."""
        # Mock OpenAI to raise an exception
        mock_openai.side_effect = Exception("API Error")
        
        messages = [
            {"sender_type": "user", "sender_id": "user1", "content": "Hello"}
        ]
        
        summary = await conversation_buffer._create_summary(messages)
        
        # Should return error message
        assert "details unavailable due to error" in summary
        assert str(len(messages)) in summary
    
    @pytest.mark.asyncio
    async def test_load_from_database_success(self, conversation_buffer):
        """Test loading conversation from database."""
        # Mock database and models
        mock_db = AsyncMock()
        
        # Create mock messages
        mock_message1 = MagicMock()
        mock_message1.content = "Hello"
        mock_message1.agent_type = "agent1"
        mock_message1.user_id = None
        mock_message1.participant_id = None
        mock_message1.additional_data = '{"key": "value"}'
        mock_message1.created_at = datetime.utcnow()
        
        mock_message2 = MagicMock()
        mock_message2.content = "Hi there"
        mock_message2.agent_type = None
        mock_message2.user_id = uuid4()
        mock_message2.participant_id = None
        mock_message2.additional_data = None
        mock_message2.created_at = datetime.utcnow()
        mock_message2.user = MagicMock()
        mock_message2.user.first_name = "John"
        mock_message2.user.last_name = "Doe"
        mock_message2.user.username = "johndoe"
        
        # Create mock result properly - the scalars().all() should return the messages directly
        messages_list = [mock_message1, mock_message2]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = messages_list
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock the _check_and_summarize method to prevent hanging
        with patch.object(conversation_buffer, '_check_and_summarize', new_callable=AsyncMock):
            await conversation_buffer.load_from_database(mock_db)
        
        assert len(conversation_buffer.messages) == 2
        assert conversation_buffer.messages[0]["content"] == "Hello"
        assert conversation_buffer.messages[0]["sender_type"] == "agent"
        assert conversation_buffer.messages[0]["sender_id"] == "agent1"
        assert conversation_buffer.messages[1]["content"] == "Hi there"
        assert conversation_buffer.messages[1]["sender_type"] == "user"
        assert conversation_buffer.messages[1]["sender_id"] == "John Doe"


class TestBufferManager:
    """Test suite for BufferManager class."""
    
    @pytest.fixture
    def buffer_manager_instance(self):
        """Create a test buffer manager."""
        return BufferManager(max_tokens=2000, cleanup_interval=60)
    
    def test_buffer_manager_initialization(self, buffer_manager_instance):
        """Test BufferManager initialization."""
        assert buffer_manager_instance.buffers == {}
        assert buffer_manager_instance.max_tokens == 2000
        assert buffer_manager_instance.cleanup_interval == 60
        assert buffer_manager_instance._cleanup_task is None
        assert buffer_manager_instance._lock is not None
    
    @pytest.mark.asyncio
    async def test_get_or_create_buffer_new(self, buffer_manager_instance):
        """Test creating a new buffer."""
        conversation_id = uuid4()
        
        buffer = await buffer_manager_instance.get_or_create_buffer(conversation_id)
        
        assert buffer is not None
        assert buffer.conversation_id == conversation_id
        assert conversation_id in buffer_manager_instance.buffers
    
    @pytest.mark.asyncio
    async def test_get_or_create_buffer_existing(self, buffer_manager_instance):
        """Test getting an existing buffer."""
        conversation_id = uuid4()
        
        # Create buffer first time
        buffer1 = await buffer_manager_instance.get_or_create_buffer(conversation_id)
        # Get buffer second time
        buffer2 = await buffer_manager_instance.get_or_create_buffer(conversation_id)
        
        assert buffer1 is buffer2
        assert len(buffer_manager_instance.buffers) == 1
    
    @pytest.mark.asyncio
    async def test_add_message_creates_buffer(self, buffer_manager_instance):
        """Test that adding a message creates a buffer if needed."""
        conversation_id = uuid4()
        
        await buffer_manager_instance.add_message(
            conversation_id=conversation_id,
            message="Hello",
            sender_id="user1",
            sender_type="user"
        )
        
        assert conversation_id in buffer_manager_instance.buffers
        buffer = buffer_manager_instance.buffers[conversation_id]
        assert len(buffer.messages) == 1
        assert buffer.messages[0]["content"] == "Hello"
    
    @pytest.mark.asyncio
    async def test_add_message_with_metadata(self, buffer_manager_instance):
        """Test adding a message with metadata."""
        conversation_id = uuid4()
        metadata = {"type": "voice", "language": "en"}
        
        await buffer_manager_instance.add_message(
            conversation_id=conversation_id,
            message="Voice message",
            sender_id="agent1",
            sender_type="agent",
            metadata=metadata
        )
        
        buffer = buffer_manager_instance.buffers[conversation_id]
        assert buffer.messages[0]["metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_get_context_existing_buffer(self, buffer_manager_instance):
        """Test getting context from existing buffer."""
        conversation_id = uuid4()
        
        # Add some messages
        await buffer_manager_instance.add_message(conversation_id, "Hello", "user1", "user")
        await buffer_manager_instance.add_message(conversation_id, "Hi there", "agent1", "agent")
        
        context = await buffer_manager_instance.get_context(conversation_id)
        
        assert context is not None
        assert "Hello" in context
        assert "Hi there" in context
    
    @pytest.mark.asyncio
    async def test_get_context_nonexistent_buffer(self, buffer_manager_instance):
        """Test getting context from non-existent buffer creates new empty buffer."""
        conversation_id = uuid4()
        
        context = await buffer_manager_instance.get_context(conversation_id)
        
        assert context is not None
        assert "CONVERSATION HISTORY:" in context
        # Should create empty buffer
        assert conversation_id in buffer_manager_instance.buffers
    
    @pytest.mark.asyncio
    async def test_clear_conversation(self, buffer_manager_instance):
        """Test clearing a conversation buffer."""
        conversation_id = uuid4()
        
        # Create buffer with messages
        await buffer_manager_instance.add_message(conversation_id, "Test", "user1", "user")
        assert conversation_id in buffer_manager_instance.buffers
        
        # Clear conversation
        await buffer_manager_instance.clear_conversation(conversation_id)
        
        assert conversation_id not in buffer_manager_instance.buffers
    
    @pytest.mark.asyncio
    async def test_clear_nonexistent_conversation(self, buffer_manager_instance):
        """Test clearing a non-existent conversation doesn't error."""
        conversation_id = uuid4()
        
        # Should not raise an exception
        await buffer_manager_instance.clear_conversation(conversation_id)
    
    @pytest.mark.asyncio
    async def test_resume_conversation(self, buffer_manager_instance):
        """Test resuming a conversation."""
        conversation_id = uuid4()
        mock_db = AsyncMock()
        
        # Mock the buffer loading
        with patch.object(ConversationBuffer, 'load_from_database') as mock_load:
            context = await buffer_manager_instance.resume_conversation(conversation_id, mock_db)
            
            assert context is not None
            assert conversation_id in buffer_manager_instance.buffers
            mock_load.assert_called_once_with(mock_db)
    
    @pytest.mark.asyncio
    async def test_update_conversation_context_force_reload(self, buffer_manager_instance):
        """Test updating conversation context with force reload."""
        conversation_id = uuid4()
        mock_db = AsyncMock()
        
        with patch.object(buffer_manager_instance, 'resume_conversation') as mock_resume:
            mock_resume.return_value = "Updated context"
            
            context = await buffer_manager_instance.update_conversation_context(
                conversation_id, mock_db, force_reload=True
            )
            
            assert context == "Updated context"
            mock_resume.assert_called_once_with(conversation_id, mock_db)
    
    @pytest.mark.asyncio
    async def test_update_conversation_context_existing_buffer(self, buffer_manager_instance):
        """Test updating conversation context with existing buffer."""
        conversation_id = uuid4()
        mock_db = AsyncMock()
        
        # Create existing buffer
        await buffer_manager_instance.add_message(conversation_id, "Existing", "user1", "user")
        
        context = await buffer_manager_instance.update_conversation_context(
            conversation_id, mock_db, force_reload=False
        )
        
        assert context is not None
        assert "Existing" in context
    
    def test_get_buffer_info_existing(self, buffer_manager_instance):
        """Test getting buffer info for existing buffer."""
        conversation_id = uuid4()
        buffer = ConversationBuffer(conversation_id, max_tokens=1000)
        buffer.add_message("Test message", "user1", "user")
        buffer.summary = "Test summary"
        buffer_manager_instance.buffers[conversation_id] = buffer
        
        info = buffer_manager_instance.get_buffer_info(conversation_id)
        
        assert info is not None
        assert info["conversation_id"] == str(conversation_id)
        assert info["message_count"] == 1
        assert info["has_summary"] is True
        assert info["max_tokens"] == 1000
        assert "last_updated" in info
        assert "token_count" in info
    
    def test_get_buffer_info_nonexistent(self, buffer_manager_instance):
        """Test getting buffer info for non-existent buffer."""
        conversation_id = uuid4()
        
        info = buffer_manager_instance.get_buffer_info(conversation_id)
        
        assert info is None
    
    def test_get_stats_empty(self, buffer_manager_instance):
        """Test getting statistics with no buffers."""
        stats = buffer_manager_instance.get_stats()
        
        assert stats["active_buffers"] == 0
        assert stats["total_messages"] == 0
        assert stats["summarized_buffers"] == 0
        assert stats["max_tokens"] == 2000
        assert stats["cleanup_interval"] == 60
        assert stats["average_token_count"] == 0
    
    def test_get_stats_with_buffers(self, buffer_manager_instance):
        """Test getting statistics with buffers."""
        # Create buffers with different states
        conv_id1 = uuid4()
        buffer1 = ConversationBuffer(conv_id1, max_tokens=1000)
        buffer1.add_message("Message 1", "user1", "user")
        buffer1.summary = "Summary 1"
        
        conv_id2 = uuid4()
        buffer2 = ConversationBuffer(conv_id2, max_tokens=1000)
        buffer2.add_message("Message 2", "user2", "user")
        buffer2.add_message("Message 3", "agent1", "agent")
        
        buffer_manager_instance.buffers[conv_id1] = buffer1
        buffer_manager_instance.buffers[conv_id2] = buffer2
        
        stats = buffer_manager_instance.get_stats()
        
        assert stats["active_buffers"] == 2
        assert stats["total_messages"] == 3
        assert stats["summarized_buffers"] == 1
        assert stats["average_token_count"] > 0
    
    @pytest.mark.asyncio
    async def test_get_conversation_summary_exists(self, buffer_manager_instance):
        """Test getting conversation summary when it exists."""
        conversation_id = uuid4()
        buffer = ConversationBuffer(conversation_id)
        buffer.summary = "Existing summary"
        buffer_manager_instance.buffers[conversation_id] = buffer
        
        summary = await buffer_manager_instance.get_conversation_summary(conversation_id)
        
        assert summary == "Existing summary"
    
    @pytest.mark.asyncio
    async def test_get_conversation_summary_none(self, buffer_manager_instance):
        """Test getting conversation summary when none exists."""
        conversation_id = uuid4()
        
        summary = await buffer_manager_instance.get_conversation_summary(conversation_id)
        
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_force_summarize_conversation_sufficient_messages(self, buffer_manager_instance):
        """Test force summarizing with sufficient messages."""
        conversation_id = uuid4()
        
        # Add enough messages
        for i in range(10):
            await buffer_manager_instance.add_message(conversation_id, f"Message {i}", f"user{i}", "user")
        
        with patch.object(ConversationBuffer, '_summarize_older_messages') as mock_summarize:
            result = await buffer_manager_instance.force_summarize_conversation(conversation_id)
            
            assert result is True
            mock_summarize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_force_summarize_conversation_insufficient_messages(self, buffer_manager_instance):
        """Test force summarizing with insufficient messages."""
        conversation_id = uuid4()
        
        # Add only a few messages
        for i in range(3):
            await buffer_manager_instance.add_message(conversation_id, f"Message {i}", f"user{i}", "user")
        
        result = await buffer_manager_instance.force_summarize_conversation(conversation_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_export_conversation_context(self, buffer_manager_instance):
        """Test exporting conversation context."""
        conversation_id = uuid4()
        
        await buffer_manager_instance.add_message(conversation_id, "Test message", "user1", "user")
        
        export_data = await buffer_manager_instance.export_conversation_context(
            conversation_id, include_metadata=True
        )
        
        assert export_data is not None
        assert export_data["conversation_id"] == str(conversation_id)
        assert export_data["message_count"] == 1
        assert export_data["has_summary"] is False
        assert "formatted_context" in export_data
        assert "messages" in export_data
        assert "token_count" in export_data
    
    @pytest.mark.asyncio
    async def test_export_conversation_context_no_metadata(self, buffer_manager_instance):
        """Test exporting conversation context without metadata."""
        conversation_id = uuid4()
        
        await buffer_manager_instance.add_message(conversation_id, "Test", "user1", "user")
        
        export_data = await buffer_manager_instance.export_conversation_context(
            conversation_id, include_metadata=False
        )
        
        assert export_data is not None
        assert "messages" not in export_data
        assert "token_count" not in export_data
        assert "formatted_context" in export_data
    
    @pytest.mark.asyncio
    async def test_import_conversation_context(self, buffer_manager_instance):
        """Test importing conversation context."""
        conversation_id = uuid4()
        context_data = {
            "messages": [
                {"content": "Hello", "sender_id": "user1", "sender_type": "user", "timestamp": "2023-01-01T00:00:00", "metadata": {}}
            ],
            "summary": "Test summary",
            "last_updated": "2023-01-01T00:00:00"
        }
        
        result = await buffer_manager_instance.import_conversation_context(conversation_id, context_data)
        
        assert result is True
        assert conversation_id in buffer_manager_instance.buffers
        buffer = buffer_manager_instance.buffers[conversation_id]
        assert len(buffer.messages) == 1
        assert buffer.summary == "Test summary"
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, buffer_manager_instance):
        """Test health check when system is healthy."""
        health = await buffer_manager_instance.health_check()
        
        # The status can be 'healthy' or 'warning' depending on cleanup task state
        assert health["status"] in ["healthy", "warning"]
        assert isinstance(health["issues"], list)
        assert "stats" in health
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_health_check_high_buffer_count(self, buffer_manager_instance):
        """Test health check with high buffer count."""
        # Mock high buffer count
        with patch.object(buffer_manager_instance, 'get_stats') as mock_stats:
            mock_stats.return_value = {
                "active_buffers": 1500,
                "total_messages": 100,
                "summarized_buffers": 0,
                "max_tokens": 2000,
                "cleanup_interval": 60,
                "average_token_count": 500,
                "max_token_count": 1000,
                "min_token_count": 100
            }
            
            health = await buffer_manager_instance.health_check()
            
            assert health["status"] == "warning"
            assert "High number of active buffers" in health["issues"]
    
    @pytest.mark.asyncio
    async def test_shutdown(self, buffer_manager_instance):
        """Test graceful shutdown."""
        # First ensure cleanup task is started
        await buffer_manager_instance.get_or_create_buffer(uuid4())
        
        # Check that cleanup task exists
        assert buffer_manager_instance._cleanup_task is not None
        
        # Call shutdown
        await buffer_manager_instance.shutdown()
        
        # The task should be cancelled
        assert buffer_manager_instance._cleanup_task.cancelled() or buffer_manager_instance._cleanup_task.done()


class TestBufferManagerSingleton:
    """Test the singleton buffer manager instance."""
    
    def test_singleton_exists(self):
        """Test that buffer manager singleton exists."""
        assert buffer_manager is not None
        assert isinstance(buffer_manager, BufferManager)
    
    def test_singleton_default_values(self):
        """Test singleton has expected default values."""
        assert buffer_manager.max_tokens == 20000
        assert buffer_manager.cleanup_interval == 3600