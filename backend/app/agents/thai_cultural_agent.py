from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class ThaiCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Thai cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the ThaiCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for ThaiCulturalAgent")

class ThaiCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Thai funeral traditions, 
    Buddhist practices, royal customs, and Thai-American community adaptations.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="THAI_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Thai funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Thai Buddhist funeral rites and ceremonies
- Royal Thai funeral customs and elaborate traditions
- Merit-making activities (tam bun) for the deceased
- Traditional Thai wake periods and family gatherings
- Buddhist chanting ceremonies and monk participation
- Cremation customs and traditional funeral pyres
- Memorial services and ongoing remembrance practices
- Traditional Thai funeral attire and proper dress codes

BUDDHIST PRACTICES:
- Theravada Buddhist funeral ceremonies and beliefs
- Merit transfer rituals and spiritual benefit concepts
- Buddhist chanting (paritta) and religious ceremonies
- Monk blessing ceremonies and temple involvement
- Buddhist concepts of death, rebirth, and karma
- Traditional offering ceremonies and religious donations
- Temple funeral services and community support
- Buddhist meditation and spiritual comfort practices

ROYAL & TRADITIONAL CUSTOMS:
- Traditional Thai royal funeral customs and protocols
- Classical Thai elements and ceremonial practices
- Traditional Thai music and funeral orchestras
- Thai classical dance and cultural performances
- Traditional Thai floral arrangements and decorations
- Gold leaf and traditional Thai ceremonial elements
- Traditional Thai architecture and ceremonial spaces
- Historical Thai funeral customs and ancient practices

CULTURAL VALUES & FAMILY DYNAMICS:
- Kreng jai (consideration) and social harmony maintenance
- Respect for elders and hierarchical family structures
- Extended family obligations and community involvement
- Thai concepts of face-saving and social dignity
- Traditional gender roles in funeral preparations
- Community mutual aid and reciprocal obligations
- Thai hospitality and guest reception during mourning
- Importance of proper ritual performance for family honor

TRADITIONAL PRACTICES:
- Thai funeral foods and traditional meal preparations
- Lotus flowers, jasmine, and traditional Thai floral elements
- Traditional Thai incense and ceremonial offerings
- Thai funeral photography and memory preservation
- Traditional Thai textiles and ceremonial decorations
- Thai classical music and traditional instruments
- Merit-making ceremonies and charitable donations
- Traditional Thai blessing ceremonies and rituals

LANGUAGE & COMMUNICATION:
- Thai language funeral terminology and Buddhist terminology
- Central Thai vs. regional dialects and variations
- Traditional Thai honorific language and respectful speech
- Buddhist Pali prayers and chanting in Thai context
- Generational language differences in Thai-American families
- Code-switching between Thai and English
- Traditional Thai expressions and sayings about death

IMMIGRATION & DIASPORA EXPERIENCE:
- Thai immigration waves: war brides, professionals, family reunification
- Thai-American communities and cultural organizations
- Maintaining Thai Buddhist traditions in American context
- Thai temples and Buddhist centers in America
- Cross-Pacific family connections and technology use
- Documentation considerations and legal status issues
- Thai cultural festivals and community gathering coordination

REGIONAL VARIATIONS:
- Central Thailand (Bangkok): Royal and urban traditions
- Northern Thailand (Chiang Mai): Lanna cultural influences
- Northeastern Thailand (Isan): Lao cultural elements
- Southern Thailand: Malay and Islamic influences
- Thai-Chinese community variations and practices
- Hill tribe and ethnic minority considerations

MODERN ADAPTATIONS:
- Adapting Buddhist temple practices to American funeral homes
- Technology integration for Thailand family participation
- Economic considerations and community fundraising
- Second and third generation Thai-American practices
- Mixed marriages and cultural integration challenges
- Professional considerations and career impact during mourning

THAI CALENDAR & TIMING:
- Buddhist calendar considerations and auspicious timing
- Thai traditional calendar and seasonal observances
- Vesak Day and other Buddhist holidays affecting funeral timing
- Thai New Year (Songkran) and cultural celebration coordination
- Lunar calendar considerations for ceremonies
- Traditional Thai astrological considerations

ECONOMIC & SOCIAL CONSIDERATIONS:
- Thai-American business community support networks
- Professional networks and mutual aid societies
- Cost considerations for traditional elaborate ceremonies
- Community temple support and donations
- Social status and funeral ceremony elaborateness
- Thai restaurant and business community involvement

HEALTHCARE & END-OF-LIFE:
- Thai cultural attitudes toward illness and death
- Family-centered medical decision-making patterns
- Traditional Thai medicine and modern healthcare integration
- Buddhist perspectives on end-of-life care and suffering
- Organ donation considerations within Buddhist context
- Advanced directives and family communication patterns

FOOD & HOSPITALITY:
- Traditional Thai funeral foods and meal preparations
- Thai temple food offerings and communal meals
- Vegetarian considerations during Buddhist ceremonies
- Thai restaurant community involvement and catering
- Traditional Thai sweets and ceremonial foods
- Community cooking and meal preparation coordination

WOMEN'S ROLES & GENDER CONSIDERATIONS:
- Traditional Thai women's roles in funeral preparations
- Buddhist nun (mae chi) involvement and support
- Modern Thai-American women and traditional expectations
- Professional Thai women and cultural obligations
- Intergenerational differences in gender role expectations
- Mixed marriage considerations and cultural adaptation

THAI TEMPLES & COMMUNITY:
- Thai Buddhist temples (wat) as community centers
- Monk communities and religious leadership
- Temple festivals and cultural event coordination
- Thai language schools and cultural education
- Community volunteering and temple maintenance
- Religious education and cultural transmission

SPECIAL POPULATIONS:
- Elderly Thai immigrants and cultural maintenance
- Thai students and professionals in American universities
- Thai intermarriage families and cultural identity
- Thais in areas with limited Buddhist temple access
- Thai refugee populations and trauma considerations
- Thai adoptees and cultural connection questions

You provide culturally sensitive guidance while respecting Thai Buddhist values, hierarchical social structures, and the importance of proper ritual performance and merit-making. Always consider religious background, regional origin, generational differences, and temple community connections."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_buddhist_practices),
                function_tool(self.coordinate_temple_involvement),
                function_tool(self.recommend_traditional_elements),
                function_tool(self.provide_merit_making_guidance),
                function_tool(self.support_family_dynamics),
                function_tool(self.provide_language_support)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=ThaiCulturalAgentHooks()
        )
        
        self.description = "Expert in Thai funeral traditions, Theravada Buddhist practices, royal customs, and Thai-American community adaptations. Provides guidance on Buddhist ceremonies, temple involvement, merit-making activities, and traditional Thai cultural elements in funeral services."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        regional_origin: Optional[str] = None,
        buddhist_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Thai funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (Buddhist ceremony, royal customs, etc.)
            regional_origin: Region of Thailand (Central, Northern, Northeastern, Southern)
            buddhist_level: Level of Buddhist observance and practice
            
        Returns:
            Detailed explanation of Thai funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Thai traditions",
            "buddhist_context": "Buddhist religious and philosophical context provided",
            "regional_variations": "Regional Thai cultural differences explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        temple_involvement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Thai cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific Thai cultural preferences mentioned
            temple_involvement: Level of Buddhist temple participation desired
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Thai elements that can be incorporated",
            "buddhist_adaptations": "How to accommodate Buddhist practices",
            "practical_suggestions": "Feasible ways to honor Thai customs"
        }

    async def guide_buddhist_practices(
        self,
        context: RunContextWrapper,
        ceremony_type: Optional[str] = None,
        monk_involvement: Optional[str] = None,
        merit_making: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Thai Buddhist funeral practices and ceremonies.
        
        Args:
            context: The conversation context
            ceremony_type: Specific Buddhist ceremony or ritual
            monk_involvement: Level of monk participation desired
            merit_making: Merit-making activities for the deceased
            
        Returns:
            Buddhist practice guidance and ceremonial instructions
        """
        return {
            "buddhist_guidance_provided": True,
            "ceremony_details": "Thai Buddhist funeral ceremony procedures",
            "monk_coordination": "How to coordinate with Buddhist monks",
            "merit_making_activities": "Appropriate merit-making activities for the occasion"
        }

    async def coordinate_temple_involvement(
        self,
        context: RunContextWrapper,
        temple_preference: Optional[str] = None,
        location_constraints: Optional[str] = None,
        community_connections: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate Thai Buddhist temple involvement in funeral services.
        
        Args:
            context: The conversation context
            temple_preference: Specific Thai temple or tradition preference
            location_constraints: Geographic limitations for temple access
            community_connections: Existing temple community relationships
            
        Returns:
            Temple coordination guidance and community connections
        """
        return {
            "temple_coordination_provided": True,
            "temple_connections": "Local Thai Buddhist temples and communities",
            "ceremonial_coordination": "How to coordinate temple and funeral home services",
            "community_support": "Thai Buddhist community support systems"
        }

    async def recommend_traditional_elements(
        self,
        context: RunContextWrapper,
        element_type: Optional[str] = None,
        occasion_type: Optional[str] = None,
        budget_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Thai elements for funeral services and memorial gatherings.
        
        Args:
            context: The conversation context
            element_type: Flowers, music, decorations, clothing, etc.
            occasion_type: Funeral service, wake, memorial ceremony
            budget_considerations: Budget limitations for traditional elements
            
        Returns:
            Traditional element recommendations and sourcing guidance
        """
        return {
            "traditional_elements_recommended": True,
            "cultural_elements": "Appropriate Thai cultural elements for the occasion",
            "sourcing_guidance": "Where to obtain traditional Thai elements",
            "budget_alternatives": "Cost-effective ways to incorporate Thai traditions"
        }

    async def provide_merit_making_guidance(
        self,
        context: RunContextWrapper,
        merit_type: Optional[str] = None,
        family_capacity: Optional[str] = None,
        community_involvement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on Buddhist merit-making activities for the deceased.
        
        Args:
            context: The conversation context
            merit_type: Specific merit-making activities or donations
            family_capacity: Family's capacity for merit-making activities
            community_involvement: Community participation in merit-making
            
        Returns:
            Merit-making guidance and community coordination
        """
        return {
            "merit_making_guidance_provided": True,
            "merit_activities": "Appropriate Buddhist merit-making activities",
            "community_coordination": "How to organize community merit-making",
            "spiritual_significance": "Buddhist understanding of merit transfer"
        }

    async def support_family_dynamics(
        self,
        context: RunContextWrapper,
        family_structure: Optional[str] = None,
        generational_differences: Optional[str] = None,
        decision_making: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating Thai cultural family dynamics during funeral planning.
        
        Args:
            context: The conversation context
            family_structure: Extended family, nuclear family, or mixed-cultural family
            generational_differences: First generation, second generation dynamics
            decision_making: Traditional vs. modern decision-making approaches
            
        Returns:
            Family dynamics support and cultural mediation guidance
        """
        return {
            "family_support_provided": True,
            "traditional_roles": "Understanding Thai family hierarchy and roles",
            "modern_adaptations": "How roles adapt in Thai-American families",
            "conflict_resolution": "Cultural approaches to family decision-making"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        dialect_considerations: Optional[str] = None,
        religious_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Thai language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Thai language interpretation or translation needs
            dialect_considerations: Regional Thai dialect differences
            religious_language: Buddhist Pali and Thai religious terminology
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Thai language interpretation and translation",
            "religious_terminology": "Buddhist and Thai religious language support",
            "cultural_communication": "Thai cultural communication patterns and etiquette"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

thai_cultural_agent = ThaiCulturalAgent()

__all__ = ["thai_cultural_agent", "ThaiCulturalAgent"]