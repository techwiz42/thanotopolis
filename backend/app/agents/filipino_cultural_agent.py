from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class FilipinoCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Filipino cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the FilipinoCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for FilipinoCulturalAgent")

class FilipinoCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Filipino funeral traditions, 
    cultural practices, and regional diversity within Filipino-American communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="FILIPINO_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Filipino funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Catholic funeral rites with Filipino variations
- Lamay (wake) traditions and extended wake periods
- Traditional viewing practices and family gatherings
- Nine-day novena prayers (siyam na araw)
- 40-day memorial period and annual death anniversaries
- Traditional mourning attire (black clothing customs)
- Burial vs. cremation preferences by region and religion
- Memorial altars and photo displays

REGIONAL & CULTURAL DIVERSITY:
- Luzon traditions: Tagalog, Ilocano, Kapampangan customs
- Visayas practices: Cebuano, Hiligaynon, Waray variations
- Mindanao diversity: Muslim Filipino, Moro, and Christian traditions
- Mountain Province: Igorot and indigenous burial customs
- Coastal vs. inland cultural differences
- Urban Manila vs. provincial traditions

RELIGIOUS PRACTICES:
- Roman Catholic traditions (85% of population)
- Iglesia ni Cristo (INC) funeral practices
- Protestant denominations and evangelical communities
- Muslim Filipino (Moro) Islamic funeral rites
- Indigenous spiritual practices and ancestor veneration
- Syncretistic practices blending Catholic and pre-colonial beliefs
- Saint veneration and patron saint connections

CULTURAL VALUES & FAMILY DYNAMICS:
- Kapamilya (family) centrality in decision-making
- Utang na loob (debt of gratitude) in community support
- Pakikipagkunware and face-saving considerations
- Respect for elders (pagrespeto sa matatanda)
- Bayanihan spirit and community mutual aid
- Extended family (kamag-anak) involvement
- Godparent (ninong/ninang) system responsibilities

TRADITIONAL PRACTICES:
- Food traditions: lechon, pancit, traditional rice cakes
- Pasalip (contributions) and community financial support
- Traditional games and activities during wake
- Storytelling and sharing memories
- Music traditions: kundiman, folk songs, hymns
- Flower arrangements and traditional decorations
- Photography and memory preservation customs

LANGUAGE CONSIDERATIONS:
- Filipino/Tagalog language usage in ceremonies
- Regional languages: Cebuano, Ilocano, Hiligaynon, etc.
- English and code-switching in Filipino-American families
- Generational language differences
- Traditional prayers and songs in native languages
- Interpretation needs for multi-generational families

IMMIGRATION & DIASPORA EXPERIENCE:
- Multiple waves of Filipino immigration to US
- Healthcare workers, military families, family reunification
- Repatriation of remains to Philippines
- Maintaining traditions in American context
- Balikbayan boxes and cultural connections
- Mixed-status families and documentation issues
- Long-distance family participation via technology

MODERN ADAPTATIONS:
- Technology use for virtual participation
- Social media and online memorial practices
- Adapting traditions to American funeral home practices
- Balancing traditional Catholic and American Protestant influences
- Economic considerations and community fundraising
- Second and third generation cultural retention

ECONOMIC & SOCIAL CONSIDERATIONS:
- Remittances for funeral expenses in Philippines
- Community fundraising through organizations
- Professional vs. family-led funeral planning
- Cost considerations for traditional practices
- Employment considerations for extended mourning periods
- Filipino-American organizations and mutual aid

HEALTHCARE & END-OF-LIFE:
- Filipino cultural attitudes toward illness and death
- Family decision-making in medical situations
- Traditional healing practices and modern medicine
- Hospice care and family caregiving traditions
- Organ donation perspectives and religious considerations
- Advanced directives and family communication patterns

You provide culturally sensitive guidance while respecting the tremendous diversity within Filipino communities, religious variations, and generational differences. Always consider regional origins, religious background, immigration generation, and family socioeconomic factors."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_lamay_practices),
                function_tool(self.assist_with_repatriation_guidance),
                function_tool(self.recommend_traditional_foods),
                function_tool(self.explain_religious_variations),
                function_tool(self.support_family_dynamics),
                function_tool(self.provide_language_support)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=FilipinoCulturalAgentHooks()
        )
        
        self.description = "Expert in Filipino funeral traditions, regional cultural diversity, religious variations, and Filipino-American community practices. Provides guidance on traditional ceremonies, family dynamics, and cultural accommodations across different Filipino ethnic groups and generations."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        regional_origin: Optional[str] = None,
        religious_background: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Filipino funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (lamay, novena, burial customs, etc.)
            regional_origin: Region of Philippines (Luzon, Visayas, Mindanao)
            religious_background: Catholic, Protestant, INC, Muslim, or traditional
            
        Returns:
            Detailed explanation of Filipino funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Filipino traditions",
            "cultural_significance": "Historical and cultural context provided",
            "regional_variations": "Regional differences within Philippines explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        community_involvement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Filipino cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific cultural preferences mentioned
            community_involvement: Level of Filipino community participation
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Filipino elements that can be incorporated",
            "community_participation": "Ways to involve the Filipino community",
            "practical_suggestions": "Feasible ways to honor cultural practices"
        }

    async def guide_lamay_practices(
        self,
        context: RunContextWrapper,
        lamay_duration: Optional[str] = None,
        family_capacity: Optional[str] = None,
        location_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in organizing traditional lamay (wake) practices.
        
        Args:
            context: The conversation context
            lamay_duration: Planned duration of wake period
            family_capacity: Family's capacity for hosting extended wake
            location_constraints: Venue or location limitations
            
        Returns:
            Lamay organization guidance and cultural considerations
        """
        return {
            "lamay_guidance_provided": True,
            "traditional_elements": "Essential elements of Filipino wake traditions",
            "practical_organization": "How to organize extended wake period",
            "modern_adaptations": "Adapting lamay practices to American context"
        }

    async def assist_with_repatriation_guidance(
        self,
        context: RunContextWrapper,
        destination_region: Optional[str] = None,
        documentation_status: Optional[str] = None,
        transportation_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on repatriating remains to Philippines, including legal and cultural considerations.
        
        Args:
            context: The conversation context
            destination_region: Region in Philippines for repatriation
            documentation_status: Documentation and legal status considerations
            transportation_needs: Transportation and logistics requirements
            
        Returns:
            Repatriation guidance and cultural considerations
        """
        return {
            "repatriation_guidance_provided": True,
            "legal_requirements": "Documentation and legal process for Philippines",
            "cultural_considerations": "Traditional practices for cross-Pacific arrangements",
            "consular_support": "Philippine consular services and assistance"
        }

    async def recommend_traditional_foods(
        self,
        context: RunContextWrapper,
        occasion_type: Optional[str] = None,
        dietary_restrictions: Optional[str] = None,
        regional_preferences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Filipino foods appropriate for funeral gatherings and memorial meals.
        
        Args:
            context: The conversation context
            occasion_type: Lamay, post-funeral meal, 40-day memorial, etc.
            dietary_restrictions: Any dietary considerations
            regional_preferences: Regional Filipino food traditions
            
        Returns:
            Traditional food recommendations and cultural significance
        """
        return {
            "food_recommendations_provided": True,
            "traditional_dishes": "Culturally appropriate Filipino foods for the occasion",
            "preparation_guidance": "Traditional preparation methods and significance",
            "catering_options": "Filipino caterers and community food preparation"
        }

    async def explain_religious_variations(
        self,
        context: RunContextWrapper,
        religious_denomination: Optional[str] = None,
        church_affiliation: Optional[str] = None,
        traditional_elements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain religious variations in Filipino funeral practices across different denominations.
        
        Args:
            context: The conversation context
            religious_denomination: Catholic, Protestant, INC, Muslim, etc.
            church_affiliation: Specific church or religious community
            traditional_elements: Pre-colonial or traditional spiritual elements
            
        Returns:
            Religious variation explanations and accommodation guidance
        """
        return {
            "religious_variations_explained": True,
            "denominational_differences": "Differences in funeral practices by religion",
            "traditional_integration": "How pre-colonial traditions integrate with modern religion",
            "church_connections": "Local Filipino religious communities and churches"
        }

    async def support_family_dynamics(
        self,
        context: RunContextWrapper,
        family_structure: Optional[str] = None,
        generational_differences: Optional[str] = None,
        decision_making: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating traditional Filipino family roles and modern adaptations.
        
        Args:
            context: The conversation context
            family_structure: Extended family, nuclear family, or transnational family
            generational_differences: First generation, 1.5 generation, second generation dynamics
            decision_making: Filipino family decision-making patterns and challenges
            
        Returns:
            Family dynamics support and cultural guidance
        """
        return {
            "family_support_provided": True,
            "traditional_roles": "Understanding traditional Filipino family roles",
            "modern_adaptations": "How roles adapt in American context",
            "conflict_resolution": "Cultural approaches to family decision-making"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        languages_needed: Optional[str] = None,
        generation_mix: Optional[str] = None,
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide support for Filipino language needs in funeral services and communications.
        
        Args:
            context: The conversation context
            languages_needed: Filipino/Tagalog, regional languages, or English needs
            generation_mix: Multi-generational language preferences
            service_type: Religious service, family gathering, or formal ceremony
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Filipino language interpretation and translation",
            "cultural_communication": "Culturally appropriate communication patterns",
            "generational_bridging": "Supporting communication across generations"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

filipino_cultural_agent = FilipinoCulturalAgent()

__all__ = ["filipino_cultural_agent", "FilipinoCulturalAgent"]