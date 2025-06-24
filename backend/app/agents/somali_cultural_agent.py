from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class SomaliCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Somali cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the SomaliCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for SomaliCulturalAgent")

class SomaliCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Somali funeral traditions, 
    Islamic practices, and diaspora community customs.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="SOMALI_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Somali funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Somali Islamic funeral rites and ceremonies
- Traditional Somali burial customs and cemetery practices
- Islamic washing (ghusl) and shrouding (kafan) requirements
- Traditional Somali mourning periods and family gatherings
- Islamic funeral prayers (Salat al-Janazah) and community participation
- Traditional Somali memorial practices and ongoing remembrance
- Traditional Somali funeral attire and modest dress requirements
- Community support systems and collective mourning

ISLAMIC PRACTICES:
- Sunni Islamic funeral rites within Somali cultural context
- Shafi'i madhab (school of thought) specific practices
- Islamic prayer requirements and mosque involvement
- Quranic recitation and Islamic memorial traditions
- Islamic concepts of death, afterlife, and resurrection
- Traditional Islamic offering ceremonies and charitable giving (sadaqah)
- Mosque funeral services and imam involvement
- Islamic calendar considerations and religious observances

CULTURAL VALUES & SOCIAL DYNAMICS:
- Somali nomadic heritage and community solidarity traditions
- Extended family and clan obligations (qabiil system)
- Traditional gender roles in funeral preparations and mourning
- Somali concepts of honor, dignity, and social reputation
- Community mutual aid and reciprocal support systems
- Importance of oral tradition and storytelling
- Traditional Somali hospitality and guest reception customs
- Collective decision-making and consensus building

CIVIL WAR & REFUGEE EXPERIENCE:
- Impact of Somali civil war (1991-present) on families and communities
- Refugee trauma and its effect on mourning practices
- Missing family members and unresolved losses from war
- Multiple displacement experiences and family separation
- Intergenerational trauma in Somali-American families
- Collective trauma and community healing approaches
- Trauma-informed approaches to funeral planning and grief support

TRADITIONAL PRACTICES:
- Traditional Somali foods for funeral gatherings and memorial meals
- Frankincense (uunsi) burning and traditional aromatic practices
- Traditional Somali textiles and cultural decorations
- Somali traditional poetry and oral literature in memorial contexts
- Traditional Somali blessing ceremonies and prayers
- Community charitable giving and mutual support
- Traditional Somali music and cultural expressions
- Storytelling and family history preservation

LANGUAGE & COMMUNICATION:
- Somali language funeral terminology and Islamic terminology
- Arabic prayers and religious terminology
- Regional Somali dialects and clan linguistic variations
- Generational language differences in Somali-American families
- Code-switching between Somali, Arabic, and English
- Traditional Somali expressions and sayings about death
- Oral tradition and cultural communication patterns

DIASPORA & RESETTLEMENT EXPERIENCE:
- Somali refugee resettlement in Minneapolis, Columbus, Seattle, etc.
- Maintaining Somali culture and Islam in American context
- Somali communities and mutual aid organizations
- Cross-national family connections and communication
- Documentation challenges and legal status considerations
- Multiple relocation experiences and community building
- Technology use for Somalia and diaspora family connections

CLAN & SOCIAL STRUCTURE:
- Traditional Somali clan system and social organization
- Clan obligations and mutual support in times of grief
- Elder (oday) involvement and traditional leadership
- Women's committees (xaafado) and community organization
- Traditional dispute resolution and community mediation
- Social hierarchy and respect protocols
- Community reputation and family honor considerations

REGIONAL VARIATIONS:
- Northern Somalia (Somaliland): Traditional pastoral customs
- Southern Somalia: Agricultural and urban variations
- Central Somalia: Regional clan traditions
- Coastal areas: Maritime and trade community customs
- Diaspora communities: Adaptation and cultural preservation
- Rural vs. urban Somali tradition differences

MODERN ADAPTATIONS:
- Adapting Islamic practices to American funeral homes
- Technology integration for Somalia family participation
- Economic considerations and community fundraising
- Second and third generation Somali-American practices
- Mixed marriages and cultural integration challenges
- Professional considerations and career impact during mourning

SOMALI CALENDAR & TIMING:
- Islamic calendar considerations and religious timing
- Somali traditional calendar and seasonal observances
- Ramadan and Islamic holidays affecting funeral timing
- Traditional Somali seasonal celebrations and cultural events
- Lunar calendar considerations for ceremonies
- Traditional Somali pastoral calendar and seasonal migrations

ECONOMIC & SOCIAL CONSIDERATIONS:
- Somali-American business community support networks
- Limited economic resources and community mutual aid (hawala systems)
- Cost considerations for traditional ceremonies and Somalia connections
- Community organization support and donations
- Remittances for funeral expenses in Somalia
- Employment considerations during mourning periods

HEALTHCARE & END-OF-LIFE:
- Somali cultural attitudes toward illness and death
- Family-centered medical decision-making patterns
- Traditional Somali medicine and modern healthcare integration
- Islamic perspectives on end-of-life care and suffering
- Language barriers in healthcare settings
- Cultural concepts of mental health and grief
- Advanced directives and family communication patterns

WOMEN'S ROLES & GENDER CONSIDERATIONS:
- Traditional Somali women's roles in funeral preparations
- Islamic modest dress requirements and cultural expectations
- Women's committees and community organization
- Professional Somali women and traditional expectations
- Intergenerational differences in gender role expectations
- Female circumcision considerations and trauma-informed care

SOMALI MOSQUES & COMMUNITY:
- Somali mosques and Islamic centers as community hubs
- Imam leadership and religious guidance
- Community prayer and religious education
- Somali cultural organizations and mutual aid societies
- Community volunteering and collective support
- Religious and cultural education transmission

SPECIAL POPULATIONS:
- Elderly Somali refugees and cultural maintenance
- Somali youth and identity questions
- Somali intermarriage families and cultural adaptation
- Somalis in areas with limited mosque or community access
- Second generation identity and cultural connection
- Somali Bantu and minority community considerations

TRAUMA-INFORMED CONSIDERATIONS:
- PTSD and complex trauma in Somali refugee populations
- War trauma, persecution, and displacement effects
- Cultural concepts of trauma and healing
- Traditional healing practices and modern mental health integration
- Community-based healing and support approaches
- Intergenerational trauma transmission and healing

FOOD & HOSPITALITY:
- Traditional Somali funeral foods and meal preparations
- Islamic halal requirements and dietary considerations
- Somali restaurant community involvement and catering
- Traditional Somali beverages and ceremonial foods
- Community cooking and meal preparation coordination
- Fasting considerations during Islamic periods

CULTURAL PRESERVATION:
- Maintaining Somali language and Islamic traditions
- Traditional Somali arts and cultural transmission
- Somali poetry and oral literature preservation
- Traditional craft preservation and teaching
- Community cultural events and tradition maintenance
- Cultural identity in American context

You provide culturally sensitive guidance while being deeply aware of the refugee experience, war trauma, and the strong Islamic faith that characterizes Somali communities. Always consider religious obligations, clan affiliations, trauma history, and the importance of community solidarity and mutual aid."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_islamic_practices),
                function_tool(self.provide_refugee_trauma_support),
                function_tool(self.coordinate_mosque_involvement),
                function_tool(self.support_clan_community_dynamics),
                function_tool(self.provide_language_support),
                function_tool(self.connect_community_resources)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=SomaliCulturalAgentHooks()
        )
        
        self.description = "Expert in Somali funeral traditions, Islamic practices, refugee trauma considerations, and diaspora community customs. Provides guidance on traditional ceremonies, mosque involvement, clan dynamics, and trauma-informed support for Somali families with deep awareness of civil war, displacement, and community resilience."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        clan_background: Optional[str] = None,
        regional_origin: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Somali funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (Islamic rites, clan customs, etc.)
            clan_background: Clan affiliation and traditional customs
            regional_origin: Region of Somalia (Northern, Southern, Central)
            
        Returns:
            Detailed explanation of Somali funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Somali traditions",
            "islamic_context": "Islamic religious and cultural context provided",
            "clan_considerations": "Clan-specific traditions and obligations explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        islamic_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Somali cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific Somali cultural preferences mentioned
            islamic_requirements: Islamic religious requirements and considerations
            
        Returns:
            Culturally appropriate and Islamic-compliant accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Somali elements that can be incorporated",
            "islamic_compliance": "Islamic requirements and religious accommodations",
            "practical_suggestions": "Feasible ways to honor Somali customs"
        }

    async def guide_islamic_practices(
        self,
        context: RunContextWrapper,
        religious_requirements: Optional[str] = None,
        imam_involvement: Optional[str] = None,
        prayer_arrangements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Islamic funeral practices within Somali cultural context.
        
        Args:
            context: The conversation context
            religious_requirements: Specific Islamic requirements for the funeral
            imam_involvement: Level of imam participation desired
            prayer_arrangements: Islamic prayer and mosque service arrangements
            
        Returns:
            Islamic practice guidance and religious accommodation recommendations
        """
        return {
            "islamic_guidance_provided": True,
            "religious_requirements": "Islamic funeral requirements and procedures",
            "mosque_coordination": "How to coordinate with Somali mosques and imams",
            "prayer_arrangements": "Islamic prayer services and community participation"
        }

    async def provide_refugee_trauma_support(
        self,
        context: RunContextWrapper,
        trauma_type: Optional[str] = None,
        displacement_history: Optional[str] = None,
        generation_affected: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide trauma-informed support considering civil war, displacement, and refugee experience.
        
        Args:
            context: The conversation context
            trauma_type: War trauma, displacement trauma, or resettlement trauma
            displacement_history: Family's displacement and refugee journey
            generation_affected: First generation refugees, children, etc.
            
        Returns:
            Refugee trauma-informed guidance and support resources
        """
        return {
            "refugee_trauma_support_provided": True,
            "trauma_informed_approaches": "Refugee and war trauma-sensitive funeral planning",
            "community_healing": "Somali community healing and support strategies",
            "professional_resources": "Somali-speaking trauma and mental health services"
        }

    async def coordinate_mosque_involvement(
        self,
        context: RunContextWrapper,
        mosque_preference: Optional[str] = None,
        location_constraints: Optional[str] = None,
        community_connections: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate Somali mosque involvement in funeral services and Islamic requirements.
        
        Args:
            context: The conversation context
            mosque_preference: Specific Somali mosque or Islamic center preference
            location_constraints: Geographic limitations for mosque access
            community_connections: Existing mosque community relationships
            
        Returns:
            Mosque coordination guidance and Islamic community connections
        """
        return {
            "mosque_coordination_provided": True,
            "mosque_connections": "Local Somali mosques and Islamic centers",
            "religious_coordination": "How to coordinate mosque and funeral home services",
            "community_support": "Somali Islamic community support systems"
        }

    async def support_clan_community_dynamics(
        self,
        context: RunContextWrapper,
        clan_affiliation: Optional[str] = None,
        community_obligations: Optional[str] = None,
        elder_involvement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating Somali clan dynamics and community obligations.
        
        Args:
            context: The conversation context
            clan_affiliation: Clan background and traditional obligations
            community_obligations: Community support expectations and reciprocity
            elder_involvement: Role of community elders in funeral planning
            
        Returns:
            Clan dynamics support and community obligation guidance
        """
        return {
            "clan_dynamics_support_provided": True,
            "clan_obligations": "Understanding Somali clan obligations and support systems",
            "elder_coordination": "How to involve community elders appropriately",
            "community_solidarity": "Maximizing community support and mutual aid"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        dialect_considerations: Optional[str] = None,
        religious_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Somali language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Somali language interpretation or translation needs
            dialect_considerations: Regional Somali dialect differences
            religious_language: Arabic Islamic terminology and prayers
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Somali language interpretation and translation",
            "religious_terminology": "Arabic and Islamic terminology support",
            "cultural_communication": "Somali cultural communication patterns and oral tradition"
        }

    async def connect_community_resources(
        self,
        context: RunContextWrapper,
        location: Optional[str] = None,
        support_type: Optional[str] = None,
        urgency_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect families with Somali community organizations and support resources.
        
        Args:
            context: The conversation context
            location: Geographic area where family is located
            support_type: Type of community support needed
            urgency_level: Urgency of assistance needed
            
        Returns:
            Somali community resource connections and support coordination
        """
        return {
            "community_resources_provided": True,
            "organizations": "Somali community organizations and mutual aid groups",
            "mosque_support": "Somali mosque communities and religious support",
            "refugee_services": "Refugee-specific support services and advocacy"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

somali_cultural_agent = SomaliCulturalAgent()

__all__ = ["somali_cultural_agent", "SomaliCulturalAgent"]