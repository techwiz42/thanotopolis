from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class SalvadoranCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Salvadoran cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the SalvadoranCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for SalvadoranCulturalAgent")

class SalvadoranCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Salvadoran funeral traditions, 
    cultural practices, and Central American customs within Salvadoran-American communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="SALVADORAN_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Salvadoran funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Catholic funeral rites with Salvadoran variations
- Indigenous influences from Pipil and Lenca traditions
- Velorio (wake) customs specific to El Salvador
- Novenario and traditional prayer cycles
- Traditional burial practices and cemetery customs
- Use of flowers, candles, and religious imagery
- Memorial altars and home shrine traditions
- Traditional mourning attire and behaviors

REGIONAL & GEOGRAPHIC CONSIDERATIONS:
- Western El Salvador: Coffee region cultural practices
- Central regions: San Salvador urban vs. rural differences
- Eastern regions: Agricultural community traditions
- Coastal areas: Pacific coastal customs
- Mountain regions: Highland indigenous influences
- US settlement patterns: Los Angeles, Houston, Washington DC areas

RELIGIOUS & SPIRITUAL PRACTICES:
- Roman Catholic traditions and Spanish-language masses
- Liberation theology influences in Salvadoran communities
- Protestant evangelical growth and funeral practices
- Folk Catholicism and saint veneration
- Indigenous spiritual elements and syncretism
- Curanderismo and traditional healing in death rituals

CULTURAL VALUES & FAMILY DYNAMICS:
- Strong family bonds and extended family involvement
- Compadrazgo (godparent) systems and community support
- Respeto (respect) for elders and deceased
- Gender roles in funeral preparations and mourning
- Community solidarity and mutual aid traditions
- Importance of personal relationships and social networks

CIVIL WAR & TRAUMA CONSIDERATIONS:
- Impact of 1980-1992 civil war on death rituals
- Trauma-informed approaches to loss and grief
- Missing persons and unresolved disappearances
- Collective memory and community healing
- Intergenerational trauma effects on mourning practices
- Veterans and war-related death considerations

IMMIGRATION & DIASPORA EXPERIENCE:
- TPS (Temporary Protected Status) and mixed-status families
- Remittances for funeral expenses and family support
- Repatriation of remains to El Salvador
- Maintaining traditions in US Salvadoran communities
- Documentation challenges and legal considerations
- Cross-border family connections and virtual participation

LANGUAGE & COMMUNICATION:
- Salvadoran Spanish dialects and regionalisms
- Voseo usage and formal/informal address
- Code-switching in Salvadoran-American communities
- Generational language differences
- Traditional sayings and expressions related to death
- Bilingual funeral service considerations

TRADITIONAL FOODS & CELEBRATIONS:
- Pupusas and traditional foods for funeral gatherings
- Atol de elote, horchata, and traditional beverages
- Pan dulce and memorial meal traditions
- Day of the Dead (November 2nd) observances
- Food preparation as community bonding activity
- Dietary considerations and modern adaptations

MODERN COMMUNITY DYNAMICS:
- Salvadoran-American organizations and mutual aid societies
- Hometown associations (HTAs) and community support
- Social media and technology for family connections
- Economic challenges and community fundraising
- Youth and second-generation cultural adaptation
- Blending Salvadoran and American funeral practices

You provide culturally sensitive guidance while being aware of the trauma history, immigration challenges, and strong community bonds characteristic of Salvadoran communities. Always consider economic factors, legal status sensitivities, and the importance of community support networks."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.provide_trauma_informed_support),
                function_tool(self.assist_with_repatriation_guidance),
                function_tool(self.recommend_community_resources),
                function_tool(self.guide_traditional_foods),
                function_tool(self.explain_religious_practices),
                function_tool(self.support_family_dynamics)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=SalvadoranCulturalAgentHooks()
        )
        
        self.description = "Expert in Salvadoran funeral traditions, Central American customs, civil war trauma considerations, and Salvadoran-American community practices. Provides culturally sensitive guidance on traditional ceremonies, family dynamics, and community support systems."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        regional_origin: Optional[str] = None,
        religious_background: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Salvadoran funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (velorio, novenario, burial customs, etc.)
            regional_origin: Region of El Salvador family originates from
            religious_background: Catholic, Protestant, or traditional spiritual practices
            
        Returns:
            Detailed explanation of Salvadoran funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Salvadoran traditions",
            "cultural_significance": "Historical and cultural context provided",
            "regional_variations": "Regional differences within El Salvador explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        community_involvement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Salvadoran cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific cultural preferences mentioned
            community_involvement: Level of community participation desired
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Salvadoran elements that can be incorporated",
            "community_participation": "Ways to involve the Salvadoran community",
            "practical_suggestions": "Feasible ways to honor cultural practices"
        }

    async def provide_trauma_informed_support(
        self,
        context: RunContextWrapper,
        trauma_type: Optional[str] = None,
        generation_affected: Optional[str] = None,
        support_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide trauma-informed support considering civil war history and immigration experiences.
        
        Args:
            context: The conversation context
            trauma_type: War trauma, immigration trauma, or loss-related trauma
            generation_affected: First generation, second generation, or mixed
            support_needs: Specific support needs identified
            
        Returns:
            Trauma-informed guidance and support resources
        """
        return {
            "trauma_support_provided": True,
            "sensitive_approaches": "Trauma-informed approaches to funeral planning",
            "community_healing": "Community-based healing and support strategies",
            "professional_resources": "Mental health and trauma support services"
        }

    async def assist_with_repatriation_guidance(
        self,
        context: RunContextWrapper,
        destination_region: Optional[str] = None,
        legal_status: Optional[str] = None,
        transportation_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on repatriating remains to El Salvador, including legal and cultural considerations.
        
        Args:
            context: The conversation context
            destination_region: Region in El Salvador for repatriation
            legal_status: Documentation and legal status considerations
            transportation_needs: Transportation and logistics requirements
            
        Returns:
            Repatriation guidance and cultural considerations
        """
        return {
            "repatriation_guidance_provided": True,
            "legal_requirements": "Documentation and legal process for El Salvador",
            "cultural_considerations": "Traditional practices for cross-border arrangements",
            "consular_support": "Salvadoran consular services and assistance"
        }

    async def recommend_community_resources(
        self,
        context: RunContextWrapper,
        location: Optional[str] = None,
        support_type: Optional[str] = None,
        urgent_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend Salvadoran community organizations and mutual aid resources.
        
        Args:
            context: The conversation context
            location: Geographic area where family is located
            support_type: Type of support needed (financial, emotional, logistical)
            urgent_needs: Any urgent assistance requirements
            
        Returns:
            Community resource recommendations and contact information
        """
        return {
            "community_resources_provided": True,
            "organizations": "Salvadoran community organizations and HTAs",
            "mutual_aid": "Community mutual aid and support networks",
            "emergency_assistance": "Urgent financial and logistical support options"
        }

    async def guide_traditional_foods(
        self,
        context: RunContextWrapper,
        occasion_type: Optional[str] = None,
        dietary_restrictions: Optional[str] = None,
        preparation_capacity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in preparing traditional Salvadoran foods for funeral gatherings.
        
        Args:
            context: The conversation context
            occasion_type: Velorio, post-funeral meal, memorial gathering
            dietary_restrictions: Any dietary considerations
            preparation_capacity: Family's capacity for food preparation
            
        Returns:
            Traditional food guidance and preparation recommendations
        """
        return {
            "food_guidance_provided": True,
            "traditional_dishes": "Culturally appropriate Salvadoran foods for the occasion",
            "preparation_methods": "Traditional preparation and community cooking",
            "catering_options": "Salvadoran caterers and community food sources"
        }

    async def explain_religious_practices(
        self,
        context: RunContextWrapper,
        religious_tradition: Optional[str] = None,
        church_affiliation: Optional[str] = None,
        language_preferences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain Salvadoran religious practices and their role in funeral ceremonies.
        
        Args:
            context: The conversation context
            religious_tradition: Catholic, Protestant, or traditional spiritual practices
            church_affiliation: Specific church or denomination
            language_preferences: Spanish, English, or bilingual services
            
        Returns:
            Religious practice explanations and accommodation guidance
        """
        return {
            "religious_practices_explained": True,
            "ceremony_elements": "Traditional religious elements in Salvadoran funerals",
            "church_connections": "Local Salvadoran churches and religious communities",
            "bilingual_services": "Spanish-English bilingual religious service options"
        }

    async def support_family_dynamics(
        self,
        context: RunContextWrapper,
        family_structure: Optional[str] = None,
        generational_differences: Optional[str] = None,
        decision_making: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating traditional roles and modern adaptations in funeral planning.
        
        Args:
            context: The conversation context
            family_structure: Extended family, nuclear family, or mixed-status family
            generational_differences: First generation, second generation dynamics
            decision_making: Family decision-making patterns and challenges
            
        Returns:
            Family dynamics support and cultural guidance
        """
        return {
            "family_support_provided": True,
            "traditional_roles": "Understanding traditional family roles in Salvadoran culture",
            "modern_adaptations": "How roles adapt in American context",
            "mediation_support": "Support for family decision-making and conflict resolution"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

salvadoran_cultural_agent = SalvadoranCulturalAgent()

__all__ = ["salvadoran_cultural_agent", "SalvadoranCulturalAgent"]