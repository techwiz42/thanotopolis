import pytest
from unittest.mock import Mock, MagicMock, patch
from agents import Agent, ModelSettings
from agents.tool import FunctionTool
from agents.run_context import RunContextWrapper
from app.agents.base_agent import BaseAgent, BaseAgentHooks
from app.agents.common_context import CommonAgentContext


class MockTool(FunctionTool):
    """Mock tool for testing."""
    def __init__(self, name="mock_tool"):
        self.name = name
        self.description = f"Description for {name}"
        self.params_json_schema = {"type": "object", "properties": {}, "required": []}
        self.strict_json_schema = False
        self.on_invoke = lambda ctx, params: None
        self.on_invoke_tool = lambda ctx, params: None


class TestBaseAgentHooks:
    """Test cases for BaseAgentHooks class."""

    @pytest.mark.asyncio
    async def test_init_context_with_buffer_context(self):
        """Test context initialization with buffer context."""
        hooks = BaseAgentHooks()
        
        # Create mock context with buffer context
        mock_agent_context = Mock()
        mock_agent_context.buffer_context = "Test buffer content"
        
        mock_context = Mock()
        mock_context.context = mock_agent_context
        
        # Should not raise any exceptions
        await hooks.init_context(mock_context)

    @pytest.mark.asyncio
    async def test_init_context_without_buffer_context(self):
        """Test context initialization without buffer context."""
        hooks = BaseAgentHooks()
        
        # Create mock context without buffer context
        mock_agent_context = Mock()
        mock_agent_context.buffer_context = None
        
        mock_context = Mock()
        mock_context.context = mock_agent_context
        
        # Should not raise any exceptions
        await hooks.init_context(mock_context)

    @pytest.mark.asyncio
    async def test_init_context_no_context_attribute(self):
        """Test context initialization when context has no 'context' attribute."""
        hooks = BaseAgentHooks()
        
        # Create mock context without context attribute
        mock_context = Mock(spec=[])  # spec=[] means no attributes
        
        # Should not raise any exceptions
        await hooks.init_context(mock_context)


class TestBaseAgent:
    """Test cases for BaseAgent class."""

    def test_initialization_with_defaults(self):
        """Test BaseAgent initialization with default values."""
        agent = BaseAgent()
        
        assert agent.name == "Agent"
        assert agent.model == "gpt-4o-mini"  # From settings.DEFAULT_AGENT_MODEL
        assert agent.tools == []
        assert agent._functions == []
        assert isinstance(agent.hooks, BaseAgentHooks)

    def test_initialization_with_parameters(self):
        """Test BaseAgent initialization with custom parameters."""
        agent = BaseAgent(
            name="TestAgent",
            model="gpt-4",
            instructions="Custom instructions",
            tool_choice="auto",
            parallel_tool_calls=False,
            max_tokens=1000
        )
        
        assert agent.name == "TestAgent"
        assert agent.model == "gpt-4"
        assert agent.model_settings.tool_choice == "auto"
        assert agent.model_settings.parallel_tool_calls is False
        assert agent.model_settings.max_tokens == 1000

    def test_initialization_with_functions(self):
        """Test BaseAgent initialization with functions."""
        def test_function():
            return "test"
        
        mock_tool = MockTool()
        
        agent = BaseAgent(functions=[test_function, mock_tool])
        
        assert len(agent._functions) == 2
        assert agent._functions[0] == test_function
        assert agent._functions[1] == mock_tool

    def test_build_instructions_with_context(self):
        """Test building instructions with conversation context."""
        agent = BaseAgent(instructions="Base instructions")
        
        # Create mock context with buffer context
        mock_agent_context = Mock()
        mock_agent_context.buffer_context = "Previous conversation"
        
        mock_context = Mock()
        mock_context.context = mock_agent_context
        
        result = agent._build_instructions_with_context(mock_context, "Base instructions")
        
        assert "Base instructions" in result
        assert "Previous conversation" in result
        assert "## Conversation History:" in result

    def test_build_instructions_without_context(self):
        """Test building instructions without conversation context."""
        agent = BaseAgent(instructions="Base instructions")
        
        # Create mock context without buffer context
        mock_context = Mock()
        mock_context.context = None
        
        result = agent._build_instructions_with_context(mock_context, "Base instructions")
        
        assert result == "Base instructions"

    def test_convert_functions_to_tools_with_tools(self):
        """Test converting functions that are already tools."""
        mock_tool = MockTool()
        
        agent = BaseAgent()
        tools = agent._convert_functions_to_tools([mock_tool])
        
        assert len(tools) == 1
        assert tools[0] == mock_tool

    @patch('app.agents.base_agent.function_tool')
    def test_convert_functions_to_tools_with_functions(self, mock_function_tool):
        """Test converting regular functions to tools."""
        def test_function():
            return "test"
        
        mock_tool = MockTool()
        mock_function_tool.return_value = mock_tool
        
        agent = BaseAgent()
        tools = agent._convert_functions_to_tools([test_function])
        
        assert len(tools) == 1
        mock_function_tool.assert_called_once_with(test_function)

    def test_convert_functions_to_tools_with_schema(self):
        """Test converting functions that already have schemas."""
        def test_function():
            return "test"
        
        # Add schema to function
        test_function.schema = {"name": "test", "parameters": {}}
        
        agent = BaseAgent()
        tools = agent._convert_functions_to_tools([test_function])
        
        assert len(tools) == 1
        assert tools[0] == test_function

    @patch('app.agents.base_agent.function_tool')
    def test_convert_functions_to_tools_with_error(self, mock_function_tool):
        """Test converting functions with error handling."""
        def test_function():
            return "test"
        
        mock_function_tool.side_effect = Exception("Test error")
        
        agent = BaseAgent()
        tools = agent._convert_functions_to_tools([test_function])
        
        # Should create sanitized version
        assert len(tools) == 1
        assert isinstance(tools[0], FunctionTool)

    def test_validate_function_schema(self):
        """Test function schema validation."""
        agent = BaseAgent()
        
        mock_tool = Mock()
        mock_tool.schema = {
            "parameters": {
                "properties": {"param1": {}, "param2": {}},
                "required": ["param1", "param2", "param3"]  # param3 not in properties
            }
        }
        
        # Should not raise exception and should fix the schema
        agent._validate_function_schema(lambda: None, mock_tool)
        
        # param3 should be removed from required
        assert "param3" not in mock_tool.schema["parameters"]["required"]

    def test_create_sanitized_function_tool(self):
        """Test creating sanitized function tool."""
        def test_function(param1, param2="default"):
            return "test"
        
        agent = BaseAgent()
        tool = agent._create_sanitized_function_tool(test_function)
        
        assert isinstance(tool, FunctionTool)
        assert tool.name == "test_function"

    def test_create_sanitized_function_tool_with_error(self):
        """Test creating sanitized function tool with error."""
        def problematic_function():
            raise Exception("This function has issues")
        
        agent = BaseAgent()
        tool = agent._create_sanitized_function_tool(problematic_function)
        
        assert isinstance(tool, FunctionTool)
        assert tool.name == "problematic_function"

    def test_functions_property_getter(self):
        """Test functions property getter."""
        def test_function():
            return "test"
        
        agent = BaseAgent(functions=[test_function])
        
        assert len(agent.functions) == 1
        assert agent.functions[0] == test_function

    def test_functions_property_setter(self):
        """Test functions property setter."""
        def test_function1():
            return "test1"
        
        def test_function2():
            return "test2"
        
        agent = BaseAgent(functions=[test_function1])
        agent.functions = [test_function2]
        
        assert len(agent.functions) == 1
        assert agent.functions[0] == test_function2

    def test_add_function(self):
        """Test adding a function to the agent."""
        def test_function():
            return "test"
        
        agent = BaseAgent()
        agent.add_function(test_function)
        
        assert len(agent.functions) == 1
        assert agent.functions[0] == test_function
        assert len(agent.tools) >= 1

    def test_add_function_tool(self):
        """Test adding a tool to the agent."""
        mock_tool = MockTool()
        
        agent = BaseAgent()
        agent.add_function(mock_tool)
        
        assert len(agent.functions) == 1
        assert agent.functions[0] == mock_tool
        assert mock_tool in agent.tools

    def test_remove_function(self):
        """Test removing a function from the agent."""
        def test_function():
            return "test"
        
        agent = BaseAgent(functions=[test_function])
        agent.remove_function("test_function")
        
        assert len(agent.functions) == 0

    def test_remove_function_with_name_attribute(self):
        """Test removing a function that has a name attribute."""
        mock_tool = MockTool("named_tool")
        
        agent = BaseAgent(functions=[mock_tool])
        agent.remove_function("named_tool")
        
        assert len(agent.functions) == 0

    def test_get_function(self):
        """Test getting a function by name."""
        def test_function():
            return "test"
        
        agent = BaseAgent(functions=[test_function])
        
        result = agent.get_function("test_function")
        assert result == test_function

    def test_get_function_not_found(self):
        """Test getting a function that doesn't exist."""
        agent = BaseAgent()
        
        result = agent.get_function("nonexistent")
        assert result is None

    def test_get_function_with_name_attribute(self):
        """Test getting a function that has a name attribute."""
        mock_tool = MockTool("named_tool")
        
        agent = BaseAgent(functions=[mock_tool])
        
        result = agent.get_function("named_tool")
        assert result == mock_tool

    def test_set_tool_choice(self):
        """Test setting tool choice."""
        agent = BaseAgent()
        agent.set_tool_choice("required")
        
        assert agent.model_settings.tool_choice == "required"

    def test_set_parallel_tool_calls(self):
        """Test setting parallel tool calls."""
        agent = BaseAgent()
        agent.set_parallel_tool_calls(False)
        
        assert agent.model_settings.parallel_tool_calls is False

    def test_clone(self):
        """Test cloning an agent."""
        def test_function():
            return "test"
        
        original = BaseAgent(
            name="Original",
            functions=[test_function],
            tool_choice="auto",
            max_tokens=1000
        )
        
        clone = original.clone(name="Clone", max_tokens=2000)
        
        assert clone.name == "Clone"
        assert clone.model_settings.max_tokens == 2000
        assert clone.model_settings.tool_choice == "auto"
        assert len(clone.functions) == 1

    def test_clone_without_overrides(self):
        """Test cloning an agent without overrides."""
        original = BaseAgent(name="Original")
        clone = original.clone()
        
        assert clone.name == "Original"
        # Should be different instances
        assert clone is not original

    @patch('app.agents.base_agent.AgentHooks')
    def test_initialization_with_custom_hooks(self, mock_agent_hooks):
        """Test initialization with custom hooks."""
        custom_hooks = Mock()
        
        agent = BaseAgent(hooks=custom_hooks)
        
        assert agent.hooks == custom_hooks

    def test_initialization_with_callable_instructions(self):
        """Test initialization with callable instructions."""
        def instruction_func(ctx, agent):
            return "Dynamic instructions"
        
        agent = BaseAgent(instructions=instruction_func)
        
        # The instructions should be wrapped in a lambda
        assert callable(agent.instructions)

    def test_kwargs_handling(self):
        """Test that extra kwargs are passed to parent constructor."""
        # This tests that tools is properly removed from kwargs
        mock_tool = MockTool()
        
        agent = BaseAgent(
            name="Test",
            tools=[mock_tool],  # This should be removed from kwargs
            functions=[mock_tool]
        )
        
        assert agent.name == "Test"

    def test_model_settings_creation(self):
        """Test ModelSettings creation with various parameters."""
        agent = BaseAgent(
            tool_choice="required",
            parallel_tool_calls=False,
            max_tokens=1500
        )
        
        assert isinstance(agent.model_settings, ModelSettings)
        assert agent.model_settings.tool_choice == "required"
        assert agent.model_settings.parallel_tool_calls is False
        assert agent.model_settings.max_tokens == 1500


class TestBaseAgentIntegration:
    """Integration tests for BaseAgent."""

    def test_full_agent_setup(self):
        """Test complete agent setup with all features."""
        def tool_function(param1: str, param2: int = 5):
            """A test tool function."""
            return f"Result: {param1}, {param2}"
        
        mock_tool = MockTool("existing_tool")
        
        agent = BaseAgent(
            name="FullTestAgent",
            model="gpt-4",
            instructions="You are a test agent",
            functions=[tool_function, mock_tool],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2000
        )
        
        # Verify all aspects
        assert agent.name == "FullTestAgent"
        assert agent.model == "gpt-4"
        assert len(agent.functions) == 2
        assert len(agent.tools) >= 2
        assert agent.model_settings.tool_choice == "auto"
        assert agent.model_settings.parallel_tool_calls is True
        assert agent.model_settings.max_tokens == 2000
        
        # Test function management
        agent.add_function(lambda: "new_func")
        assert len(agent.functions) == 3
        
        # Test cloning
        clone = agent.clone(name="ClonedAgent", max_tokens=3000)
        assert clone.name == "ClonedAgent"
        assert clone.model_settings.max_tokens == 3000
        assert len(clone.functions) == 3

    def test_error_recovery(self):
        """Test agent behavior with problematic functions."""
        def good_function():
            return "good"
        
        def problematic_function():
            raise Exception("This function is broken")
        
        # Should handle problematic functions gracefully
        agent = BaseAgent(functions=[good_function, problematic_function])
        
        # Should still have both functions, but problematic one should be sanitized
        assert len(agent.functions) == 2
        assert len(agent.tools) >= 2


if __name__ == "__main__":
    pytest.main([__file__])