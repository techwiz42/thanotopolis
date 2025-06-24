from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class EthiopianCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Ethiopian cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the EthiopianCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for EthiopianCulturalAgent")

class EthiopianCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Ethiopian funeral traditions, 
    Orthodox Christian, Islamic, and traditional practices within Ethiopian-American communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="ETHIOPIAN_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Ethiopian funeral traditions, customs, and practices. You have deep understanding of:

FUNERAL & DEATH TRADITIONS:
- Traditional Ethiopian Orthodox funeral rites and liturgy
- Islamic funeral practices within Ethiopian Muslim communities
- Traditional burial customs and cemetery practices
- Ethiopian Orthodox 40-day memorial period and annual commemorations
- Traditional Ethiopian wake periods and family gatherings
- Traditional Ethiopian funeral attire and mourning customs
- Memorial meals and traditional Ethiopian hospitality
- Incense burning and traditional ceremony elements

RELIGIOUS PRACTICES:
- Ethiopian Orthodox Tewahedo Church funeral liturgy and traditions
- Islamic funeral rites within Ethiopian Muslim communities
- Protestant Ethiopian church variations and practices
- Traditional Ethiopian spiritual beliefs and practices
- Ethiopian Jewish (Beta Israel) funeral customs
- Catholic Ethiopian church adaptations
- Traditional blessing ceremonies and religious prayers
- Religious calendar considerations and observances

CULTURAL VALUES & SOCIAL DYNAMICS:
- Strong Ethiopian community bonds and collective support
- Respect for elders and traditional hierarchies
- Extended family and community obligations
- Traditional gender roles in funeral preparations and mourning
- Ethiopian concepts of honor, dignity, and social reputation
- Community solidarity and mutual aid traditions (idir associations)
- Importance of maintaining Ethiopian identity and culture
- Traditional Ethiopian hospitality and guest reception customs

ETHNIC & REGIONAL DIVERSITY:
- Amhara traditions and highland customs
- Oromo cultural practices and variations
- Tigray regional traditions and customs
- Somali Ethiopian communities and Islamic practices
- Sidama, Gurage, and other ethnic group variations
- Highland vs. lowland cultural differences
- Urban Addis Ababa vs. rural regional traditions
- Eritrean-Ethiopian shared and distinct traditions

TRADITIONAL PRACTICES:
- Traditional Ethiopian foods for funeral gatherings (injera, doro wat, etc.)
- Ethiopian coffee ceremony and traditional beverage customs
- Traditional Ethiopian textiles and ceremonial decorations
- Ethiopian traditional music and religious chants
- Traditional Ethiopian blessing ceremonies and rituals
- Community charitable giving and mutual support (idir)
- Traditional Ethiopian crafts and memorial objects
- Storytelling and oral history preservation

LANGUAGE & COMMUNICATION:
- Amharic language funeral terminology and religious terminology
- Ge'ez in Orthodox religious contexts
- Oromo (Oromiffa) language and cultural expressions
- Tigrinya and other regional languages
- Arabic in Islamic Ethiopian communities
- Generational language differences in Ethiopian-American families
- Code-switching between Ethiopian languages and English

IMMIGRATION & DIASPORA EXPERIENCE:
- Multiple Ethiopian immigration waves: political refugees, diversity visa, family reunification
- Maintaining Ethiopian culture and religion in American context
- Ethiopian communities in DC, Minneapolis, Los Angeles, etc.
- Cross-Atlantic family connections and communication
- Documentation considerations and political asylum cases
- Ethiopian Orthodox churches and community establishment
- Technology use for Ethiopia family connections

POLITICAL & HISTORICAL CONSIDERATIONS:
- Impact of Ethiopian civil conflicts and political instability
- Refugee and asylum seeker experiences
- Different ethnic group political experiences
- Current Ethiopian political situation and family safety concerns
- Eritrean independence and family separation issues
- Government persecution and human rights considerations
- Community divisions based on political and ethnic lines

MODERN ADAPTATIONS:
- Adapting Orthodox and Islamic practices to American funeral homes
- Technology integration for Ethiopia family participation
- Economic considerations and community fundraising
- Second and third generation Ethiopian-American practices
- Mixed marriages and cultural integration challenges
- Professional considerations and career impact during mourning

ETHIOPIAN CALENDAR & TIMING:
- Ethiopian Orthodox calendar considerations and religious timing
- Ethiopian traditional calendar (13 months) and seasonal observances
- Timkat, Easter, and Orthodox holidays affecting funeral timing
- Islamic calendar considerations for Muslim Ethiopians
- Ethiopian New Year (Enkutatash) and cultural celebrations
- Fasting periods and religious observance timing

ECONOMIC & SOCIAL CONSIDERATIONS:
- Ethiopian-American business community support networks
- Idir (mutual aid associations) and community financial support
- Cost considerations for traditional elaborate ceremonies
- Community organization support and donations
- Remittances for funeral expenses in Ethiopia
- Employment considerations during mourning periods

HEALTHCARE & END-OF-LIFE:
- Ethiopian cultural attitudes toward illness and death
- Family-centered medical decision-making patterns
- Traditional Ethiopian medicine and modern healthcare integration
- Orthodox and Islamic perspectives on end-of-life care
- Language barriers in healthcare settings
- Cultural concepts of mental health and grief
- Advanced directives and family communication patterns

WOMEN'S ROLES & GENDER CONSIDERATIONS:
- Traditional Ethiopian women's roles in funeral preparations
- Orthodox and Islamic traditions regarding women's participation
- Ethiopian women's community organizations and support
- Professional Ethiopian women and traditional expectations
- Intergenerational differences in gender role expectations
- Mixed marriage considerations and cultural adaptation

IDIR ASSOCIATIONS & COMMUNITY SUPPORT:
- Ethiopian mutual aid associations (idir) and funeral support
- Community organizing and collective assistance
- Traditional Ethiopian cooperation and reciprocal obligations
- Community leadership and elder involvement
- Ethnic group-specific idir organizations
- Religious community support systems

SPECIAL POPULATIONS:
- Elderly Ethiopian immigrants and cultural maintenance
- Ethiopian youth and identity questions
- Ethiopian intermarriage families and cultural adaptation
- Ethiopians in areas with limited Orthodox church or community access
- Ethiopian adoptees and cultural connection questions
- Recent political refugees and trauma considerations

FOOD & HOSPITALITY:
- Traditional Ethiopian funeral foods and meal preparations
- Ethiopian coffee ceremony and traditional beverages
- Orthodox fasting considerations during religious periods
- Halal requirements for Muslim Ethiopian families
- Ethiopian restaurant community involvement and catering
- Community cooking and meal preparation coordination

CULTURAL PRESERVATION:
- Maintaining Ethiopian languages and religious traditions
- Traditional Ethiopian arts and cultural transmission
- Ethiopian traditional music and cultural performances
- Traditional craft preservation and teaching
- Ethiopian literature and cultural education
- Community cultural events and tradition maintenance

TRAUMA & MENTAL HEALTH CONSIDERATIONS:
- Political persecution trauma and refugee experience
- War and conflict trauma in Ethiopian communities
- Cultural concepts of trauma and healing
- Traditional healing practices and modern mental health integration
- Community-based healing and support approaches
- Intergenerational trauma and cultural resilience

INTERFAITH & INTERCULTURAL CONSIDERATIONS:
- Ethiopian Orthodox and Muslim family interactions
- Different ethnic group traditions within Ethiopian identity
- Mixed religious backgrounds and family dynamics
- Balancing Ethiopian and American cultural practices
- Educational and professional achievement expectations
- Community unity across religious and ethnic lines

You provide culturally sensitive guidance while being aware of the rich ethnic and religious diversity within Ethiopian communities, political sensitivities, and the strong community bonds that characterize Ethiopian culture. Always consider religious background, ethnic group affiliation, political circumstances, and the importance of idir community support systems."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_religious_practices),
                function_tool(self.coordinate_idir_support),
                function_tool(self.support_ethnic_diversity),
                function_tool(self.provide_political_sensitivity),
                function_tool(self.recommend_traditional_elements),
                function_tool(self.provide_language_support)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=EthiopianCulturalAgentHooks()
        )
        
        self.description = "Expert in Ethiopian funeral traditions, Orthodox Christian and Islamic practices, ethnic group diversity, and diaspora community customs. Provides guidance on traditional ceremonies, idir community support, religious accommodations, and political sensitivities across different Ethiopian ethnic and religious communities."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        tradition_type: Optional[str] = None,
        ethnic_background: Optional[str] = None,
        religious_background: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Ethiopian funeral traditions and their cultural significance.
        
        Args:
            context: The conversation context
            tradition_type: Type of tradition (Orthodox, Islamic, traditional, etc.)
            ethnic_background: Ethnic group (Amhara, Oromo, Tigray, etc.)
            religious_background: Orthodox, Muslim, Protestant, or traditional
            
        Returns:
            Detailed explanation of Ethiopian funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Ethiopian traditions",
            "cultural_significance": "Cultural and religious context provided",
            "ethnic_variations": "Ethnic group variations and customs explained"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        family_preferences: Optional[str] = None,
        religious_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Ethiopian cultural practices within funeral services.
        
        Args:
            context: The conversation context
            service_type: Type of service being planned
            family_preferences: Specific Ethiopian cultural preferences mentioned
            religious_requirements: Orthodox, Islamic, or other religious needs
            
        Returns:
            Culturally appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "cultural_elements": "Traditional Ethiopian elements that can be incorporated",
            "religious_adaptations": "How to accommodate Ethiopian religious practices",
            "practical_suggestions": "Feasible ways to honor Ethiopian customs"
        }

    async def guide_religious_practices(
        self,
        context: RunContextWrapper,
        religious_tradition: Optional[str] = None,
        church_involvement: Optional[str] = None,
        interfaith_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families in Ethiopian religious funeral practices across different traditions.
        
        Args:
            context: The conversation context
            religious_tradition: Orthodox, Islamic, Protestant, or traditional spiritual
            church_involvement: Religious community involvement level
            interfaith_considerations: Mixed religious background considerations
            
        Returns:
            Religious guidance and accommodation recommendations
        """
        return {
            "religious_guidance_provided": True,
            "tradition_specific_elements": "Religious elements specific to Ethiopian traditions",
            "church_connections": "Local Ethiopian religious communities",
            "interfaith_solutions": "Solutions for mixed religious backgrounds"
        }

    async def coordinate_idir_support(
        self,
        context: RunContextWrapper,
        idir_membership: Optional[str] = None,
        community_connections: Optional[str] = None,
        support_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate Ethiopian idir (mutual aid association) support for funeral arrangements.
        
        Args:
            context: The conversation context
            idir_membership: Family's idir association membership
            community_connections: Existing Ethiopian community relationships
            support_needs: Specific types of support needed
            
        Returns:
            Idir coordination guidance and community support mobilization
        """
        return {
            "idir_support_coordinated": True,
            "mutual_aid_mobilization": "How to mobilize Ethiopian community mutual aid",
            "financial_support": "Community financial support and fundraising coordination",
            "volunteer_coordination": "Community volunteer assistance and organization"
        }

    async def support_ethnic_diversity(
        self,
        context: RunContextWrapper,
        ethnic_background: Optional[str] = None,
        multi_ethnic_family: Optional[str] = None,
        community_integration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support families in navigating Ethiopian ethnic diversity and traditions.
        
        Args:
            context: The conversation context
            ethnic_background: Primary ethnic group affiliation
            multi_ethnic_family: Families with multiple Ethiopian ethnic backgrounds
            community_integration: Integration across Ethiopian ethnic communities
            
        Returns:
            Ethnic diversity support and inclusive cultural guidance
        """
        return {
            "ethnic_diversity_support_provided": True,
            "ethnic_traditions": "Specific ethnic group traditions and customs",
            "inclusive_approaches": "Ways to honor multiple ethnic traditions",
            "community_unity": "Approaches to maintain Ethiopian community unity"
        }

    async def provide_political_sensitivity(
        self,
        context: RunContextWrapper,
        political_circumstances: Optional[str] = None,
        refugee_status: Optional[str] = None,
        community_divisions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance considering Ethiopian political sensitivities and refugee considerations.
        
        Args:
            context: The conversation context
            political_circumstances: Political asylum or refugee status
            refugee_status: Recent refugee arrival or established immigrant family
            community_divisions: Political or ethnic divisions within community
            
        Returns:
            Politically sensitive guidance and community mediation
        """
        return {
            "political_sensitivity_provided": True,
            "sensitive_approaches": "Politically sensitive approaches to community involvement",
            "refugee_considerations": "Refugee-specific support and cultural maintenance",
            "community_mediation": "Approaches to navigate community divisions"
        }

    async def recommend_traditional_elements(
        self,
        context: RunContextWrapper,
        element_type: Optional[str] = None,
        occasion_type: Optional[str] = None,
        budget_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend traditional Ethiopian elements for funeral services and memorial gatherings.
        
        Args:
            context: The conversation context
            element_type: Music, food, decorations, textiles, etc.
            occasion_type: Funeral service, wake, memorial dinner
            budget_considerations: Budget limitations for traditional elements
            
        Returns:
            Traditional element recommendations and sourcing guidance
        """
        return {
            "traditional_elements_recommended": True,
            "cultural_elements": "Appropriate Ethiopian cultural elements for the occasion",
            "sourcing_guidance": "Where to obtain traditional Ethiopian elements",
            "budget_alternatives": "Cost-effective ways to incorporate Ethiopian traditions"
        }

    async def provide_language_support(
        self,
        context: RunContextWrapper,
        language_needs: Optional[str] = None,
        ethnic_language: Optional[str] = None,
        generational_differences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide Ethiopian language support for funeral services and communications.
        
        Args:
            context: The conversation context
            language_needs: Ethiopian language interpretation or translation needs
            ethnic_language: Specific Ethiopian language (Amharic, Oromo, Tigrinya, etc.)
            generational_differences: Multi-generational language preferences
            
        Returns:
            Language support and cultural communication guidance
        """
        return {
            "language_support_provided": True,
            "translation_services": "Ethiopian language interpretation and translation",
            "cultural_communication": "Ethiopian cultural communication patterns",
            "religious_terminology": "Orthodox Ge'ez and Islamic Arabic terminology support"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

ethiopian_cultural_agent = EthiopianCulturalAgent()

__all__ = ["ethiopian_cultural_agent", "EthiopianCulturalAgent"]