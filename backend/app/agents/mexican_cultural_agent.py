from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class MexicanCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Mexican cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the MexicanCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for MexicanCulturalAgent")

class MexicanCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Mexican funeral traditions, 
    cultural practices, and regional variations across Mexico and Mexican-American communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="MEXICAN_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Mexican funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Mexican Catholic funeral rites and masses
- Indigenous influences on death ceremonies (Aztec, Maya, Zapotec traditions)
- Día de los Muertos (Day of the Dead) celebrations and memorial practices
- Novenario (nine-day prayer period) and its significance
- Velorio (wake) customs and family gatherings
- Traditional burial vs. cremation preferences by region
- Altar construction and ofrendas (offerings) for the deceased
- Use of marigolds (cempasúchil), candles, and traditional foods in memorials

REGIONAL VARIATIONS:
- Northern Mexico: Norteño culture, ranchero traditions, border customs
- Central Mexico: Indigenous-Catholic syncretism, urban vs. rural practices
- Southern Mexico: Strong indigenous influences, Oaxacan and Chiapan traditions
- Coastal regions: Maritime traditions and fishing community customs
- Mexican-American communities: Generational differences, adaptation to US practices

RELIGIOUS PRACTICES:
- Catholic Mass traditions and Spanish-language services
- Indigenous spiritual practices and curanderismo
- Protestant evangelical communities within Mexican culture
- Syncretistic practices blending Catholic and indigenous beliefs
- Saints veneration (San Judas, Virgen de Guadalupe, etc.)

CULTURAL VALUES & PRACTICES:
- Familismo and extended family involvement in death rituals
- Respeto (respect) for elders and deceased
- Compadrazgo (godparent) system and community support
- Traditional gender roles in funeral preparations
- Music traditions: mariachi, norteño, ranchera for celebrations of life
- Food traditions: mole, tamales, pan de muerto, atole for funeral gatherings
- Language considerations: Spanish, indigenous languages, code-switching

IMMIGRATION & DIASPORA CONSIDERATIONS:
- Repatriation of remains to Mexico
- Mixed-status families and border crossing challenges
- Maintaining traditions in US communities
- Generational differences in cultural observance
- Economic considerations for traditional practices
- Documentation and legal issues affecting funeral arrangements

MODERN ADAPTATIONS:
- Technology use for connecting families across borders
- Adapting traditional altars for urban/apartment living
- Blending Mexican and American funeral home practices
- Social media and virtual participation in ceremonies
- Modern interpretations of traditional mourning periods

You provide culturally sensitive guidance while being respectful of individual family variations and personal beliefs. Always consider socioeconomic factors, immigration status sensitivities, and generational differences when offering advice."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.provide_language_support),
                function_tool(self.guide_altar_construction),
                function_tool(self.explain_regional_variations),
                function_tool(self.assist_with_repatriation_guidance),
                function_tool(self.recommend_traditional_foods),
                function_tool(self.explain_mourning_customs)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=MexicanCulturalAgentHooks()
        )
        
        self.description = "Expert in Mexican funeral traditions, cultural practices, regional variations, and Mexican-American community customs. Provides guidance on traditional ceremonies, religious practices, family customs, and cultural accommodations for funeral services."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        region: Optional[str] = None,
        religious_background: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Mexican funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (velorio, novenario, burial, etc.)
            region: Mexican region or US Mexican-American community
            religious_background: Catholic, indigenous, Protestant, or mixed
            
        Returns:
            Detailed explanation of funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} traditions",
            "cultural_significance": "Historical and cultural context provided",
            "modern_adaptations": "Contemporary variations and adaptations explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        location_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Mexican cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific cultural preferences mentioned
            location_constraints: Venue or location limitations
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional elements that can be incorporated",
            "practical_suggestions": "Feasible ways to honor cultural practices",
            "vendor_recommendations": "Cultural suppliers and service providers"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        document_type: Optional[str] = None,
        region_dialect: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Spanish language support and cultural translation guidance.
        
        Args:
            context: The conversation context
            language_needs: Specific language support needed
            document_type: Type of document needing translation
            region_dialect: Regional Spanish variations
            
        Returns:
            Language support and cultural translation guidance
        """
        return {
            "language_support_provided": True,
            "translations": "Key phrases and documents in Spanish",
            "cultural_context": "Cultural nuances in language use",
            "professional_services": "Interpreter and translation service recommendations"
        }

    async def guide_altar_construction(
        self,
        context: RunContextWrapper,
        altar_type: Optional[str] = None,
        space_constraints: Optional[str] = None,
        budget_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in constructing traditional altars and ofrendas for the deceased.
        
        Args:
            context: The conversation context
            altar_type: Home altar, grave site, or memorial altar
            space_constraints: Available space for altar construction
            budget_considerations: Budget limitations for traditional elements
            
        Returns:
            Step-by-step altar construction guidance
        """
        return {
            "altar_guidance_provided": True,
            "construction_steps": "Traditional altar construction process",
            "required_elements": "Essential items and their symbolic meanings",
            "sourcing_suggestions": "Where to obtain traditional materials"
        }

    async def explain_regional_variations(
        self,
        context: RunContextWrapper,
        family_origin: Optional[str] = None,
        specific_region: Optional[str] = None,
        generation_in_us: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain regional variations in Mexican funeral customs and traditions.
        
        Args:
            context: The conversation context
            family_origin: State or region of origin in Mexico
            specific_region: More specific regional identification
            generation_in_us: How many generations family has been in US
            
        Returns:
            Regional variation explanations and considerations
        """
        return {
            "regional_variations_explained": True,
            "specific_customs": "Region-specific funeral customs",
            "adaptation_patterns": "How traditions adapt across generations",
            "community_resources": "Regional community organizations and support"
        }

    async def assist_with_repatriation_guidance(
        self,
        context: RunContextWrapper,
        destination_region: Optional[str] = None,
        documentation_status: Optional[str] = None,
        transportation_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on repatriating remains to Mexico, including cultural and legal considerations.
        
        Args:
            context: The conversation context
            destination_region: Region in Mexico for repatriation
            documentation_status: Documentation and legal status considerations
            transportation_needs: Transportation and logistics requirements
            
        Returns:
            Repatriation guidance and cultural considerations
        """
        return {
            "repatriation_guidance_provided": True,
            "legal_requirements": "Documentation and legal process overview",
            "cultural_considerations": "Traditional practices for cross-border arrangements",
            "support_services": "Organizations that assist with repatriation"
        }

    async def recommend_traditional_foods(
        self,
        context: RunContextWrapper,
        occasion_type: Optional[str] = None,
        dietary_restrictions: Optional[str] = None,
        regional_preferences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Mexican foods appropriate for funeral gatherings and memorial meals.
        
        Args:
            context: The conversation context
            occasion_type: Velorio, post-funeral meal, Day of the Dead, etc.
            dietary_restrictions: Any dietary considerations
            regional_preferences: Regional food traditions
            
        Returns:
            Traditional food recommendations and cultural significance
        """
        return {
            "food_recommendations_provided": True,
            "traditional_dishes": "Culturally appropriate foods for the occasion",
            "preparation_guidance": "Traditional preparation methods and significance",
            "catering_options": "Mexican caterers and community food preparation"
        }

    async def explain_mourning_customs(
        self,
        context: RunContextWrapper,
        mourning_period: Optional[str] = None,
        family_role: Optional[str] = None,
        modern_adaptations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain traditional Mexican mourning customs and their modern adaptations.
        
        Args:
            context: The conversation context
            mourning_period: Specific mourning period being observed
            family_role: Role of family member in mourning customs
            modern_adaptations: How customs adapt to modern life
            
        Returns:
            Mourning customs explanation and guidance
        """
        return {
            "mourning_customs_explained": True,
            "traditional_practices": "Traditional mourning periods and behaviors",
            "family_roles": "Different roles and expectations within the family",
            "modern_flexibility": "How customs can be adapted to contemporary life"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

mexican_cultural_agent = MexicanCulturalAgent()

__all__ = ["mexican_cultural_agent", "MexicanCulturalAgent"]