import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents import WebSearchTool
from agents.run_context import RunContextWrapper
from app.agents.web_search_agent import WebSearchAgent
from app.agents.common_context import CommonAgentContext


class TestWebSearchAgent:
    """Test cases for WebSearchAgent class."""

    def test_initialization_default(self):
        """Test WebSearchAgent initialization with default values."""
        agent = WebSearchAgent()
        
        assert agent.name == "Web Search Assistant"
        assert agent.model == "gpt-4o-mini"  # From settings
        assert agent._search_location is None
        assert agent._search_context_size == "medium"
        assert agent.description == "Specialist in performing web searches to find up-to-date information from the internet"
        assert len(agent.functions) == 4  # WebSearchTool + 3 custom functions
        assert agent.model_settings.tool_choice == "auto"
        assert agent.model_settings.parallel_tool_calls is True
        assert agent.model_settings.max_tokens == 2048

    def test_initialization_with_parameters(self):
        """Test WebSearchAgent initialization with custom parameters."""
        agent = WebSearchAgent(
            name="Custom Search Agent",
            search_location="New York, USA",
            search_context_size="high",
            tool_choice="required",
            parallel_tool_calls=False
        )
        
        assert agent.name == "Custom Search Agent"
        assert agent._search_location == "New York, USA"
        assert agent._search_context_size == "high"
        assert agent.model_settings.tool_choice == "required"
        assert agent.model_settings.parallel_tool_calls is False

    @patch('app.agents.web_search_agent.WebSearchTool')
    def test_initialization_with_valid_location(self, mock_web_search_tool):
        """Test initialization with valid location format."""
        mock_tool = Mock()
        mock_web_search_tool.return_value = mock_tool
        
        agent = WebSearchAgent(search_location="San Francisco, USA")
        
        # Should call WebSearchTool with parsed location
        mock_web_search_tool.assert_called_with(
            user_location={"city": "San Francisco", "country": "USA"},
            search_context_size=None
        )

    @patch('app.agents.web_search_agent.WebSearchTool')
    def test_initialization_with_invalid_location(self, mock_web_search_tool):
        """Test initialization with invalid location format."""
        mock_tool = Mock()
        mock_web_search_tool.return_value = mock_tool
        
        agent = WebSearchAgent(search_location="InvalidLocation")
        
        # Should call WebSearchTool without location due to invalid format
        # The second call should be without user_location
        calls = mock_web_search_tool.call_args_list
        assert len(calls) >= 1

    @patch('app.agents.web_search_agent.WebSearchTool')
    def test_initialization_websearchtool_exception(self, mock_web_search_tool):
        """Test initialization when WebSearchTool raises exception."""
        # First call raises exception, second call works (for fallback)
        mock_tool = Mock()
        mock_web_search_tool.side_effect = [Exception("Tool creation failed"), mock_tool]
        
        # Should not raise exception, should handle gracefully
        agent = WebSearchAgent()
        
        assert agent is not None
        # Should still have the custom functions even if WebSearchTool failed
        assert len(agent.functions) >= 3

    @pytest.mark.asyncio
    async def test_init_context(self):
        """Test context initialization."""
        agent = WebSearchAgent()
        mock_context = Mock()
        
        # Should not raise any exceptions
        await agent.init_context(mock_context)

    def test_description_property(self):
        """Test description property."""
        agent = WebSearchAgent()
        description = agent.description
        
        assert isinstance(description, str)
        assert "web search" in description.lower()
        assert "internet" in description.lower()

    def test_refine_search_terms_basic(self):
        """Test basic search term refinement."""
        agent = WebSearchAgent()
        context = Mock()
        
        result = agent.refine_search_terms(
            context,
            original_query="artificial intelligence applications",
            focus_area="healthcare"
        )
        
        assert isinstance(result, list)
        assert len(result) > 1
        assert "artificial intelligence applications" in result
        # Should include focus area combinations
        healthcare_variants = [term for term in result if "healthcare" in term]
        assert len(healthcare_variants) > 0

    def test_refine_search_terms_long_query(self):
        """Test search term refinement with long query."""
        agent = WebSearchAgent()
        context = Mock()
        
        long_query = "machine learning algorithms for natural language processing applications"
        result = agent.refine_search_terms(context, original_query=long_query)
        
        assert isinstance(result, list)
        # Should include shortened version
        shortened_variants = [term for term in result if len(term.split()) <= 4]
        assert len(shortened_variants) > 0

    def test_refine_search_terms_how_to_query(self):
        """Test search term refinement with how-to queries."""
        agent = WebSearchAgent()
        context = Mock()
        
        result = agent.refine_search_terms(
            context,
            original_query="implement neural networks"
        )
        
        # Should include "how to" variant
        how_to_variants = [term for term in result if term.startswith("how to")]
        assert len(how_to_variants) > 0

    def test_refine_search_terms_with_spaces(self):
        """Test search term refinement with quoted versions."""
        agent = WebSearchAgent()
        context = Mock()
        
        result = agent.refine_search_terms(
            context,
            original_query="machine learning"
        )
        
        # Should include quoted version
        quoted_variants = [term for term in result if '"' in term]
        assert len(quoted_variants) > 0

    def test_refine_search_terms_defaults(self):
        """Test search term refinement with default values."""
        agent = WebSearchAgent()
        context = Mock()
        
        result = agent.refine_search_terms(context)
        
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_synthesize_information_basic(self):
        """Test basic information synthesis."""
        agent = WebSearchAgent()
        context = Mock()
        
        search_results = [
            {"title": "Article 1", "content": "Content 1"},
            {"title": "Article 2", "content": "Content 2"}
        ]
        
        result = agent.synthesize_information(
            context,
            search_results=search_results,
            focus_question="What is AI?"
        )
        
        assert isinstance(result, str)
        assert "What is AI?" in result
        assert "Article 1" in result
        assert "Article 2" in result
        assert "2 sources" in result

    def test_synthesize_information_empty_results(self):
        """Test information synthesis with empty results."""
        agent = WebSearchAgent()
        context = Mock()
        
        result = agent.synthesize_information(context, search_results=[])
        
        assert isinstance(result, str)
        assert "No search results" in result

    def test_synthesize_information_defaults(self):
        """Test information synthesis with default values."""
        agent = WebSearchAgent()
        context = Mock()
        
        result = agent.synthesize_information(context)
        
        assert isinstance(result, str)
        assert "General information synthesis" in result

    def test_extract_key_information_basic(self):
        """Test basic key information extraction."""
        agent = WebSearchAgent()
        context = Mock()
        
        result = agent.extract_key_information(
            context,
            text="This is a sample text with important information.",
            extraction_targets=["dates", "statistics"]
        )
        
        assert isinstance(result, dict)
        assert "text_length" in result
        assert "summary" in result
        assert "dates" in result
        assert "statistics" in result
        assert result["text_length"] == str(len("This is a sample text with important information."))

    def test_extract_key_information_defaults(self):
        """Test key information extraction with default values."""
        agent = WebSearchAgent()
        context = Mock()
        
        result = agent.extract_key_information(context)
        
        assert isinstance(result, dict)
        assert "text_length" in result
        assert "summary" in result
        assert "general information" in result

    def test_clone_basic(self):
        """Test basic agent cloning."""
        original = WebSearchAgent(
            name="Original Agent",
            search_location="London, UK",
            search_context_size="high"
        )
        
        clone = original.clone()
        
        assert clone.name == "Original Agent"
        assert clone._search_location == "London, UK"
        assert clone._search_context_size == "high"
        assert clone is not original

    def test_clone_with_overrides(self):
        """Test agent cloning with parameter overrides."""
        original = WebSearchAgent(
            name="Original Agent",
            search_location="London, UK",
            tool_choice="auto"
        )
        
        clone = original.clone(
            name="Cloned Agent",
            search_location="Paris, France",
            tool_choice="required"
        )
        
        assert clone.name == "Cloned Agent"
        assert clone._search_location == "Paris, France"
        assert clone.model_settings.tool_choice == "required"

    def test_clone_filters_none_values(self):
        """Test that clone filters out None values."""
        original = WebSearchAgent()
        
        clone = original.clone(
            name="New Agent",
            search_location=None,  # Should use default
            model=None  # Should use default
        )
        
        assert clone.name == "New Agent"
        # Should use original values for None parameters
        assert clone._search_location == original._search_location

    def test_functions_are_properly_set(self):
        """Test that all expected functions are set."""
        agent = WebSearchAgent()
        
        # Should have WebSearchTool + 3 custom functions
        assert len(agent.functions) == 4
        
        # Check function names
        function_names = []
        for func in agent.functions:
            if hasattr(func, 'name'):
                function_names.append(func.name)
            elif hasattr(func, '__name__'):
                function_names.append(func.__name__)
        
        expected_functions = ['refine_search_terms', 'synthesize_information', 'extract_key_information']
        for expected in expected_functions:
            assert any(expected in name for name in function_names)

    def test_instructions_content(self):
        """Test that instructions contain expected content."""
        agent = WebSearchAgent()
        
        instructions = agent.instructions
        if callable(instructions):
            # If instructions is a function, call it with mock context
            mock_ctx = Mock()
            mock_ctx.context = Mock()
            mock_ctx.context.buffer_context = None
            instructions = instructions(mock_ctx, agent)
        
        assert isinstance(instructions, str)
        assert "web search" in instructions.lower()
        assert "search the web" in instructions.lower()
        assert "cite your sources" in instructions.lower()
        assert "best practices" in instructions.lower()

    def test_model_settings(self):
        """Test model settings configuration."""
        agent = WebSearchAgent(
            tool_choice="required",
            parallel_tool_calls=False
        )
        
        assert agent.model_settings.tool_choice == "required"
        assert agent.model_settings.parallel_tool_calls is False
        assert agent.model_settings.max_tokens == 2048

    def test_search_location_parsing(self):
        """Test search location parsing edge cases."""
        # Test with extra whitespace
        agent1 = WebSearchAgent(search_location=" Tokyo , Japan ")
        assert agent1._search_location == " Tokyo , Japan "
        
        # Test with single word (invalid format)
        agent2 = WebSearchAgent(search_location="London")
        assert agent2._search_location == "London"

    def test_search_context_size_default(self):
        """Test search context size default handling."""
        agent = WebSearchAgent()
        assert agent._search_context_size == "medium"
        
        agent_with_context = WebSearchAgent(search_context_size="low")
        assert agent_with_context._search_context_size == "low"

    @patch('app.agents.web_search_agent.function_tool')
    def test_function_tool_creation(self, mock_function_tool):
        """Test that function_tool is called for custom methods."""
        mock_function_tool.return_value = Mock()
        
        agent = WebSearchAgent()
        
        # Should be called for each custom method
        assert mock_function_tool.call_count >= 3


class TestWebSearchAgentIntegration:
    """Integration tests for WebSearchAgent."""

    def test_complete_agent_setup(self):
        """Test complete agent setup with all features."""
        agent = WebSearchAgent(
            name="Integration Test Agent",
            search_location="San Francisco, USA",
            search_context_size="high",
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=1500
        )
        
        # Verify all aspects
        assert agent.name == "Integration Test Agent"
        assert agent._search_location == "San Francisco, USA"
        assert agent._search_context_size == "high"
        assert agent.model_settings.tool_choice == "auto"
        assert agent.model_settings.parallel_tool_calls is True
        assert agent.model_settings.max_tokens == 1500
        assert len(agent.functions) == 4
        
        # Test description
        description = agent.description
        assert "web search" in description.lower()
        
        # Test method calls
        context = Mock()
        
        # Test refine_search_terms
        search_terms = agent.refine_search_terms(
            context,
            "test query",
            "test focus"
        )
        assert isinstance(search_terms, list)
        
        # Test synthesize_information
        synthesis = agent.synthesize_information(
            context,
            [{"title": "Test", "content": "Content"}],
            "Test question"
        )
        assert isinstance(synthesis, str)
        
        # Test extract_key_information
        extraction = agent.extract_key_information(
            context,
            "test text",
            ["dates"]
        )
        assert isinstance(extraction, dict)

    def test_agent_workflow_simulation(self):
        """Test simulated agent workflow."""
        agent = WebSearchAgent()
        context = Mock()
        
        # Step 1: Refine search terms
        original_query = "latest AI research developments"
        refined_terms = agent.refine_search_terms(
            context,
            original_query=original_query,
            focus_area="machine learning"
        )
        
        assert len(refined_terms) > 1
        assert original_query in refined_terms
        
        # Step 2: Simulate search results
        mock_results = [
            {
                "title": "Latest AI Breakthroughs in 2024",
                "content": "Recent advances in machine learning have led to significant improvements...",
                "url": "https://example.com/ai-breakthroughs"
            },
            {
                "title": "Machine Learning Research Trends",
                "content": "Current trends in ML research include federated learning, transfer learning...",
                "url": "https://example.com/ml-trends"
            }
        ]
        
        # Step 3: Extract key information
        for result in mock_results:
            key_info = agent.extract_key_information(
                context,
                text=result["content"],
                extraction_targets=["trends", "technologies"]
            )
            assert "trends" in key_info
            assert "technologies" in key_info
        
        # Step 4: Synthesize information
        synthesis = agent.synthesize_information(
            context,
            search_results=mock_results,
            focus_question="What are the latest AI developments?"
        )
        
        assert "Latest AI Breakthroughs" in synthesis
        assert "Machine Learning Research" in synthesis
        assert "2 sources" in synthesis

    def test_error_handling(self):
        """Test error handling in various scenarios."""
        agent = WebSearchAgent()
        context = Mock()
        
        # Test with None values
        result1 = agent.refine_search_terms(context, None, None)
        assert isinstance(result1, list)
        
        result2 = agent.synthesize_information(context, None, None)
        assert isinstance(result2, str)
        
        result3 = agent.extract_key_information(context, None, None)
        assert isinstance(result3, dict)
        
        # Test with empty values
        result4 = agent.synthesize_information(context, [], "")
        assert "No search results" in result4


if __name__ == "__main__":
    pytest.main([__file__])
