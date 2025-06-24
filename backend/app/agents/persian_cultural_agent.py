from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class PersianCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Persian cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the PersianCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for PersianCulturalAgent")

class PersianCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Persian/Iranian funeral traditions, 
    Zoroastrian heritage, Islamic practices, and secular modern adaptations.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="PERSIAN_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Persian/Iranian funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Persian funeral rites and ancient customs
- Islamic funeral practices within Persian cultural context
- Zoroastrian influences and historical traditions
- Shia Islamic mourning rituals and commemorations
- Traditional Persian burial customs and cemetery practices
- Memorial gatherings and community support systems
- Persian poetry and literature in memorial contexts
- Traditional mourning attire and behavioral expectations

RELIGIOUS & SPIRITUAL VARIATIONS:
- Shia Islamic funeral rites and religious obligations
- Sunni Islamic practices within Persian communities
- Zoroastrian funeral traditions and fire temple connections
- Bahá'í funeral practices and community support
- Persian Jewish (Mizrahi) funeral customs
- Christian Persian communities and church practices
- Secular Persian cultural practices and modern adaptations

CULTURAL VALUES & FAMILY DYNAMICS:
- Ta'arof (Persian politeness) and social etiquette in grief contexts
- Extended family obligations and hierarchical respect
- Gender roles in funeral preparations and mourning
- Hospitality traditions and guest reception during mourning
- Community solidarity and mutual support systems
- Importance of family honor and social reputation
- Traditional Persian concepts of fate and acceptance

HISTORICAL & POLITICAL CONSIDERATIONS:
- Impact of 1979 Revolution on Persian-American communities
- Pre-revolution vs. post-revolution immigration experiences
- Political asylum and refugee family considerations
- Iran-Iraq War trauma and veteran family support
- Current political tensions and family separation issues
- Different waves of Persian immigration to America
- Documentation and travel restriction considerations

TRADITIONAL PRACTICES:
- Persian funeral foods and memorial meal traditions
- Rosewater, saffron, and traditional Persian elements
- Poetry recitation: Hafez, Rumi, classical Persian literature
- Traditional Persian music and mourning songs
- Sofreh (ceremonial table) arrangements for memorials
- Charitable giving and community support traditions
- Memorial garden and nature connection customs

LANGUAGE & COMMUNICATION:
- Persian/Farsi language funeral terminology and prayers
- Classical Persian poetry and literary references
- Regional dialects and linguistic variations
- Arabic prayers within Persian Islamic context
- Generational language differences in Persian-American families
- Code-switching between Persian and English
- Traditional Persian expressions and sayings about death

PERSIAN NEW YEAR & CALENDAR:
- Nowruz and Persian calendar considerations
- Seasonal memorial observances and timing
- Traditional Persian holidays and mourning period interactions
- Spring cleaning and renewal traditions in grief context
- Persian calendar system and anniversary calculations
- Cultural festivals and community gathering coordination

DIASPORA EXPERIENCE:
- Los Angeles (Tehrangeles) Persian community
- Persian communities in New York, DC, Bay Area
- Maintaining Persian culture in American context
- Cross-generational cultural transmission
- Persian cultural organizations and community centers
- Professional networks and business community support
- Technology use for Iran family connections

MODERN ADAPTATIONS:
- Adapting traditional practices to American funeral homes
- Technology integration for Iran-based family participation
- Economic considerations and community fundraising
- Second and third generation Persian-American practices
- Mixed marriages and cultural integration
- Professional considerations and career impact during mourning

ECONOMIC & SOCIAL CONSIDERATIONS:
- Persian-American business community mutual support
- Professional networks and career considerations
- Cost considerations for traditional elaborate ceremonies
- Community associations and cultural organization support
- Social status and community reputation factors
- Educational achievement emphasis and family expectations

HEALTHCARE & END-OF-LIFE:
- Persian cultural attitudes toward illness and death disclosure
- Family-centered medical decision-making patterns
- Traditional Persian medicine and modern healthcare integration
- Hospice care and family caregiving traditions
- Organ donation perspectives within religious contexts
- Advanced directives and family communication patterns

WOMEN'S ROLES & GENDER CONSIDERATIONS:
- Traditional Persian women's roles in mourning and preparation
- Modern adaptations and gender equality considerations
- Professional Persian women and traditional expectations
- Islamic modest dress requirements and cultural expectations
- Intergenerational differences in gender role expectations
- Mixed marriage considerations and cultural adaptation

ARTS & CULTURAL EXPRESSION:
- Persian calligraphy and artistic memorial elements
- Traditional Persian carpets and decorative elements
- Persian gardens and nature-based memorial concepts
- Classical Persian music and contemporary adaptations
- Persian cuisine and traditional foods for gatherings
- Literature and poetry as comfort and memorial tools

SPECIAL POPULATIONS:
- Elderly Persian immigrants and cultural maintenance
- Young Persian-Americans and identity questions
- Persian students and professionals in American universities
- Mixed heritage families and cultural identity
- Persian refugees and asylum seekers
- Persians in areas with limited community infrastructure

POLITICAL & SOCIAL SENSITIVITIES:
- Iranian government vs. Persian cultural identity distinctions
- Political asylum considerations and family safety
- Travel restrictions and family visit limitations
- Community divisions based on political views
- Religious freedom and practice considerations
- Cultural preservation vs. American integration balance

You provide culturally sensitive guidance while being aware of the complex political situation, religious diversity, and the strong cultural identity that characterizes Persian communities. Always consider religious background, immigration circumstances, generational differences, and the importance of Persian cultural preservation."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.provide_religious_guidance),
                function_tool(self.support_political_sensitivities),
                function_tool(self.guide_persian_customs),
                function_tool(self.recommend_traditional_elements),
                function_tool(self.provide_language_support),
                function_tool(self.connect_community_resources)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=PersianCulturalAgentHooks()
        )
        
        self.description = "Expert in Persian/Iranian funeral traditions, Zoroastrian heritage, Islamic practices, and secular adaptations. Provides guidance on traditional ceremonies, religious accommodations, political sensitivities, and Persian-American community customs across different religious and generational backgrounds."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        religious_background: Optional[str] = None,
        regional_origin: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Persian funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (Islamic, Zoroastrian, secular, etc.)
            religious_background: Shia, Sunni, Zoroastrian, Bahá'í, or secular
            regional_origin: Region of Iran or Persian cultural area
            
        Returns:
            Detailed explanation of Persian funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Persian traditions",
            "cultural_significance": "Historical and cultural context provided",
            "religious_integration": "How religious and cultural elements blend"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        religious_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Persian cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific Persian cultural preferences mentioned
            religious_requirements: Islamic, Zoroastrian, or other religious needs
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Persian elements that can be incorporated",
            "religious_adaptations": "How to accommodate religious requirements",
            "practical_suggestions": "Feasible ways to honor Persian customs"
        }

    async def provide_religious_guidance(
        self,
        context: RunContextWrapper,
        religious_tradition: Optional[str] = None,
        community_connections: Optional[str] = None,
        interfaith_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on religious variations in Persian funeral practices.
        
        Args:
            context: The conversation context
            religious_tradition: Specific religious tradition within Persian culture
            community_connections: Religious community involvement
            interfaith_considerations: Mixed religious background considerations
            
        Returns:
            Religious guidance and accommodation recommendations
        """
        return {
            "religious_guidance_provided": True,
            "tradition_specific_elements": "Religious elements specific to the tradition",
            "community_connections": "Local Persian religious communities",
            "interfaith_solutions": "Solutions for mixed religious backgrounds"
        }

    async def support_political_sensitivities(
        self,
        context: RunContextWrapper,
        political_circumstances: Optional[str] = None,
        family_safety: Optional[str] = None,
        documentation_concerns: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide support considering political sensitivities and asylum considerations.
        
        Args:
            context: The conversation context
            political_circumstances: Political asylum or refugee status
            family_safety: Safety concerns for family in Iran
            documentation_concerns: Documentation or legal status issues
            
        Returns:
            Politically sensitive guidance and support resources
        """
        return {
            "political_support_provided": True,
            "sensitive_considerations": "Political sensitivity guidance for funeral planning",
            "safety_protocols": "Considerations for family safety and privacy",
            "legal_resources": "Legal assistance and advocacy resources"
        }

    async def guide_persian_customs(
        self,
        context: RunContextWrapper,
        custom_type: Optional[str] = None,
        family_traditions: Optional[str] = None,
        modern_adaptations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in traditional Persian customs and their modern adaptations.
        
        Args:
            context: The conversation context
            custom_type: Specific Persian custom or practice
            family_traditions: Family-specific traditions or regional variations
            modern_adaptations: How to adapt traditions to American context
            
        Returns:
            Persian cultural guidance and adaptation suggestions
        """
        return {
            "persian_customs_guidance_provided": True,
            "traditional_practices": "Traditional Persian customs and their meanings",
            "adaptation_strategies": "How to adapt customs to modern American context",
            "family_integration": "How to honor family-specific traditions"
        }

    async def recommend_traditional_elements(
        self,
        context: RunContextWrapper,
        element_type: Optional[str] = None,
        occasion_type: Optional[str] = None,
        budget_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Persian elements for funeral services and memorial gatherings.
        
        Args:
            context: The conversation context
            element_type: Poetry, music, food, decorations, etc.
            occasion_type: Funeral service, memorial gathering, or anniversary
            budget_considerations: Budget limitations for traditional elements
            
        Returns:
            Traditional element recommendations and sourcing guidance
        """
        return {
            "traditional_elements_recommended": True,
            "cultural_elements": "Appropriate Persian cultural elements for the occasion",
            "sourcing_guidance": "Where to obtain traditional Persian elements",
            "budget_alternatives": "Cost-effective ways to incorporate Persian traditions"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        generational_differences: Optional[str] = None,
        literary_elements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Persian language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Persian language interpretation or translation needs
            generational_differences: Multi-generational language preferences
            literary_elements: Persian poetry and literature for memorial use
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Persian language interpretation and translation",
            "literary_elements": "Persian poetry and literature for memorial contexts",
            "cultural_communication": "Persian cultural communication patterns"
        }

    async def connect_community_resources(
        self,
        context: RunContextWrapper,
        location: Optional[str] = None,
        community_type: Optional[str] = None,
        support_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect families with Persian community organizations and support resources.
        
        Args:
            context: The conversation context
            location: Geographic area where family is located
            community_type: Religious, cultural, or professional community preference
            support_needs: Type of community support needed
            
        Returns:
            Persian community resource connections and support coordination
        """
        return {
            "community_resources_provided": True,
            "organizations": "Persian community organizations and cultural centers",
            "professional_networks": "Persian professional and business communities",
            "mutual_aid": "Community mutual aid and support systems"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

persian_cultural_agent = PersianCulturalAgent()

__all__ = ["persian_cultural_agent", "PersianCulturalAgent"]