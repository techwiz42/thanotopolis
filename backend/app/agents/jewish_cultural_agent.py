from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class JewishCulturalAgentHooks(BaseAgentHooks):
    """Custom hooks for the Jewish cultural agent."""
    
    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the JewishCulturalAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for JewishCulturalAgent")

class JewishCulturalAgent(BaseAgent):
    """
    A specialized agent with deep knowledge of Jewish funeral traditions across
    Orthodox, Conservative, Reform, and secular variations within American Jewish communities.
    """
    
    OWNER_DOMAINS = []  # Free agent available to all organizations
    
    def __init__(self, name="JEWISH_CULTURAL"):
        instructions = """You are a culturally knowledgeable specialist in Jewish funeral traditions, customs, and practices across all denominations. You have deep understanding of:

JEWISH FUNERAL TRADITIONS & HALAKHA:
- Orthodox funeral practices and strict halakhic requirements
- Conservative movement adaptations and interpretations
- Reform Jewish practices and modern accommodations
- Reconstructionist and secular Jewish customs
- Traditional burial requirements and cemetery considerations
- Tahara (ritual purification) and chevra kadisha involvement
- Immediate burial customs and timing considerations
- Prohibition against cremation in traditional Judaism vs. liberal acceptance

MOURNING PERIODS & PRACTICES:
- Shiva (seven-day mourning period) customs and house preparation
- Shloshim (30-day period) and year-long mourning for parents
- Yahrzeit (death anniversary) observances and memorial practices
- Kaddish recitation obligations and synagogue participation
- Mourning restrictions and permitted activities
- Memorial candle lighting and ongoing remembrance
- Unveiling ceremonies and headstone dedications

RELIGIOUS VARIATIONS:
- Orthodox: Strict halakhic observance and traditional practices
- Conservative: Halakhic commitment with modern adaptations
- Reform: Ethical Judaism with flexible ritual observance
- Reconstructionist: Judaism as evolving civilization
- Secular/Cultural: Jewish identity without religious practice
- Hasidic variations and specific sect customs
- Sephardic vs. Ashkenazi traditional differences

CULTURAL VALUES & FAMILY DYNAMICS:
- Pikuach nefesh (preservation of life) and medical decisions
- Kavod hamet (honor of the deceased) in funeral planning
- Family obligations and community support systems
- Intergenerational religious observance differences
- Mixed marriages and interfaith family considerations
- Jewish identity through matrilineal descent and conversion
- Community responsibility and mutual aid traditions

AMERICAN JEWISH EXPERIENCE:
- Immigration waves: German Jews (1840s), Eastern European (1880s-1920s), Holocaust survivors, Soviet Jews, recent Israeli emigration
- Regional Jewish communities: Northeast, South, West Coast, Midwest
- Suburban synagogue culture and community centers
- Jewish day schools and educational institution involvement
- Professional and business network communities
- Interfaith families and Jewish identity questions

HOLOCAUST & HISTORICAL TRAUMA:
- Survivor families and intergenerational trauma effects
- Memorial traditions related to Holocaust remembrance
- Missing family records and genealogical gaps
- Collective trauma and community healing approaches
- Second and third generation Holocaust impact
- Memorial practices for victims without graves

LANGUAGE & COMMUNICATION:
- Hebrew prayers and ritual terminology
- Yiddish cultural expressions and sayings
- Ladino in Sephardic communities
- English-Hebrew bilingual service needs
- Traditional blessings and memorial phrases
- Generational language preferences and retention

SYNAGOGUE & COMMUNITY INVOLVEMENT:
- Rabbi and cantor roles in funeral services
- Synagogue burial society (chevra kadisha) participation
- Minyan requirements for mourning prayers
- Community support systems and meal coordination
- Jewish cemetery regulations and practices
- Synagogue memorial boards and ongoing remembrance

MODERN ADAPTATIONS & CHALLENGES:
- Technology use: live-streaming services, virtual minyan participation
- COVID-19 adaptations and remote participation
- Environmental considerations and green burial options
- Gender equality in traditionally male-dominated mourning rituals
- LGBTQ+ inclusion in Jewish funeral practices
- Assisted living and nursing home Jewish community needs

INTERFAITH & MIXED FAMILY CONSIDERATIONS:
- Non-Jewish spouses and funeral participation
- Children with one Jewish parent and identity questions
- Conversion considerations and religious status
- Balancing Jewish and non-Jewish family traditions
- Cemetery burial restrictions and accommodation needs
- Clergy cooperation and interfaith service elements

ECONOMIC & SOCIAL CONSIDERATIONS:
- Jewish funeral home services and kosher considerations
- Cemetery plot costs and Jewish cemetery requirements
- Community fundraising for families in need
- Professional leave considerations for mourning periods
- Social status and community reputation factors
- Charitable giving (tzedakah) in memory of deceased

LIFECYCLE & RITUAL INTEGRATION:
- Connection to other Jewish lifecycle events
- Bar/Bat Mitzvah and confirmation community connections
- Wedding and family celebration community involvement
- Jewish holiday observance and calendar considerations
- Life cycle education and preparation programs
- Community celebration and mourning integration

SPECIAL POPULATIONS:
- Elderly Jewish communities and end-of-life care
- Young Jewish professionals in major metropolitan areas
- Jewish college students away from family communities
- Jews by choice (converts) and family dynamics
- Interfaith families navigating Jewish practice
- Jews living in areas with limited Jewish infrastructure

ETHICAL & PHILOSOPHICAL CONSIDERATIONS:
- Jewish perspectives on death, afterlife, and resurrection
- Medical ethics and end-of-life decision making
- Organ donation within different Jewish movements
- Autopsy considerations and religious permissibility
- Advance directives and Jewish ethical guidance
- Social justice values in funeral and memorial practices

You provide culturally sensitive guidance while respecting the wide spectrum of Jewish religious observance, from strictly Orthodox to completely secular, and the complexity of American Jewish identity. Always consider denominational differences, family religious background, intermarriage factors, and community resources."""

        super().__init__(
            name=name,
            instructions=instructions,
            functions=[
                function_tool(self.explain_funeral_traditions),
                function_tool(self.suggest_cultural_accommodations),
                function_tool(self.guide_mourning_practices),
                function_tool(self.provide_denominational_guidance),
                function_tool(self.support_interfaith_families),
                function_tool(self.connect_community_resources),
                function_tool(self.explain_halakhic_considerations),
                function_tool(self.assist_with_memorial_planning)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=2048,
            hooks=JewishCulturalAgentHooks()
        )
        
        self.description = "Expert in Jewish funeral traditions across Orthodox, Conservative, Reform, and secular practices. Provides guidance on mourning customs, denominational variations, interfaith considerations, and American Jewish community resources. Knowledgeable about halakhic requirements, modern adaptations, and diverse Jewish family dynamics."

    async def explain_funeral_traditions(
        self,
        context: RunContextWrapper,
        denomination: Optional[str] = None,
        tradition_type: Optional[str] = None,
        family_background: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain specific Jewish funeral traditions across different denominations and observance levels.
        
        Args:
            context: The conversation context
            denomination: Orthodox, Conservative, Reform, Reconstructionist, or secular
            tradition_type: Specific tradition (burial, shiva, tahara, etc.)
            family_background: Ashkenazi, Sephardic, or mixed heritage
            
        Returns:
            Detailed explanation of Jewish funeral traditions
        """
        return {
            "traditions_explained": True,
            "tradition_details": f"Detailed explanation for {tradition_type or 'general'} Jewish traditions",
            "denominational_context": "Variations across Jewish movements explained",
            "halakhic_basis": "Religious law foundations and modern interpretations"
        }

    async def suggest_cultural_accommodations(
        self,
        context: RunContextWrapper,
        observance_level: Optional[str] = None,
        family_preferences: Optional[str] = None,
        venue_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest accommodations to honor Jewish cultural and religious practices within funeral services.
        
        Args:
            context: The conversation context
            observance_level: Level of religious observance in the family
            family_preferences: Specific Jewish cultural preferences mentioned
            venue_constraints: Funeral home or cemetery limitations
            
        Returns:
            Culturally and religiously appropriate accommodation suggestions
        """
        return {
            "accommodations_provided": True,
            "religious_elements": "Jewish religious elements that can be incorporated",
            "practical_adaptations": "Ways to adapt traditions to available facilities",
            "kosher_considerations": "Kosher requirements and religious compliance"
        }

    async def guide_mourning_practices(
        self,
        context: RunContextWrapper,
        mourning_stage: Optional[str] = None,
        relationship_to_deceased: Optional[str] = None,
        community_support: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide families through Jewish mourning practices including shiva, shloshim, and yahrzeit.
        
        Args:
            context: The conversation context
            mourning_stage: Shiva, shloshim, yahrzeit, or general mourning
            relationship_to_deceased: Spouse, parent, child, sibling, or other
            community_support: Available Jewish community support systems
            
        Returns:
            Mourning practice guidance and community support coordination
        """
        return {
            "mourning_guidance_provided": True,
            "practice_details": "Specific mourning practices and their duration",
            "community_involvement": "How community supports mourning families",
            "modern_adaptations": "Contemporary adaptations of traditional practices"
        }

    async def provide_denominational_guidance(
        self,
        context: RunContextWrapper,
        denomination: Optional[str] = None,
        mixed_denomination_family: Optional[str] = None,
        religious_questions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide guidance on denominational differences in Jewish funeral practices.
        
        Args:
            context: The conversation context
            denomination: Specific Jewish denomination or movement
            mixed_denomination_family: Families with different Jewish observance levels
            religious_questions: Specific religious or halakhic questions
            
        Returns:
            Denominational guidance and religious interpretation
        """
        return {
            "denominational_guidance_provided": True,
            "movement_differences": "Differences between Jewish denominations",
            "compromise_solutions": "Solutions for mixed-observance families",
            "religious_authority": "Appropriate religious consultation recommendations"
        }

    async def support_interfaith_families(
        self,
        context: RunContextWrapper,
        interfaith_status: Optional[str] = None,
        non_jewish_participation: Optional[str] = None,
        identity_questions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Support interfaith families navigating Jewish funeral practices and identity questions.
        
        Args:
            context: The conversation context
            interfaith_status: Jewish-non-Jewish marriage or mixed heritage
            non_jewish_participation: Non-Jewish family member participation needs
            identity_questions: Questions about Jewish identity and practice
            
        Returns:
            Interfaith family support and accommodation guidance
        """
        return {
            "interfaith_support_provided": True,
            "participation_guidance": "How non-Jewish family can respectfully participate",
            "identity_considerations": "Jewish identity and practice questions addressed",
            "inclusive_approaches": "Ways to honor both Jewish and non-Jewish traditions"
        }

    async def connect_community_resources(
        self,
        context: RunContextWrapper,
        location: Optional[str] = None,
        denomination_preference: Optional[str] = None,
        support_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect families with Jewish community organizations, synagogues, and support resources.
        
        Args:
            context: The conversation context
            location: Geographic area where family is located
            denomination_preference: Preferred Jewish denomination or openness to any
            support_type: Type of community support needed
            
        Returns:
            Jewish community resource connections and support coordination
        """
        return {
            "community_resources_provided": True,
            "synagogue_connections": "Local synagogues and Jewish communities",
            "support_organizations": "Jewish organizations providing funeral and grief support",
            "volunteer_services": "Community volunteers and mutual aid resources"
        }

    async def explain_halakhic_considerations(
        self,
        context: RunContextWrapper,
        halakhic_question: Optional[str] = None,
        observance_level: Optional[str] = None,
        rabbinical_consultation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain Jewish religious law (halakha) considerations related to death and mourning.
        
        Args:
            context: The conversation context
            halakhic_question: Specific religious law question
            observance_level: Family's level of halakhic observance
            rabbinical_consultation: Need for rabbinical authority consultation
            
        Returns:
            Halakhic explanation and religious authority guidance
        """
        return {
            "halakhic_guidance_provided": True,
            "religious_law_explanation": "Jewish religious law principles and applications",
            "modern_interpretations": "Contemporary rabbinical interpretations and rulings",
            "rabbinical_referral": "Appropriate rabbinical consultation recommendations"
        }

    async def assist_with_memorial_planning(
        self,
        context: RunContextWrapper,
        memorial_type: Optional[str] = None,
        timing_considerations: Optional[str] = None,
        community_involvement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assist with planning Jewish memorial services, unveilings, and yahrzeit observances.
        
        Args:
            context: The conversation context
            memorial_type: Unveiling, yahrzeit, or other memorial service
            timing_considerations: Jewish calendar and timing requirements
            community_involvement: Desired level of community participation
            
        Returns:
            Memorial planning guidance and community coordination
        """
        return {
            "memorial_planning_provided": True,
            "planning_guidelines": "Jewish memorial service planning requirements",
            "timing_guidance": "Appropriate timing according to Jewish calendar",
            "community_coordination": "How to involve Jewish community in memorial planning"
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

jewish_cultural_agent = JewishCulturalAgent()

__all__ = ["jewish_cultural_agent", "JewishCulturalAgent"]