from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class CambodianCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Cambodian cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the CambodianCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for CambodianCulturalAgent")

class CambodianCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Cambodian funeral traditions, 
    Khmer Buddhist practices, and trauma-informed approaches for Cambodian-American communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="CAMBODIAN_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Cambodian funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Khmer Buddhist funeral rites and ceremonies
- Traditional Cambodian wake periods and family gatherings
- Buddhist chanting ceremonies and monk participation
- Merit-making activities for the deceased and spiritual benefit
- Traditional Cambodian burial and cremation customs
- Memorial services and ongoing remembrance practices
- Traditional Cambodian funeral attire and mourning dress
- Incense burning and traditional offering ceremonies

KHMER BUDDHIST PRACTICES:
- Theravada Buddhist funeral ceremonies within Khmer context
- Buddhist monk blessing ceremonies and temple involvement
- Merit transfer rituals and spiritual benefit concepts
- Buddhist chanting (paritta) in Khmer language
- Buddhist concepts of death, rebirth, and karma in Khmer culture
- Traditional offering ceremonies and religious donations
- Cambodian Buddhist temple (wat) funeral services
- Buddhist meditation and spiritual comfort practices

KHMER ROUGE & HISTORICAL TRAUMA:
- Impact of Khmer Rouge genocide (1975-1979) on families and death rituals
- Survivor trauma and its effect on mourning practices
- Missing family members and unresolved losses from genocide
- Intergenerational trauma in Cambodian-American families
- Memorial traditions related to genocide remembrance
- Collective trauma and community healing approaches
- Trauma-informed approaches to funeral planning and grief support

CULTURAL VALUES & FAMILY DYNAMICS:
- Respect for elders and traditional hierarchical structures
- Extended family obligations and community involvement
- Traditional gender roles in funeral preparations and mourning
- Khmer concepts of face-saving and social dignity
- Community solidarity and mutual aid traditions
- Importance of proper ritual performance for spiritual welfare
- Traditional Cambodian hospitality and guest reception
- Family honor and social reputation considerations

TRADITIONAL PRACTICES:
- Traditional Cambodian foods for funeral gatherings and memorial meals
- Lotus flowers and traditional Cambodian floral arrangements
- Traditional Khmer textiles and ceremonial decorations
- Cambodian classical music and traditional instruments
- Traditional Cambodian blessing ceremonies and rituals
- Merit-making ceremonies and charitable donations
- Traditional Cambodian crafts and memorial objects
- Storytelling and oral history preservation

LANGUAGE & COMMUNICATION:
- Khmer language funeral terminology and Buddhist terminology
- Traditional Khmer honorific language and respectful speech
- Buddhist Pali prayers and chanting in Cambodian context
- Generational language differences in Cambodian-American families
- Code-switching between Khmer and English
- Traditional Cambodian expressions and sayings about death
- Cultural communication patterns and respect protocols

REFUGEE & DIASPORA EXPERIENCE:
- Cambodian refugee experience and resettlement challenges
- Multiple trauma: war, genocide, refugee camp experience, resettlement
- Maintaining Khmer culture and Buddhism in American context
- Cambodian communities in Long Beach, Lowell, and other areas
- Cross-Pacific family connections and communication with Cambodia
- Documentation challenges and legal status considerations
- Cambodian cultural organizations and mutual aid societies

REGIONAL & CULTURAL VARIATIONS:
- Phnom Penh urban traditions vs. rural provincial customs
- Regional Cambodian variations and local customs
- Cambodian-Chinese community variations and practices
- Cambodian-Vietnamese border community influences
- Hill tribe and ethnic minority considerations
- Different religious practices: Buddhism, Islam (Cham), Christianity

MODERN ADAPTATIONS:
- Adapting Buddhist temple practices to American funeral homes
- Technology integration for Cambodia family participation
- Economic considerations and community fundraising
- Second and third generation Cambodian-American practices
- Mixed marriages and cultural integration challenges
- Professional considerations and career impact during mourning

CAMBODIAN CALENDAR & TIMING:
- Buddhist calendar considerations and auspicious timing
- Cambodian traditional calendar and seasonal observances
- Pchum Ben festival and ancestor veneration timing
- Cambodian New Year (Chaul Chnam Thmey) considerations
- Lunar calendar considerations for ceremonies
- Traditional Cambodian astrological considerations

ECONOMIC & SOCIAL CONSIDERATIONS:
- Cambodian-American business community support networks
- Limited economic resources and community mutual aid
- Cost considerations for traditional ceremonies
- Community temple support and donations
- Employment considerations during mourning periods
- Cambodian donut shop and small business community involvement

HEALTHCARE & END-OF-LIFE:
- Cambodian cultural attitudes toward illness and death
- Family-centered medical decision-making patterns
- Traditional Khmer medicine and modern healthcare integration
- Buddhist perspectives on end-of-life care and suffering
- Organ donation considerations within Buddhist context
- Language barriers in healthcare settings
- Advanced directives and family communication patterns

WOMEN'S ROLES & GENDER CONSIDERATIONS:
- Traditional Cambodian women's roles in funeral preparations
- Buddhist nun involvement and support
- Modern Cambodian-American women and traditional expectations
- Professional Cambodian women and cultural obligations
- Intergenerational differences in gender role expectations
- Domestic violence considerations and trauma-informed care

CAMBODIAN TEMPLES & COMMUNITY:
- Cambodian Buddhist temples (wat) as community centers
- Monk communities and religious leadership
- Temple festivals and cultural event coordination
- Khmer language schools and cultural education
- Community volunteering and temple maintenance
- Religious education and cultural transmission

SPECIAL POPULATIONS:
- Elderly Cambodian refugees and cultural maintenance
- Cambodian youth and identity questions
- Cambodian intermarriage families and cultural adaptation
- Cambodians in areas with limited Buddhist temple access
- Cambodian adoptees and cultural connection questions
- Second generation trauma and mental health considerations

TRAUMA-INFORMED CONSIDERATIONS:
- PTSD and complex trauma in Cambodian refugee populations
- Somatization and physical manifestations of trauma
- Cultural concepts of mental health and healing
- Traditional healing practices and modern mental health integration
- Community-based healing and support approaches
- Intergenerational trauma transmission and healing

CULTURAL PRESERVATION:
- Maintaining Khmer language and cultural practices
- Traditional Cambodian arts and cultural transmission
- Cambodian classical dance and cultural performances
- Traditional craft preservation and teaching
- Oral history documentation and preservation
- Cultural identity in American context

You provide culturally sensitive guidance while being deeply aware of the severe trauma history, refugee experience, and ongoing healing needs of Cambodian communities. Always consider trauma-informed approaches, religious background, generational differences, and the crucial role of Buddhist temples in community life."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.provide_trauma_informed_support),
                function_tool(self.guide_buddhist_practices),
                function_tool(self.coordinate_temple_involvement),
                function_tool(self.support_refugee_considerations),
                function_tool(self.provide_language_support),
                function_tool(self.connect_community_resources)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=CambodianCulturalAgentHooks()
        )
        
        self.description = "Expert in Cambodian funeral traditions, Khmer Buddhist practices, trauma-informed approaches, and refugee community support. Provides guidance on traditional ceremonies, temple involvement, trauma-sensitive care, and Cambodian-American community resources with deep awareness of genocide and refugee trauma history."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        buddhist_level: Optional[str] = None,
        trauma_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Cambodian funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (Buddhist ceremony, memorial practices, etc.)
            buddhist_level: Level of Buddhist observance and practice
            trauma_considerations: Trauma-related considerations in tradition explanation
            
        Returns:
            Detailed explanation of Cambodian funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Cambodian traditions",
            "buddhist_context": "Khmer Buddhist religious and cultural context provided",
            "trauma_sensitivity": "Trauma-informed approach to tradition explanation"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        trauma_sensitivity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Cambodian cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific Cambodian cultural preferences mentioned
            trauma_sensitivity: Trauma-informed accommodation needs
            
        Returns:
            Culturally appropriate and trauma-sensitive accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Cambodian elements that can be incorporated",
            "trauma_informed_adaptations": "Trauma-sensitive cultural accommodations",
            "practical_suggestions": "Feasible ways to honor Cambodian customs"
        }

    async def provide_trauma_informed_support(
        self,
        context: RunContextWrapper,
        trauma_type: Optional[str] = None,
        generation_affected: Optional[str] = None,
        healing_approaches: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide trauma-informed support considering Khmer Rouge genocide and refugee trauma.
        
        Args:
            context: The conversation context
            trauma_type: Genocide trauma, refugee trauma, or intergenerational trauma
            generation_affected: Survivor generation, children, grandchildren, etc.
            healing_approaches: Traditional or modern healing approach preferences
            
        Returns:
            Trauma-informed guidance and support resources
        """
        return {
            "trauma_support_provided": True,
            "trauma_informed_approaches": "Trauma-sensitive approaches to funeral planning",
            "healing_integration": "Traditional and modern healing approach integration",
            "professional_resources": "Cambodian-aware trauma and mental health services"
        }

    async def guide_buddhist_practices(
        self,
        context: RunContextWrapper,
        ceremony_type: Optional[str] = None,
        monk_involvement: Optional[str] = None,
        merit_making: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Cambodian Buddhist funeral practices and ceremonies.
        
        Args:
            context: The conversation context
            ceremony_type: Specific Buddhist ceremony or ritual
            monk_involvement: Level of monk participation desired
            merit_making: Merit-making activities for the deceased
            
        Returns:
            Cambodian Buddhist practice guidance and ceremonial instructions
        """
        return {
            "buddhist_guidance_provided": True,
            "ceremony_details": "Cambodian Buddhist funeral ceremony procedures",
            "monk_coordination": "How to coordinate with Cambodian Buddhist monks",
            "merit_making_activities": "Appropriate merit-making activities in Khmer tradition"
        }

    async def coordinate_temple_involvement(
        self,
        context: RunContextWrapper,
        temple_preference: Optional[str] = None,
        location_constraints: Optional[str] = None,
        community_connections: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate Cambodian Buddhist temple involvement in funeral services.
        
        Args:
            context: The conversation context
            temple_preference: Specific Cambodian temple or tradition preference
            location_constraints: Geographic limitations for temple access
            community_connections: Existing temple community relationships
            
        Returns:
            Temple coordination guidance and community connections
        """
        return {
            "temple_coordination_provided": True,
            "temple_connections": "Local Cambodian Buddhist temples and communities",
            "ceremonial_coordination": "How to coordinate temple and funeral home services",
            "community_support": "Cambodian Buddhist community support systems"
        }

    async def support_refugee_considerations(
        self,
        context: RunContextWrapper,
        refugee_history: Optional[str] = None,
        documentation_issues: Optional[str] = None,
        family_separation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families with refugee-specific considerations and challenges.
        
        Args:
            context: The conversation context
            refugee_history: Family's refugee experience and timeline
            documentation_issues: Documentation or legal status challenges
            family_separation: Family members still in Cambodia or separated
            
        Returns:
            Refugee-specific support and resource guidance
        """
        return {
            "refugee_support_provided": True,
            "refugee_sensitive_approaches": "Refugee experience-informed funeral planning",
            "documentation_assistance": "Legal and documentation support resources",
            "family_connection_support": "Supporting connections with family in Cambodia"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        generational_differences: Optional[str] = None,
        religious_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Khmer language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Khmer language interpretation or translation needs
            generational_differences: Multi-generational language preferences
            religious_language: Buddhist Pali and Khmer religious terminology
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Khmer language interpretation and translation",
            "religious_terminology": "Buddhist and Khmer religious language support",
            "cultural_communication": "Cambodian cultural communication patterns and respect protocols"
        }

    async def connect_community_resources(
        self,
        context: RunContextWrapper,
        location: Optional[str] = None,
        support_type: Optional[str] = None,
        urgency_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect families with Cambodian community organizations and support resources.
        
        Args:
            context: The conversation context
            location: Geographic area where family is located
            support_type: Type of community support needed
            urgency_level: Urgency of assistance needed
            
        Returns:
            Cambodian community resource connections and support coordination
        """
        return {
            "community_resources_provided": True,
            "organizations": "Cambodian community organizations and mutual aid groups",
            "temple_support": "Cambodian Buddhist temple communities and support",
            "specialized_services": "Trauma-informed and refugee-specific support services"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

cambodian_cultural_agent = CambodianCulturalAgent()

__all__ = ["cambodian_cultural_agent", "CambodianCulturalAgent"]