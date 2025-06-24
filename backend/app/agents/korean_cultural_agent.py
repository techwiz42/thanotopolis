from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class KoreanCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Korean cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the KoreanCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for KoreanCulturalAgent")

class KoreanCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Korean funeral traditions, 
    Confucian values, and modern Korean-American community practices.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="KOREAN_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Korean funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Korean funeral rites (jangrae) and ceremonies
- Confucian influence on Korean death rituals and ancestor veneration
- Buddhist funeral practices and temple ceremonies
- Christian (Protestant and Catholic) Korean funeral adaptations
- Traditional 3-day wake period and family gatherings
- Proper funeral attire: hanbok and modern mourning dress
- Ancestral tablet preparation and shrine arrangements
- Memorial services and anniversary commemorations

CONFUCIAN VALUES & FAMILY DYNAMICS:
- Filial piety (hyo) and respect for parents and ancestors
- Hierarchical family structure and decision-making
- Gender roles in funeral preparations and mourning
- Eldest son responsibilities and inheritance customs
- Extended family obligations and social expectations
- Proper etiquette and ceremonial behavior
- Generational respect and deference patterns

TRADITIONAL PRACTICES:
- Jesa (ancestral memorial services) and ritual procedures
- Traditional Korean funeral foods and ceremonial meals
- Incense burning and offering arrangements
- Bowing rituals (jeol) and proper ceremonial conduct
- Traditional Korean funeral music and instruments
- Burial vs. cremation preferences and regional variations
- Mourning periods and behavioral expectations
- Memorial photography and family documentation

RELIGIOUS VARIATIONS:
- Buddhist temple funeral services and monk ceremonies
- Protestant Christian funeral services in Korean churches
- Catholic funeral masses with Korean cultural elements
- Traditional shamanic elements and folk religion influences
- Secular/non-religious modern Korean funeral practices
- Syncretistic practices blending Confucian, Buddhist, and Christian elements

KOREAN WAR & HISTORICAL TRAUMA:
- Impact of Korean War on families and death rituals
- Separated families and cross-border memorial issues
- Veteran families and war-related death considerations
- Collective trauma and historical memory
- North Korea-South Korea political considerations
- Refugee and immigrant experiences

IMMIGRATION & DIASPORA EXPERIENCE:
- Waves of Korean immigration: 1960s-70s, 1980s-90s, recent arrivals
- Korean-American community organizations and churches
- Maintaining traditions in American Korean communities
- Repatriation of remains to South Korea
- Documentation and legal considerations
- Cross-Pacific family connections and technology use

LANGUAGE & COMMUNICATION:
- Korean language funeral terminology and honorifics
- Formal vs. informal speech levels in funeral contexts
- Generational language differences in Korean-American families
- Traditional prayers and ceremonial language
- Bilingual funeral service considerations
- Cultural communication patterns and respect protocols

MODERN KOREAN-AMERICAN ADAPTATIONS:
- Second and third generation cultural retention
- Balancing traditional Confucian and American individualistic values
- Technology integration: live-streaming, virtual participation
- Adapting traditional practices to American funeral homes
- Economic considerations and community support
- Professional success culture and grief expression

CULTURAL VALUES & SOCIAL DYNAMICS:
- Nunchi (social awareness) and harmony maintenance
- Jeong (emotional bonds) and community relationships
- Han (deep sorrow/resilience) and collective emotional processing
- Face-saving (chemyeon) and social reputation concerns
- Community mutual aid and reciprocal obligations
- Education emphasis and achievement expectations

HEALTHCARE & END-OF-LIFE:
- Korean cultural attitudes toward illness and death disclosure
- Family-centered medical decision-making
- Traditional Korean medicine and modern healthcare integration
- Hospice care and family caregiving traditions
- Organ donation perspectives and cultural considerations
- Advanced directives and family communication patterns

ECONOMIC & SOCIAL CONSIDERATIONS:
- Korean-American business community support networks
- Rotating credit associations (gye) and mutual financial aid
- Professional vs. family-led funeral planning
- Cost considerations for traditional elaborate ceremonies
- Employment considerations for mourning periods
- Social status and funeral ceremony elaborateness

GENERATIONAL DIFFERENCES:
- First generation (ilse): Traditional Korean practices
- Second generation (ise): Korean-American adaptations
- Third generation (samse): American with Korean heritage
- Language retention and cultural practice continuation
- Intergenerational conflict over traditional vs. modern approaches
- Mixed marriages and cultural integration challenges

SPECIAL CONSIDERATIONS:
- Korean age calculation system and ceremonial importance
- Seasonal and lunar calendar considerations for ceremonies
- Traditional Korean concepts of death and afterlife
- Importance of proper ritual performance for family honor
- Educational achievement culture and grief processing
- Technology and social media use in memorial practices

You provide culturally sensitive guidance while respecting Korean hierarchical values, Confucian principles, and the strong emphasis on family honor and proper ritual performance. Always consider generational differences, religious background, and the importance of maintaining social harmony and respect."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_jesa_ceremonies),
                function_tool(self.assist_with_repatriation_guidance),
                function_tool(self.support_family_hierarchy),
                function_tool(self.provide_religious_guidance),
                function_tool(self.recommend_traditional_foods),
                function_tool(self.provide_language_support)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=KoreanCulturalAgentHooks()
        )
        
        self.description = "Expert in Korean funeral traditions, Confucian values, ancestral memorial services, and Korean-American community practices. Provides guidance on traditional ceremonies, family hierarchy, religious accommodations, and cultural integration across generations."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        religious_background: Optional[str] = None,
        generational_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Korean funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (jangrae, jesa, mourning customs, etc.)
            religious_background: Buddhist, Christian, Confucian, or traditional
            generational_context: First, second, or third generation Korean-American
            
        Returns:
            Detailed explanation of Korean funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Korean traditions",
            "confucian_context": "Confucian values and cultural significance provided",
            "modern_adaptations": "Contemporary Korean-American adaptations explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        venue_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Korean cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific cultural preferences mentioned
            venue_constraints: Funeral home or venue limitations
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Korean elements that can be incorporated",
            "hierarchy_considerations": "How to respect Korean family hierarchy",
            "practical_adaptations": "Feasible ways to honor cultural practices"
        }

    async def guide_jesa_ceremonies(
        self,
        context: RunContextWrapper,
        ceremony_type: Optional[str] = None,
        family_traditions: Optional[str] = None,
        space_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Korean ancestral memorial services (jesa) and proper ritual conduct.
        
        Args:
            context: The conversation context
            ceremony_type: Annual jesa, death anniversary, or seasonal memorial
            family_traditions: Specific family or regional traditions
            space_requirements: Space and setup requirements for ceremony
            
        Returns:
            Jesa ceremony guidance and ritual instructions
        """
        return {
            "jesa_guidance_provided": True,
            "ritual_procedures": "Step-by-step jesa ceremony instructions",
            "food_preparations": "Traditional foods and arrangements required",
            "family_roles": "Proper roles and responsibilities for family members"
        }

    async def assist_with_repatriation_guidance(
        self,
        context: RunContextWrapper,
        destination_region: Optional[str] = None,
        family_connections: Optional[str] = None,
        documentation_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on repatriating remains to South Korea, including cultural and legal considerations.
        
        Args:
            context: The conversation context
            destination_region: Region in South Korea for repatriation
            family_connections: Family remaining in Korea
            documentation_needs: Required documentation and legal processes
            
        Returns:
            Repatriation guidance and cultural considerations
        """
        return {
            "repatriation_guidance_provided": True,
            "legal_requirements": "Documentation and legal processes for South Korea",
            "cultural_considerations": "Traditional practices for transpacific arrangements",
            "consular_support": "Korean consular services and assistance"
        }

    async def support_family_hierarchy(
        self,
        context: RunContextWrapper,
        family_structure: Optional[str] = None,
        decision_making: Optional[str] = None,
        generational_conflicts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating Korean hierarchical family dynamics during funeral planning.
        
        Args:
            context: The conversation context
            family_structure: Traditional extended family or modern nuclear family
            decision_making: Traditional vs. modern decision-making approaches
            generational_conflicts: Conflicts between traditional and modern approaches
            
        Returns:
            Family hierarchy support and cultural mediation guidance
        """
        return {
            "hierarchy_support_provided": True,
            "traditional_roles": "Understanding Korean family hierarchy in funeral contexts",
            "modern_adaptations": "How hierarchy adapts in Korean-American families",
            "conflict_resolution": "Mediating between traditional and modern expectations"
        }

    async def provide_religious_guidance(
        self,
        context: RunContextWrapper,
        religious_tradition: Optional[str] = None,
        church_involvement: Optional[str] = None,
        traditional_elements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on religious variations in Korean funeral practices.
        
        Args:
            context: The conversation context
            religious_tradition: Buddhist, Protestant, Catholic, or traditional
            church_involvement: Korean church community involvement
            traditional_elements: Confucian or traditional spiritual elements
            
        Returns:
            Religious guidance and integration recommendations
        """
        return {
            "religious_guidance_provided": True,
            "tradition_specific_elements": "Religious elements specific to the tradition",
            "korean_church_connections": "Local Korean church communities and support",
            "cultural_integration": "How to blend religious and cultural practices"
        }

    async def recommend_traditional_foods(
        self,
        context: RunContextWrapper,
        occasion_type: Optional[str] = None,
        dietary_restrictions: Optional[str] = None,
        preparation_capacity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Korean foods appropriate for funeral gatherings and memorial services.
        
        Args:
            context: The conversation context
            occasion_type: Wake, post-funeral meal, jesa ceremony
            dietary_restrictions: Any dietary considerations
            preparation_capacity: Family's capacity for traditional food preparation
            
        Returns:
            Traditional food recommendations and preparation guidance
        """
        return {
            "food_recommendations_provided": True,
            "traditional_dishes": "Culturally appropriate Korean foods for the occasion",
            "preparation_methods": "Traditional preparation and ceremonial significance",
            "community_support": "Korean community food preparation and catering"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        honorific_requirements: Optional[str] = None,
        generational_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Korean language support for funeral services and formal communications.
        
        Args:
            context: The conversation context
            language_needs: Korean language interpretation or translation needs
            honorific_requirements: Formal Korean honorific language requirements
            generational_considerations: Multi-generational language preferences
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Korean language interpretation and translation",
            "honorific_guidance": "Proper Korean honorific usage in funeral contexts",
            "cultural_communication": "Culturally appropriate Korean communication patterns"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

korean_cultural_agent = KoreanCulturalAgent()

__all__ = ["korean_cultural_agent", "KoreanCulturalAgent"]