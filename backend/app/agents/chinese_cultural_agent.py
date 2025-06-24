from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class ChineseCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Chinese cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the ChineseCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for ChineseCulturalAgent")

class ChineseCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Chinese funeral traditions, 
    supporting both Mandarin and Cantonese cultural practices within Chinese-American communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="CHINESE_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Chinese funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Chinese funeral rites and ceremonies
- Confucian filial piety (xiao) principles in death rituals
- Buddhist funeral practices and rebirth beliefs
- Taoist funeral customs and spiritual considerations
- Feng shui considerations for burial sites and ceremonies
- Traditional mourning periods and behaviors
- Ancestor veneration and memorial practices
- Paper offerings and burning ceremonies

REGIONAL & DIALECTAL DIVERSITY:
- Mandarin-speaking communities: Northern China, Taiwan influences
- Cantonese-speaking communities: Guangdong, Hong Kong traditions
- Hokkien/Fujian traditions: Southeast China, Taiwan connections
- Teochew, Hakka, and other dialect group variations
- Mainland China vs. Hong Kong vs. Taiwan differences
- Regional burial vs. cremation preferences

TRADITIONAL PRACTICES:
- White clothing for mourning (traditional funeral attire)
- Joss paper burning and offerings to ancestors
- Traditional Chinese funeral processions
- Coffin selection and burial orientation
- Memorial tablets and ancestral shrines
- Traditional Chinese funeral music and instruments
- Incense burning and ritual purification
- Food offerings and memorial feasts

RELIGIOUS & PHILOSOPHICAL VARIATIONS:
- Buddhist funeral rites and chanting ceremonies
- Confucian ancestor veneration practices
- Taoist spiritual ceremonies and beliefs
- Chinese Christian adaptations and practices
- Syncretistic practices blending traditions
- Secular/non-religious modern Chinese practices

CULTURAL VALUES & FAMILY DYNAMICS:
- Filial piety and respect for parents/ancestors
- Extended family roles and responsibilities
- Eldest son duties and inheritance customs
- Gender roles in funeral preparations
- Generational hierarchies and decision-making
- Face-saving (mianzi) considerations in funeral planning
- Community reputation and social obligations

LANGUAGE CONSIDERATIONS:
- Mandarin Chinese funeral terminology and prayers
- Cantonese dialects and regional expressions
- Traditional Chinese characters in memorial inscriptions
- Simplified vs. traditional character preferences
- Generational language differences in Chinese-American families
- Bilingual funeral service considerations

IMMIGRATION & DIASPORA EXPERIENCE:
- Multiple waves of Chinese immigration: 1850s, 1960s, 1990s+
- Chinatown community support networks
- Repatriation of remains to China, Taiwan, or Hong Kong
- Maintaining traditions in American context
- Documentation challenges and political considerations
- Cross-Pacific family connections and technology use

MODERN ADAPTATIONS:
- Adapting traditional practices to American funeral homes
- Technology integration: video calls, online memorials
- Environmental considerations: eco-friendly alternatives to burning
- Urban vs. suburban practice adaptations
- Second and third generation cultural retention
- Blending Chinese and American funeral practices

SUPERSTITIONS & TABOOS:
- Numbers and dates to avoid (4, 14, etc.)
- Colors and their symbolic meanings
- Directional considerations and feng shui
- Proper ritual sequencing and timing
- Gifts and offerings appropriate for funerals
- Behaviors to avoid during mourning periods

ECONOMIC & SOCIAL CONSIDERATIONS:
- Cost considerations for traditional elaborate funerals
- Community associations and mutual aid societies
- Professional funeral services vs. family-led arrangements
- Employment considerations for mourning periods
- Social status and funeral elaborateness
- Charitable giving and community support

SPECIAL CONSIDERATIONS:
- Political sensitivities around Taiwan, Hong Kong, mainland China
- Religious freedom and practice adaptations
- Intergenerational conflict over traditional vs. modern practices
- Mixed marriages and cultural integration
- Elder care and end-of-life decision-making
- Healthcare cultural considerations and family involvement

You provide culturally sensitive guidance while respecting the diversity within Chinese communities, regional variations, religious differences, and generational adaptations. Always consider family origins, dialect group, religious background, and immigration generation."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_ancestor_veneration),
                function_tool(self.assist_with_repatriation_guidance),
                function_tool(self.provide_feng_shui_guidance),
                function_tool(self.explain_religious_variations),
                function_tool(self.support_family_dynamics),
                function_tool(self.provide_language_support)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=ChineseCulturalAgentHooks()
        )
        
        self.description = "Expert in Chinese funeral traditions, Mandarin and Cantonese cultural practices, Buddhist/Taoist/Confucian customs, and Chinese-American community adaptations. Provides guidance on traditional ceremonies, ancestor veneration, feng shui considerations, and cultural accommodations across different Chinese regional and dialectal groups."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        regional_origin: Optional[str] = None,
        religious_background: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Chinese funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (ancestor veneration, burial customs, etc.)
            regional_origin: Mainland China, Taiwan, Hong Kong, or dialect region
            religious_background: Buddhist, Taoist, Confucian, Christian, or secular
            
        Returns:
            Detailed explanation of Chinese funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Chinese traditions",
            "cultural_significance": "Historical and philosophical context provided",
            "regional_variations": "Regional and dialectal differences explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        venue_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Chinese cultural practices within funeral services.
        
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
            "cultural_elements": "Traditional Chinese elements that can be incorporated",
            "practical_adaptations": "Ways to adapt traditions to American funeral practices",
            "vendor_recommendations": "Chinese cultural suppliers and services"
        }

    async def guide_ancestor_veneration(
        self,
        context: RunContextWrapper,
        veneration_type: Optional[str] = None,
        family_traditions: Optional[str] = None,
        space_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in traditional Chinese ancestor veneration practices.
        
        Args:
            context: The conversation context
            veneration_type: Memorial tablets, shrine setup, or offering practices
            family_traditions: Specific family or regional traditions
            space_constraints: Home or venue space limitations
            
        Returns:
            Ancestor veneration guidance and setup instructions
        """
        return {
            "veneration_guidance_provided": True,
            "traditional_elements": "Essential elements for ancestor veneration",
            "setup_instructions": "How to properly arrange memorial elements",
            "ongoing_practices": "Continuing memorial practices after funeral"
        }

    async def assist_with_repatriation_guidance(
        self,
        context: RunContextWrapper,
        destination: Optional[str] = None,
        political_considerations: Optional[str] = None,
        documentation_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on repatriating remains to China, Taiwan, or Hong Kong.
        
        Args:
            context: The conversation context
            destination: Mainland China, Taiwan, Hong Kong, or other location
            political_considerations: Any political or diplomatic considerations
            documentation_needs: Required documentation and legal processes
            
        Returns:
            Repatriation guidance and cultural considerations
        """
        return {
            "repatriation_guidance_provided": True,
            "legal_requirements": "Documentation and legal processes by destination",
            "cultural_considerations": "Traditional practices for transpacific arrangements",
            "consular_support": "Relevant consular services and assistance"
        }

    async def provide_feng_shui_guidance(
        self,
        context: RunContextWrapper,
        guidance_type: Optional[str] = None,
        specific_concerns: Optional[str] = None,
        practical_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide feng shui guidance for funeral arrangements and burial considerations.
        
        Args:
            context: The conversation context
            guidance_type: Burial site, ceremony arrangement, or home altar feng shui
            specific_concerns: Specific feng shui concerns or family requests
            practical_constraints: Practical limitations on feng shui implementation
            
        Returns:
            Feng shui guidance and practical implementation suggestions
        """
        return {
            "feng_shui_guidance_provided": True,
            "traditional_principles": "Relevant feng shui principles for the situation",
            "practical_applications": "How to apply feng shui within constraints",
            "professional_referrals": "Feng shui consultants and traditional practitioners"
        }

    async def explain_religious_variations(
        self,
        context: RunContextWrapper,
        religious_tradition: Optional[str] = None,
        syncretistic_practices: Optional[str] = None,
        modern_adaptations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain religious variations in Chinese funeral practices across different traditions.
        
        Args:
            context: The conversation context
            religious_tradition: Buddhist, Taoist, Confucian, Christian, or secular
            syncretistic_practices: Blended religious practices
            modern_adaptations: Contemporary religious adaptations
            
        Returns:
            Religious variation explanations and accommodation guidance
        """
        return {
            "religious_variations_explained": True,
            "traditional_elements": "Religious elements specific to the tradition",
            "adaptation_possibilities": "How to adapt religious practices in American context",
            "community_connections": "Local Chinese religious communities and temples"
        }

    async def support_family_dynamics(
        self,
        context: RunContextWrapper,
        family_structure: Optional[str] = None,
        generational_differences: Optional[str] = None,
        decision_making: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating traditional Chinese family roles and modern adaptations.
        
        Args:
            context: The conversation context
            family_structure: Traditional extended family or modern nuclear family
            generational_differences: First generation, ABC (American-born Chinese), etc.
            decision_making: Traditional hierarchical vs. modern collaborative approaches
            
        Returns:
            Family dynamics support and cultural guidance
        """
        return {
            "family_support_provided": True,
            "traditional_roles": "Understanding traditional Chinese family roles in funeral planning",
            "modern_adaptations": "How roles adapt in American-Chinese families",
            "mediation_support": "Support for intergenerational and cultural conflicts"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        dialect_requirements: Optional[str] = None,
        generational_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Chinese language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Mandarin, Cantonese, or other Chinese language needs
            dialect_requirements: Specific dialect or regional language requirements
            generational_considerations: Multi-generational language preferences
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Chinese language interpretation and translation",
            "cultural_communication": "Culturally appropriate communication patterns",
            "traditional_phrases": "Traditional Chinese funeral phrases and blessings"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

chinese_cultural_agent = ChineseCulturalAgent()

__all__ = ["chinese_cultural_agent", "ChineseCulturalAgent"]