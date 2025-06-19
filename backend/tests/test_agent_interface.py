import pytest
from unittest.mock import Mock, patch
import logging

from app.agents.agent_interface import AgentInterface


class MockAgent:
    """Mock agent class for testing."""
    
    def __init__(self, agent_type: str, description: str = None):
        self.agent_type = agent_type
        self.description = description


class TestAgentInterface:
    """Test suite for AgentInterface."""

    @pytest.fixture
    def agent_interface(self):
        """Create a fresh AgentInterface instance for each test."""
        return AgentInterface()

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing."""
        return {
            "MODERATOR": MockAgent("MODERATOR", "Moderates conversations"),
            "ASSISTANT": MockAgent("ASSISTANT", "General assistance"),
            "CALCULATOR": MockAgent("CALCULATOR")  # No description
        }

    def test_initialization(self, agent_interface):
        """Test AgentInterface initialization."""
        assert agent_interface.base_agents == {}
        assert agent_interface.conversation_agents == {}
        assert agent_interface.agent_descriptions == {}

    def test_register_base_agent_with_description(self, agent_interface, mock_agents):
        """Test registering a base agent with description."""
        agent = mock_agents["MODERATOR"]
        
        agent_interface.register_base_agent("moderator", agent)  # lowercase input
        
        # Should normalize to uppercase
        assert "MODERATOR" in agent_interface.base_agents
        assert agent_interface.base_agents["MODERATOR"] == agent
        assert agent_interface.agent_descriptions["MODERATOR"] == "Moderates conversations"

    def test_register_base_agent_without_description(self, agent_interface, mock_agents):
        """Test registering a base agent without description."""
        agent = mock_agents["CALCULATOR"]
        
        agent_interface.register_base_agent("CALCULATOR", agent)
        
        assert "CALCULATOR" in agent_interface.base_agents
        assert agent_interface.base_agents["CALCULATOR"] == agent
        assert agent_interface.agent_descriptions["CALCULATOR"] == "CALCULATOR agent"

    def test_register_base_agent_case_normalization(self, agent_interface, mock_agents):
        """Test that agent types are normalized to uppercase."""
        agent = mock_agents["MODERATOR"]
        
        # Test various case combinations
        agent_interface.register_base_agent("moderator", agent)
        agent_interface.register_base_agent("Assistant", MockAgent("Assistant"))
        agent_interface.register_base_agent("CALCULATOR", MockAgent("CALCULATOR"))
        
        # All should be uppercase in storage
        assert "MODERATOR" in agent_interface.base_agents
        assert "ASSISTANT" in agent_interface.base_agents
        assert "CALCULATOR" in agent_interface.base_agents
        
        # Should not have lowercase versions
        assert "moderator" not in agent_interface.base_agents
        assert "Assistant" not in agent_interface.base_agents

    def test_setup_conversation_new_thread(self, agent_interface, mock_agents):
        """Test setting up agents for a new conversation thread."""
        # Register base agents first
        for agent_type, agent in mock_agents.items():
            agent_interface.register_base_agent(agent_type, agent)
        
        thread_id = "thread-123"
        agent_types = ["MODERATOR", "ASSISTANT"]
        
        agent_interface.setup_conversation(thread_id, agent_types)
        
        # Verify conversation agents were set up
        assert thread_id in agent_interface.conversation_agents
        assert "MODERATOR" in agent_interface.conversation_agents[thread_id]
        assert "ASSISTANT" in agent_interface.conversation_agents[thread_id]
        assert agent_interface.conversation_agents[thread_id]["MODERATOR"] == mock_agents["MODERATOR"]
        assert agent_interface.conversation_agents[thread_id]["ASSISTANT"] == mock_agents["ASSISTANT"]

    def test_setup_conversation_case_normalization(self, agent_interface, mock_agents):
        """Test that setup_conversation normalizes agent types to uppercase."""
        # Register base agents
        for agent_type, agent in mock_agents.items():
            agent_interface.register_base_agent(agent_type, agent)
        
        thread_id = "thread-456"
        agent_types = ["moderator", "Assistant"]  # Mixed case
        
        agent_interface.setup_conversation(thread_id, agent_types)
        
        # Should be normalized to uppercase
        assert "MODERATOR" in agent_interface.conversation_agents[thread_id]
        assert "ASSISTANT" in agent_interface.conversation_agents[thread_id]

    def test_setup_conversation_missing_base_agent(self, agent_interface, mock_agents, caplog):
        """Test setup_conversation with missing base agent."""
        # Register only one agent
        agent_interface.register_base_agent("MODERATOR", mock_agents["MODERATOR"])
        
        thread_id = "thread-789"
        agent_types = ["MODERATOR", "NONEXISTENT"]
        
        with caplog.at_level(logging.WARNING):
            agent_interface.setup_conversation(thread_id, agent_types)
        
        # Should set up the existing agent and warn about the missing one
        assert "MODERATOR" in agent_interface.conversation_agents[thread_id]
        assert "NONEXISTENT" not in agent_interface.conversation_agents[thread_id]
        assert "Base agent NONEXISTENT not found" in caplog.text

    def test_setup_conversation_already_exists(self, agent_interface, mock_agents):
        """Test that setup_conversation skips already set up agents."""
        # Register base agents
        agent_interface.register_base_agent("MODERATOR", mock_agents["MODERATOR"])
        
        thread_id = "thread-existing"
        
        # First setup
        agent_interface.setup_conversation(thread_id, ["MODERATOR"])
        original_agent = agent_interface.conversation_agents[thread_id]["MODERATOR"]
        
        # Second setup with same agent should skip
        agent_interface.setup_conversation(thread_id, ["MODERATOR"])
        
        # Should be the same instance (not recreated)
        assert agent_interface.conversation_agents[thread_id]["MODERATOR"] is original_agent

    def test_get_agent_from_conversation(self, agent_interface, mock_agents):
        """Test getting an agent from conversation-specific storage."""
        # Set up conversation
        agent_interface.register_base_agent("MODERATOR", mock_agents["MODERATOR"])
        thread_id = "thread-get"
        agent_interface.setup_conversation(thread_id, ["MODERATOR"])
        
        # Get agent
        agent = agent_interface.get_agent(thread_id, "moderator")  # lowercase input
        
        assert agent == mock_agents["MODERATOR"]

    def test_get_agent_auto_setup(self, agent_interface, mock_agents):
        """Test that get_agent automatically sets up agent if not in conversation."""
        # Register base agent but don't set up conversation
        agent_interface.register_base_agent("MODERATOR", mock_agents["MODERATOR"])
        
        thread_id = "thread-auto"
        
        # Get agent should auto-setup
        agent = agent_interface.get_agent(thread_id, "MODERATOR")
        
        assert agent == mock_agents["MODERATOR"]
        assert thread_id in agent_interface.conversation_agents
        assert "MODERATOR" in agent_interface.conversation_agents[thread_id]

    def test_get_agent_not_found(self, agent_interface, caplog):
        """Test getting a non-existent agent."""
        thread_id = "thread-notfound"
        
        with caplog.at_level(logging.WARNING):
            agent = agent_interface.get_agent(thread_id, "NONEXISTENT")
        
        assert agent is None
        assert "Agent NONEXISTENT not found" in caplog.text

    def test_get_agent_types_base_agents(self, agent_interface, mock_agents):
        """Test getting agent types from base agents."""
        # Register agents
        for agent_type, agent in mock_agents.items():
            agent_interface.register_base_agent(agent_type, agent)
        
        agent_types = agent_interface.get_agent_types()
        
        assert set(agent_types) == {"MODERATOR", "ASSISTANT", "CALCULATOR"}

    def test_get_agent_types_conversation_specific(self, agent_interface, mock_agents):
        """Test getting agent types for a specific conversation."""
        # Register all agents
        for agent_type, agent in mock_agents.items():
            agent_interface.register_base_agent(agent_type, agent)
        
        # Set up conversation with subset
        thread_id = "thread-subset"
        agent_interface.setup_conversation(thread_id, ["MODERATOR", "ASSISTANT"])
        
        agent_types = agent_interface.get_agent_types(thread_id)
        
        assert set(agent_types) == {"MODERATOR", "ASSISTANT"}

    def test_get_agent_types_nonexistent_thread(self, agent_interface, mock_agents):
        """Test getting agent types for non-existent thread falls back to base agents."""
        # Register agents
        for agent_type, agent in mock_agents.items():
            agent_interface.register_base_agent(agent_type, agent)
        
        agent_types = agent_interface.get_agent_types("nonexistent-thread")
        
        assert set(agent_types) == {"MODERATOR", "ASSISTANT", "CALCULATOR"}

    def test_get_agent_descriptions(self, agent_interface, mock_agents):
        """Test getting agent descriptions."""
        # Register agents
        for agent_type, agent in mock_agents.items():
            agent_interface.register_base_agent(agent_type, agent)
        
        descriptions = agent_interface.get_agent_descriptions()
        
        expected = {
            "MODERATOR": "Moderates conversations",
            "ASSISTANT": "General assistance",
            "CALCULATOR": "CALCULATOR agent"  # Default description
        }
        assert descriptions == expected

    def test_cleanup_conversation(self, agent_interface, mock_agents):
        """Test cleaning up conversation agents."""
        # Set up conversation
        agent_interface.register_base_agent("MODERATOR", mock_agents["MODERATOR"])
        thread_id = "thread-cleanup"
        agent_interface.setup_conversation(thread_id, ["MODERATOR"])
        
        # Verify setup
        assert thread_id in agent_interface.conversation_agents
        
        # Cleanup
        agent_interface.cleanup_conversation(thread_id)
        
        # Verify cleanup
        assert thread_id not in agent_interface.conversation_agents

    def test_cleanup_conversation_nonexistent(self, agent_interface):
        """Test cleaning up non-existent conversation doesn't error."""
        # Should not raise an exception
        agent_interface.cleanup_conversation("nonexistent-thread")

    def test_multiple_conversations(self, agent_interface, mock_agents):
        """Test handling multiple conversations simultaneously."""
        # Register agents
        for agent_type, agent in mock_agents.items():
            agent_interface.register_base_agent(agent_type, agent)
        
        # Set up multiple conversations
        thread1 = "thread-1"
        thread2 = "thread-2"
        
        agent_interface.setup_conversation(thread1, ["MODERATOR", "ASSISTANT"])
        agent_interface.setup_conversation(thread2, ["MODERATOR", "CALCULATOR"])
        
        # Verify both conversations exist
        assert thread1 in agent_interface.conversation_agents
        assert thread2 in agent_interface.conversation_agents
        
        # Verify correct agents in each
        assert set(agent_interface.get_agent_types(thread1)) == {"MODERATOR", "ASSISTANT"}
        assert set(agent_interface.get_agent_types(thread2)) == {"MODERATOR", "CALCULATOR"}
        
        # Cleanup one conversation
        agent_interface.cleanup_conversation(thread1)
        
        # Verify only thread1 was cleaned up
        assert thread1 not in agent_interface.conversation_agents
        assert thread2 in agent_interface.conversation_agents

    def test_agent_instance_sharing(self, agent_interface, mock_agents):
        """Test that agent instances are shared between conversations."""
        # Register agent
        agent_interface.register_base_agent("MODERATOR", mock_agents["MODERATOR"])
        
        # Set up two conversations
        thread1 = "thread-share-1"
        thread2 = "thread-share-2"
        
        agent1 = agent_interface.get_agent(thread1, "MODERATOR")
        agent2 = agent_interface.get_agent(thread2, "MODERATOR")
        
        # Should be the same instance (shared base agent)
        assert agent1 is agent2
        assert agent1 is mock_agents["MODERATOR"]

    def test_register_agent_with_str_description(self, agent_interface):
        """Test registering agent where description needs string conversion."""
        class AgentWithObjectDescription:
            def __init__(self):
                self.description = ["Complex", "description", "object"]
        
        agent = AgentWithObjectDescription()
        agent_interface.register_base_agent("COMPLEX", agent)
        
        # Should convert to string
        description = agent_interface.agent_descriptions["COMPLEX"]
        assert isinstance(description, str)
        assert "Complex" in description

    def test_error_handling_in_setup_conversation(self, agent_interface, caplog):
        """Test error handling during conversation setup."""
        # Mock the base_agents dict to raise an exception during access
        original_base_agents = agent_interface.base_agents
        
        # Create a mock that raises exception on __getitem__
        mock_base_agents = Mock()
        mock_base_agents.__contains__ = Mock(return_value=True)  # Agent exists
        mock_base_agents.__getitem__ = Mock(side_effect=Exception("Setup error"))
        
        agent_interface.base_agents = mock_base_agents
        
        thread_id = "thread-error"
        
        try:
            with caplog.at_level(logging.ERROR):
                agent_interface.setup_conversation(thread_id, ["PROBLEMATIC"])
            
            # Should log error but not crash
            assert "Failed to set up agent PROBLEMATIC" in caplog.text
        finally:
            # Restore original
            agent_interface.base_agents = original_base_agents

    def test_singleton_instance(self):
        """Test that the singleton instance is available."""
        from app.agents.agent_interface import agent_interface
        
        assert isinstance(agent_interface, AgentInterface)

    def test_empty_agent_types_list(self, agent_interface):
        """Test setup_conversation with empty agent types list."""
        thread_id = "thread-empty"
        
        agent_interface.setup_conversation(thread_id, [])
        
        # Should create empty conversation entry
        assert thread_id in agent_interface.conversation_agents
        assert agent_interface.conversation_agents[thread_id] == {}

    def test_get_agent_descriptions_empty(self, agent_interface):
        """Test getting descriptions when no agents are registered."""
        descriptions = agent_interface.get_agent_descriptions()
        
        assert descriptions == {}

    def test_get_agent_types_empty(self, agent_interface):
        """Test getting agent types when no agents are registered."""
        agent_types = agent_interface.get_agent_types()
        
        assert agent_types == []