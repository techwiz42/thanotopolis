from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class VietnameseCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Vietnamese cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the VietnameseCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for VietnameseCulturalAgent")

class VietnameseCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Vietnamese funeral traditions, 
    Buddhist and Catholic practices within Vietnamese-American communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="VIETNAMESE_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Vietnamese funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Vietnamese funeral rites and ancestor veneration
- Buddhist funeral ceremonies and rebirth beliefs
- Catholic Vietnamese funeral practices and adaptations
- Confucian filial piety influences in death rituals
- Traditional mourning periods (49 days, 100 days, annual commemorations)
- White mourning attire and traditional funeral clothing
- Incense burning and altar arrangements
- Traditional Vietnamese funeral processions

RELIGIOUS PRACTICES:
- Mahayana Buddhist funeral rites and chanting
- Catholic Mass with Vietnamese cultural elements
- Caodaism funeral practices and beliefs
- Ancestor worship and spirit veneration
- Traditional Vietnamese folk religion elements
- Syncretistic practices blending Buddhism, Catholicism, and folk beliefs
- Temple and church community involvement

CULTURAL VALUES & FAMILY DYNAMICS:
- Filial piety (hiếu thảo) and respect for parents/ancestors
- Extended family roles and generational hierarchies
- Gender roles in funeral preparations and mourning
- Community support and mutual aid (tương trợ)
- Face-saving considerations and social harmony
- Traditional Vietnamese concepts of death and afterlife
- Importance of proper funeral rites for spiritual peace

TRADITIONAL PRACTICES:
- Altar construction and ancestral shrine setup
- Paper money burning and spirit offerings
- Traditional Vietnamese funeral foods and feasts
- Mourning rituals and behavioral expectations
- Memorial anniversary celebrations (giỗ)
- Feng shui considerations in burial arrangements
- Traditional Vietnamese funeral music and ceremonies
- Photography and memory preservation customs

VIETNAM WAR & TRAUMA CONSIDERATIONS:
- War trauma and its impact on Vietnamese refugee families
- Missing in action (MIA) and unresolved losses
- Collective trauma and community healing approaches
- Veteran families and war-related death considerations
- Intergenerational trauma effects on mourning practices
- Trauma-informed approaches to loss and grief

IMMIGRATION & DIASPORA EXPERIENCE:
- Vietnamese refugee waves: 1975, boat people, family reunification
- Maintaining traditions in American Vietnamese communities
- Repatriation of remains to Vietnam
- Documentation challenges and political considerations
- Cross-Pacific family connections and virtual participation
- Mixed-status families and immigration concerns
- Vietnamese-American community organizations and mutual aid

LANGUAGE & COMMUNICATION:
- Vietnamese language funeral terminology and prayers
- Regional dialect differences (Northern, Central, Southern Vietnam)
- Generational language differences in Vietnamese-American families
- Traditional sayings and expressions related to death
- Bilingual funeral service considerations
- Code-switching in Vietnamese-American communities

REGIONAL VARIATIONS:
- Northern Vietnam (Hanoi region): Traditional Confucian influences
- Central Vietnam (Hue region): Imperial court traditions and Buddhist practices
- Southern Vietnam (Saigon region): More diverse religious practices
- Mekong Delta: River and agricultural community customs
- Mountain regions: Ethnic minority influences and practices

MODERN ADAPTATIONS:
- Technology use for virtual participation and live-streaming
- Social media and online memorial practices
- Adapting traditional practices to American funeral homes
- Balancing traditional Buddhist/Catholic and American practices
- Economic considerations and community fundraising
- Second and third generation cultural retention

ECONOMIC & SOCIAL CONSIDERATIONS:
- Remittances for funeral expenses in Vietnam
- Community fundraising through Vietnamese organizations
- Professional vs. family-led funeral planning
- Cost considerations for traditional elaborate ceremonies
- Employment considerations for extended mourning periods
- Vietnamese-American business community support

HEALTHCARE & END-OF-LIFE:
- Vietnamese cultural attitudes toward illness and death
- Family decision-making in medical situations
- Traditional medicine and modern healthcare integration
- Hospice care and family caregiving traditions
- Organ donation perspectives and cultural considerations
- Advanced directives and family communication patterns

SPECIAL CONSIDERATIONS:
- Political sensitivities around Communist Vietnam vs. refugee experience
- Religious freedom and practice adaptations in America
- Intergenerational conflict over traditional vs. modern practices
- Mixed marriages and cultural integration challenges
- Elder care traditions and filial responsibility
- Educational and professional success expectations affecting grief

You provide culturally sensitive guidance while being aware of war trauma, refugee experience, and the complex relationship many Vietnamese Americans have with their homeland. Always consider religious background, regional origin, immigration generation, and family socioeconomic factors."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_ancestor_veneration),
                function_tool(self.assist_with_repatriation_guidance),
                function_tool(self.provide_buddhist_catholic_guidance),
                function_tool(self.support_trauma_informed_care),
                function_tool(self.recommend_traditional_foods),
                function_tool(self.provide_language_support)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=VietnameseCulturalAgentHooks()
        )
        
        self.description = "Expert in Vietnamese funeral traditions, Buddhist and Catholic practices, war trauma considerations, and Vietnamese-American community customs. Provides guidance on traditional ceremonies, ancestor veneration, religious accommodations, and culturally sensitive support for refugee and immigrant families."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        regional_origin: Optional[str] = None,
        religious_background: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Vietnamese funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (ancestor veneration, mourning periods, etc.)
            regional_origin: Northern, Central, or Southern Vietnam
            religious_background: Buddhist, Catholic, Caodaist, or traditional
            
        Returns:
            Detailed explanation of Vietnamese funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Vietnamese traditions",
            "cultural_significance": "Historical and spiritual context provided",
            "regional_variations": "Regional differences within Vietnam explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        religious_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Vietnamese cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific cultural preferences mentioned
            religious_requirements: Buddhist, Catholic, or traditional spiritual needs
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Vietnamese elements that can be incorporated",
            "religious_adaptations": "How to accommodate Buddhist or Catholic practices",
            "practical_suggestions": "Feasible ways to honor cultural practices"
        }

    async def guide_ancestor_veneration(
        self,
        context: RunContextWrapper,
        altar_type: Optional[str] = None,
        family_traditions: Optional[str] = None,
        space_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Vietnamese ancestor veneration and altar setup practices.
        
        Args:
            context: The conversation context
            altar_type: Home altar, memorial altar, or cemetery arrangements
            family_traditions: Specific family or regional traditions
            space_constraints: Home or venue space limitations
            
        Returns:
            Ancestor veneration guidance and altar setup instructions
        """
        return {
            "veneration_guidance_provided": True,
            "altar_setup": "Traditional Vietnamese altar arrangement and elements",
            "ongoing_practices": "Daily and anniversary memorial practices",
            "spiritual_significance": "Meaning and importance of ancestor veneration"
        }

    async def assist_with_repatriation_guidance(
        self,
        context: RunContextWrapper,
        destination_region: Optional[str] = None,
        political_considerations: Optional[str] = None,
        family_connections: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on repatriating remains to Vietnam, including political and cultural considerations.
        
        Args:
            context: The conversation context
            destination_region: Region in Vietnam for repatriation
            political_considerations: Political or diplomatic considerations
            family_connections: Family remaining in Vietnam
            
        Returns:
            Repatriation guidance and cultural considerations
        """
        return {
            "repatriation_guidance_provided": True,
            "legal_requirements": "Documentation and legal processes for Vietnam",
            "political_considerations": "Diplomatic and political factors to consider",
            "cultural_traditions": "Traditional practices for transpacific arrangements"
        }

    async def provide_buddhist_catholic_guidance(
        self,
        context: RunContextWrapper,
        religious_preference: Optional[str] = None,
        mixed_family: Optional[str] = None,
        ceremony_integration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on Buddhist and Catholic funeral practices within Vietnamese tradition.
        
        Args:
            context: The conversation context
            religious_preference: Buddhist, Catholic, or mixed religious practices
            mixed_family: Families with both Buddhist and Catholic members
            ceremony_integration: How to integrate different religious elements
            
        Returns:
            Religious practice guidance and integration suggestions
        """
        return {
            "religious_guidance_provided": True,
            "buddhist_elements": "Traditional Vietnamese Buddhist funeral practices",
            "catholic_elements": "Vietnamese Catholic funeral adaptations",
            "integration_strategies": "How to respectfully blend religious traditions"
        }

    async def support_trauma_informed_care(
        self,
        context: RunContextWrapper,
        trauma_type: Optional[str] = None,
        generation_affected: Optional[str] = None,
        support_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide trauma-informed support considering war history and refugee experience.
        
        Args:
            context: The conversation context
            trauma_type: War trauma, refugee trauma, or intergenerational trauma
            generation_affected: First generation refugees, second generation, etc.
            support_needs: Specific trauma-informed support needs
            
        Returns:
            Trauma-informed guidance and support resources
        """
        return {
            "trauma_support_provided": True,
            "sensitive_approaches": "Trauma-informed approaches to funeral planning",
            "community_healing": "Community-based healing and support strategies",
            "professional_resources": "Vietnamese-speaking mental health and trauma services"
        }

    async def recommend_traditional_foods(
        self,
        context: RunContextWrapper,
        occasion_type: Optional[str] = None,
        dietary_restrictions: Optional[str] = None,
        regional_preferences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Vietnamese foods appropriate for funeral gatherings and memorial meals.
        
        Args:
            context: The conversation context
            occasion_type: Wake, post-funeral meal, anniversary memorial
            dietary_restrictions: Any dietary considerations
            regional_preferences: Northern, Central, or Southern Vietnamese cuisine
            
        Returns:
            Traditional food recommendations and cultural significance
        """
        return {
            "food_recommendations_provided": True,
            "traditional_dishes": "Culturally appropriate Vietnamese foods for the occasion",
            "preparation_guidance": "Traditional preparation methods and significance",
            "catering_options": "Vietnamese caterers and community food preparation"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        dialect_considerations: Optional[str] = None,
        generational_differences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Vietnamese language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Vietnamese language interpretation or translation needs
            dialect_considerations: Regional Vietnamese dialect differences
            generational_differences: Multi-generational language preferences
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Vietnamese language interpretation and translation",
            "cultural_communication": "Culturally appropriate communication patterns",
            "traditional_phrases": "Traditional Vietnamese funeral prayers and blessings"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

vietnamese_cultural_agent = VietnameseCulturalAgent()

__all__ = ["vietnamese_cultural_agent", "VietnameseCulturalAgent"]