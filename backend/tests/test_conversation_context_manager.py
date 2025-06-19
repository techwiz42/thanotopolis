import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.memory.conversation_context_manager import ConversationContextManager


class TestConversationContextManager:
    """Test suite for ConversationContextManager."""

    @pytest.fixture
    def context_manager(self):
        """Create a ConversationContextManager instance."""
        return ConversationContextManager(max_tokens=1000)

    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        return [
            {
                "id": "msg1",
                "content": "Hello, how can you help me?",
                "created_at": "2024-01-01T10:00:00",
                "user_id": "user1",
                "user": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "username": "johndoe"
                },
                "agent_type": None
            },
            {
                "id": "msg2",
                "content": "I can help you with various tasks.",
                "created_at": "2024-01-01T10:01:00",
                "user_id": None,
                "user": None,
                "agent_type": "ASSISTANT"
            },
            {
                "id": "msg3",
                "content": "What about funeral planning?",
                "created_at": "2024-01-01T10:02:00",
                "user_id": "user1",
                "user": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "username": "johndoe"
                },
                "agent_type": None
            }
        ]

    def test_initialization_default_tokens(self):
        """Test ConversationContextManager initialization with default tokens."""
        manager = ConversationContextManager()
        assert manager.max_tokens == 4000

    def test_initialization_custom_tokens(self, context_manager):
        """Test ConversationContextManager initialization with custom tokens."""
        assert context_manager.max_tokens == 1000

    def test_count_tokens(self, context_manager):
        """Test token counting approximation."""
        text = "Hello world! This is a test message with multiple words."
        
        tokens = context_manager.count_tokens(text)
        
        # Should be approximately 1 token per 4 characters
        expected_tokens = len(text) // 4
        assert tokens == expected_tokens

    def test_count_tokens_empty_string(self, context_manager):
        """Test token counting with empty string."""
        tokens = context_manager.count_tokens("")
        assert tokens == 0

    def test_count_tokens_short_string(self, context_manager):
        """Test token counting with short string."""
        tokens = context_manager.count_tokens("Hi")
        assert tokens == 0  # 2 characters // 4 = 0

    @pytest.mark.asyncio
    async def test_format_conversation_context_empty_messages(self, context_manager):
        """Test formatting with empty message list."""
        context = await context_manager.format_conversation_context([])
        
        assert context == "CONVERSATION HISTORY:\nNo previous messages."

    @pytest.mark.asyncio
    async def test_format_conversation_context_basic(self, context_manager, sample_messages):
        """Test basic context formatting."""
        context = await context_manager.format_conversation_context(sample_messages)
        
        # Verify header
        assert context.startswith("CONVERSATION HISTORY:")
        
        # Verify all messages are included
        assert "[John Doe] (2024-01-01 10:00:00): Hello, how can you help me?" in context
        assert "[ASSISTANT] (2024-01-01 10:01:00): I can help you with various tasks." in context
        assert "[John Doe] (2024-01-01 10:02:00): What about funeral planning?" in context

    @pytest.mark.asyncio
    async def test_format_conversation_context_user_variations(self, context_manager):
        """Test formatting with various user message formats."""
        messages = [
            # User with full name
            {
                "content": "Message 1",
                "created_at": "2024-01-01T10:00:00",
                "user_id": "user1",
                "user": {"first_name": "John", "last_name": "Doe", "username": "johndoe"},
                "agent_type": None
            },
            # User with only first name
            {
                "content": "Message 2",
                "created_at": "2024-01-01T10:01:00",
                "user_id": "user2",
                "user": {"first_name": "Jane", "last_name": "", "username": "jane"},
                "agent_type": None
            },
            # User with only username
            {
                "content": "Message 3",
                "created_at": "2024-01-01T10:02:00",
                "user_id": "user3",
                "user": {"first_name": "", "last_name": "", "username": "anonymous"},
                "agent_type": None
            },
            # User with no name information
            {
                "content": "Message 4",
                "created_at": "2024-01-01T10:03:00",
                "user_id": "user4",
                "user": {"username": "unknown"},
                "agent_type": None
            }
        ]
        
        context = await context_manager.format_conversation_context(messages)
        
        assert "[John Doe]" in context
        assert "[Jane]" in context
        assert "[USER: anonymous]" in context
        assert "[USER: unknown]" in context

    @pytest.mark.asyncio
    async def test_format_conversation_context_agent_messages(self, context_manager):
        """Test formatting with various agent message types."""
        messages = [
            {
                "content": "Agent message 1",
                "created_at": "2024-01-01T10:00:00",
                "user_id": None,
                "agent_type": "MODERATOR"
            },
            {
                "content": "Agent message 2",
                "created_at": "2024-01-01T10:01:00",
                "user_id": None,
                "agent_type": "ASSISTANT"
            },
            {
                "content": "Unknown agent message",
                "created_at": "2024-01-01T10:02:00",
                "user_id": None,
                "agent_type": None
            }
        ]
        
        context = await context_manager.format_conversation_context(messages)
        
        assert "[MODERATOR]" in context
        assert "[ASSISTANT]" in context
        assert "[USER]" in context  # Unknown agent type falls back to USER

    @pytest.mark.asyncio
    async def test_format_conversation_context_timestamp_formats(self, context_manager):
        """Test formatting with various timestamp formats."""
        messages = [
            # ISO format string
            {
                "content": "Message 1",
                "created_at": "2024-01-01T10:00:00",
                "user_id": "user1",
                "user": {"username": "user1"},
                "agent_type": None
            },
            # Datetime object
            {
                "content": "Message 2",
                "created_at": datetime(2024, 1, 1, 10, 1, 0),
                "user_id": "user1",
                "user": {"username": "user1"},
                "agent_type": None
            },
            # Invalid timestamp string
            {
                "content": "Message 3",
                "created_at": "invalid-timestamp",
                "user_id": "user1",
                "user": {"username": "user1"},
                "agent_type": None
            },
            # No timestamp
            {
                "content": "Message 4",
                "created_at": None,
                "user_id": "user1",
                "user": {"username": "user1"},
                "agent_type": None
            }
        ]
        
        context = await context_manager.format_conversation_context(messages)
        
        assert "(2024-01-01 10:00:00)" in context
        assert "(2024-01-01 10:01:00)" in context
        assert "(invalid-timestamp)" in context
        assert "(Unknown time)" in context

    @pytest.mark.asyncio
    async def test_format_conversation_context_under_token_limit(self, context_manager):
        """Test formatting when under token limit."""
        # Create short messages that won't exceed limit
        messages = [
            {
                "content": "Short message",
                "created_at": "2024-01-01T10:00:00",
                "user_id": "user1",
                "user": {"username": "user1"},
                "agent_type": None
            }
        ]
        
        context = await context_manager.format_conversation_context(messages, summarize_if_needed=True)
        
        # Should not trigger summarization
        assert "SUMMARY OF EARLIER CONVERSATION:" not in context
        assert "RECENT CONVERSATION HISTORY:" not in context
        assert context.startswith("CONVERSATION HISTORY:")

    @pytest.mark.asyncio
    async def test_format_conversation_context_over_token_limit(self, context_manager):
        """Test formatting when over token limit triggers summarization."""
        # Create many long messages to exceed the 1000 token limit
        messages = []
        long_content = "This is a very long message that contains many words and will contribute significantly to the token count. " * 20
        
        for i in range(15):  # 15 long messages
            messages.append({
                "content": f"Message {i}: {long_content}",
                "created_at": f"2024-01-01T10:{i:02d}:00",
                "user_id": "user1",
                "user": {"username": f"user{i}"},
                "agent_type": None
            })
        
        with patch.object(context_manager, '_summarize_messages', return_value="Summary of earlier messages"):
            context = await context_manager.format_conversation_context(messages, summarize_if_needed=True)
            
            # Should trigger summarization
            assert "SUMMARY OF EARLIER CONVERSATION:" in context
            assert "RECENT CONVERSATION HISTORY:" in context
            assert "Summary of earlier messages" in context

    @pytest.mark.asyncio
    async def test_format_conversation_context_summarization_disabled(self, context_manager):
        """Test formatting with summarization disabled."""
        # Create many long messages
        messages = []
        long_content = "Very long message content. " * 50
        
        for i in range(15):
            messages.append({
                "content": f"Message {i}: {long_content}",
                "created_at": f"2024-01-01T10:{i:02d}:00",
                "user_id": "user1",
                "user": {"username": f"user{i}"},
                "agent_type": None
            })
        
        context = await context_manager.format_conversation_context(messages, summarize_if_needed=False)
        
        # Should not trigger summarization even if over limit
        assert "SUMMARY OF EARLIER CONVERSATION:" not in context
        assert "RECENT CONVERSATION HISTORY:" not in context
        assert context.startswith("CONVERSATION HISTORY:")

    @pytest.mark.asyncio
    async def test_summarize_messages_empty(self, context_manager):
        """Test summarization with empty messages."""
        summary = await context_manager._summarize_messages([])
        
        assert summary == "No previous conversation."

    @pytest.mark.asyncio
    async def test_summarize_messages_basic(self, context_manager):
        """Test basic message summarization."""
        messages = [
            {
                "content": "I need help with funeral arrangements",
                "user": {"username": "john"},
                "agent_type": None
            },
            {
                "content": "I can help you with funeral planning",
                "agent_type": "FUNERAL_AGENT"
            },
            {
                "content": "What about burial costs?",
                "user": {"username": "john"},
                "agent_type": None
            }
        ]
        
        summary = await context_manager._summarize_messages(messages)
        
        assert "john" in summary
        assert "FUNERAL_AGENT" in summary
        assert "3 messages" in summary
        assert "funeral" in summary

    @pytest.mark.asyncio
    async def test_summarize_messages_multiple_participants(self, context_manager):
        """Test summarization with multiple participants."""
        messages = [
            {
                "content": "Hello",
                "user": {"username": "alice"},
                "agent_type": None
            },
            {
                "content": "Hi there",
                "agent_type": "ASSISTANT"
            },
            {
                "content": "How are you?",
                "user": {"username": "bob"},
                "agent_type": None
            },
            {
                "content": "I'm doing well",
                "agent_type": "MODERATOR"
            }
        ]
        
        summary = await context_manager._summarize_messages(messages)
        
        assert "alice, bob" in summary or "bob, alice" in summary
        assert "ASSISTANT, MODERATOR" in summary or "MODERATOR, ASSISTANT" in summary
        assert "4 messages" in summary

    @pytest.mark.asyncio
    async def test_summarize_messages_topic_detection(self, context_manager):
        """Test topic detection in summarization."""
        messages = [
            {
                "content": "I need help planning a funeral service for my grandmother",
                "user": {"username": "jane"},
                "agent_type": None
            },
            {
                "content": "I can assist with funeral arrangements and burial options",
                "agent_type": "FUNERAL_AGENT"
            },
            {
                "content": "What are the cremation costs in our area?",
                "user": {"username": "jane"},
                "agent_type": None
            },
            {
                "content": "Let me help you with memorial service planning",
                "agent_type": "FUNERAL_AGENT"
            }
        ]
        
        summary = await context_manager._summarize_messages(messages)
        
        # Should detect funeral-related topics
        funeral_keywords = ["funeral", "burial", "cremation", "memorial"]
        found_keywords = [keyword for keyword in funeral_keywords if keyword in summary.lower()]
        assert len(found_keywords) > 0

    @pytest.mark.asyncio
    async def test_summarize_messages_no_topics(self, context_manager):
        """Test summarization when no specific topics are detected."""
        messages = [
            {
                "content": "Hello there",
                "user": {"username": "user1"},
                "agent_type": None
            },
            {
                "content": "How can I help you today?",
                "agent_type": "ASSISTANT"
            }
        ]
        
        summary = await context_manager._summarize_messages(messages)
        
        assert "various topics" in summary

    @pytest.mark.asyncio
    async def test_format_conversation_context_missing_user_info(self, context_manager):
        """Test formatting with missing user information."""
        messages = [
            # Message with no user info at all
            {
                "content": "Message without user",
                "created_at": "2024-01-01T10:00:00",
                "user_id": "user1",
                "user": None,
                "agent_type": None
            },
            # Message with user but no username
            {
                "content": "Message with partial user",
                "created_at": "2024-01-01T10:01:00",
                "user_id": "user2",
                "user": {"first_name": "John"},
                "agent_type": None
            }
        ]
        
        context = await context_manager.format_conversation_context(messages)
        
        assert "[USER]" in context  # Fallback for missing user info

    def test_token_counting_edge_cases(self, context_manager):
        """Test token counting with various edge cases."""
        # Unicode characters
        unicode_text = "Hello 世界! 🌍"
        tokens = context_manager.count_tokens(unicode_text)
        assert tokens >= 0
        
        # Very long text
        long_text = "word " * 1000
        tokens = context_manager.count_tokens(long_text)
        expected = len(long_text) // 4
        assert tokens == expected
        
        # Text with special characters
        special_text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        tokens = context_manager.count_tokens(special_text)
        assert tokens >= 0

    @pytest.mark.asyncio
    async def test_summarization_preserves_recent_messages(self, context_manager):
        """Test that summarization preserves the last 10 messages."""
        # Create 20 messages
        messages = []
        for i in range(20):
            messages.append({
                "content": f"Message {i}",
                "created_at": f"2024-01-01T10:{i:02d}:00",
                "user_id": "user1",
                "user": {"username": "user1"},
                "agent_type": None
            })
        
        # Mock count_tokens to return high value for triggering summarization
        with patch.object(context_manager, 'count_tokens', return_value=5000):
            with patch.object(context_manager, '_summarize_messages', return_value="Summary"):
                context = await context_manager.format_conversation_context(messages, summarize_if_needed=True)
                
                # Should contain recent messages (last 10)
                for i in range(10, 20):
                    assert f"Message {i}" in context
                
                # Should not contain early messages directly (they're summarized)
                for i in range(0, 10):
                    # These messages should not appear in the recent section
                    # (they may appear in summary, but not as formatted messages)
                    recent_section = context.split("RECENT CONVERSATION HISTORY:")[1] if "RECENT CONVERSATION HISTORY:" in context else context
                    assert f"[user1] (2024-01-01 10:{i:02d}:00): Message {i}" not in recent_section