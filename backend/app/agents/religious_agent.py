from typing import Dict, Any, Optional, List
import logging
from agents import function_tool, ModelSettings, RunContextWrapper, WebSearchTool
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class ReligiousAgentHooks(BaseAgentHooks):
    """Custom hooks for the religious traditions agent."""

    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the ReligiousAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for ReligiousAgent")

class ReligiousAgent(BaseAgent):
    """
    A specialized agent with encyclopedic knowledge of world religions and their funeral/burial traditions.
    Primarily collaborates with other agents to provide religious and cultural guidance for funeral services.
    """
    
    def __init__(self, name="RELIGIOUS_TRADITIONS"):
        # Define religious traditions instructions
        religious_instructions = """You are a religious traditions specialist with encyclopedic knowledge of world religions and their funeral, burial, and mourning practices. You primarily support other agents with religious and cultural guidance, though you may respond directly when specifically asked about religious matters.

## YOUR KNOWLEDGE BASE

**MAJOR WORLD RELIGIONS**: Deep understanding of funeral and mourning practices for:
- Christianity (Catholic, Protestant, Orthodox, Coptic, and other denominations)
- Islam (Sunni, Shia, and various cultural interpretations)
- Judaism (Orthodox, Conservative, Reform, and cultural practices)
- Hinduism (various traditions, regional practices, caste considerations)
- Buddhism (Theravada, Mahayana, Vajrayana, and cultural variations)
- Sikhism (traditional and modern practices)

**OTHER FAITH TRADITIONS**: Knowledge of funeral practices for:
- Bahá'í Faith, Jainism, Zoroastrianism
- Indigenous spiritual traditions (with appropriate respect and caution)
- African traditional religions and practices
- Native American spiritual traditions (general knowledge, not specific tribal practices)
- Ancient traditions still practiced (Egyptian, Greek, Roman influences)

**CULTURAL AND REGIONAL VARIATIONS**: Understanding that:
- Religious practices vary significantly by region and family tradition
- Many families blend religious traditions or adapt practices
- Immigration and cultural integration affect traditional practices
- Economic factors may influence how traditions are observed
- Generational differences in religious observance

## YOUR COLLABORATION ROLE

**SUPPORTING OTHER AGENTS**: Provide religious guidance to:
- **Scheduling Agent**: Timing requirements, religious calendar considerations, required waiting periods
- **Sensitive Chat Agent**: Religious comfort and appropriate responses
- **Grief Support Agent**: Faith-based grief resources and religious mourning periods
- **Compliance Agent**: Religious documentation requirements and exemptions
- **Financial Services Agent**: Religious considerations affecting costs and payment timing

**DIRECT RESPONSES**: You may respond directly when:
- Specifically asked about religious practices or traditions
- Families need clarification about religious requirements
- Staff needs guidance on accommodating religious needs
- Emergency situations require immediate religious protocol guidance

## YOUR APPROACH

You maintain a respectful, informative, and non-judgmental approach while:
- Never making assumptions about a family's level of religious observance
- Understanding that families may have mixed religious backgrounds
- Recognizing that people may have personal variations of traditional practices
- Respecting both traditional and modern interpretations of religious practices
- Acknowledging when practices are culturally specific rather than universally religious

## IMPORTANT BOUNDARIES

**WHAT YOU DO**:
- Provide factual information about religious funeral and burial practices
- Explain timing requirements and religious calendar considerations
- Suggest appropriate accommodations for religious needs
- Connect families with appropriate religious leaders when requested
- Research less common or regional religious practices

**WHAT YOU DO NOT DO**:
- Provide theological advice or religious counseling
- Make judgments about the "correctness" of religious practices
- Assume someone's religious practices based on their background
- Speak authoritatively about specific tribal or highly localized traditions
- Provide religious rituals or serve as a religious officiant

## RESEARCH CAPABILITIES

You have access to web search to:
- Research less common religious traditions and practices
- Find current information about religious calendar dates and observances
- Locate appropriate religious contacts and resources in the local area
- Verify regional variations of religious practices
- Find specific religious requirements for funeral and burial practices

Your goal is to ensure that all funeral services can appropriately honor and accommodate the religious and spiritual needs of families while respecting the diversity of beliefs and practices."""

        # Create web search tool for religious research
        web_search_tool = WebSearchTool(search_context_size="medium")
        
        # Initialize with religious knowledge and research capabilities
        super().__init__(
            name=name,
            instructions=religious_instructions,
            functions=[
                web_search_tool,  # Include web search for research
                function_tool(self.provide_religious_guidance),
                function_tool(self.research_religious_practices),
                function_tool(self.identify_religious_requirements),
                function_tool(self.suggest_religious_accommodations),
                function_tool(self.find_religious_resources)
            ],
            tool_choice="auto",
            parallel_tool_calls=False,  # Sequential for thoughtful religious guidance
            max_tokens=1024,
            hooks=ReligiousAgentHooks()
        )
        
        # Agent description
        self.description = ("Specialist in world religious traditions and funeral practices, "
                          "providing cultural and religious guidance for funeral services")

    async def provide_religious_guidance(
        self,
        context: RunContextWrapper,
        religious_background: Optional[str] = None,
        specific_question: Optional[str] = None,
        service_type: Optional[str] = None,
        cultural_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide religious guidance for funeral and burial practices.
        
        Args:
            context: The conversation context
            religious_background: Religious or cultural background of the family
            specific_question: Specific religious question or concern
            service_type: Type of service being planned
            cultural_considerations: Additional cultural factors to consider
            
        Returns:
            Religious guidance and recommendations
        """
        logger.info(f"Providing religious guidance for {religious_background} tradition")
        
        return {
            "religious_guidance": f"Guidance for {religious_background or 'diverse religious'} traditions",
            "general_principles": {
                "respect_for_tradition": "Honor the family's specific religious practices and level of observance",
                "flexibility": "Understand that families may adapt traditional practices to their circumstances",
                "consultation": "Encourage families to consult with their religious leaders when appropriate",
                "documentation": "Ensure any religious requirements are properly documented and communicated"
            },
            "common_considerations": {
                "timing_requirements": [
                    "Some religions require burial within specific timeframes",
                    "Religious calendar may affect scheduling (Sabbath, holy days)",
                    "Mourning periods may have specific timing requirements",
                    "Prayer times and religious observances may need accommodation"
                ],
                "preparation_practices": [
                    "Specific body preparation requirements",
                    "Religious washing or cleansing rituals",
                    "Dress requirements and religious garments",
                    "Items to be buried with the deceased"
                ],
                "service_elements": [
                    "Required prayers, readings, or rituals",
                    "Music and singing restrictions or requirements",
                    "Participation requirements for family and attendees",
                    "Officiant requirements (clergy, religious leader)"
                ],
                "burial_considerations": [
                    "Orientation requirements for burial",
                    "Grave depth or construction requirements",
                    "Casket or burial container specifications",
                    "Cemetery section or religious requirements"
                ]
            },
            "family_consultation": [
                "Ask about family's specific level of religious observance",
                "Inquire about any family traditions or regional variations",
                "Discuss any religious leaders they want involved",
                "Confirm understanding of any religious restrictions or requirements"
            ],
            "accommodation_notes": [
                "Work with family to understand their specific needs",
                "Coordinate with religious leaders as requested by family",
                "Ensure staff understands any special requirements",
                "Document religious accommodations for service delivery"
            ]
        }

    async def research_religious_practices(
        self,
        context: RunContextWrapper,
        religion_or_culture: Optional[str] = None,
        specific_practice: Optional[str] = None,
        geographic_region: Optional[str] = None,
        research_focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Research specific religious or cultural practices using web search capabilities.
        
        Args:
            context: The conversation context
            religion_or_culture: Specific religion or cultural group to research
            specific_practice: Particular practice or ritual to investigate
            geographic_region: Geographic region for cultural variations
            research_focus: Focus area for research (timing, burial, mourning, etc.)
            
        Returns:
            Research findings and practical application guidance
        """
        return {
            "research_focus": f"Researching {religion_or_culture or 'religious'} practices",
            "research_methodology": {
                "primary_sources": "Academic and religious authority sources preferred",
                "cultural_context": "Understanding regional and cultural variations",
                "practical_application": "Focus on funeral and burial practice implications",
                "verification": "Cross-reference multiple authoritative sources"
            },
            "research_areas": {
                "funeral_practices": [
                    "Traditional funeral service elements and requirements",
                    "Modern adaptations and variations",
                    "Regional differences in practice",
                    "Generational changes in observance"
                ],
                "burial_requirements": [
                    "Specific burial timing requirements",
                    "Burial orientation and grave preparation",
                    "Casket and burial container specifications",
                    "Cemetery and location requirements"
                ],
                "mourning_traditions": [
                    "Mourning period length and requirements",
                    "Family obligations during mourning",
                    "Memorial and remembrance practices",
                    "Annual observances and commemoration"
                ],
                "ritual_elements": [
                    "Required prayers, readings, and ceremonial elements",
                    "Music, singing, and artistic expression guidelines",
                    "Participation requirements for attendees",
                    "Objects, symbols, and religious items"
                ]
            },
            "practical_application": {
                "scheduling_implications": "How religious practices affect service timing",
                "facility_requirements": "Special facility or equipment needs",
                "staff_preparation": "Staff training needs for cultural sensitivity",
                "family_guidance": "How to discuss options with families respectfully"
            },
            "consultation_recommendations": [
                "Connect with local religious leaders for specific guidance",
                "Consult with cultural community organizations",
                "Verify practices with family's own religious authorities",
                "Respect family's specific interpretation of traditions"
            ]
        }

    async def identify_religious_requirements(
        self,
        context: RunContextWrapper,
        family_background: Optional[str] = None,
        service_timeline: Optional[str] = None,
        special_circumstances: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Identify specific religious requirements that must be accommodated.
        
        Args:
            context: The conversation context
            family_background: Religious and cultural background information
            service_timeline: Proposed timeline for services
            special_circumstances: Any special circumstances affecting requirements
            
        Returns:
            Specific religious requirements and accommodation needs
        """
        return {
            "religious_requirements": f"Requirements assessment for {family_background or 'family traditions'}",
            "critical_requirements": {
                "timing_mandates": [
                    "Burial within 24 hours (Islamic tradition)",
                    "Burial before sunset on day of death (some Jewish traditions)",
                    "No services during Sabbath (Friday evening to Saturday evening for Jewish, Sunday for some Christian)",
                    "Avoidance of holy days and religious festivals"
                ],
                "preparation_mandates": [
                    "Ritual washing by specific individuals (Islamic, Jewish)",
                    "Body not to be left alone (Jewish tradition)",
                    "Specific clothing or shroud requirements",
                    "No embalming or minimal preservation (Islamic, Jewish, some Hindu)"
                ],
                "service_mandates": [
                    "Specific prayers or readings required",
                    "Religious officiant required (priest, imam, rabbi, etc.)",
                    "Gender separation requirements",
                    "Specific ritual objects or symbols needed"
                ],
                "burial_mandates": [
                    "Burial facing specific direction (Mecca for Islamic)",
                    "Direct earth burial (no vault required)",
                    "Specific grave depth requirements",
                    "Family involvement in burial process"
                ]
            },
            "accommodation_planning": {
                "facility_modifications": "Special facility setup or equipment needs",
                "scheduling_adjustments": "Timeline adjustments for religious requirements",
                "staff_preparation": "Staff training for religious sensitivity",
                "vendor_coordination": "Religious caterers, musicians, or specialists"
            },
            "flexibility_areas": [
                "Practices that can be adapted to circumstances",
                "Options when traditional requirements cannot be fully met",
                "Modern interpretations of traditional practices",
                "Emergency or unusual circumstance accommodations"
            ],
            "consultation_priority": [
                "Requirements that should be confirmed with religious authorities",
                "Practices that vary significantly between families",
                "Regional or cultural variations to verify",
                "Modern adaptations to discuss with family"
            ]
        }

    async def suggest_religious_accommodations(
        self,
        context: RunContextWrapper,
        identified_needs: Optional[str] = None,
        facility_constraints: Optional[str] = None,
        timeline_constraints: Optional[str] = None,
        budget_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest practical accommodations for religious requirements.
        
        Args:
            context: The conversation context
            identified_needs: Religious needs that have been identified
            facility_constraints: Any facility limitations
            timeline_constraints: Timeline limitations or conflicts
            budget_considerations: Budget constraints affecting accommodations
            
        Returns:
            Practical accommodation suggestions and implementation guidance
        """
        return {
            "accommodation_suggestions": "Practical religious accommodation options",
            "facility_accommodations": {
                "prayer_space": [
                    "Quiet space for prayer and reflection",
                    "Proper orientation for directional prayers (Mecca, Jerusalem)",
                    "Removal of religious symbols that may conflict",
                    "Separate spaces for gender-segregated prayer"
                ],
                "preparation_space": [
                    "Private space for ritual washing or preparation",
                    "Access for religious leaders or family members",
                    "Appropriate facilities for religious preparation requirements",
                    "Storage for religious items and ceremonial objects"
                ],
                "service_modifications": [
                    "Altar or ceremonial area setup for specific traditions",
                    "Sound system capabilities for religious music or chanting",
                    "Seating arrangements for religious requirements",
                    "Display areas for religious symbols or photographs"
                ]
            },
            "timing_accommodations": {
                "religious_calendar": [
                    "Schedule around major religious holidays",
                    "Accommodate daily prayer times",
                    "Respect Sabbath and holy day restrictions",
                    "Plan for religious fasting periods"
                ],
                "service_timing": [
                    "Adjust service length for religious requirements",
                    "Allow time for pre-service religious preparations",
                    "Coordinate multiple religious elements or traditions",
                    "Plan for post-service religious observances"
                ]
            },
            "staffing_accommodations": {
                "religious_sensitivity": [
                    "Staff training on specific religious practices",
                    "Cultural competency for religious interactions",
                    "Understanding of religious restrictions and requirements",
                    "Coordination with religious leaders and authorities"
                ],
                "specialized_support": [
                    "Coordinate with religious officials",
                    "Arrange for cultural interpreters if needed",
                    "Connect with religious community resources",
                    "Facilitate religious ritual requirements"
                ]
            },
            "cost_considerations": {
                "required_accommodations": "Accommodations provided at no additional charge",
                "optional_enhancements": "Additional services available for enhanced observance",
                "community_resources": "Religious community support and assistance",
                "alternative_options": "Lower-cost ways to meet religious requirements"
            }
        }

    async def find_religious_resources(
        self,
        context: RunContextWrapper,
        religious_tradition: Optional[str] = None,
        resource_type: Optional[str] = None,
        geographic_area: Optional[str] = None,
        specific_need: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find religious resources and contacts for families and funeral service support.
        
        Args:
            context: The conversation context
            religious_tradition: Specific religious tradition or denomination
            resource_type: Type of resource needed (clergy, facilities, suppliers)
            geographic_area: Local geographic area for resource location
            specific_need: Specific religious need or requirement
            
        Returns:
            Religious resources and contact information
        """
        return {
            "religious_resources": f"Resources for {religious_tradition or 'diverse religious'} needs",
            "clergy_and_officiants": {
                "local_religious_leaders": [
                    "Contact information for local priests, ministers, pastors",
                    "Imam and Islamic community leaders",
                    "Rabbis and Jewish community contacts", 
                    "Hindu priests and community spiritual leaders",
                    "Buddhist monks and meditation teachers",
                    "Sikh gurdwara leaders and community elders"
                ],
                "specialized_clergy": [
                    "Military chaplains for veteran services",
                    "Hospital chaplains familiar with death situations",
                    "Interfaith ministers for blended families",
                    "Cultural community spiritual leaders"
                ]
            },
            "religious_facilities": {
                "houses_of_worship": [
                    "Churches, mosques, synagogues, temples available for services",
                    "Community centers with religious significance",
                    "Meditation centers and spiritual retreat facilities",
                    "Cultural centers with religious accommodation"
                ],
                "specialized_facilities": [
                    "Ritual washing facilities",
                    "Religious preparation rooms",
                    "Prayer halls and meditation spaces",
                    "Community kitchens for religious meals"
                ]
            },
            "religious_suppliers": {
                "ritual_items": [
                    "Religious music and audio resources",
                    "Ceremonial objects and religious symbols",
                    "Religious texts and prayer books",
                    "Traditional clothing and burial garments"
                ],
                "food_and_catering": [
                    "Kosher and halal catering services",
                    "Vegetarian and vegan options for religious requirements",
                    "Traditional cultural foods for memorial meals",
                    "Religious dietary accommodation specialists"
                ]
            },
            "community_support": {
                "religious_organizations": [
                    "Local religious community organizations",
                    "Cultural associations with religious connections",
                    "Interfaith dialogue and support groups",
                    "Religious charity and assistance organizations"
                ],
                "support_services": [
                    "Religious grief counseling and support",
                    "Faith-based family assistance programs",
                    "Religious education and cultural preservation groups",
                    "Volunteer religious support networks"
                ]
            }
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

# Create the religious traditions agent instance
religious_traditions_agent = ReligiousAgent()

# Expose the agent for importing by other modules
__all__ = ["religious_traditions_agent", "ReligiousAgent"]
