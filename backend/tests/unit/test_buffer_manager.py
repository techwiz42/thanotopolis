"""Tests for buffer_manager.py"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import json

from app.core.buffer_manager import BufferManager, ConversationBuffer


class TestConversationBuffer:
    """Test ConversationBuffer class"""
    
    @pytest.fixture
    def buffer(self):
        """Create a test buffer"""
        return ConversationBuffer(uuid4(), max_tokens=1000)
    
    def test_initialization(self):
        """Test buffer initialization"""
        conv_id = uuid4()
        max_tokens = 2000
        buffer = ConversationBuffer(conv_id, max_tokens)
        
        assert buffer.conversation_id == conv_id
        assert buffer.max_tokens == max_tokens
        assert buffer.messages == []
        assert buffer.summary is None
        assert isinstance(buffer.last_updated, datetime)
        assert buffer.encoding is not None
        assert buffer._lock is not None
    
    def test_count_tokens(self, buffer):
        """Test token counting"""
        # Test normal token counting
        text = "Hello, this is a test message"
        token_count = buffer.count_tokens(text)
        assert isinstance(token_count, int)
        assert token_count > 0
        
        # Test fallback on error
        with patch.object(buffer.encoding, 'encode', side_effect=Exception("Test error")):
            token_count = buffer.count_tokens("Test text")
            assert token_count == len("Test text") // 4  # Fallback calculation
    
    def test_add_message(self, buffer):
        """Test adding messages to buffer"""
        message = "Test message"
        sender_id = "test_user"
        sender_type = "user"
        metadata = {"key": "value"}
        
        buffer.add_message(message, sender_id, sender_type, metadata)
        
        assert len(buffer.messages) == 1
        msg = buffer.messages[0]
        assert msg["content"] == message
        assert msg["sender_id"] == sender_id
        assert msg["sender_type"] == sender_type
        assert msg["metadata"] == metadata
        assert "timestamp" in msg
    
    def test_get_formatted_context_no_messages(self, buffer):
        """Test formatted context with no messages"""
        context = buffer.get_formatted_context()
        assert context == "CONVERSATION HISTORY:"
    
    def test_get_formatted_context_with_messages(self, buffer):
        """Test formatted context with messages"""
        buffer.add_message("Hello", "user1", "user")
        buffer.add_message("Hi there", "agent1", "agent")
        
        context = buffer.get_formatted_context()
        assert "CONVERSATION HISTORY:" in context
        assert "[USER]: Hello" in context
        assert "[agent1]: Hi there" in context
    
    def test_get_formatted_context_with_summary(self, buffer):
        """Test formatted context with summary"""
        buffer.summary = "Previous conversation summary"
        buffer.add_message("Recent message", "user1", "user")
        
        context = buffer.get_formatted_context()
        assert "CONVERSATION SUMMARY:" in context
        assert "Previous conversation summary" in context
        assert "RECENT CONVERSATION:" in context
        assert "[USER]: Recent message" in context
    
    @pytest.mark.asyncio
    async def test_check_and_summarize_under_limit(self, buffer):
        """Test summarization check when under token limit"""
        # Add a few messages
        for i in range(5):
            buffer.add_message(f"Message {i}", "user", "user")
        
        # Mock token count to be under limit
        with patch.object(buffer, 'count_tokens', return_value=500):
            await buffer._check_and_summarize()
        
        # Should not trigger summarization
        assert buffer.summary is None
        assert len(buffer.messages) == 5
    
    @pytest.mark.asyncio
    async def test_check_and_summarize_over_limit(self, buffer):
        """Test summarization when over token limit"""
        # Add many messages
        for i in range(25):
            buffer.add_message(f"Message {i}", "user", "user")
        
        # Mock token count to be over limit and mock summarization
        with patch.object(buffer, 'count_tokens', return_value=1500):
            with patch.object(buffer, '_summarize_older_messages', new_callable=AsyncMock) as mock_summarize:
                await buffer._check_and_summarize()
                mock_summarize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarize_older_messages_few_messages(self, buffer):
        """Test summarization with few messages (should not summarize)"""
        # Add less than 20 messages
        for i in range(10):
            buffer.add_message(f"Message {i}", "user", "user")
        
        await buffer._summarize_older_messages()
        
        assert buffer.summary is None
        assert len(buffer.messages) == 10
    
    @pytest.mark.asyncio
    async def test_create_summary_with_openai(self, buffer):
        """Test summary creation with OpenAI"""
        messages = [
            {"content": "Hello", "sender_id": "user1", "sender_type": "user"},
            {"content": "Hi there", "sender_id": "agent1", "sender_type": "agent"},
            {"content": "How are you?", "sender_id": "user1", "sender_type": "user"}
        ]
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Summary of conversation"))]
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            summary = await buffer._create_summary(messages)
            
            assert summary == "Summary of conversation"
            mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_summary_error_handling(self, buffer):
        """Test summary creation error handling"""
        messages = [{"content": "Test", "sender_id": "user", "sender_type": "user"}]
        
        with patch('openai.AsyncOpenAI', side_effect=Exception("API Error")):
            summary = await buffer._create_summary(messages)
            
            assert "[Summary of 1 messages - details unavailable due to error]" in summary
    
    @pytest.mark.asyncio
    async def test_load_from_database_mocked(self, buffer):
        """Test loading conversation from database with mocked data"""
        # Mock database models
        mock_messages = []
        for i in range(3):
            msg = MagicMock()
            msg.conversation_id = buffer.conversation_id
            msg.content = f"Message {i}"
            msg.agent_type = "test_agent" if i == 1 else None
            msg.user_id = uuid4() if i != 1 else None
            msg.participant_id = None
            msg.created_at = datetime.utcnow()
            msg.additional_data = json.dumps({"key": f"value{i}"})
            
            if i != 1:
                msg.user = MagicMock(first_name="Test", last_name="User", username="testuser")
            else:
                msg.user = None
            
            msg.participant = None
            mock_messages.append(msg)
        
        # Mock database query
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_db.execute.return_value = mock_result
        
        with patch.object(buffer, '_check_and_summarize', new_callable=AsyncMock):
            await buffer.load_from_database(mock_db)
        
        assert len(buffer.messages) == 3
        assert buffer.messages[0]["sender_type"] == "user"
        assert buffer.messages[1]["sender_type"] == "agent"
        assert buffer.messages[1]["sender_id"] == "test_agent"


class TestBufferManager:
    """Test BufferManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create a test buffer manager"""
        return BufferManager(max_tokens=1000, cleanup_interval=60)
    
    def test_initialization(self):
        """Test buffer manager initialization"""
        manager = BufferManager(max_tokens=2000, cleanup_interval=120)
        
        assert manager.buffers == {}
        assert manager.max_tokens == 2000
        assert manager.cleanup_interval == 120
        assert manager._cleanup_task is None
        assert manager._lock is not None
    
    @pytest.mark.asyncio
    async def test_get_or_create_buffer_new(self, manager):
        """Test creating a new buffer"""
        conv_id = uuid4()
        
        buffer = await manager.get_or_create_buffer(conv_id)
        
        assert isinstance(buffer, ConversationBuffer)
        assert buffer.conversation_id == conv_id
        assert buffer.max_tokens == manager.max_tokens
        assert conv_id in manager.buffers
    
    @pytest.mark.asyncio
    async def test_get_or_create_buffer_existing(self, manager):
        """Test getting existing buffer"""
        conv_id = uuid4()
        
        # Create buffer first time
        buffer1 = await manager.get_or_create_buffer(conv_id)
        
        # Get same buffer second time
        buffer2 = await manager.get_or_create_buffer(conv_id)
        
        assert buffer1 is buffer2
        assert len(manager.buffers) == 1
    
    @pytest.mark.asyncio
    async def test_get_or_create_buffer_with_db(self, manager):
        """Test creating buffer with database loading"""
        conv_id = uuid4()
        mock_db = AsyncMock()
        
        with patch.object(ConversationBuffer, 'load_from_database', new_callable=AsyncMock) as mock_load:
            buffer = await manager.get_or_create_buffer(conv_id, mock_db)
            
            mock_load.assert_called_once_with(mock_db)
    
    @pytest.mark.asyncio
    async def test_add_message(self, manager):
        """Test adding message to buffer"""
        conv_id = uuid4()
        
        await manager.add_message(
            conv_id, 
            "Test message", 
            "user1", 
            "user",
            metadata={"key": "value"}
        )
        
        assert conv_id in manager.buffers
        buffer = manager.buffers[conv_id]
        assert len(buffer.messages) == 1
        assert buffer.messages[0]["content"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_get_context(self, manager):
        """Test getting conversation context"""
        conv_id = uuid4()
        
        # Add some messages
        await manager.add_message(conv_id, "Hello", "user1", "user")
        await manager.add_message(conv_id, "Hi there", "agent1", "agent")
        
        context = await manager.get_context(conv_id)
        
        assert context is not None
        assert "Hello" in context
        assert "Hi there" in context
    
    @pytest.mark.asyncio
    async def test_get_context_error_handling(self, manager):
        """Test context retrieval error handling"""
        conv_id = uuid4()
        
        with patch.object(manager, 'get_or_create_buffer', side_effect=Exception("Test error")):
            context = await manager.get_context(conv_id)
            
            assert context is None
    
    @pytest.mark.asyncio
    async def test_resume_conversation(self, manager):
        """Test resuming a conversation"""
        conv_id = uuid4()
        mock_db = AsyncMock()
        
        with patch.object(ConversationBuffer, 'load_from_database', new_callable=AsyncMock):
            context = await manager.resume_conversation(conv_id, mock_db)
            
            assert context is not None
            assert conv_id in manager.buffers
    
    @pytest.mark.asyncio
    async def test_clear_conversation(self, manager):
        """Test clearing a conversation"""
        conv_id = uuid4()
        
        # Create a buffer
        await manager.get_or_create_buffer(conv_id)
        assert conv_id in manager.buffers
        
        # Clear it
        await manager.clear_conversation(conv_id)
        assert conv_id not in manager.buffers
    
    @pytest.mark.asyncio
    async def test_update_conversation_context_force_reload(self, manager):
        """Test updating context with force reload"""
        conv_id = uuid4()
        mock_db = AsyncMock()
        
        with patch.object(manager, 'resume_conversation', new_callable=AsyncMock) as mock_resume:
            mock_resume.return_value = "Reloaded context"
            
            context = await manager.update_conversation_context(conv_id, mock_db, force_reload=True)
            
            mock_resume.assert_called_once_with(conv_id, mock_db)
            assert context == "Reloaded context"
    
    def test_get_buffer_info(self, manager):
        """Test getting buffer information"""
        conv_id = uuid4()
        buffer = ConversationBuffer(conv_id, max_tokens=1000)
        buffer.messages = [{"content": "Test", "sender_id": "user", "sender_type": "user", "timestamp": datetime.utcnow().isoformat()}]
        manager.buffers[conv_id] = buffer
        
        info = manager.get_buffer_info(conv_id)
        
        assert info is not None
        assert info["conversation_id"] == str(conv_id)
        assert info["message_count"] == 1
        assert info["has_summary"] is False
        assert "last_updated" in info
        assert "token_count" in info
        assert info["max_tokens"] == 1000
    
    def test_get_stats(self, manager):
        """Test getting manager statistics"""
        # Add some buffers
        for i in range(3):
            conv_id = uuid4()
            buffer = ConversationBuffer(conv_id)
            for j in range(i + 1):
                buffer.add_message(f"Message {j}", "user", "user")
            manager.buffers[conv_id] = buffer
        
        stats = manager.get_stats()
        
        assert stats["active_buffers"] == 3
        assert stats["total_messages"] == 6  # 1 + 2 + 3
        assert stats["summarized_buffers"] == 0
        assert stats["max_tokens"] == manager.max_tokens
        assert stats["cleanup_interval"] == manager.cleanup_interval
        assert "average_token_count" in stats
        assert "max_token_count" in stats
        assert "min_token_count" in stats
    
    @pytest.mark.asyncio
    async def test_get_conversation_summary(self, manager):
        """Test getting conversation summary"""
        conv_id = uuid4()
        buffer = ConversationBuffer(conv_id)
        buffer.summary = "Test summary"
        manager.buffers[conv_id] = buffer
        
        summary = await manager.get_conversation_summary(conv_id)
        
        assert summary == "Test summary"
    
    @pytest.mark.asyncio
    async def test_force_summarize_conversation(self, manager):
        """Test forcing conversation summarization"""
        conv_id = uuid4()
        
        # Add enough messages to trigger summarization
        for i in range(10):
            await manager.add_message(conv_id, f"Message {i}", "user", "user")
        
        with patch.object(manager.buffers[conv_id], '_summarize_older_messages', new_callable=AsyncMock):
            result = await manager.force_summarize_conversation(conv_id)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_export_conversation_context(self, manager):
        """Test exporting conversation context"""
        conv_id = uuid4()
        
        # Add some messages
        await manager.add_message(conv_id, "Test message", "user", "user")
        
        export_data = await manager.export_conversation_context(conv_id, include_metadata=True)
        
        assert export_data is not None
        assert export_data["conversation_id"] == str(conv_id)
        assert export_data["message_count"] == 1
        assert "formatted_context" in export_data
        assert "messages" in export_data
        assert "token_count" in export_data
    
    @pytest.mark.asyncio
    async def test_import_conversation_context(self, manager):
        """Test importing conversation context"""
        conv_id = uuid4()
        context_data = {
            "messages": [{"content": "Imported message", "sender_id": "user", "sender_type": "user"}],
            "summary": "Imported summary",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        result = await manager.import_conversation_context(conv_id, context_data)
        
        assert result is True
        assert conv_id in manager.buffers
        buffer = manager.buffers[conv_id]
        assert len(buffer.messages) == 1
        assert buffer.summary == "Imported summary"
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, manager):
        """Test health check when healthy"""
        # Mock cleanup task as running and healthy stats
        manager._cleanup_task = MagicMock()
        manager._cleanup_task.done.return_value = False
        
        # Mock stats to avoid buffer limits issues
        with patch.object(manager, 'get_stats') as mock_stats:
            mock_stats.return_value = {
                "active_buffers": 5,  # Low number
                "total_messages": 10,
                "summarized_buffers": 0,
                "max_tokens": manager.max_tokens,
                "cleanup_interval": manager.cleanup_interval,
                "average_token_count": 100,  # Well below limit
                "max_token_count": 200,
                "min_token_count": 50
            }
            
            health = await manager.health_check()
            
            assert health["status"] == "healthy"
            assert health["issues"] == []
            assert "stats" in health
            assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_health_check_with_issues(self, manager):
        """Test health check with issues"""
        # Create many buffers to trigger warning
        for i in range(1001):
            manager.buffers[uuid4()] = ConversationBuffer(uuid4())
        
        health = await manager.health_check()
        
        assert health["status"] == "warning"
        assert len(health["issues"]) > 0
        assert "High number of active buffers" in health["issues"]
    
    @pytest.mark.asyncio
    async def test_periodic_cleanup(self, manager):
        """Test periodic cleanup of old buffers"""
        # Create old and new buffers
        old_conv_id = uuid4()
        new_conv_id = uuid4()
        
        old_buffer = ConversationBuffer(old_conv_id)
        old_buffer.last_updated = datetime.utcnow() - timedelta(hours=7)
        
        new_buffer = ConversationBuffer(new_conv_id)
        new_buffer.last_updated = datetime.utcnow()
        
        manager.buffers[old_conv_id] = old_buffer
        manager.buffers[new_conv_id] = new_buffer
        
        await manager._cleanup_old_buffers()
        
        assert old_conv_id not in manager.buffers
        assert new_conv_id in manager.buffers
    
    def test_cleanup_on_deletion(self, manager):
        """Test cleanup when manager is deleted"""
        manager._cleanup_task = MagicMock()
        manager._cleanup_task.done.return_value = False
        manager._cleanup_task.cancel = MagicMock()
        
        # Call __del__ directly
        manager.__del__()
        
        manager._cleanup_task.cancel.assert_called_once()