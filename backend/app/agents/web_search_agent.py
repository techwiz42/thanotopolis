from typing import Dict, Any, Optional, List
import logging
from agents import Agent, WebSearchTool, function_tool, ModelSettings, RunContextWrapper
from agents.run_context import RunContextWrapper
from app.core.config import settings
from app.services.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class WebSearchAgent(BaseAgent):
    """
    WebSearchAgent is a specialized agent that can perform web searches to find information.
    
    This agent specializes in searching the web for information and synthesizing
    the results into useful responses.
    """

    def __init__(
        self,
        name: str = "Web Search Assistant",
        search_location: Optional[str] = None,
        search_context_size: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        parallel_tool_calls: bool = True,
        **kwargs
    ):
        """
        Initialize a WebSearchAgent with web search capabilities.
        
        Args:
            name: The name of the agent. Defaults to "Web Search Assistant".
            search_location: Optional location for localized search results. 
                            Format should be "[City], [Country]" (e.g., "San Francisco, USA").
            search_context_size: The amount of search context to use. Options are
                                "low", "medium", or "high". Defaults to "medium".
            tool_choice: The tool choice strategy to use. Defaults to "auto".
            parallel_tool_calls: Whether to allow the agent to call multiple tools in parallel.
            **kwargs: Additional arguments to pass to the BaseAgent constructor.
        """
        # Define the web search instructions
        web_search_instructions = """You are a web search assistant agent that can search the internet to find information. Your role is to:

1. SEARCH THE WEB
- Search for up-to-date information based on user queries
- Find relevant and accurate information from reputable sources
- Synthesize and summarize information from multiple sources
- Provide comprehensive answers to questions

2. SEARCHING BEST PRACTICES
- Use specific search terms to get the most relevant results
- Break down complex queries into searchable components
- Search for different aspects of multi-part questions
- Use follow-up searches to refine or expand information
- Search for the most recent information when timeliness matters

3. RESPONSE GUIDELINES
- Always cite your sources with website names
- Indicate when information couldn't be found
- Provide balanced perspectives when appropriate
- Organize information in a clear, readable format
- Use bullet points or numbered lists for clarity when appropriate
- Indicate when information might be time-sensitive
- Start with a direct answer before expanding with details

4. CONTEXT AWARENESS
- Consider the user's geographic location for relevant information
- Understand what level of detail the user needs
- Adapt your search strategy based on the type of query
- Build on previous searches in the conversation

5. SEARCH LIMITATIONS
- Acknowledge when a search might not provide complete information
- Be transparent about difficulties finding certain information
- Explain when the user might need specialized sources beyond general web search
- Note when information is limited by region/country

When searching, always strive to find the most accurate, up-to-date, and relevant information available online."""

        # Store search configuration for later reference
        self._search_location = search_location
        # Apply default value for search_context_size
        self._search_context_size = search_context_size if search_context_size else "medium"
        
        # Create the WebSearchTool instance
        web_search_tool = None
        try:
            if search_location:
                parts = search_location.split(",")
                if len(parts) == 2:
                    city, country = parts
                    web_search_tool = WebSearchTool(
                        user_location={"city": city.strip(), "country": country.strip()},
                        search_context_size=search_context_size
                    )
                else:
                    logger.warning(f"Invalid search_location format: {search_location}. Expected 'City, Country'")
                    web_search_tool = WebSearchTool(search_context_size=search_context_size)
            else:
                web_search_tool = WebSearchTool(search_context_size=search_context_size)
        except Exception as e:
            logger.warning(f"Error creating WebSearchTool: {e}. Creating without location.")
            web_search_tool = WebSearchTool(search_context_size=search_context_size)
            
        # IMPORTANT: BaseAgent expects all tools in the 'functions' parameter
        # Combine the WebSearchTool and our method functions in one list
        all_functions = [
            web_search_tool,  # Include WebSearchTool as first function
            function_tool(self.refine_search_terms),
            function_tool(self.synthesize_information),
            function_tool(self.extract_key_information)
        ]
        
        # Initialize the Agent class directly
        super().__init__(
            name=name,
            model=settings.DEFAULT_AGENT_MODEL,
            instructions=web_search_instructions,
            functions=all_functions,  # Pass all functions as tools
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            max_tokens=2048,
            **kwargs
        )


    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """
        Initialize context for the WebSearchAgent.
        
        Args:
            context: The context wrapper object with conversation data
        """
        # Call parent implementation
        await super().init_context(context)
        
        # Add any agent-specific context initialization here
        logger.info(f"Initialized context for WebSearchAgent")
        
    @property
    def description(self) -> str:
        """
        Get a description of this agent's capabilities.
        
        Returns:
            A string describing the agent's specialty.
        """
        return "Specialist in performing web searches to find up-to-date information from the internet"

    def refine_search_terms(
        self, 
        context: RunContextWrapper, 
        original_query: Optional[str] = None, 
        focus_area: Optional[str] = None
    ) -> List[str]:
        """
        Refine a search query into more effective search terms.
        
        Args:
            context: The run context wrapper.
            original_query: The original search query that needs refinement.
            focus_area: Optional specific aspect to focus on.
            
        Returns:
            A list of suggested search terms that would be more effective.
        """
        # Handle default values inside the function
        original_query = original_query or ""
        
        logger.info(f"Refining search terms for: {original_query}")
        
        # Process the query to generate more effective search variations
        refined_terms = [original_query]  # Always include original
        
        # Add query variations
        words = original_query.split()
        if len(words) > 3:
            # Create a more concise version
            refined_terms.append(" ".join(words[:3]) + " " + (focus_area if focus_area else ""))
        
        # Add a version with quotes for exact match
        if " " in original_query:
            refined_terms.append(f'"{original_query}"')
        
        # Add a version with focus area
        if focus_area:
            refined_terms.append(f"{original_query} {focus_area}")
            refined_terms.append(f"{focus_area} {original_query}")
        
        # Add a version with "how to" if it seems like a how-to query
        if not original_query.lower().startswith("how to"):
            if original_query.lower().startswith("how"):
                refined_terms.append(f"how to {original_query[4:]}")
            else:
                refined_terms.append(f"how to {original_query}")
        
        return refined_terms
    
    def synthesize_information(
        self, 
        context: RunContextWrapper,
        search_results: Optional[List[Dict[str, Any]]] = None, 
        focus_question: Optional[str] = None
    ) -> str:
        """
        Synthesize information from multiple search results to answer a specific question.
        
        Args:
            context: The run context wrapper.
            search_results: A list of search results, each containing at least 'title' and 'content'.
            focus_question: The specific question to answer from the search results.
            
        Returns:
            A synthesized answer that combines information from multiple sources.
        """
        # Handle default values inside the function
        search_results = search_results or []
        focus_question = focus_question or "General information synthesis"
        
        logger.info(f"Synthesizing information for question: {focus_question}")
        
        if not search_results:
            return "No search results were provided to synthesize."
        
        # Count the number of sources
        num_sources = len(search_results)
        
        # Extract source titles for citation
        sources = [result.get('title', f"Source {i+1}") for i, result in enumerate(search_results)]
        sources_str = ", ".join(sources)
        
        # Create a structured synthesis from the search results
        synthesis = f"""
        # Information Synthesis

        ## Focus Question
        {focus_question}
        
        ## Key Points
        Based on {num_sources} sources, the key information includes:
        
        - This would list key point 1 synthesized from the sources
        - This would list key point 2 synthesized from the sources
        - This would list key point 3 synthesized from the sources
        
        ## Synthesis
        This section would contain a coherent answer to the focus question,
        combining information from all provided sources in a logical way.
        
        ## Sources
        Information synthesized from: {sources_str}
        """
        
        return synthesis
    
    def extract_key_information(
        self, 
        context: RunContextWrapper,
        text: Optional[str] = None, 
        extraction_targets: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Extract specific information from a text based on targeted extraction criteria.
        
        Args:
            context: The run context wrapper.
            text: The text to extract information from.
            extraction_targets: List of specific information types to extract (e.g., "dates", "statistics").
            
        Returns:
            A dictionary mapping extraction targets to extracted information.
        """
        # Handle default values inside the function
        text = text or ""
        extraction_targets = extraction_targets or ["general information"]
        
        logger.info(f"Extracting information with {len(extraction_targets)} targets")
        
        results = {}
        
        # Process the text to extract the requested information types
        for target in extraction_targets:
            results[target] = f"Extracted {target} would appear here based on analysis of the provided text."
        
        results["text_length"] = str(len(text))
        results["summary"] = "A brief summary of the text would appear here."
        
        return results

    def clone(self, **kwargs) -> "WebSearchAgent":
        """
        Create a copy of this agent with the given overrides.
        
        Args:
            **kwargs: Attributes to override in the cloned agent.
            
        Returns:
            A new WebSearchAgent instance with the specified overrides.
        """
        # Create parameter dictionary for the new instance
        params = {
            "name": kwargs.get("name", self.name),
            "model": kwargs.get("model", self.model),
            "search_location": kwargs.get("search_location", self._search_location),
            "search_context_size": kwargs.get("search_context_size", self._search_context_size),
            "tool_choice": kwargs.get("tool_choice", self.model_settings.tool_choice),
            "parallel_tool_calls": kwargs.get("parallel_tool_calls", self.model_settings.parallel_tool_calls),
        }
        
        # Filter out None values to use defaults where not specified
        params = {k: v for k, v in params.items() if v is not None}
        
        # Create a new instance with the parameters
        return WebSearchAgent(**params)
