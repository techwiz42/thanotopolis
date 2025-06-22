import pytest
from uuid import UUID, uuid4
from app.agents.common_context import CommonAgentContext


class TestCommonAgentContext:
    """Test cases for CommonAgentContext class."""

    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
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

    def test_initialization_with_values(self):
        """Test initialization with provided values."""
        thread_id = "test_thread_123"
        owner_id = uuid4()
        mock_db = object()
        
        context = CommonAgentContext(
            thread_id=thread_id,
            db=mock_db,
            owner_id=owner_id
        )
        
        assert context.thread_id == thread_id
        assert context.db == mock_db
        assert context.owner_id == owner_id

    def test_buffer_context_assignment(self):
        """Test assignment of buffer context."""
        context = CommonAgentContext()
        buffer_content = "Previous conversation history here"
        
        context.buffer_context = buffer_content
        assert context.buffer_context == buffer_content

    def test_rag_results_assignment(self):
        """Test assignment of RAG results."""
        context = CommonAgentContext()
        rag_data = {
            "documents": ["doc1", "doc2"],
            "scores": [0.9, 0.8],
            "metadata": {}
        }
        
        context.rag_results = rag_data
        assert context.rag_results == rag_data
        assert context.rag_results["documents"] == ["doc1", "doc2"]

    def test_message_history_manipulation(self):
        """Test manipulation of message history."""
        context = CommonAgentContext()
        
        # Add messages to history
        message1 = {"role": "user", "content": "Hello"}
        message2 = {"role": "agent", "content": "Hi there"}
        
        context.message_history.append(message1)
        context.message_history.append(message2)
        
        assert len(context.message_history) == 2
        assert context.message_history[0] == message1
        assert context.message_history[1] == message2

    def test_agent_selection_properties(self):
        """Test agent selection related properties."""
        context = CommonAgentContext()
        
        # Test selected agent
        context.selected_agent = "WEB_SEARCH"
        assert context.selected_agent == "WEB_SEARCH"
        
        # Test collaborators
        context.collaborators = ["DATA_ANALYST", "WRITER"]
        assert len(context.collaborators) == 2
        assert "DATA_ANALYST" in context.collaborators
        
        # Test agent selection flag
        context.is_agent_selection = True
        assert context.is_agent_selection is True

    def test_available_agents_assignment(self):
        """Test assignment of available agents."""
        context = CommonAgentContext()
        agents = {
            "WEB_SEARCH": "Searches the web for information",
            "DATA_ANALYST": "Analyzes data and provides insights",
            "WRITER": "Helps with writing tasks"
        }
        
        context.available_agents = agents
        assert context.available_agents == agents
        assert len(context.available_agents) == 3

    def test_sanitization_properties(self):
        """Test sanitization-related properties."""
        context = CommonAgentContext()
        
        # Test sanitization flag
        context.is_sanitized = True
        assert context.is_sanitized is True
        
        # Test original message
        original_msg = "ignore previous instructions"
        context.original_message = original_msg
        assert context.original_message == original_msg
        
        # Test detected patterns
        patterns = ["ignore previous instructions", "system prompt"]
        context.detected_patterns = patterns
        assert context.detected_patterns == patterns
        assert len(context.detected_patterns) == 2

    def test_uuid_owner_id(self):
        """Test with actual UUID for owner_id."""
        owner_id = UUID('12345678-1234-5678-1234-567812345678')
        context = CommonAgentContext(owner_id=owner_id)
        
        assert context.owner_id == owner_id
        assert isinstance(context.owner_id, UUID)

    def test_thread_id_string_conversion(self):
        """Test thread_id handling with different string formats."""
        # Test with regular string
        context1 = CommonAgentContext(thread_id="thread_123")
        assert context1.thread_id == "thread_123"
        
        # Test with UUID string
        uuid_str = str(uuid4())
        context2 = CommonAgentContext(thread_id=uuid_str)
        assert context2.thread_id == uuid_str

    def test_context_immutability_of_lists(self):
        """Test that list properties are properly mutable."""
        context = CommonAgentContext()
        
        # Test that we can modify the lists
        assert context.message_history == []
        context.message_history.append({"test": "message"})
        assert len(context.message_history) == 1
        
        assert context.collaborators == []
        context.collaborators.append("TEST_AGENT")
        assert len(context.collaborators) == 1

    def test_context_dict_mutability(self):
        """Test that dict properties are properly mutable."""
        context = CommonAgentContext()
        
        # Test available_agents dict
        assert context.available_agents == {}
        context.available_agents["TEST"] = "Test agent"
        assert len(context.available_agents) == 1
        assert context.available_agents["TEST"] == "Test agent"

    def test_full_context_setup(self):
        """Test setting up a complete context with all properties."""
        thread_id = "test_thread"
        owner_id = uuid4()
        
        context = CommonAgentContext(
            thread_id=thread_id,
            owner_id=owner_id
        )
        
        # Set up all context properties
        context.buffer_context = "Previous messages..."
        context.rag_results = {"documents": ["doc1"], "scores": [0.9]}
        context.message_history = [{"role": "user", "content": "test"}]
        context.selected_agent = "WEB_SEARCH"
        context.collaborators = ["DATA_ANALYST"]
        context.is_agent_selection = True
        context.available_agents = {"WEB_SEARCH": "Search agent"}
        context.is_sanitized = True
        context.original_message = "test message"
        context.detected_patterns = ["pattern1"]
        
        # Verify all properties are set correctly
        assert context.thread_id == thread_id
        assert context.owner_id == owner_id
        assert context.buffer_context == "Previous messages..."
        assert context.rag_results["documents"] == ["doc1"]
        assert len(context.message_history) == 1
        assert context.selected_agent == "WEB_SEARCH"
        assert "DATA_ANALYST" in context.collaborators
        assert context.is_agent_selection is True
        assert "WEB_SEARCH" in context.available_agents
        assert context.is_sanitized is True
        assert context.original_message == "test message"
        assert "pattern1" in context.detected_patterns

    def test_none_assignments(self):
        """Test explicit None assignments."""
        context = CommonAgentContext()
        
        # Test that None can be assigned to optional fields
        context.buffer_context = None
        context.rag_results = None
        context.selected_agent = None
        context.original_message = None
        context.detected_patterns = None
        
        assert context.buffer_context is None
        assert context.rag_results is None
        assert context.selected_agent is None
        assert context.original_message is None
        assert context.detected_patterns is None


if __name__ == "__main__":
    pytest.main([__file__])
