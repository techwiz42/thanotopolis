from typing import Dict, Any, Optional, List, Union
import logging
import json
from agents import Agent, WebSearchTool, function_tool, ModelSettings, RunContextWrapper
from agents.run_context import RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class RegulatoryAgent(BaseAgent):
    """
    RegulatoryAgent is a specialized agent that can discover and analyze regulations.
    
    This agent specializes in finding relevant federal, state, and local regulations and
    interpreting them in the context of a user's activities or questions.
    """

    def __init__(
        self,
        name: str = "Regulatory",
        search_location: Optional[str] = None,
        search_context_size: Optional[str] = None,
        tool_choice: Optional[str] = "auto",
        parallel_tool_calls: bool = True,
        **kwargs
    ):
        """
        Initialize a RegulatoryAgent with web search and analysis capabilities.
        
        Args:
            name: The name of the agent. Defaults to "Regulatory Assistant".
            search_location: Optional location for localized search results. 
                            Format should be "[City], [Country]" (e.g., "San Francisco, USA").
            search_context_size: The amount of search context to use. Options are
                                "low", "medium", or "high". Defaults to "medium".
            tool_choice: The tool choice strategy to use. Defaults to "auto".
            parallel_tool_calls: Whether to allow the agent to call multiple tools in parallel.
            **kwargs: Additional arguments to pass to the BaseAgent constructor.
        """
        # Define the regulatory assistant instructions
        regulatory_instructions = """You are a regulatory research and analysis assistant that helps discover and interpret relevant regulations. Your role is to:

1. DISCOVER REGULATIONS
- Search for relevant federal, state, and local regulations based on user queries
- Find authoritative regulatory information from government sources
- Identify applicable laws, codes, standards, and compliance requirements
- Locate recent regulatory changes and updates

2. RESEARCH BEST PRACTICES
- Use specific search terms focused on regulations and compliance
- Break down complex regulatory questions into searchable components
- Search across multiple jurisdictions when appropriate
- Use follow-up searches to find interpretations of complex regulations
- Search for the most recent regulatory information when timeliness matters

3. ANALYZE REGULATIONS
- Interpret how regulations might apply to specific situations
- Explain regulatory requirements in clear, accessible language
- Identify potential compliance issues or considerations
- Outline regulatory processes and requirements
- Provide regulatory context to help with decision-making

4. RESPONSE GUIDELINES
- Always cite your regulatory sources with proper attribution
- Indicate when regulatory information couldn't be found
- Provide balanced perspectives on regulatory interpretation when appropriate
- Organize information in a clear, readable format
- Use bullet points or numbered lists for clarity when appropriate
- Indicate when regulatory information might be time-sensitive or subject to change
- Start with a direct answer before expanding with regulatory details

5. CONTEXT AWARENESS
- Consider jurisdictional differences in regulations
- Understand what level of regulatory detail the user needs
- Adapt your search strategy based on the type of regulatory query
- Build on previous searches in the conversation

6. SEARCH LIMITATIONS
- Acknowledge when a search might not provide complete regulatory information
- Be transparent about difficulties finding certain regulatory information
- Explain when the user might need specialized legal sources beyond general web search
- Note when regulatory information is limited by jurisdiction

7. INTERPRETATION GUIDELINES
- Always include a disclaimer that your regulatory interpretations are not legal advice
- Present balanced interpretations when regulations are ambiguous
- Identify when multiple interpretations of regulations exist
- Highlight where regulations may conflict or overlap
- Present potential approaches to regulatory compliance
- Note when the user should consult a legal professional for definitive guidance

8. MANDATORY DISCLAIMER
ALWAYS include the following disclaimer at the end of your response:
"DISCLAIMER: This information is provided for general informational purposes only and should not be taken as legal advice. The information provided may not reflect the most current legal developments, and may vary by jurisdiction. Always consult with a qualified legal professional for advice on specific regulatory compliance matters."

When searching for regulations, always strive to find the most accurate, up-to-date, and relevant regulatory information available from authoritative sources."""

        # Store search configuration for later reference
        self._search_location = search_location
        # Apply default value for search_context_size
        self._search_context_size = search_context_size if search_context_size else "high"
        
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
            
        # Combine the WebSearchTool and our method functions in one list
        all_functions = [
            web_search_tool,  # Include WebSearchTool as first function
            function_tool(self.search_regulations),
            function_tool(self.analyze_regulation),
            function_tool(self.generate_compliance_guidelines),
            function_tool(self.identify_jurisdictions),
            function_tool(self.format_regulatory_analysis)
        ]
        
        # Initialize the Agent class directly
        super().__init__(
            name=name,
            model=settings.DEFAULT_AGENT_MODEL,
            instructions=regulatory_instructions,
            functions=all_functions,  # Pass all functions as tools
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            max_tokens=2048,
            **kwargs
        )


    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """
        Initialize context for the RegulatoryAgent.
        
        Args:
            context: The context wrapper object with conversation data
        """
        # Call parent implementation
        await super().init_context(context)
        
        # Add any agent-specific context initialization here
        logger.info(f"Initialized context for RegulatoryAgent")
        
    @property
    def description(self) -> str:
        """
        Get a description of this agent's capabilities.
        
        Returns:
            A string describing the agent's specialty.
        """
        return "Specialist in discovering and interpreting federal, state, and local regulations applicable to specific activities"

    def search_regulations(
        self, 
        context: RunContextWrapper, 
        activity: str,
        jurisdiction: Optional[str] = None,
        regulation_type: Optional[str] = None
    ) -> str:
        """
        Search for regulations applicable to a specific activity in a given jurisdiction.
        
        Args:
            context: The run context wrapper.
            activity: The specific activity or business area to find regulations for.
            jurisdiction: Optional jurisdiction (federal, state, city, county) to focus on.
            regulation_type: Optional type of regulation (e.g., environmental, safety, financial).
            
        Returns:
            A structured summary of the applicable regulations found.
        """
        logger.info(f"Searching regulations for activity: {activity} in jurisdiction: {jurisdiction or 'any'}")
        
        # Format a response structure for regulation search results
        jurisdiction_str = f" in {jurisdiction}" if jurisdiction else ""
        regulation_type_str = f" {regulation_type}" if regulation_type else ""
        
        response = f"""
        # Regulatory Search Results: {regulation_type_str} Regulations for {activity}{jurisdiction_str}
        
        This is a structured template that would be filled with actual regulations found via web search.
        The regulatory agent would search the web for relevant regulations and format them here.
        
        ## Jurisdiction Coverage
        - Federal regulations relevant to {activity}
        - State regulations{jurisdiction_str}
        - Local ordinances and codes{jurisdiction_str}
        
        ## Applicable Regulations
        - Regulation 1: Title and reference
        - Regulation 2: Title and reference
        - Regulation 3: Title and reference
        
        ## Key Requirements Summary
        - Key requirement 1
        - Key requirement 2
        - Key requirement 3
        """
        
        return response
    
    def analyze_regulation(
        self, 
        context: RunContextWrapper,
        regulation_text: str,
        specific_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a specific regulation text and extract key components or answer a specific question.
        
        Args:
            context: The run context wrapper.
            regulation_text: The text of the regulation to analyze.
            specific_question: Optional specific question about the regulation.
            
        Returns:
            A dictionary with structured analysis of the regulation.
        """
        logger.info(f"Analyzing regulation with specific question: {specific_question or 'None'}")
        
        # Create a structured analysis of the regulation
        analysis = {
            "summary": "A brief summary of what this regulation covers and requires",
            "key_requirements": [
                "Key requirement 1 from the regulation",
                "Key requirement 2 from the regulation",
                "Key requirement 3 from the regulation"
            ],
            "applicability": "Who/what this regulation applies to",
            "enforcement": "How this regulation is enforced",
            "penalties": "Potential penalties for non-compliance",
            "specific_answer": specific_question if specific_question else "No specific question was asked"
        }
        
        return analysis
    
    def generate_compliance_guidelines(
        self, 
        context: RunContextWrapper,
        regulation_name: str,
        activity_description: str,
        jurisdiction: Optional[str] = None
    ) -> str:
        """
        Generate practical compliance guidelines for a specific activity under a given regulation.
        
        Args:
            context: The run context wrapper.
            regulation_name: The name or reference of the regulation.
            activity_description: Description of the activity needing compliance guidance.
            jurisdiction: Optional jurisdiction specification.
            
        Returns:
            A formatted compliance guideline document.
        """
        logger.info(f"Generating compliance guidelines for {regulation_name} applied to {activity_description}")
        
        jurisdiction_str = jurisdiction if jurisdiction else "applicable jurisdictions"
        
        guidelines = f"""
        # Compliance Guidelines: {regulation_name}
        
        ## Activity: {activity_description}
        ## Jurisdiction: {jurisdiction_str}
        
        ### Compliance Requirements
        1. Requirement 1: Description and implementation steps
        2. Requirement 2: Description and implementation steps
        3. Requirement 3: Description and implementation steps
        
        ### Documentation Needed
        - Document type 1: Purpose and details
        - Document type 2: Purpose and details
        - Document type 3: Purpose and details
        
        ### Reporting Requirements
        - Reporting requirement 1: Frequency, content, submission process
        - Reporting requirement 2: Frequency, content, submission process
        
        ### Best Practices for Compliance
        - Best practice 1
        - Best practice 2
        - Best practice 3
        
        ### Common Compliance Challenges
        - Challenge 1: Potential solutions
        - Challenge 2: Potential solutions
        
        DISCLAIMER: This information is provided for general informational purposes only and should not be taken as legal advice. The information provided may not reflect the most current legal developments, and may vary by jurisdiction. Always consult with a qualified legal professional for advice on specific regulatory compliance matters.
        """
        
        return guidelines
    
    def identify_jurisdictions(
        self, 
        context: RunContextWrapper,
        activity: str,
        location: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Identify the relevant jurisdictions that might have applicable regulations for an activity.
        
        Args:
            context: The run context wrapper.
            activity: The activity or business area.
            location: Optional location information to narrow jurisdictions.
            
        Returns:
            A list of relevant jurisdictions with their regulatory scope.
        """
        logger.info(f"Identifying jurisdictions for {activity} in location: {location or 'not specified'}")
        
        # Create a structured list of jurisdictions
        jurisdictions = [
            {
                "level": "Federal",
                "name": "United States",
                "relevant_agencies": ["Agency 1", "Agency 2"],
                "regulatory_areas": ["Area 1", "Area 2"]
            }
        ]
        
        # Add state level if location provided
        if location:
            # This would parse the location to determine the state
            if "," in location:
                city, state_or_country = location.split(",", 1)
                state = state_or_country.strip()
                
                jurisdictions.append({
                    "level": "State",
                    "name": state,
                    "relevant_agencies": ["State Agency 1", "State Agency 2"],
                    "regulatory_areas": ["State Area 1", "State Area 2"]
                })
                
                jurisdictions.append({
                    "level": "Local",
                    "name": city.strip(),
                    "relevant_agencies": ["Local Agency 1", "Local Agency 2"],
                    "regulatory_areas": ["Local Area 1", "Local Area 2"]
                })
        
        return jurisdictions
    
    def format_regulatory_analysis(
        self, 
        context: RunContextWrapper,
        activity: str,
        regulations: List[str],
        interpretation: str,
        risk_level: str
    ) -> str:
        """
        Format a comprehensive regulatory analysis with proper disclaimer.
        
        Args:
            context: The run context wrapper.
            activity: The activity being analyzed.
            regulations: List of regulations that apply.
            interpretation: The regulatory interpretation.
            risk_level: Optional risk level assessment (low, medium, high).
            
        Returns:
            A formatted regulatory analysis with disclaimer.
        """
        logger.info(f"Formatting regulatory analysis for {activity} with risk level: {risk_level}")
        
        # Create a formatted regulatory analysis
        analysis = f"""
        # Regulatory Analysis: {activity}
        
        ## Applicable Regulations
        {chr(10).join(['- ' + reg for reg in regulations])}
        
        ## Regulatory Interpretation
        {interpretation}
        
        ## Compliance Risk Assessment
        Risk Level: {risk_level.upper()}
        
        ### Risk Factors
        - Risk factor 1
        - Risk factor 2
        - Risk factor 3
        
        ### Mitigation Strategies
        - Strategy 1
        - Strategy 2
        - Strategy 3
        
        ## Next Steps
        1. Step 1
        2. Step 2
        3. Step 3
        
        DISCLAIMER: This information is provided for general informational purposes only and should not be taken as legal advice. The information provided may not reflect the most current legal developments, and may vary by jurisdiction. Always consult with a qualified legal professional for advice on specific regulatory compliance matters.
        """
        
        return analysis

    def clone(self, **kwargs) -> "RegulatoryAgent":
        """
        Create a copy of this agent with the given overrides.
        
        Args:
            **kwargs: Attributes to override in the cloned agent.
            
        Returns:
            A new RegulatoryAgent instance with the specified overrides.
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
        return RegulatoryAgent(**params)

# Create the singleton instance
regulatory_agent = RegulatoryAgent()
