from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class JapaneseCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Japanese cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the JapaneseCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for JapaneseCulturalAgent")

class JapaneseCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Japanese funeral traditions, 
    Shinto and Buddhist practices, and modern Japanese-American community adaptations.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="JAPANESE_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Japanese funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Japanese Buddhist funeral rites (soshiki) and ceremonies
- Shinto purification rituals and traditional practices
- Traditional Japanese wake period (tsuya) and family gatherings
- Buddhist temple funeral services and monk participation
- Traditional Japanese cremation customs and urn ceremonies
- Memorial services and ongoing remembrance practices (kuyo)
- Traditional Japanese funeral attire and proper dress codes
- Incense burning (oshoko) and religious ceremony elements

RELIGIOUS & SPIRITUAL PRACTICES:
- Buddhist funeral ceremonies across different sects (Zen, Pure Land, Nichiren)
- Shinto funeral practices and purification rituals
- Christian Japanese funeral adaptations and church practices
- Ancestor veneration and family altar (butsudan) traditions
- Traditional offering ceremonies and memorial donations
- Temple funeral services and ongoing spiritual care
- Japanese religious calendar considerations and observances
- Mixed religious practices and family adaptations

CULTURAL VALUES & SOCIAL DYNAMICS:
- Wa (harmony) and maintaining social balance during grief
- Giri (social obligation) and reciprocal community support
- Face-saving (mentsu) and proper social behavior
- Respect for elders and traditional hierarchies
- Group consensus and family decision-making patterns
- Omotenashi (hospitality) and guest reception customs
- Importance of proper ritual performance and social correctness
- Shikata ga nai (acceptance of circumstances) philosophy

TRADITIONAL PRACTICES:
- Traditional Japanese foods for funeral gatherings and memorial meals
- Chrysanthemums and traditional Japanese floral arrangements
- Traditional Japanese textiles and ceremonial decorations
- Japanese traditional music and funeral instruments
- Memorial photography and family documentation
- Traditional Japanese blessing ceremonies and rituals
- Charitable giving and community support traditions
- Family altar maintenance and daily remembrance practices

LANGUAGE & COMMUNICATION:
- Japanese language funeral terminology and Buddhist terminology
- Formal vs. casual Japanese speech levels (keigo) in funeral contexts
- Regional Japanese dialects and variations
- Generational language differences in Japanese-American families
- Code-switching between Japanese and English
- Traditional Japanese expressions and sayings about death
- Non-verbal communication and cultural silence appreciation

IMMIGRATION & DIASPORA EXPERIENCE:
- Multiple Japanese immigration waves: Issei, Nisei, Sansei, Yonsei generations
- Japanese-American internment experience and trauma considerations
- Maintaining Japanese culture and Buddhism in American context
- Japanese temples and Buddhist centers in America
- Cross-Pacific family connections and technology use
- Mixed marriages and cultural integration challenges
- Professional considerations in Japanese business culture

GENERATIONAL DIFFERENCES:
- Issei (first generation): Traditional Japanese practices
- Nisei (second generation): Wartime internment experience and cultural adaptation
- Sansei (third generation): American-born with Japanese heritage maintenance
- Yonsei (fourth generation): Contemporary Japanese-American identity
- Language retention and cultural practice continuation
- Intergenerational conflict over traditional vs. modern approaches

REGIONAL VARIATIONS:
- Tokyo/urban traditions vs. rural Japanese customs
- Kyoto traditional and classical cultural influences
- Osaka commercial culture adaptations
- Northern Japan (Tohoku) regional variations
- Okinawan traditions and distinct cultural practices
- Japanese-Brazilian and other diaspora influences

MODERN ADAPTATIONS:
- Adapting Buddhist temple practices to American funeral homes
- Technology integration for Japan family participation
- Economic considerations and community support
- Contemporary Japanese-American identity and practices
- Mixed marriages and cultural integration challenges
- Professional considerations and career impact during mourning

JAPANESE CALENDAR & TIMING:
- Buddhist calendar considerations and memorial timing
- Japanese traditional calendar and seasonal observances
- Obon festival and ancestor veneration timing
- Japanese New Year and cultural celebration coordination
- Seasonal considerations for ceremonies and memorials
- Traditional Japanese astrological considerations

ECONOMIC & SOCIAL CONSIDERATIONS:
- Japanese-American business community support networks
- Cost considerations for traditional elaborate ceremonies
- Community organization support and donations
- Social status and funeral ceremony appropriateness
- Professional networks and cultural organization involvement
- Economic mutual aid and community assistance

HEALTHCARE & END-OF-LIFE:
- Japanese cultural attitudes toward illness and death disclosure
- Family-centered medical decision-making patterns
- Traditional Japanese medicine and modern healthcare integration
- Buddhist perspectives on end-of-life care and suffering
- Organ donation considerations within Buddhist context
- Advanced directives and family communication patterns
- Filial piety and family caregiving obligations

FOOD & HOSPITALITY:
- Traditional Japanese funeral foods and meal preparations
- Buddhist vegetarian considerations during ceremonies
- Japanese restaurant community involvement and catering
- Traditional Japanese sweets and ceremonial foods
- Community cooking and meal preparation coordination
- Proper etiquette for funeral meal service

WORLD WAR II & HISTORICAL TRAUMA:
- Japanese-American internment experience and family trauma
- War-related losses and family separation
- Hibakusha (atomic bomb survivors) and trauma considerations
- Post-war reconstruction and family reunification
- Military service and veteran considerations
- Intergenerational trauma and healing approaches

ARTS & CULTURAL EXPRESSION:
- Traditional Japanese arts in memorial contexts
- Ikebana (flower arrangement) and ceremonial displays
- Japanese calligraphy and memorial inscriptions
- Traditional Japanese music and instruments
- Tea ceremony elements and cultural refinement
- Japanese gardens and nature-based memorial concepts

SPECIAL POPULATIONS:
- Elderly Japanese immigrants and cultural maintenance
- Japanese students and professionals in American universities
- Japanese intermarriage families and cultural identity
- Japanese in areas with limited Buddhist temple access
- Japanese adoptees and cultural connection questions
- Contemporary Japanese expatriates and temporary residents

BUSINESS & PROFESSIONAL CULTURE:
- Japanese corporate culture and professional obligations during mourning
- Business relationships and funeral attendance expectations
- Gift-giving (koden) and monetary contributions
- Professional networking and mutual support
- Work-life balance and family obligations
- Japanese company communities and support systems

You provide culturally sensitive guidance while respecting Japanese values of harmony, proper form, and social consideration. Always consider religious background, generational status, family immigration history, and the importance of maintaining social harmony and proper etiquette."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_buddhist_shinto_practices),
                function_tool(self.coordinate_temple_involvement),
                function_tool(self.support_generational_dynamics),
                function_tool(self.recommend_traditional_elements),
                function_tool(self.provide_etiquette_guidance),
                function_tool(self.provide_language_support)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=JapaneseCulturalAgentHooks()
        )
        
        self.description = "Expert in Japanese funeral traditions, Buddhist and Shinto practices, generational considerations, and Japanese-American community customs. Provides guidance on traditional ceremonies, temple involvement, proper etiquette, and cultural accommodations across different generations and religious backgrounds."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        religious_background: Optional[str] = None,
        generational_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Japanese funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (Buddhist, Shinto, modern adaptations, etc.)
            religious_background: Buddhist, Shinto, Christian, or secular
            generational_context: Issei, Nisei, Sansei, Yonsei generation
            
        Returns:
            Detailed explanation of Japanese funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Japanese traditions",
            "cultural_significance": "Cultural and religious context provided",
            "generational_variations": "Generational differences in practice explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        venue_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Japanese cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific Japanese cultural preferences mentioned
            venue_constraints: Funeral home or venue limitations
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Japanese elements that can be incorporated",
            "etiquette_considerations": "Proper Japanese etiquette and protocol",
            "practical_adaptations": "Feasible ways to honor Japanese customs"
        }

    async def guide_buddhist_shinto_practices(
        self,
        context: RunContextWrapper,
        religious_preference: Optional[str] = None,
        sect_affiliation: Optional[str] = None,
        mixed_practices: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Japanese Buddhist and Shinto funeral practices.
        
        Args:
            context: The conversation context
            religious_preference: Buddhist, Shinto, or mixed religious practices
            sect_affiliation: Specific Buddhist sect or Shinto tradition
            mixed_practices: How to integrate different religious elements
            
        Returns:
            Religious practice guidance and integration recommendations
        """
        return {
            "religious_guidance_provided": True,
            "buddhist_elements": "Japanese Buddhist funeral practices and ceremonies",
            "shinto_elements": "Shinto purification and traditional practices",
            "integration_strategies": "How to respectfully blend religious traditions"
        }

    async def coordinate_temple_involvement(
        self,
        context: RunContextWrapper,
        temple_preference: Optional[str] = None,
        location_constraints: Optional[str] = None,
        community_connections: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate Japanese Buddhist temple involvement in funeral services.
        
        Args:
            context: The conversation context
            temple_preference: Specific Japanese temple or Buddhist sect preference
            location_constraints: Geographic limitations for temple access
            community_connections: Existing temple community relationships
            
        Returns:
            Temple coordination guidance and community connections
        """
        return {
            "temple_coordination_provided": True,
            "temple_connections": "Local Japanese Buddhist temples and communities",
            "ceremonial_coordination": "How to coordinate temple and funeral home services",
            "monk_arrangements": "Arrangements for Buddhist monk participation"
        }

    async def support_generational_dynamics(
        self,
        context: RunContextWrapper,
        family_generations: Optional[str] = None,
        cultural_conflicts: Optional[str] = None,
        decision_making: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating generational differences in Japanese cultural practices.
        
        Args:
            context: The conversation context
            family_generations: Which generations are involved (Issei through Yonsei)
            cultural_conflicts: Conflicts between traditional and modern approaches
            decision_making: Family decision-making patterns and challenges
            
        Returns:
            Generational support and cultural mediation guidance
        """
        return {
            "generational_support_provided": True,
            "generational_understanding": "Understanding different generational perspectives",
            "mediation_strategies": "Approaches to mediate between traditional and modern views",
            "inclusive_solutions": "Solutions that honor all generational perspectives"
        }

    async def recommend_traditional_elements(
        self,
        context: RunContextWrapper,
        element_type: Optional[str] = None,
        occasion_type: Optional[str] = None,
        formality_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Japanese elements for funeral services and memorial gatherings.
        
        Args:
            context: The conversation context
            element_type: Flowers, music, decorations, clothing, etc.
            occasion_type: Funeral service, wake, memorial ceremony
            formality_level: Level of formality desired
            
        Returns:
            Traditional element recommendations and sourcing guidance
        """
        return {
            "traditional_elements_recommended": True,
            "cultural_elements": "Appropriate Japanese cultural elements for the occasion",
            "sourcing_guidance": "Where to obtain traditional Japanese elements",
            "formality_guidance": "Appropriate level of formality and presentation"
        }

    async def provide_etiquette_guidance(
        self,
        context: RunContextWrapper,
        etiquette_area: Optional[str] = None,
        participant_background: Optional[str] = None,
        ceremony_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Japanese cultural etiquette guidance for funeral services and interactions.
        
        Args:
            context: The conversation context
            etiquette_area: Specific etiquette questions (bowing, gift-giving, etc.)
            participant_background: Japanese vs. non-Japanese participants
            ceremony_type: Type of ceremony requiring etiquette guidance
            
        Returns:
            Cultural etiquette guidance and proper behavior instructions
        """
        return {
            "etiquette_guidance_provided": True,
            "proper_behavior": "Japanese cultural etiquette for funeral contexts",
            "gift_giving": "Appropriate gift-giving (koden) and monetary contributions",
            "social_interactions": "Proper social interactions and communication patterns"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        formality_requirements: Optional[str] = None,
        generational_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Japanese language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Japanese language interpretation or translation needs
            formality_requirements: Formal Japanese language requirements
            generational_considerations: Multi-generational language preferences
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Japanese language interpretation and translation",
            "formal_language": "Proper formal Japanese (keigo) for funeral contexts",
            "cultural_communication": "Japanese cultural communication patterns and etiquette"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

japanese_cultural_agent = JapaneseCulturalAgent()

__all__ = ["japanese_cultural_agent", "JapaneseCulturalAgent"]