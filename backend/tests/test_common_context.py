import pytest
from uuid import uuid4, UUID

from app.agents.common_context import CommonAgentContext


class TestCommonAgentContext:
    """Test suite for CommonAgentContext."""

    def test_initialization_default_values(self):
        """Test CommonAgentContext initialization with default values."""
        context = CommonAgentContext()
        
        assert context.thread_id is None
        assert context.db is None
        assert context.owner_id is None
        assert context.buffer_context is None
        assert context.rag_results is None
        assert context.message_history == []
        assert context.selected_agent is None
        assert context.collaborators == []
        assert context.is_agent_selection is False
        assert context.available_agents == {}
        assert context.is_sanitized is False
        assert context.original_message is None
        assert context.detected_patterns is None

    def test_initialization_with_parameters(self):
        """Test CommonAgentContext initialization with provided parameters."""
        thread_id = "test-thread-123"
        mock_db = object()  # Mock database object
        owner_id = uuid4()
        
        context = CommonAgentContext(
            thread_id=thread_id,
            db=mock_db,
            owner_id=owner_id
        )
        
        assert context.thread_id == thread_id
        assert context.db == mock_db
        assert context.owner_id == owner_id
        
        # Other fields should still have default values
        assert context.buffer_context is None
        assert context.rag_results is None
        assert context.message_history == []
        assert context.selected_agent is None
        assert context.collaborators == []
        assert context.is_agent_selection is False
        assert context.available_agents == {}
        assert context.is_sanitized is False
        assert context.original_message is None
        assert context.detected_patterns is None

    def test_initialization_partial_parameters(self):
        """Test CommonAgentContext initialization with partial parameters."""
        thread_id = "partial-thread"
        
        context = CommonAgentContext(thread_id=thread_id)
        
        assert context.thread_id == thread_id
        assert context.db is None
        assert context.owner_id is None

    def test_attributes_can_be_modified(self):
        """Test that context attributes can be modified after initialization."""
        context = CommonAgentContext()
        
        # Test modifying basic attributes
        context.thread_id = "new-thread"
        context.buffer_context = "some buffer content"
        context.selected_agent = "MODERATOR"
        context.is_agent_selection = True
        context.is_sanitized = True
        
        assert context.thread_id == "new-thread"
        assert context.buffer_context == "some buffer content"
        assert context.selected_agent == "MODERATOR"
        assert context.is_agent_selection is True
        assert context.is_sanitized is True

    def test_message_history_operations(self):
        """Test operations on message_history list."""
        context = CommonAgentContext()
        
        # Add messages
        message1 = {"role": "user", "content": "Hello"}
        message2 = {"role": "assistant", "content": "Hi there"}
        
        context.message_history.append(message1)
        context.message_history.append(message2)
        
        assert len(context.message_history) == 2
        assert context.message_history[0] == message1
        assert context.message_history[1] == message2
        
        # Clear history
        context.message_history.clear()
        assert len(context.message_history) == 0

    def test_collaborators_operations(self):
        """Test operations on collaborators list."""
        context = CommonAgentContext()
        
        # Add collaborators
        context.collaborators.append("AGENT_1")
        context.collaborators.append("AGENT_2")
        context.collaborators.extend(["AGENT_3", "AGENT_4"])
        
        assert len(context.collaborators) == 4
        assert "AGENT_1" in context.collaborators
        assert "AGENT_4" in context.collaborators
        
        # Remove collaborator
        context.collaborators.remove("AGENT_2")
        assert "AGENT_2" not in context.collaborators
        assert len(context.collaborators) == 3

    def test_available_agents_operations(self):
        """Test operations on available_agents dictionary."""
        context = CommonAgentContext()
        
        # Add agents
        context.available_agents["MODERATOR"] = "Moderates conversations"
        context.available_agents["ASSISTANT"] = "General assistance"
        
        assert len(context.available_agents) == 2
        assert context.available_agents["MODERATOR"] == "Moderates conversations"
        assert context.available_agents["ASSISTANT"] == "General assistance"
        
        # Update agent description
        context.available_agents["MODERATOR"] = "Updated description"
        assert context.available_agents["MODERATOR"] == "Updated description"
        
        # Remove agent
        del context.available_agents["ASSISTANT"]
        assert "ASSISTANT" not in context.available_agents
        assert len(context.available_agents) == 1

    def test_rag_results_operations(self):
        """Test operations on rag_results dictionary."""
        context = CommonAgentContext()
        
        # Set RAG results
        rag_data = {
            "documents": ["doc1", "doc2"],
            "scores": [0.9, 0.8],
            "metadata": {"source": "knowledge_base"}
        }
        context.rag_results = rag_data
        
        assert context.rag_results == rag_data
        assert context.rag_results["documents"] == ["doc1", "doc2"]
        assert context.rag_results["metadata"]["source"] == "knowledge_base"

    def test_prompt_injection_protection_fields(self):
        """Test prompt injection protection related fields."""
        context = CommonAgentContext()
        
        # Set protection fields
        context.is_sanitized = True
        context.original_message = "Original user message"
        context.detected_patterns = ["pattern1", "pattern2", "jailbreak_attempt"]
        
        assert context.is_sanitized is True
        assert context.original_message == "Original user message"
        assert len(context.detected_patterns) == 3
        assert "jailbreak_attempt" in context.detected_patterns

    def test_owner_id_uuid_handling(self):
        """Test handling of UUID owner_id."""
        owner_id = uuid4()
        context = CommonAgentContext(owner_id=owner_id)
        
        assert context.owner_id == owner_id
        assert isinstance(context.owner_id, UUID)
        
        # Change owner
        new_owner_id = uuid4()
        context.owner_id = new_owner_id
        assert context.owner_id == new_owner_id
        assert context.owner_id != owner_id

    def test_thread_id_string_handling(self):
        """Test handling of string thread_id."""
        thread_id = "conversation-thread-12345"
        context = CommonAgentContext(thread_id=thread_id)
        
        assert context.thread_id == thread_id
        assert isinstance(context.thread_id, str)
        
        # Change thread ID
        new_thread_id = "new-conversation-67890"
        context.thread_id = new_thread_id
        assert context.thread_id == new_thread_id

    def test_context_as_state_container(self):
        """Test using context as a complete state container."""
        context = CommonAgentContext()
        
        # Simulate building up context during conversation
        context.thread_id = "conv-001"
        context.owner_id = uuid4()
        context.selected_agent = "MODERATOR"
        context.is_agent_selection = False
        
        # Add conversation history
        context.message_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"}
        ]
        
        # Add available agents
        context.available_agents = {
            "MODERATOR": "Conversation moderator",
            "ASSISTANT": "General assistant"
        }
        
        # Add collaborators
        context.collaborators = ["ASSISTANT"]
        
        # Add buffer content
        context.buffer_context = "Previous conversation context..."
        
        # Add RAG results
        context.rag_results = {
            "relevant_docs": ["doc1", "doc2"],
            "confidence": 0.85
        }
        
        # Set security flags
        context.is_sanitized = True
        context.original_message = "What can you help me with?"
        
        # Verify all state is preserved
        assert context.thread_id == "conv-001"
        assert isinstance(context.owner_id, UUID)
        assert context.selected_agent == "MODERATOR"
        assert context.is_agent_selection is False
        assert len(context.message_history) == 2
        assert len(context.available_agents) == 2
        assert "ASSISTANT" in context.collaborators
        assert context.buffer_context == "Previous conversation context..."
        assert context.rag_results["confidence"] == 0.85
        assert context.is_sanitized is True
        assert context.original_message == "What can you help me with?"

    def test_none_values_handling(self):
        """Test handling when attributes are explicitly set to None."""
        context = CommonAgentContext(
            thread_id="test-thread",
            db=object(),
            owner_id=uuid4()
        )
        
        # Explicitly set to None
        context.thread_id = None
        context.db = None
        context.owner_id = None
        context.buffer_context = None
        context.rag_results = None
        context.selected_agent = None
        context.original_message = None
        context.detected_patterns = None
        
        # Verify all are None
        assert context.thread_id is None
        assert context.db is None
        assert context.owner_id is None
        assert context.buffer_context is None
        assert context.rag_results is None
        assert context.selected_agent is None
        assert context.original_message is None
        assert context.detected_patterns is None
        
        # Lists and dicts should still be empty, not None
        assert context.message_history == []
        assert context.collaborators == []
        assert context.available_agents == {}
        assert context.is_agent_selection is False
        assert context.is_sanitized is False

    def test_boolean_flags_behavior(self):
        """Test behavior of boolean flags."""
        context = CommonAgentContext()
        
        # Test default values
        assert context.is_agent_selection is False
        assert context.is_sanitized is False
        
        # Test setting to True
        context.is_agent_selection = True
        context.is_sanitized = True
        assert context.is_agent_selection is True
        assert context.is_sanitized is True
        
        # Test setting back to False
        context.is_agent_selection = False
        context.is_sanitized = False
        assert context.is_agent_selection is False
        assert context.is_sanitized is False