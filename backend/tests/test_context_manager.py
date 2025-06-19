import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.context_manager import ContextManager
from app.models.models import Message


class TestContextManager:
    """Test suite for ContextManager."""

    @pytest.fixture
    def context_manager(self):
        """Create a ContextManager instance."""
        return ContextManager(history_limit=5)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_thread_id(self):
        """Create a sample thread ID."""
        return uuid4()

    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        conversation_id = uuid4()
        user_id = uuid4()
        
        messages = []
        
        # User message
        user_msg = Message()
        user_msg.id = uuid4()
        user_msg.conversation_id = conversation_id
        user_msg.user_id = user_id
        user_msg.agent_type = None
        user_msg.content = "Hello, how can you help me?"
        user_msg.created_at = datetime(2024, 1, 1, 10, 0, 0)
        user_msg.message_metadata = {
            "participant_name": "John Doe"
        }
        messages.append(user_msg)
        
        # Agent message
        agent_msg = Message()
        agent_msg.id = uuid4()
        agent_msg.conversation_id = conversation_id
        agent_msg.user_id = None
        agent_msg.agent_type = "ASSISTANT"
        agent_msg.content = "I can help you with various tasks."
        agent_msg.created_at = datetime(2024, 1, 1, 10, 1, 0)
        agent_msg.message_metadata = {}
        messages.append(agent_msg)
        
        # Another user message
        user_msg2 = Message()
        user_msg2.id = uuid4()
        user_msg2.conversation_id = conversation_id
        user_msg2.user_id = user_id
        user_msg2.agent_type = None
        user_msg2.content = "What about specific assistance?"
        user_msg2.created_at = datetime(2024, 1, 1, 10, 2, 0)
        user_msg2.message_metadata = {
            "participant_name": "John Doe"
        }
        messages.append(user_msg2)
        
        return messages

    def test_initialization_default_limit(self):
        """Test ContextManager initialization with default limit."""
        manager = ContextManager()
        assert manager.history_limit == 20

    def test_initialization_custom_limit(self, context_manager):
        """Test ContextManager initialization with custom limit."""
        assert context_manager.history_limit == 5

    @pytest.mark.asyncio
    async def test_get_conversation_context_success(self, context_manager, mock_db, sample_thread_id, sample_messages):
        """Test successful context retrieval."""
        # Mock database query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_messages
        mock_db.execute.return_value = mock_result
        
        # Get context
        context = await context_manager.get_conversation_context(mock_db, sample_thread_id)
        
        # Verify database query was called
        mock_db.execute.assert_called_once()
        
        # Verify context formatting
        expected_lines = [
            "[John Doe] Hello, how can you help me?",
            "[ASSISTANT Agent] I can help you with various tasks.",
            "[John Doe] What about specific assistance?"
        ]
        
        for line in expected_lines:
            assert line in context

    @pytest.mark.asyncio
    async def test_get_conversation_context_with_exclude(self, context_manager, mock_db, sample_thread_id, sample_messages):
        """Test context retrieval with excluded message."""
        exclude_id = sample_messages[1].id  # Exclude the agent message
        
        # Mock database query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_messages[0], sample_messages[2]]
        mock_db.execute.return_value = mock_result
        
        # Get context
        context = await context_manager.get_conversation_context(
            mock_db, 
            sample_thread_id, 
            exclude_message_id=exclude_id
        )
        
        # Verify excluded message is not in context
        assert "I can help you with various tasks." not in context
        assert "Hello, how can you help me?" in context
        assert "What about specific assistance?" in context

    @pytest.mark.asyncio
    async def test_get_conversation_context_empty_result(self, context_manager, mock_db, sample_thread_id):
        """Test context retrieval with no messages."""
        # Mock empty database result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Get context
        context = await context_manager.get_conversation_context(mock_db, sample_thread_id)
        
        # Should return empty string
        assert context == ""

    @pytest.mark.asyncio
    async def test_get_conversation_context_database_error(self, context_manager, mock_db, sample_thread_id):
        """Test context retrieval with database error."""
        # Mock database error
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        # Get context
        context = await context_manager.get_conversation_context(mock_db, sample_thread_id)
        
        # Should return empty string on error
        assert context == ""

    @pytest.mark.asyncio
    async def test_get_conversation_context_message_formatting(self, context_manager, mock_db, sample_thread_id):
        """Test proper message formatting for different message types."""
        thread_id = sample_thread_id
        
        # Create messages with various metadata scenarios
        messages = []
        
        # User message with full name
        user_msg = Message()
        user_msg.id = uuid4()
        user_msg.conversation_id = thread_id
        user_msg.user_id = uuid4()
        user_msg.agent_type = None
        user_msg.content = "User message with name"
        user_msg.message_metadata = {"participant_name": "Jane Smith"}
        messages.append(user_msg)
        
        # User message without participant name
        user_msg_no_name = Message()
        user_msg_no_name.id = uuid4()
        user_msg_no_name.conversation_id = thread_id
        user_msg_no_name.user_id = uuid4()
        user_msg_no_name.agent_type = None
        user_msg_no_name.content = "User message without name"
        user_msg_no_name.message_metadata = {}
        messages.append(user_msg_no_name)
        
        # Agent message with agent type
        agent_msg = Message()
        agent_msg.id = uuid4()
        agent_msg.conversation_id = thread_id
        agent_msg.user_id = None
        agent_msg.agent_type = "MODERATOR"
        agent_msg.content = "Agent message with type"
        agent_msg.message_metadata = {}
        messages.append(agent_msg)
        
        # Agent message without agent type
        agent_msg_no_type = Message()
        agent_msg_no_type.id = uuid4()
        agent_msg_no_type.conversation_id = thread_id
        agent_msg_no_type.user_id = None
        agent_msg_no_type.agent_type = None
        agent_msg_no_type.content = "Agent message without type"
        agent_msg_no_type.message_metadata = {}
        messages.append(agent_msg_no_type)
        
        # Mock database result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = messages
        mock_db.execute.return_value = mock_result
        
        # Get context
        context = await context_manager.get_conversation_context(mock_db, sample_thread_id)
        
        # Verify formatting
        assert "[Jane Smith] User message with name" in context
        assert "[User] User message without name" in context
        assert "[MODERATOR Agent] Agent message with type" in context
        assert "[User] Agent message without type" in context  # No agent_type means treated as user

    @pytest.mark.asyncio
    async def test_get_conversation_context_respects_limit(self, context_manager, mock_db, sample_thread_id):
        """Test that context respects the history limit."""
        thread_id = sample_thread_id
        
        # Create more messages than the limit (limit is 5)
        messages = []
        for i in range(10):
            msg = Message()
            msg.id = uuid4()
            msg.conversation_id = thread_id
            msg.user_id = uuid4()
            msg.agent_type = None
            msg.content = f"Message {i}"
            msg.message_metadata = {"participant_name": f"User{i}"}
            messages.append(msg)
        
        # Mock database result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = messages
        mock_db.execute.return_value = mock_result
        
        # Get context
        context = await context_manager.get_conversation_context(mock_db, sample_thread_id)
        
        # Verify that database query used the limit
        call_args = mock_db.execute.call_args[0][0]
        # Check that the query has a limit clause
        assert hasattr(call_args, '_limit_clause')

    @pytest.mark.asyncio
    async def test_get_conversation_context_chronological_order(self, context_manager, mock_db, sample_thread_id):
        """Test that messages are returned in chronological order."""
        thread_id = sample_thread_id
        
        # Create messages with different timestamps
        messages = []
        
        # Message 3 (latest)
        msg3 = Message()
        msg3.id = uuid4()
        msg3.conversation_id = thread_id
        msg3.content = "Third message"
        msg3.created_at = datetime(2024, 1, 1, 10, 2, 0)
        msg3.message_metadata = {"participant_name": "User"}
        msg3.user_id = uuid4()
        msg3.agent_type = None
        
        # Message 1 (earliest)
        msg1 = Message()
        msg1.id = uuid4()
        msg1.conversation_id = thread_id
        msg1.content = "First message"
        msg1.created_at = datetime(2024, 1, 1, 10, 0, 0)
        msg1.message_metadata = {"participant_name": "User"}
        msg1.user_id = uuid4()
        msg1.agent_type = None
        
        # Message 2 (middle)
        msg2 = Message()
        msg2.id = uuid4()
        msg2.conversation_id = thread_id
        msg2.content = "Second message"
        msg2.created_at = datetime(2024, 1, 1, 10, 1, 0)
        msg2.message_metadata = {"participant_name": "User"}
        msg2.user_id = uuid4()
        msg2.agent_type = None
        
        # Return messages in reverse chronological order (as they would come from DB)
        messages = [msg3, msg2, msg1]
        
        # Mock database result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = messages
        mock_db.execute.return_value = mock_result
        
        # Get context
        context = await context_manager.get_conversation_context(mock_db, sample_thread_id)
        
        # Verify chronological order in output
        lines = context.split('\n')
        assert "First message" in lines[0]
        assert "Second message" in lines[1]
        assert "Third message" in lines[2]

    @pytest.mark.asyncio
    async def test_format_context_for_agent(self, context_manager, mock_db, sample_thread_id):
        """Test format_context_for_agent method."""
        current_msg_id = uuid4()
        
        # Mock the get_conversation_context method
        with patch.object(context_manager, 'get_conversation_context', return_value="test context") as mock_get_context:
            result = await context_manager.format_context_for_agent(
                mock_db, 
                sample_thread_id, 
                current_message_id=current_msg_id
            )
            
            # Verify it calls get_conversation_context with correct parameters
            mock_get_context.assert_called_once_with(
                mock_db,
                sample_thread_id,
                exclude_message_id=current_msg_id
            )
            
            # Verify result
            assert result == "test context"

    @pytest.mark.asyncio
    async def test_format_context_for_agent_no_current_message(self, context_manager, mock_db, sample_thread_id):
        """Test format_context_for_agent without current message ID."""
        # Mock the get_conversation_context method
        with patch.object(context_manager, 'get_conversation_context', return_value="test context") as mock_get_context:
            result = await context_manager.format_context_for_agent(mock_db, sample_thread_id)
            
            # Verify it calls get_conversation_context with None exclude_message_id
            mock_get_context.assert_called_once_with(
                mock_db,
                sample_thread_id,
                exclude_message_id=None
            )
            
            # Verify result
            assert result == "test context"

    @pytest.mark.asyncio
    async def test_message_metadata_edge_cases(self, context_manager, mock_db, sample_thread_id):
        """Test handling of edge cases in message metadata."""
        thread_id = sample_thread_id
        
        # Create messages with edge case metadata
        messages = []
        
        # Message with None metadata
        msg_none_metadata = Message()
        msg_none_metadata.id = uuid4()
        msg_none_metadata.conversation_id = thread_id
        msg_none_metadata.user_id = uuid4()
        msg_none_metadata.agent_type = None
        msg_none_metadata.content = "Message with None metadata"
        msg_none_metadata.message_metadata = None
        messages.append(msg_none_metadata)
        
        # Message with empty metadata
        msg_empty_metadata = Message()
        msg_empty_metadata.id = uuid4()
        msg_empty_metadata.conversation_id = thread_id
        msg_empty_metadata.user_id = None
        msg_empty_metadata.agent_type = "AGENT"
        msg_empty_metadata.content = "Message with empty metadata"
        msg_empty_metadata.message_metadata = {}
        messages.append(msg_empty_metadata)
        
        # Mock database result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = messages
        mock_db.execute.return_value = mock_result
        
        # Get context
        context = await context_manager.get_conversation_context(mock_db, sample_thread_id)
        
        # Verify graceful handling of metadata edge cases
        assert "[User] Message with None metadata" in context
        assert "[AGENT Agent] Message with empty metadata" in context

    def test_singleton_instance(self):
        """Test that the singleton instance is available."""
        from app.services.context_manager import context_manager
        
        assert isinstance(context_manager, ContextManager)
        assert context_manager.history_limit == 20  # Default value