import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from app.agents.agent_interface import AgentInterface, agent_interface


class TestAgentInterface:
    """Test the AgentInterface class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.interface = AgentInterface()
        
        # Create mock agents for testing
        self.mock_agent1 = Mock()
        self.mock_agent1.description = "Test Agent 1"
        
        self.mock_agent2 = Mock()
        self.mock_agent2.description = "Test Agent 2"
        
        self.mock_agent_no_desc = Mock()
        del self.mock_agent_no_desc.description  # Ensure no description attribute
        
    def test_init(self):
        """Test AgentInterface initialization."""
        interface = AgentInterface()
        assert interface.base_agents == {}
        assert interface.conversation_agents == {}
        assert interface.agent_descriptions == {}
        
    def test_register_base_agent_with_description(self):
        """Test registering a base agent with description."""
        agent_type = "TEST_AGENT"
        
        self.interface.register_base_agent(agent_type, self.mock_agent1)
        
        assert "TEST_AGENT" in self.interface.base_agents
        assert self.interface.base_agents["TEST_AGENT"] == self.mock_agent1
        assert self.interface.agent_descriptions["TEST_AGENT"] == "Test Agent 1"
        
    def test_register_base_agent_without_description(self):
        """Test registering a base agent without description."""
        agent_type = "NO_DESC_AGENT"
        
        self.interface.register_base_agent(agent_type, self.mock_agent_no_desc)
        
        assert "NO_DESC_AGENT" in self.interface.base_agents
        assert self.interface.base_agents["NO_DESC_AGENT"] == self.mock_agent_no_desc
        assert self.interface.agent_descriptions["NO_DESC_AGENT"] == "NO_DESC_AGENT agent"
        
    def test_register_base_agent_case_normalization(self):
        """Test that agent types are normalized to uppercase."""
        agent_type = "test_agent"
        
        self.interface.register_base_agent(agent_type, self.mock_agent1)
        
        assert "TEST_AGENT" in self.interface.base_agents
        assert "test_agent" not in self.interface.base_agents
        
    @patch('app.agents.agent_interface.logger')
    def test_register_base_agent_logging(self, mock_logger):
        """Test that registering an agent logs the action."""
        agent_type = "LOG_TEST"
        
        self.interface.register_base_agent(agent_type, self.mock_agent1)
        
        mock_logger.info.assert_called_with("Registered base agent: LOG_TEST")
        
    def test_setup_conversation_new_thread(self):
        """Test setting up agents for a new conversation thread."""
        # First register some base agents
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        self.interface.register_base_agent("AGENT2", self.mock_agent2)
        
        thread_id = "test_thread_1"
        agent_types = ["AGENT1", "AGENT2"]
        
        self.interface.setup_conversation(thread_id, agent_types)
        
        assert thread_id in self.interface.conversation_agents
        assert "AGENT1" in self.interface.conversation_agents[thread_id]
        assert "AGENT2" in self.interface.conversation_agents[thread_id]
        assert self.interface.conversation_agents[thread_id]["AGENT1"] == self.mock_agent1
        assert self.interface.conversation_agents[thread_id]["AGENT2"] == self.mock_agent2
        
    def test_setup_conversation_existing_thread(self):
        """Test setting up additional agents for an existing conversation thread."""
        # Register base agents
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        self.interface.register_base_agent("AGENT2", self.mock_agent2)
        
        thread_id = "test_thread_1"
        
        # Set up first agent
        self.interface.setup_conversation(thread_id, ["AGENT1"])
        assert len(self.interface.conversation_agents[thread_id]) == 1
        
        # Set up second agent
        self.interface.setup_conversation(thread_id, ["AGENT2"])
        assert len(self.interface.conversation_agents[thread_id]) == 2
        
    def test_setup_conversation_skip_existing_agents(self):
        """Test that already set up agents are skipped."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        
        thread_id = "test_thread_1"
        
        # Set up agent first time
        self.interface.setup_conversation(thread_id, ["AGENT1"])
        original_agent = self.interface.conversation_agents[thread_id]["AGENT1"]
        
        # Set up same agent again
        self.interface.setup_conversation(thread_id, ["AGENT1"])
        
        # Should be the same instance (not re-created)
        assert self.interface.conversation_agents[thread_id]["AGENT1"] is original_agent
        
    def test_setup_conversation_case_normalization(self):
        """Test that agent types are normalized during conversation setup."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        
        thread_id = "test_thread_1"
        
        # Use lowercase agent type
        self.interface.setup_conversation(thread_id, ["agent1"])
        
        assert "AGENT1" in self.interface.conversation_agents[thread_id]
        
    @patch('app.agents.agent_interface.logger')
    def test_setup_conversation_missing_base_agent(self, mock_logger):
        """Test handling of missing base agents during setup."""
        thread_id = "test_thread_1"
        
        self.interface.setup_conversation(thread_id, ["NONEXISTENT"])
        
        mock_logger.warning.assert_called_with("Base agent NONEXISTENT not found, skipping")
        assert thread_id in self.interface.conversation_agents
        assert len(self.interface.conversation_agents[thread_id]) == 0
        
    @patch('app.agents.agent_interface.logger')
    def test_setup_conversation_exception_handling(self, mock_logger):
        """Test exception handling during conversation setup."""
        # Create a mock agent that raises an exception when accessed
        failing_agent = Mock()
        failing_agent.side_effect = Exception("Test exception")
        
        self.interface.register_base_agent("FAILING_AGENT", failing_agent)
        thread_id = "test_thread_1"
        
        # This should handle the exception gracefully
        self.interface.setup_conversation(thread_id, ["FAILING_AGENT"])
        
        mock_logger.error.assert_called()
        
    def test_get_agent_existing_conversation(self):
        """Test getting an agent from an existing conversation."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        
        thread_id = "test_thread_1"
        self.interface.setup_conversation(thread_id, ["AGENT1"])
        
        agent = self.interface.get_agent(thread_id, "AGENT1")
        assert agent == self.mock_agent1
        
    def test_get_agent_auto_setup(self):
        """Test that get_agent automatically sets up agents from base templates."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        
        thread_id = "test_thread_2"
        
        # Get agent without explicitly setting up conversation
        agent = self.interface.get_agent(thread_id, "AGENT1")
        
        assert agent == self.mock_agent1
        assert thread_id in self.interface.conversation_agents
        assert "AGENT1" in self.interface.conversation_agents[thread_id]
        
    def test_get_agent_case_normalization(self):
        """Test that get_agent normalizes agent types to uppercase."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        
        thread_id = "test_thread_1"
        
        # Use lowercase agent type
        agent = self.interface.get_agent(thread_id, "agent1")
        
        assert agent == self.mock_agent1
        
    def test_get_agent_nonexistent(self):
        """Test getting a nonexistent agent returns None."""
        thread_id = "test_thread_1"
        
        agent = self.interface.get_agent(thread_id, "NONEXISTENT")
        
        assert agent is None
        
    @patch('app.agents.agent_interface.logger')
    def test_get_agent_nonexistent_logging(self, mock_logger):
        """Test that getting a nonexistent agent logs a warning."""
        thread_id = "test_thread_1"
        
        self.interface.get_agent(thread_id, "NONEXISTENT")
        
        mock_logger.warning.assert_called_with("Agent NONEXISTENT not found for thread test_thread_1")
        
    def test_get_agent_types_base_agents(self):
        """Test getting agent types from base agents."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        self.interface.register_base_agent("AGENT2", self.mock_agent2)
        
        agent_types = self.interface.get_agent_types()
        
        assert set(agent_types) == {"AGENT1", "AGENT2"}
        
    def test_get_agent_types_conversation_specific(self):
        """Test getting agent types for a specific conversation."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        self.interface.register_base_agent("AGENT2", self.mock_agent2)
        
        thread_id = "test_thread_1"
        self.interface.setup_conversation(thread_id, ["AGENT1"])
        
        # Should return only agents set up for this conversation
        agent_types = self.interface.get_agent_types(thread_id)
        assert agent_types == ["AGENT1"]
        
        # Should still return all base agents when no thread_id provided
        all_agent_types = self.interface.get_agent_types()
        assert set(all_agent_types) == {"AGENT1", "AGENT2"}
        
    def test_get_agent_types_nonexistent_thread(self):
        """Test getting agent types for a nonexistent thread returns base agents."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        
        agent_types = self.interface.get_agent_types("nonexistent_thread")
        
        assert agent_types == ["AGENT1"]
        
    def test_get_agent_descriptions(self):
        """Test getting agent descriptions."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        self.interface.register_base_agent("AGENT2", self.mock_agent_no_desc)
        
        descriptions = self.interface.get_agent_descriptions()
        
        expected = {
            "AGENT1": "Test Agent 1",
            "AGENT2": "AGENT2 agent"
        }
        assert descriptions == expected
        
    def test_cleanup_conversation_existing(self):
        """Test cleaning up an existing conversation."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        
        thread_id = "test_thread_1"
        self.interface.setup_conversation(thread_id, ["AGENT1"])
        
        # Verify conversation exists
        assert thread_id in self.interface.conversation_agents
        
        # Clean up
        self.interface.cleanup_conversation(thread_id)
        
        # Verify conversation is removed
        assert thread_id not in self.interface.conversation_agents
        
    @patch('app.agents.agent_interface.logger')
    def test_cleanup_conversation_logging(self, mock_logger):
        """Test that cleanup logs the action."""
        self.interface.register_base_agent("AGENT1", self.mock_agent1)
        
        thread_id = "test_thread_1"
        self.interface.setup_conversation(thread_id, ["AGENT1"])
        
        self.interface.cleanup_conversation(thread_id)
        
        mock_logger.info.assert_called_with("Cleaned up agents for conversation test_thread_1")
        
    def test_cleanup_conversation_nonexistent(self):
        """Test cleaning up a nonexistent conversation doesn't error."""
        # Should not raise an exception
        self.interface.cleanup_conversation("nonexistent_thread")
        
        # Should still be empty
        assert len(self.interface.conversation_agents) == 0


class TestAgentInterfaceSingleton:
    """Test the singleton agent_interface instance."""
    
    def test_singleton_instance_exists(self):
        """Test that the singleton instance exists and is an AgentInterface."""
        assert agent_interface is not None
        assert isinstance(agent_interface, AgentInterface)
        
    def test_singleton_instance_persistence(self):
        """Test that the singleton instance persists across imports."""
        # Register an agent
        mock_agent = Mock()
        mock_agent.description = "Singleton Test Agent"
        
        agent_interface.register_base_agent("SINGLETON_TEST", mock_agent)
        
        # Verify it's there
        assert "SINGLETON_TEST" in agent_interface.base_agents
        
        # Import again (simulating module re-import)
        from app.agents.agent_interface import agent_interface as imported_interface
        
        # Should be the same instance with the same data
        assert imported_interface is agent_interface
        assert "SINGLETON_TEST" in imported_interface.base_agents


class TestAgentInterfaceIntegration:
    """Integration tests for AgentInterface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.interface = AgentInterface()
        
        # Create multiple mock agents
        self.agents = {}
        for i in range(3):
            agent = Mock()
            agent.description = f"Integration Test Agent {i + 1}"
            self.agents[f"AGENT{i + 1}"] = agent
            self.interface.register_base_agent(f"AGENT{i + 1}", agent)
            
    def test_multiple_conversations_isolation(self):
        """Test that multiple conversations are properly isolated."""
        thread1 = "thread_1"
        thread2 = "thread_2"
        
        # Set up different agents for each conversation
        self.interface.setup_conversation(thread1, ["AGENT1", "AGENT2"])
        self.interface.setup_conversation(thread2, ["AGENT2", "AGENT3"])
        
        # Verify isolation
        thread1_agents = self.interface.get_agent_types(thread1)
        thread2_agents = self.interface.get_agent_types(thread2)
        
        assert set(thread1_agents) == {"AGENT1", "AGENT2"}
        assert set(thread2_agents) == {"AGENT2", "AGENT3"}
        
        # Verify agents are accessible
        assert self.interface.get_agent(thread1, "AGENT1") == self.agents["AGENT1"]
        assert self.interface.get_agent(thread1, "AGENT3") is None
        assert self.interface.get_agent(thread2, "AGENT3") == self.agents["AGENT3"]
        assert self.interface.get_agent(thread2, "AGENT1") == self.agents["AGENT1"]  # Auto-setup
        
    def test_conversation_lifecycle(self):
        """Test the complete lifecycle of a conversation."""
        thread_id = str(uuid4())
        
        # 1. Start with no conversation
        assert thread_id not in self.interface.conversation_agents
        
        # 2. Set up conversation
        self.interface.setup_conversation(thread_id, ["AGENT1", "AGENT2"])
        assert len(self.interface.conversation_agents[thread_id]) == 2
        
        # 3. Add more agents
        self.interface.setup_conversation(thread_id, ["AGENT3"])
        assert len(self.interface.conversation_agents[thread_id]) == 3
        
        # 4. Access agents
        agent1 = self.interface.get_agent(thread_id, "AGENT1")
        assert agent1 == self.agents["AGENT1"]
        
        # 5. Clean up
        self.interface.cleanup_conversation(thread_id)
        assert thread_id not in self.interface.conversation_agents
        
        # 6. Verify base agents still exist
        assert len(self.interface.base_agents) == 3
        
    def test_agent_descriptions_consistency(self):
        """Test that agent descriptions remain consistent across operations."""
        descriptions = self.interface.get_agent_descriptions()
        
        expected = {
            "AGENT1": "Integration Test Agent 1",
            "AGENT2": "Integration Test Agent 2", 
            "AGENT3": "Integration Test Agent 3"
        }
        
        assert descriptions == expected
        
        # Set up conversations and verify descriptions don't change
        self.interface.setup_conversation("test_thread", ["AGENT1", "AGENT2"])
        
        descriptions_after = self.interface.get_agent_descriptions()
        assert descriptions_after == expected
        
    def test_concurrent_conversation_operations(self):
        """Test operations on multiple conversations simultaneously."""
        threads = [f"thread_{i}" for i in range(5)]
        
        # Set up multiple conversations with different agent combinations
        for i, thread in enumerate(threads):
            agents_for_thread = [f"AGENT{(i % 3) + 1}", f"AGENT{((i + 1) % 3) + 1}"]
            self.interface.setup_conversation(thread, agents_for_thread)
            
        # Verify all conversations exist and are properly configured
        for thread in threads:
            assert thread in self.interface.conversation_agents
            assert len(self.interface.conversation_agents[thread]) == 2
            
        # Clean up conversations one by one
        for thread in threads:
            self.interface.cleanup_conversation(thread)
            assert thread not in self.interface.conversation_agents
            
        # Verify base agents are unaffected
        assert len(self.interface.base_agents) == 3