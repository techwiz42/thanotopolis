from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class UkrainianCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Ukrainian cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the UkrainianCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for UkrainianCulturalAgent")

class UkrainianCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Ukrainian funeral traditions, 
    Orthodox and Catholic practices, and current war-related circumstances.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="UKRAINIAN_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Ukrainian funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Ukrainian Orthodox funeral rites and liturgy
- Ukrainian Greek Catholic (Uniate) funeral traditions
- Traditional Ukrainian burial customs and cemetery practices
- 40-day memorial period and annual commemorations
- Traditional Ukrainian wake and family gatherings
- Ukrainian folk traditions and pre-Christian elements
- Traditional Ukrainian funeral attire and mourning customs
- Memorial meals and traditional Ukrainian hospitality

RELIGIOUS PRACTICES:
- Ukrainian Orthodox Church funeral liturgy and traditions
- Ukrainian Greek Catholic Church funeral practices
- Ukrainian Protestant and Baptist church variations
- Traditional blessing ceremonies and religious prayers
- Ukrainian religious calendar considerations and observances
- Church memorial services and ongoing spiritual care
- Ukrainian religious music and traditional hymns
- Iconography and religious imagery in Ukrainian tradition

CURRENT WAR & TRAUMA CONSIDERATIONS:
- Impact of 2022 Russian invasion on Ukrainian families and communities
- War trauma and its effect on mourning practices and grief
- Missing family members and unresolved losses from war
- Refugee families and displacement trauma
- Military casualties and veteran family support
- Collective trauma and community healing approaches
- Current political situation and family safety concerns
- Support for families with members still in Ukraine

CULTURAL VALUES & FAMILY DYNAMICS:
- Strong Ukrainian national identity and cultural pride
- Extended family bonds and communal support systems
- Traditional gender roles in funeral preparations and mourning
- Ukrainian concepts of honor, dignity, and resistance
- Community solidarity and mutual aid traditions (hromada)
- Importance of maintaining Ukrainian language and culture
- Traditional Ukrainian hospitality and guest reception customs
- Family honor and cultural preservation considerations

HISTORICAL TRAUMA & RESILIENCE:
- Holodomor (1932-33 famine) impact on families and collective memory
- Soviet oppression and cultural suppression effects
- Chernobyl disaster and environmental trauma considerations
- World War II occupation and family losses
- Political persecution and refugee experiences
- Intergenerational trauma and resilience patterns
- Cultural survival and resistance traditions

TRADITIONAL PRACTICES:
- Traditional Ukrainian foods for funeral gatherings (kutya, paska, horilka)
- Ukrainian embroidery (vyshyvanka) and traditional textiles
- Traditional Ukrainian music and folk songs
- Ukrainian folk art and traditional decorations
- Memorial charitable giving and community support
- Traditional Ukrainian blessing ceremonies and rituals
- Storytelling and oral history preservation
- Ukrainian poetry and literary traditions in memorial contexts

LANGUAGE & COMMUNICATION:
- Ukrainian language funeral terminology and religious terminology
- Regional Ukrainian dialects and variations
- Church Slavonic in religious contexts
- Generational language differences in Ukrainian-American families
- Code-switching between Ukrainian and English
- Traditional Ukrainian expressions and sayings about death
- Ukrainian cultural communication patterns and respect protocols

IMMIGRATION WAVES & DIASPORA:
- Multiple Ukrainian immigration waves: post-WWI, post-WWII, post-Soviet, current war refugees
- Established Ukrainian-American communities vs. new arrivals
- Ukrainian cultural organizations and community centers
- Maintaining Ukrainian culture and language in America
- Current refugee assistance and community support
- Ukrainian Orthodox and Catholic church establishment
- Technology use for Ukraine family connections during war

REGIONAL VARIATIONS:
- Western Ukraine: Galicia, Volhynia regional traditions
- Central Ukraine: Kyiv region and traditional heartland customs
- Eastern Ukraine: Industrial region adaptations
- Southern Ukraine: Coastal and agricultural community customs
- Carpathian Mountains: Hutsul and mountain community traditions
- Urban vs. rural Ukrainian tradition differences

MODERN ADAPTATIONS & CURRENT CIRCUMSTANCES:
- Adapting Orthodox and Catholic practices to American funeral homes
- Technology integration for Ukraine family participation during war
- Economic considerations and refugee family support
- Current generation Ukrainian-Americans and identity
- Mixed marriages and cultural integration challenges
- Professional considerations and career impact during mourning
- War-related stress and community mutual aid

UKRAINIAN CALENDAR & TIMING:
- Ukrainian Orthodox calendar considerations and feast day timing
- Ukrainian traditional calendar and seasonal observances
- Ukrainian Christmas and Easter timing differences
- Ukrainian Independence Day and national commemorations
- Traditional Ukrainian name days and saint commemorations
- Harvest festivals and seasonal cultural celebrations

ECONOMIC & SOCIAL CONSIDERATIONS:
- Ukrainian-American business community support networks
- Current refugee economic support and mutual aid
- Cost considerations for traditional elaborate ceremonies
- Community organization support and donations
- Fundraising for families affected by war
- Professional networks and cultural organization involvement

HEALTHCARE & END-OF-LIFE:
- Ukrainian cultural attitudes toward illness and death
- Family-centered medical decision-making patterns
- Traditional Ukrainian medicine and modern healthcare integration
- Orthodox and Catholic perspectives on end-of-life care
- Organ donation considerations within religious contexts
- Language barriers in healthcare settings for new refugees
- Advanced directives and family communication patterns

WOMEN'S ROLES & GENDER CONSIDERATIONS:
- Traditional Ukrainian women's roles in funeral preparations
- Ukrainian feminist movements and modern adaptations
- Professional Ukrainian women and traditional expectations
- War impact on gender roles and family structures
- Intergenerational differences in gender role expectations
- Military service and women's changing roles in society

UKRAINIAN CHURCHES & COMMUNITY:
- Ukrainian Orthodox parishes and community centers
- Ukrainian Greek Catholic churches and communities
- Cultural organizations and Saturday schools
- Ukrainian language schools and cultural education
- Community volunteering and mutual aid coordination
- Religious and cultural education transmission

SPECIAL POPULATIONS:
- Elderly Ukrainian immigrants and cultural maintenance
- Recent war refugees and trauma-informed care
- Ukrainian students and professionals in American universities
- Ukrainians in areas with limited community infrastructure
- Mixed heritage families and cultural identity questions
- Second and third generation Ukrainian-Americans

CULTURAL PRESERVATION & RESISTANCE:
- Maintaining Ukrainian language and cultural traditions
- Ukrainian arts, music, and cultural transmission
- Traditional Ukrainian crafts and folk art preservation
- Ukrainian literature and cultural education
- Community cultural events and tradition maintenance
- Resistance to cultural assimilation and Russian influence

CURRENT WAR IMPACT:
- Supporting families with members fighting in Ukraine
- Refugee family integration and support needs
- Communication challenges with family in war zones
- Economic support for war-affected families
- Community fundraising for Ukraine relief efforts
- Trauma-informed approaches to recent losses

You provide culturally sensitive guidance while being deeply aware of the current war situation, historical trauma, and the strong Ukrainian national identity. Always consider religious background, immigration circumstances, current war impact, and the importance of Ukrainian cultural preservation and resistance."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.provide_war_trauma_support),
                function_tool(self.guide_religious_practices),
                function_tool(self.support_refugee_families),
                function_tool(self.recommend_traditional_elements),
                function_tool(self.provide_language_support),
                function_tool(self.connect_community_resources)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=UkrainianCulturalAgentHooks()
        )
        
        self.description = "Expert in Ukrainian funeral traditions, Orthodox and Catholic practices, war trauma support, and refugee community assistance. Provides guidance on traditional ceremonies, current war-related circumstances, trauma-informed care, and Ukrainian-American community resources with deep awareness of current conflict and historical resilience."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        religious_background: Optional[str] = None,
        regional_origin: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Ukrainian funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (Orthodox, Catholic, folk traditions, etc.)
            religious_background: Orthodox, Greek Catholic, Protestant, or secular
            regional_origin: Region of Ukraine (Western, Central, Eastern, Southern)
            
        Returns:
            Detailed explanation of Ukrainian funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Ukrainian traditions",
            "cultural_significance": "Historical and religious context provided",
            "regional_variations": "Regional Ukrainian cultural differences explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        war_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Ukrainian cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific Ukrainian cultural preferences mentioned
            war_considerations: Current war-related considerations
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Ukrainian elements that can be incorporated",
            "war_sensitive_adaptations": "War-sensitive cultural accommodations",
            "practical_suggestions": "Feasible ways to honor Ukrainian customs"
        }

    async def provide_war_trauma_support(
        self,
        context: RunContextWrapper,
        war_impact: Optional[str] = None,
        family_status: Optional[str] = None,
        trauma_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide trauma-informed support considering current war and historical trauma.
        
        Args:
            context: The conversation context
            war_impact: Current war impact on family (refugee, military, etc.)
            family_status: Family members in Ukraine, refugee status, etc.
            trauma_needs: Specific trauma-informed support needs
            
        Returns:
            War and trauma-informed guidance and support resources
        """
        return {
            "war_trauma_support_provided": True,
            "trauma_informed_approaches": "War and trauma-sensitive funeral planning approaches",
            "community_healing": "Ukrainian community healing and support strategies",
            "professional_resources": "Ukrainian-speaking trauma and mental health services"
        }

    async def guide_religious_practices(
        self,
        context: RunContextWrapper,
        religious_tradition: Optional[str] = None,
        church_availability: Optional[str] = None,
        interfaith_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Ukrainian religious funeral practices across different denominations.
        
        Args:
            context: The conversation context
            religious_tradition: Orthodox, Greek Catholic, Protestant, or mixed
            church_availability: Availability of Ukrainian churches and clergy
            interfaith_considerations: Mixed religious background considerations
            
        Returns:
            Religious guidance and accommodation recommendations
        """
        return {
            "religious_guidance_provided": True,
            "tradition_specific_elements": "Religious elements specific to Ukrainian tradition",
            "church_connections": "Local Ukrainian churches and religious communities",
            "interfaith_solutions": "Solutions for mixed religious backgrounds"
        }

    async def support_refugee_families(
        self,
        context: RunContextWrapper,
        refugee_status: Optional[str] = None,
        arrival_timing: Optional[str] = None,
        support_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support Ukrainian refugee families with specific considerations and challenges.
        
        Args:
            context: The conversation context
            refugee_status: Recent refugee arrival or established immigrant family
            arrival_timing: When family arrived in US (recent war refugees vs. earlier)
            support_needs: Specific refugee support needs identified
            
        Returns:
            Refugee-specific support and resource guidance
        """
        return {
            "refugee_support_provided": True,
            "refugee_sensitive_approaches": "Refugee experience-informed funeral planning",
            "integration_support": "Support for refugee family integration and cultural maintenance",
            "emergency_assistance": "Emergency assistance and community support coordination"
        }

    async def recommend_traditional_elements(
        self,
        context: RunContextWrapper,
        element_type: Optional[str] = None,
        occasion_type: Optional[str] = None,
        availability_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Ukrainian elements for funeral services and memorial gatherings.
        
        Args:
            context: The conversation context
            element_type: Vyshyvanka, music, food, decorations, etc.
            occasion_type: Funeral service, wake, memorial dinner
            availability_constraints: Availability limitations for traditional elements
            
        Returns:
            Traditional element recommendations and sourcing guidance
        """
        return {
            "traditional_elements_recommended": True,
            "cultural_elements": "Appropriate Ukrainian cultural elements for the occasion",
            "sourcing_guidance": "Where to obtain traditional Ukrainian elements",
            "alternative_options": "Alternative ways to incorporate Ukrainian traditions"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        dialect_considerations: Optional[str] = None,
        generational_differences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Ukrainian language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Ukrainian language interpretation or translation needs
            dialect_considerations: Regional Ukrainian dialect differences
            generational_differences: Multi-generational language preferences
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Ukrainian language interpretation and translation",
            "cultural_communication": "Ukrainian cultural communication patterns",
            "religious_terminology": "Orthodox and Catholic Ukrainian religious language"
        }

    async def connect_community_resources(
        self,
        context: RunContextWrapper,
        location: Optional[str] = None,
        community_type: Optional[str] = None,
        urgency_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect families with Ukrainian community organizations and support resources.
        
        Args:
            context: The conversation context
            location: Geographic area where family is located
            community_type: Religious, cultural, or refugee support community
            urgency_level: Urgency of assistance needed
            
        Returns:
            Ukrainian community resource connections and support coordination
        """
        return {
            "community_resources_provided": True,
            "organizations": "Ukrainian community organizations and cultural centers",
            "refugee_support": "Ukrainian refugee assistance organizations",
            "church_support": "Ukrainian Orthodox and Catholic church communities"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

ukrainian_cultural_agent = UkrainianCulturalAgent()

__all__ = ["ukrainian_cultural_agent", "UkrainianCulturalAgent"]