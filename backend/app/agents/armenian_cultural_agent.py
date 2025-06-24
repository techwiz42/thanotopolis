from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class ArmenianCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Armenian cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the ArmenianCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for ArmenianCulturalAgent")

class ArmenianCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Armenian funeral traditions, 
    Orthodox Christian practices, and diaspora community customs.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="ARMENIAN_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Armenian funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Armenian Apostolic Orthodox funeral rites and liturgy
- Traditional Armenian burial customs and cemetery practices
- 40-day memorial period (karasunk) and annual commemorations
- Traditional mourning attire and behavioral expectations
- Memorial meals and communal gathering traditions
- Incense burning and religious ceremony elements
- Traditional Armenian funeral music and hymns
- Memorial photography and family documentation

RELIGIOUS PRACTICES:
- Armenian Apostolic Church funeral liturgy and traditions
- Catholic Armenian (Mekhitarist) funeral practices
- Protestant Armenian church variations
- Traditional blessing ceremonies and prayers
- Priest involvement and religious community support
- Church memorial services and ongoing spiritual care
- Religious calendar considerations and feast day avoidances

ARMENIAN GENOCIDE & HISTORICAL TRAUMA:
- Impact of 1915 Armenian Genocide on family structures and death rituals
- Missing family members and unresolved losses from genocide
- Intergenerational trauma and its effect on mourning practices
- Memorial traditions related to genocide remembrance
- Collective memory and community healing approaches
- Survivor families and inherited trauma considerations

CULTURAL VALUES & FAMILY DYNAMICS:
- Strong extended family bonds and communal support
- Respect for elders and traditional hierarchies
- Gender roles in funeral preparations and mourning
- Community solidarity and mutual aid traditions
- Importance of family honor and social reputation
- Traditional hospitality and guest welcoming customs
- Preservation of Armenian identity and cultural continuity

DIASPORA EXPERIENCE:
- Armenian communities worldwide: Middle East, Europe, Americas
- Maintaining traditions across different host countries
- Language preservation: Eastern and Western Armenian
- Community organizations and cultural institutions
- Church as community center and cultural anchor
- Cross-border family connections and communication
- Repatriation considerations to Armenia

TRADITIONAL PRACTICES:
- Traditional Armenian foods for memorial meals
- Ritualistic elements: bread breaking, wine sharing
- Memorial charitable giving and community support
- Traditional Armenian crafts and memorial objects
- Storytelling and oral history preservation
- Community gathering spaces and social protocols
- Traditional Armenian calendar and religious observances

LANGUAGE & COMMUNICATION:
- Eastern Armenian (Republic of Armenia) vs. Western Armenian
- Classical Armenian in religious contexts
- Generational language retention and loss
- Traditional prayers and funeral terminology
- Bilingual service considerations
- Cultural expressions and sayings related to death

REGIONAL VARIATIONS:
- Lebanon Armenian community traditions
- Syrian Armenian practices and adaptations
- Iranian Armenian customs and variations
- Turkish Armenian heritage and hidden practices
- American Armenian community developments
- French Armenian community influences

MODERN ADAPTATIONS:
- Technology use for diaspora family connections
- Social media and virtual memorial practices
- Adapting traditions to non-Armenian funeral homes
- Balancing traditional and modern American practices
- Second and third generation cultural retention
- Mixed marriages and cultural integration challenges

ECONOMIC & SOCIAL CONSIDERATIONS:
- Community fundraising and mutual financial support
- Professional vs. family-led funeral arrangements
- Cost considerations for traditional elaborate ceremonies
- Employment considerations during mourning periods
- Social status and community expectations
- Armenian business networks and professional communities

HEALTHCARE & END-OF-LIFE:
- Armenian cultural attitudes toward illness and death
- Family-centered medical decision-making patterns
- Traditional views on end-of-life care and interventions
- Hospice care and family caregiving traditions
- Organ donation perspectives within religious context
- Advanced directives and family communication

CULTURAL PRESERVATION:
- Importance of maintaining Armenian traditions in diaspora
- Teaching younger generations about cultural practices
- Role of Armenian schools and cultural organizations
- Language preservation efforts and cultural transmission
- Community events and cultural celebration integration
- Archives and documentation of family histories

SPECIAL CONSIDERATIONS:
- Political sensitivities around Armenian independence and genocide recognition
- Religious calendar and fasting period considerations
- Traditional Armenian hospitality expectations
- Community reputation and social obligations
- Educational achievement emphasis and family expectations
- Professional networks and community business support

You provide culturally sensitive guidance while being aware of the deep historical trauma, strong diaspora identity, and the crucial role of the Armenian Apostolic Church in community life. Always consider generational differences, regional variations, and the importance of cultural preservation."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_orthodox_practices),
                function_tool(self.support_genocide_trauma_awareness),
                function_tool(self.assist_with_repatriation_guidance),
                function_tool(self.recommend_traditional_foods),
                function_tool(self.provide_language_support),
                function_tool(self.connect_community_resources)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=ArmenianCulturalAgentHooks()
        )
        
        self.description = "Expert in Armenian funeral traditions, Armenian Apostolic Orthodox practices, genocide trauma considerations, and diaspora community customs. Provides guidance on traditional ceremonies, religious accommodations, and culturally sensitive support for Armenian families worldwide."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        regional_origin: Optional[str] = None,
        religious_background: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Armenian funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (liturgy, karasunk, memorial meals, etc.)
            regional_origin: Armenian diaspora community origin
            religious_background: Apostolic, Catholic, Protestant, or secular
            
        Returns:
            Detailed explanation of Armenian funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Armenian traditions",
            "cultural_significance": "Historical and religious context provided",
            "diaspora_variations": "Regional diaspora community differences explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        community_involvement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Armenian cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific cultural preferences mentioned
            community_involvement: Level of Armenian community participation
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Armenian elements that can be incorporated",
            "community_participation": "Ways to involve the Armenian community",
            "practical_suggestions": "Feasible ways to honor cultural practices"
        }

    async def guide_orthodox_practices(
        self,
        context: RunContextWrapper,
        church_affiliation: Optional[str] = None,
        liturgical_requirements: Optional[str] = None,
        priest_availability: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Armenian Apostolic Orthodox funeral practices and liturgical requirements.
        
        Args:
            context: The conversation context
            church_affiliation: Specific Armenian church community
            liturgical_requirements: Specific liturgical needs or preferences
            priest_availability: Availability of Armenian clergy
            
        Returns:
            Orthodox practice guidance and liturgical information
        """
        return {
            "orthodox_guidance_provided": True,
            "liturgical_elements": "Armenian Apostolic funeral liturgy components",
            "church_connections": "Local Armenian churches and clergy contacts",
            "ritual_requirements": "Essential Orthodox practices and accommodations needed"
        }

    async def support_genocide_trauma_awareness(
        self,
        context: RunContextWrapper,
        trauma_considerations: Optional[str] = None,
        family_history: Optional[str] = None,
        generation_affected: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide trauma-informed support considering Armenian Genocide history and intergenerational trauma.
        
        Args:
            context: The conversation context
            trauma_considerations: Specific trauma-related considerations
            family_history: Family's genocide or diaspora history
            generation_affected: Survivor generation, children, grandchildren, etc.
            
        Returns:
            Trauma-informed guidance and support resources
        """
        return {
            "trauma_support_provided": True,
            "sensitive_approaches": "Trauma-informed approaches to funeral planning",
            "historical_awareness": "Genocide trauma considerations and community healing",
            "professional_resources": "Armenian-aware mental health and trauma support services"
        }

    async def assist_with_repatriation_guidance(
        self,
        context: RunContextWrapper,
        destination: Optional[str] = None,
        family_connections: Optional[str] = None,
        documentation_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on repatriating remains to Armenia or other Armenian diaspora communities.
        
        Args:
            context: The conversation context
            destination: Armenia or other diaspora community
            family_connections: Family connections in destination country
            documentation_needs: Required documentation and legal processes
            
        Returns:
            Repatriation guidance and cultural considerations
        """
        return {
            "repatriation_guidance_provided": True,
            "legal_requirements": "Documentation and legal processes by destination",
            "cultural_considerations": "Traditional practices for international arrangements",
            "community_support": "Armenian diaspora organizations and assistance"
        }

    async def recommend_traditional_foods(
        self,
        context: RunContextWrapper,
        occasion_type: Optional[str] = None,
        dietary_restrictions: Optional[str] = None,
        preparation_capacity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Armenian foods appropriate for funeral gatherings and memorial meals.
        
        Args:
            context: The conversation context
            occasion_type: Wake, post-funeral meal, 40-day memorial
            dietary_restrictions: Any dietary considerations
            preparation_capacity: Family's capacity for traditional food preparation
            
        Returns:
            Traditional food recommendations and preparation guidance
        """
        return {
            "food_recommendations_provided": True,
            "traditional_dishes": "Culturally appropriate Armenian foods for the occasion",
            "preparation_methods": "Traditional preparation and cultural significance",
            "community_support": "Armenian community food preparation and catering"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_variant: Optional[str] = None,
        generation_needs: Optional[str] = None,
        liturgical_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Armenian language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_variant: Eastern Armenian, Western Armenian, or Classical Armenian
            generation_needs: Multi-generational language preferences
            liturgical_language: Religious service language requirements
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Armenian language interpretation and translation",
            "liturgical_support": "Classical Armenian liturgical language assistance",
            "cultural_communication": "Culturally appropriate Armenian communication patterns"
        }

    async def connect_community_resources(
        self,
        context: RunContextWrapper,
        location: Optional[str] = None,
        support_type: Optional[str] = None,
        urgency_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect families with Armenian community organizations and support resources.
        
        Args:
            context: The conversation context
            location: Geographic area where family is located
            support_type: Type of community support needed
            urgency_level: Urgency of assistance needed
            
        Returns:
            Community resource connections and support coordination
        """
        return {
            "community_resources_provided": True,
            "organizations": "Armenian community organizations and mutual aid groups",
            "church_support": "Armenian church communities and pastoral care",
            "cultural_institutions": "Armenian cultural centers and support networks"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

armenian_cultural_agent = ArmenianCulturalAgent()

__all__ = ["armenian_cultural_agent", "ArmenianCulturalAgent"]