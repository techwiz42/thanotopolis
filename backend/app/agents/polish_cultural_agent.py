from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class PolishCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Polish cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the PolishCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for PolishCulturalAgent")

class PolishCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Polish funeral traditions, 
    Catholic practices, and immigration history within Polish-American communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="POLISH_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Polish funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Polish Catholic funeral rites and liturgy
- Traditional Polish burial customs and cemetery practices
- Polish funeral Mass traditions and church involvement
- Traditional Polish wake (czuwanie) and family gatherings
- Polish memorial periods and anniversary commemorations
- Traditional Polish funeral attire and mourning customs
- Memorial meals and traditional Polish hospitality
- Traditional Polish funeral music and hymns

RELIGIOUS PRACTICES:
- Roman Catholic funeral liturgy within Polish tradition
- Polish Catholic parish involvement and community support
- Traditional blessing ceremonies and religious prayers
- Polish religious calendar considerations and observances
- Church memorial services and ongoing spiritual care
- Polish Catholic saints and devotional practices
- Traditional Polish religious music and hymns
- Priest involvement and Polish-speaking clergy

IMMIGRATION WAVES & HISTORICAL EXPERIENCE:
- Multiple Polish immigration waves: 1880s-1920s, post-WWII, Solidarity era (1980s), recent EU migration
- Maintaining Polish culture and Catholicism in American context
- Polish-American communities and parish establishment
- Historical persecution and resilience traditions
- World War II impact and family losses
- Communist era suppression and religious resistance
- Solidarity movement and political freedom struggles

CULTURAL VALUES & FAMILY DYNAMICS:
- Strong Polish Catholic faith and religious observance
- Extended family bonds and communal support
- Respect for elders and traditional hierarchies
- Traditional gender roles in funeral preparations and mourning
- Polish concepts of honor, dignity, and family reputation
- Community solidarity and mutual aid traditions
- Importance of maintaining Polish language and culture
- Traditional Polish hospitality and guest reception customs

TRADITIONAL PRACTICES:
- Traditional Polish funeral foods and memorial meal preparations
- Polish traditional decorations and ceremonial elements
- Traditional Polish textiles and cultural items
- Polish folk traditions and cultural expressions
- Traditional Polish blessing ceremonies and rituals
- Community charitable giving and mutual support
- Traditional Polish crafts and memorial objects
- Storytelling and family history preservation

LANGUAGE & COMMUNICATION:
- Polish language funeral terminology and Catholic terminology
- Latin prayers in Polish Catholic context
- Regional Polish dialects and variations
- Generational language differences in Polish-American families
- Code-switching between Polish and English
- Traditional Polish expressions and sayings about death
- Formal vs. informal Polish speech patterns in mourning contexts

REGIONAL VARIATIONS:
- Greater Poland (Wielkopolska): Traditional heartland customs
- Lesser Poland (Malopolska): Krakow region traditions
- Silesia: Industrial region adaptations and German influences
- Mazovia: Warsaw region and central Polish customs
- Pomerania and northern regions: Baltic coastal traditions
- Mountain regions (Podhale): Highland customs and traditions

MODERN ADAPTATIONS:
- Adapting Catholic practices to American funeral homes
- Technology integration for Poland family participation
- Economic considerations and community fundraising
- Second through fifth generation Polish-American practices
- Mixed marriages and cultural integration challenges
- Professional considerations and career impact during mourning

POLISH CALENDAR & TIMING:
- Catholic calendar considerations and feast day timing
- Polish traditional calendar and seasonal observances
- All Saints' Day (Dzień Wszystkich Świętych) and cemetery traditions
- Christmas and Easter timing and cultural celebrations
- Polish national holidays and cultural commemorations
- Saint name days and traditional Polish celebrations

ECONOMIC & SOCIAL CONSIDERATIONS:
- Polish-American business community support networks
- Polonia organizations and mutual aid societies
- Cost considerations for traditional Catholic elaborate ceremonies
- Community organization support and donations
- Social status and funeral ceremony appropriateness
- Polish cultural organization involvement

HEALTHCARE & END-OF-LIFE:
- Polish cultural attitudes toward illness and death
- Family-centered medical decision-making patterns
- Traditional Polish folk medicine and modern healthcare integration
- Catholic perspectives on end-of-life care and suffering
- Organ donation considerations within Catholic context
- Advanced directives and family communication patterns
- Polish concepts of suffering and redemption

WOMEN'S ROLES & GENDER CONSIDERATIONS:
- Traditional Polish women's roles in funeral preparations
- Catholic traditions regarding women's participation
- Polish women's organizations and community support
- Professional Polish women and traditional expectations
- Intergenerational differences in gender role expectations
- Mixed marriage considerations and cultural adaptation

POLISH PARISHES & COMMUNITY:
- Polish Catholic parishes and community centers
- Polish-speaking priests and religious leadership
- Parish festivals and cultural event coordination
- Polish language schools and cultural education
- Community volunteering and parish maintenance
- Religious and cultural education transmission

SPECIAL POPULATIONS:
- Elderly Polish immigrants and cultural maintenance
- Recent Polish immigrants and EU migration
- Polish students and professionals in American universities
- Poles in areas with limited Polish parish or community access
- Polish intermarriage families and cultural adaptation
- Second through fifth generation Polish-Americans

FOOD & HOSPITALITY:
- Traditional Polish funeral foods and meal preparations (pierogi, kielbasa, etc.)
- Polish Catholic fasting considerations during Lent
- Polish restaurant and bakery community involvement
- Traditional Polish beverages and ceremonial foods
- Community cooking and meal preparation coordination
- Polish feast traditions and ceremonial meals

CULTURAL PRESERVATION:
- Maintaining Polish language and Catholic traditions
- Traditional Polish arts and cultural transmission
- Polish folk music and cultural performances
- Traditional craft preservation and teaching (wycinanki, pisanki)
- Polish literature and cultural education
- Community cultural events and tradition maintenance

HISTORICAL TRAUMA & RESILIENCE:
- World War II occupation and Holocaust impact
- Communist era suppression and religious persecution
- Solidarity movement and struggle for freedom
- Political persecution and refugee experiences
- Intergenerational trauma and resilience patterns
- Cultural survival and resistance traditions

POLONIA ORGANIZATIONS:
- Polish-American organizations and mutual aid societies
- Polish American Congress and advocacy groups
- Polish cultural centers and community organizations
- Polish veterans organizations and military honors
- Professional Polish-American associations
- Polish fraternal benefit societies

INTERFAITH & INTERCULTURAL CONSIDERATIONS:
- Polish Catholic and other Christian denomination interactions
- Polish Jewish heritage and interfaith families
- Mixed ethnic marriages and cultural integration
- Balancing Polish and American cultural practices
- Educational and professional achievement expectations
- Community relationships with other ethnic Catholic communities

CURRENT CONNECTIONS:
- Modern Poland connections and family visits
- EU membership impact on Polish-American identity
- Technology use for Poland family connections
- Contemporary Polish culture and traditions
- Polish language maintenance across generations
- Polish media and cultural consumption in America

You provide culturally sensitive guidance while being aware of the strong Catholic faith, rich cultural traditions, and complex immigration history that characterizes Polish-American communities. Always consider religious background, immigration generation, regional origin, and the importance of family honor and Polish cultural preservation."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_catholic_practices),
                function_tool(self.coordinate_parish_involvement),
                function_tool(self.support_generational_dynamics),
                function_tool(self.recommend_traditional_elements),
                function_tool(self.provide_language_support),
                function_tool(self.connect_polonia_resources)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=PolishCulturalAgentHooks()
        )
        
        self.description = "Expert in Polish funeral traditions, Catholic practices, immigration history, and Polonia community customs. Provides guidance on traditional ceremonies, parish involvement, generational considerations, and cultural preservation across different Polish-American immigration generations and regional backgrounds."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        regional_origin: Optional[str] = None,
        immigration_generation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Polish funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (Catholic rites, folk customs, etc.)
            regional_origin: Region of Poland (Wielkopolska, Malopolska, Silesia, etc.)
            immigration_generation: Immigration wave or generation in America
            
        Returns:
            Detailed explanation of Polish funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Polish traditions",
            "cultural_significance": "Historical and religious context provided",
            "regional_variations": "Regional Polish cultural differences explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        catholic_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Polish cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific Polish cultural preferences mentioned
            catholic_requirements: Catholic religious requirements and considerations
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Polish elements that can be incorporated",
            "catholic_adaptations": "How to accommodate Polish Catholic practices",
            "practical_suggestions": "Feasible ways to honor Polish customs"
        }

    async def guide_catholic_practices(
        self,
        context: RunContextWrapper,
        parish_affiliation: Optional[str] = None,
        liturgical_preferences: Optional[str] = None,
        priest_availability: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Polish Catholic funeral practices and liturgical requirements.
        
        Args:
            context: The conversation context
            parish_affiliation: Specific Polish parish or Catholic community
            liturgical_preferences: Specific liturgical needs or Polish traditions
            priest_availability: Availability of Polish-speaking clergy
            
        Returns:
            Catholic practice guidance and liturgical information
        """
        return {
            "catholic_guidance_provided": True,
            "liturgical_elements": "Polish Catholic funeral liturgy components",
            "parish_connections": "Local Polish parishes and Polish-speaking clergy",
            "traditional_adaptations": "How to incorporate Polish Catholic traditions"
        }

    async def coordinate_parish_involvement(
        self,
        context: RunContextWrapper,
        parish_preference: Optional[str] = None,
        community_connections: Optional[str] = None,
        language_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate Polish parish involvement in funeral services and community support.
        
        Args:
            context: The conversation context
            parish_preference: Specific Polish parish or Catholic community preference
            community_connections: Existing parish community relationships
            language_needs: Polish language requirements for services
            
        Returns:
            Parish coordination guidance and community connections
        """
        return {
            "parish_coordination_provided": True,
            "parish_connections": "Local Polish parishes and Catholic communities",
            "community_support": "Polish parish community support systems",
            "language_coordination": "Polish-language liturgical and community services"
        }

    async def support_generational_dynamics(
        self,
        context: RunContextWrapper,
        family_generations: Optional[str] = None,
        cultural_retention: Optional[str] = None,
        language_differences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating generational differences in Polish cultural practices.
        
        Args:
            context: The conversation context
            family_generations: Which generations are involved in funeral planning
            cultural_retention: Level of Polish cultural practice across generations
            language_differences: Language preferences and abilities across generations
            
        Returns:
            Generational support and cultural integration guidance
        """
        return {
            "generational_support_provided": True,
            "generational_understanding": "Understanding different generational perspectives on Polish traditions",
            "cultural_bridge_building": "Ways to bridge generational and cultural differences",
            "inclusive_planning": "Inclusive approaches to honor all generations"
        }

    async def recommend_traditional_elements(
        self,
        context: RunContextWrapper,
        element_type: Optional[str] = None,
        occasion_type: Optional[str] = None,
        regional_preferences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Polish elements for funeral services and memorial gatherings.
        
        Args:
            context: The conversation context
            element_type: Music, food, decorations, religious items, etc.
            occasion_type: Funeral Mass, wake, memorial dinner
            regional_preferences: Regional Polish traditions and preferences
            
        Returns:
            Traditional element recommendations and sourcing guidance
        """
        return {
            "traditional_elements_recommended": True,
            "cultural_elements": "Appropriate Polish cultural elements for the occasion",
            "sourcing_guidance": "Where to obtain traditional Polish elements",
            "regional_authenticity": "Regional Polish authenticity and traditional accuracy"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        generational_preferences: Optional[str] = None,
        liturgical_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Polish language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Polish language interpretation or translation needs
            generational_preferences: Multi-generational language preferences
            liturgical_language: Polish Catholic liturgical language requirements
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Polish language interpretation and translation",
            "liturgical_support": "Polish Catholic liturgical language assistance",
            "cultural_communication": "Polish cultural communication patterns and etiquette"
        }

    async def connect_polonia_resources(
        self,
        context: RunContextWrapper,
        location: Optional[str] = None,
        organization_type: Optional[str] = None,
        support_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect families with Polish-American (Polonia) organizations and support resources.
        
        Args:
            context: The conversation context
            location: Geographic area where family is located
            organization_type: Religious, cultural, or professional organization preference
            support_needs: Type of community support needed
            
        Returns:
            Polonia community resource connections and support coordination
        """
        return {
            "polonia_resources_provided": True,
            "organizations": "Polish-American organizations and cultural centers",
            "parish_support": "Polish Catholic parish communities and support",
            "mutual_aid": "Polonia mutual aid societies and community assistance"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

polish_cultural_agent = PolishCulturalAgent()

__all__ = ["polish_cultural_agent", "PolishCulturalAgent"]