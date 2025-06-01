from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class GriefSupportAgentHooks(BaseAgentHooks):
    """Custom hooks for the grief support and follow-up agent."""

    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the GriefSupportAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for GriefSupportAgent")

class GriefSupportAgent(BaseAgent):
    """
    A specialized agent for providing ongoing grief support and follow-up care
    to families after funeral services, with cultural sensitivity and professional boundaries.
    """
    
    def __init__(self, name="GRIEF_SUPPORT"):
        # Define grief support instructions
        grief_support_instructions = """You are a grief support and follow-up specialist for funeral homes. Your role focuses on providing compassionate, ongoing support to families while maintaining professional boundaries and cultural sensitivity.

## YOUR RESPONSIBILITIES

**FOLLOW-UP COMMUNICATION**: Provide thoughtful, timely follow-up with families:
- Initial follow-up within 2-3 days after service
- Milestone check-ins (1 month, 3 months, 6 months, 1 year anniversary)
- Holiday and birthday remembrance communications
- Response to family-initiated contact for support

**GRIEF EDUCATION AND RESOURCES**: Provide appropriate grief support information:
- Normal grief process education
- Available local support groups and counseling services
- Grief literature and resource recommendations
- Online support resources and memorial options
- Seasonal grief support (holidays, anniversaries)

**MEMORIAL SERVICE COORDINATION**: Assist with ongoing memorial needs:
- Anniversary service planning
- Memorial garden or tribute coordination
- Annual remembrance events
- Memorial donation coordination

**FAMILY SUPPORT SERVICES**: Connect families with additional support:
- Grief counseling referrals (professional therapists)
- Support group information (local and online)
- Practical assistance resources (legal, financial)
- Spiritual care connections (chaplains, clergy)

**COMMUNITY OUTREACH**: Support broader community grief education:
- Grief education workshops
- Community memorial events
- Partnerships with counseling services
- Educational content development

## YOUR APPROACH

You maintain a warm, professional, and respectful approach while:
- Recognizing that everyone grieves differently and at their own pace
- Respecting cultural and religious approaches to grief and mourning
- Understanding that some families prefer more support, others prefer privacy
- Never pressuring families to engage beyond their comfort level
- Maintaining professional boundaries while offering genuine care
- Being sensitive to the ongoing nature of grief (it's not a linear process)

## GRIEF SUPPORT PRINCIPLES

**Individual Pace**: Respect that each person grieves at their own pace and in their own way
**Cultural Sensitivity**: Honor diverse cultural and religious approaches to grief and mourning
**Professional Boundaries**: Provide support and resources while referring to professional counselors when appropriate
**Non-Intrusive Care**: Offer support without being pushy or overwhelming to grieving families
**Long-term Perspective**: Understand that grief support is needed well beyond the funeral service

## WHAT YOU DO NOT DO

- You do not provide professional grief counseling or therapy
- You do not diagnose or treat mental health conditions
- You do not pressure families to participate in follow-up services
- You do not share family information without explicit permission
- You do not make assumptions about how long grief "should" last

## WHAT YOU DO

- Provide caring, appropriate follow-up communication
- Connect families with professional grief counseling resources
- Offer practical support and resource information
- Coordinate memorial services and remembrance activities
- Respect boundaries while remaining available for support

You serve as a bridge between the immediate funeral service and long-term healing, offering families ongoing connection and support while respecting their individual grief journeys."""

        # Initialize with grief support capabilities
        super().__init__(
            name=name,
            instructions=grief_support_instructions,
            functions=[
                function_tool(self.plan_follow_up_communication),
                function_tool(self.provide_grief_resources),
                function_tool(self.coordinate_memorial_services),
                function_tool(self.track_anniversary_dates),
                function_tool(self.connect_support_services)
            ],
            tool_choice="auto",
            parallel_tool_calls=False,  # Sequential for sensitive communications
            max_tokens=1024,
            hooks=GriefSupportAgentHooks()
        )
        
        # Agent description
        self.description = ("Specialist in providing compassionate follow-up care, grief support resources, "
                          "and memorial coordination for families after funeral services")

    async def plan_follow_up_communication(
        self,
        context: RunContextWrapper,
        family_preferences: Optional[str] = None,
        cultural_considerations: Optional[str] = None,
        communication_method: Optional[str] = None,
        timeline: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Plan appropriate follow-up communication schedule based on family preferences.
        
        Args:
            context: The conversation context
            family_preferences: Family's stated preferences for follow-up
            cultural_considerations: Relevant cultural or religious considerations
            communication_method: Preferred method (phone, email, card, visit)
            timeline: Specific timeline or standard schedule
            
        Returns:
            Follow-up communication plan with timeline and approach
        """
        logger.info(f"Planning follow-up communication with cultural considerations: {cultural_considerations}")
        
        return {
            "follow_up_plan": "Personalized communication schedule created",
            "family_preferences": family_preferences or "Standard follow-up requested",
            "cultural_sensitivity": cultural_considerations or "Standard approach with general sensitivity",
            "communication_schedule": {
                "initial_follow_up": "2-3 days after service - brief check-in call or card",
                "one_week": "One week follow-up - how are immediate needs being met",
                "one_month": "One month check-in - how is adjustment progressing",
                "three_months": "Three month contact - seasonal adjustment, resource needs",
                "six_months": "Six month milestone - ongoing support assessment",
                "one_year_anniversary": "Anniversary remembrance - memorial options discussion"
            },
            "communication_approach": {
                "tone": "Warm, respectful, non-intrusive",
                "method": communication_method or "Phone call with card follow-up",
                "duration": "Brief unless family indicates desire for longer conversation",
                "content_focus": "Care and support, not business development"
            },
            "cultural_adaptations": [
                "Respect mourning period customs and traditions",
                "Understand family hierarchy and communication preferences",
                "Honor religious observances and significant dates",
                "Adapt timing based on cultural grief practices"
            ],
            "documentation_notes": [
                "Record family preferences for future reference",
                "Note any special circumstances or needs",
                "Track response to follow-up efforts",
                "Maintain confidentiality of all family information"
            ]
        }

    async def provide_grief_resources(
        self,
        context: RunContextWrapper,
        grief_stage: Optional[str] = None,
        specific_needs: Optional[str] = None,
        family_demographics: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide appropriate grief support resources and information.
        
        Args:
            context: The conversation context
            grief_stage: Current stage or timing of grief
            specific_needs: Specific support needs identified
            family_demographics: Relevant family information for resource matching
            resource_type: Type of resources requested (counseling, support groups, etc.)
            
        Returns:
            Curated grief support resources and information
        """
        return {
            "grief_resources": "Comprehensive support resource compilation",
            "immediate_support": {
                "crisis_support": [
                    "24/7 grief crisis hotline numbers",
                    "Emergency counseling services",
                    "Suicide prevention resources if needed"
                ],
                "practical_assistance": [
                    "Meal delivery services for families",
                    "Household assistance resources",
                    "Childcare support during difficult times"
                ]
            },
            "ongoing_support_options": {
                "professional_counseling": [
                    "Individual grief counseling referrals",
                    "Family therapy specialists",
                    "Trauma-informed therapy for difficult losses",
                    "Child and adolescent grief specialists"
                ],
                "support_groups": [
                    "Local grief support groups",
                    "Specific loss support (spouse, child, sudden loss)",
                    "Online support communities",
                    "Peer support programs"
                ],
                "educational_resources": [
                    "Grief process education materials",
                    "Books and literature recommendations",
                    "Online grief courses and webinars",
                    "Grief blogs and helpful websites"
                ]
            },
            "specialized_support": {
                "children_and_teens": "Age-appropriate grief resources and counseling",
                "sudden_or_traumatic_loss": "Specialized trauma and crisis support",
                "prolonged_grief": "Resources for complicated or extended grief",
                "anniversary_reactions": "Support for grief anniversary responses"
            },
            "memorial_and_remembrance": [
                "Memorial service planning assistance",
                "Memory preservation ideas and services",
                "Charitable giving in memory options",
                "Anniversary remembrance suggestions"
            ],
            "resource_delivery": {
                "information_packet": "Customized resource packet mailed to family",
                "digital_resources": "Email links to online resources and support",
                "personal_consultation": "Phone consultation to discuss specific needs",
                "follow_up_support": "Check back on resource utilization and helpfulness"
            }
        }

    async def coordinate_memorial_services(
        self,
        context: RunContextWrapper,
        memorial_type: Optional[str] = None,
        timing_preference: Optional[str] = None,
        family_wishes: Optional[str] = None,
        budget_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate memorial services and remembrance activities for families.
        
        Args:
            context: The conversation context
            memorial_type: Type of memorial service or activity
            timing_preference: When the family would like the memorial
            family_wishes: Specific family wishes for the memorial
            budget_considerations: Budget constraints or considerations
            
        Returns:
            Memorial service coordination plan
        """
        return {
            "memorial_coordination": "Comprehensive memorial planning initiated",
            "memorial_options": {
                "anniversary_services": [
                    "One-year anniversary memorial service",
                    "Birthday remembrance gatherings",
                    "Holiday memorial observances",
                    "Ongoing annual remembrance services"
                ],
                "memorial_projects": [
                    "Memorial garden plantings or dedications",
                    "Charitable memorial funds establishment",
                    "Memory book or video compilation",
                    "Memorial scholarship or award creation"
                ],
                "community_memorials": [
                    "Community remembrance events",
                    "Memorial walks or runs",
                    "Awareness campaigns in memory",
                    "Public memorial dedications"
                ]
            },
            "planning_considerations": {
                "timing": timing_preference or "Anniversary date or family preference",
                "location": "Funeral home, church, community center, or outdoor venue",
                "format": "Religious, secular, or mixed format based on family wishes",
                "participation": "Family-only, friends included, or community-wide"
            },
            "coordination_services": [
                "Venue arrangement and setup",
                "Invitation design and distribution",
                "Program development and printing",
                "Audio/visual support for presentations",
                "Catering or reception coordination",
                "Memory display creation and setup"
            ],
            "budget_options": {
                "simple_memorial": "Low-cost options focusing on remembrance",
                "moderate_memorial": "Enhanced services with reception",
                "comprehensive_memorial": "Full-service memorial with all amenities",
                "community_supported": "Community-funded or sponsored elements"
            },
            "ongoing_support": [
                "Annual memorial service coordination",
                "Memorial website or online tribute maintenance",
                "Memory preservation services",
                "Family memorial tradition development"
            ]
        }

    async def track_anniversary_dates(
        self,
        context: RunContextWrapper,
        family_information: Optional[str] = None,
        important_dates: Optional[str] = None,
        communication_preferences: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track and manage important anniversary dates for appropriate follow-up.
        
        Args:
            context: The conversation context
            family_information: Basic family information for tracking
            important_dates: Key dates to track (death, birth, wedding anniversaries)
            communication_preferences: How family wants to be contacted on anniversaries
            
        Returns:
            Anniversary tracking system and communication plan
        """
        return {
            "anniversary_tracking": "Comprehensive date tracking system established",
            "tracked_dates": {
                "primary_anniversaries": [
                    "Date of death (monthly for first year, then annually)",
                    "Birthday of deceased",
                    "Wedding anniversary (if spouse surviving)",
                    "Other significant family dates"
                ],
                "milestone_dates": [
                    "30 days after service",
                    "90 days after service", 
                    "6 months after service",
                    "One year anniversary",
                    "Subsequent annual anniversaries"
                ],
                "challenging_periods": [
                    "First major holidays after loss",
                    "Mother's Day/Father's Day",
                    "Family reunion times",
                    "Season when death occurred"
                ]
            },
            "communication_strategy": {
                "advance_contact": "Contact family 1-2 weeks before difficult dates",
                "day_of_acknowledgment": "Brief, caring acknowledgment on the actual date",
                "resource_offering": "Offer specific support resources for difficult times",
                "memorial_suggestions": "Suggest meaningful ways to honor memory"
            },
            "tracking_system": {
                "calendar_integration": "All important dates added to follow-up calendar",
                "reminder_system": "Automated reminders for staff follow-up",
                "family_preferences": "Record how each family wants to be contacted",
                "cultural_considerations": "Note cultural observances and sensitivities"
            },
            "support_escalation": [
                "Monitor for signs of complicated grief",
                "Increase support during particularly difficult anniversaries",
                "Provide additional resources during challenging periods",
                "Refer to professional counseling when appropriate"
            ]
        }

    async def connect_support_services(
        self,
        context: RunContextWrapper,
        support_need: Optional[str] = None,
        urgency_level: Optional[str] = None,
        family_preferences: Optional[str] = None,
        geographic_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect families with appropriate professional grief support services.
        
        Args:
            context: The conversation context
            support_need: Type of support needed (counseling, legal, financial, etc.)
            urgency_level: How urgent the need is
            family_preferences: Family preferences for type of support
            geographic_area: Geographic area for local resource matching
            
        Returns:
            Support service connections and referral information
        """
        return {
            "support_connections": "Professional support service referrals prepared",
            "counseling_services": {
                "individual_therapy": [
                    "Licensed grief counselors in local area",
                    "Therapists specializing in loss and bereavement",
                    "Trauma-informed therapists for sudden loss",
                    "Child and adolescent grief specialists"
                ],
                "group_therapy": [
                    "Grief support groups (various types of loss)",
                    "Widow/widower support groups",
                    "Parent loss support groups",
                    "Sibling loss support groups"
                ],
                "family_therapy": [
                    "Family therapy for grief processing",
                    "Family communication improvement",
                    "Multi-generational grief support",
                    "Blended family grief support"
                ]
            },
            "practical_support": {
                "legal_assistance": [
                    "Estate planning attorneys",
                    "Probate and estate administration",
                    "Social Security and benefits guidance",
                    "Insurance claim assistance"
                ],
                "financial_guidance": [
                    "Financial planning for life changes",
                    "Widow/widower financial assistance programs",
                    "Insurance claim processing help",
                    "Government benefit navigation"
                ],
                "daily_life_support": [
                    "Meal delivery services",
                    "Household assistance programs",
                    "Transportation assistance",
                    "Childcare support services"
                ]
            },
            "referral_process": {
                "initial_contact": "Provide family with contact information and introduction",
                "warm_handoff": "Facilitate introduction when appropriate",
                "follow_up": "Check on success of referral and ongoing needs",
                "ongoing_coordination": "Maintain connection for continued support"
            },
            "service_vetting": [
                "Verify credentials and licensing of referred professionals",
                "Maintain relationships with trusted local providers",
                "Gather feedback on referral success",
                "Continuously update resource database"
            ]
        }

    @property
    def description(self) -> str:
        """Get a description of this agent's capabilities."""
        return self._description

    @description.setter 
    def description(self, value: str) -> None:
        """Set the agent's description."""
        self._description = value

# Create the grief support agent instance
grief_support_agent = GriefSupportAgent()

# Expose the agent for importing by other modules
__all__ = ["grief_support_agent", "GriefSupportAgent"]
