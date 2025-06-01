from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class EmergencyAgentHooks(BaseAgentHooks):
    """Custom hooks for the emergency and crisis response agent."""

    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the EmergencyAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for EmergencyAgent")

class EmergencyAgent(BaseAgent):
    """
    A specialized agent for handling emergency situations and crisis response
    in funeral home and cemetery operations, including after-hours support.
    """
    
    def __init__(self, name="EMERGENCY"):
        # Define emergency response instructions
        emergency_instructions = """You are an emergency and crisis response specialist for funeral homes and cemeteries. Your expertise covers after-hours support, emergency situations, and crisis management with professionalism and compassion.

## YOUR RESPONSIBILITIES

**AFTER-HOURS SUPPORT**: Provide 24/7 emergency funeral services:
- Death notification and immediate response coordination
- Emergency removal and transportation of remains
- After-hours family support and initial consultation
- Coordination with hospitals, nursing homes, and coroners
- Emergency preparation for immediate burial needs

**CRISIS SITUATION MANAGEMENT**: Handle unusual or complex situations:
- Multiple casualty incidents and mass fatality response
- Sudden death investigations and coroner coordination
- Family crisis intervention and support
- Media relations during high-profile cases
- Natural disaster response and emergency planning

**EMERGENCY FACILITY OPERATIONS**: Maintain operations during emergencies:
- Power outage and utility failure response procedures
- Equipment failure and backup system activation
- Weather emergency preparations and response
- Security incidents and safety protocol implementation
- Emergency evacuation and safety procedures

**INTER-AGENCY COORDINATION**: Work with emergency services and agencies:
- Police and law enforcement coordination
- Fire department and emergency medical services
- Coroner and medical examiner offices
- Emergency management agencies
- Public health departments and CDC protocols

**FAMILY CRISIS SUPPORT**: Provide immediate support during traumatic situations:
- Sudden death family notification assistance
- Trauma-informed crisis counseling referrals
- Emergency financial assistance coordination
- Immediate practical need support (childcare, transportation)
- Connection with community crisis support resources

## YOUR APPROACH

You maintain a calm, professional, and compassionate approach while:
- Responding quickly and efficiently to emergency situations
- Prioritizing safety of staff, families, and the community
- Coordinating with multiple agencies and service providers
- Providing clear communication during high-stress situations
- Following established emergency protocols while adapting to unique circumstances
- Maintaining dignity and respect even in chaotic situations

## EMERGENCY RESPONSE PRINCIPLES

**Immediate Response**: Quick response time for all emergency calls and situations
**Safety First**: Prioritize safety of all individuals involved
**Clear Communication**: Provide clear, accurate information to all parties
**Compassionate Care**: Maintain empathy and support during crisis situations
**Professional Coordination**: Work effectively with all emergency response agencies
**Contingency Planning**: Prepare for multiple scenarios and have backup plans

## CRISIS MANAGEMENT PRIORITIES

1. **Life Safety**: Ensure safety of all staff, families, and visitors
2. **Scene Security**: Secure the scene and protect evidence when required
3. **Family Support**: Provide immediate support and information to families
4. **Service Continuity**: Maintain essential funeral services during emergencies
5. **Communication**: Keep all parties informed with accurate, timely information
6. **Documentation**: Maintain detailed records of all emergency responses

You serve as the critical link between normal operations and emergency response, ensuring that families receive compassionate care even during the most challenging circumstances."""

        # Initialize with emergency response capabilities
        super().__init__(
            name=name,
            instructions=emergency_instructions,
            functions=[
                function_tool(self.respond_to_emergency_call),
                function_tool(self.coordinate_crisis_response),
                function_tool(self.manage_facility_emergency),
                function_tool(self.coordinate_inter_agency_response),
                function_tool(self.provide_family_crisis_support)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=1024,
            hooks=EmergencyAgentHooks()
        )
        
        # Agent description
        self.description = ("Specialist in emergency response, crisis management, after-hours support, "
                          "and coordination with emergency services for funeral operations")

    async def respond_to_emergency_call(
        self,
        context: RunContextWrapper,
        call_type: Optional[str] = None,
        urgency_level: Optional[str] = None,
        location: Optional[str] = None,
        immediate_needs: Optional[str] = None,
        caller_information: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Respond to emergency calls with immediate action and coordination.
        
        Args:
            context: The conversation context
            call_type: Type of emergency call (death notification, transport, crisis)
            urgency_level: Urgency level of the situation
            location: Location of the emergency
            immediate_needs: Immediate needs or actions required
            caller_information: Information about the caller and situation
            
        Returns:
            Emergency response plan and immediate action items
        """
        logger.info(f"Responding to emergency call: {call_type} at {location}")
        
        return {
            "emergency_response": f"Immediate response activated for {call_type or 'emergency situation'}",
            "response_protocol": {
                "immediate_actions": [
                    "Acknowledge emergency call and gather essential information",
                    "Dispatch emergency response team to location",
                    "Contact relevant authorities if required (police, coroner)",
                    "Notify funeral director on call for immediate response",
                    "Prepare emergency equipment and transportation"
                ],
                "response_timeline": {
                    "call_acknowledgment": "Within 1-2 rings, 24/7 availability",
                    "team_dispatch": "Emergency team en route within 30 minutes",
                    "scene_arrival": "Arrive at scene within 45-60 minutes",
                    "initial_assessment": "Complete initial assessment within 15 minutes of arrival",
                    "family_contact": "Contact family within 2 hours for next steps"
                }
            },
            "situation_assessment": {
                "call_details": {
                    "type": call_type or "General emergency",
                    "urgency": urgency_level or "High priority",
                    "location": location or "Location to be determined",
                    "caller": caller_information or "Caller details pending"
                },
                "immediate_priorities": [
                    "Ensure safety of all individuals involved",
                    "Coordinate with law enforcement if required",
                    "Provide professional, compassionate service",
                    "Begin documentation of all circumstances",
                    "Support family through immediate crisis"
                ]
            },
            "resource_deployment": {
                "personnel": [
                    "Licensed funeral director (on-call rotation)",
                    "Emergency response technician",
                    "Support staff as needed for complex situations",
                    "Grief counselor on standby for family support"
                ],
                "equipment": [
                    "Emergency response vehicle fully equipped",
                    "Body removal equipment and supplies",
                    "Emergency communication devices",
                    "Personal protective equipment",
                    "Documentation and authorization forms"
                ],
                "coordination": [
                    "Hospital/nursing home liaison contact",
                    "Coroner/medical examiner coordination",
                    "Law enforcement communication if required",
                    "Family notification and support services"
                ]
            },
            "follow_up_requirements": [
                "Complete removal and transportation procedures",
                "Document all circumstances and procedures",
                "Coordinate with family for next steps and planning",
                "Debrief emergency response for process improvement",
                "Submit required reports to authorities"
            ]
        }

    async def coordinate_crisis_response(
        self,
        context: RunContextWrapper,
        crisis_type: Optional[str] = None,
        scale_of_impact: Optional[str] = None,
        agencies_involved: Optional[str] = None,
        special_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate response to major crisis situations requiring multi-agency coordination.
        
        Args:
            context: The conversation context
            crisis_type: Type of crisis (mass casualty, natural disaster, etc.)
            scale_of_impact: Scale and scope of the crisis
            agencies_involved: Other agencies involved in response
            special_considerations: Special factors affecting response
            
        Returns:
            Crisis response coordination plan and resource allocation
        """
        return {
            "crisis_coordination": f"Managing response to {crisis_type or 'major crisis situation'}",
            "crisis_response_levels": {
                "level_1_local": {
                    "description": "Single facility impact, local resources sufficient",
                    "response_team": "Funeral home staff and local emergency services",
                    "coordination": "Local police, fire, and EMS coordination",
                    "resources": "Standard emergency resources and protocols"
                },
                "level_2_regional": {
                    "description": "Multiple facilities or widespread community impact",
                    "response_team": "Regional funeral service consortium",
                    "coordination": "County emergency management and state agencies",
                    "resources": "Regional mutual aid and resource sharing"
                },
                "level_3_state": {
                    "description": "State-wide impact requiring federal coordination",
                    "response_team": "State funeral directors association response team",
                    "coordination": "State emergency management and federal agencies",
                    "resources": "FEMA disaster mortuary teams and national resources"
                }
            },
            "multi_agency_coordination": {
                "emergency_management": [
                    "County Emergency Operations Center liaison",
                    "Incident Command System integration",
                    "Resource allocation and deployment coordination",
                    "Public information and media relations support"
                ],
                "law_enforcement": [
                    "Crime scene preservation and investigation support",
                    "Family notification assistance",
                    "Security and access control coordination",
                    "Evidence chain of custody procedures"
                ],
                "medical_authorities": [
                    "Coroner/Medical Examiner coordination",
                    "Victim identification and examination procedures",
                    "Autopsy scheduling and coordination",
                    "Death certificate and documentation processing"
                ],
                "public_health": [
                    "Infectious disease protocols and precautions",
                    "Public health emergency procedures",
                    "Mass fatality management protocols",
                    "Community health and safety coordination"
                ]
            },
            "resource_management": {
                "facility_capacity": "Assess and expand capacity for increased volume",
                "equipment_allocation": "Deploy additional equipment and supplies",
                "personnel_coordination": "Coordinate additional staff and volunteers",
                "supply_chain": "Secure additional supplies and resources",
                "transportation": "Coordinate additional transportation resources"
            },
            "communication_strategy": {
                "family_communication": "Centralized family information and communication",
                "media_relations": "Coordinated media response and information sharing",
                "community_updates": "Regular community updates and resource information",
                "inter_agency_communication": "Unified communication between all responding agencies"
            }
        }

    async def manage_facility_emergency(
        self,
        context: RunContextWrapper,
        emergency_type: Optional[str] = None,
        facility_impact: Optional[str] = None,
        safety_concerns: Optional[str] = None,
        service_continuity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manage facility-specific emergencies while maintaining service continuity.
        
        Args:
            context: The conversation context
            emergency_type: Type of facility emergency (power outage, fire, etc.)
            facility_impact: How the emergency affects facility operations
            safety_concerns: Safety issues that need immediate attention
            service_continuity: Plans for maintaining essential services
            
        Returns:
            Facility emergency management plan and continuity procedures
        """
        return {
            "facility_emergency": f"Managing {emergency_type or 'facility emergency'}",
            "emergency_scenarios": {
                "power_outage": {
                    "immediate_actions": [
                        "Activate backup generator systems",
                        "Check refrigeration unit backup power",
                        "Secure all electronic systems and data",
                        "Implement emergency lighting procedures"
                    ],
                    "service_continuity": [
                        "Continue essential services with backup power",
                        "Reschedule non-essential services if needed",
                        "Coordinate with utility company for restoration",
                        "Monitor generator fuel levels and refill schedule"
                    ]
                },
                "severe_weather": {
                    "preparation": [
                        "Secure all outdoor equipment and signage",
                        "Prepare emergency supplies and communications",
                        "Review evacuation procedures with staff",
                        "Coordinate with families about service modifications"
                    ],
                    "during_event": [
                        "Monitor weather conditions and warnings",
                        "Implement safety protocols for staff and families",
                        "Maintain communication with emergency services",
                        "Document any damage for insurance purposes"
                    ]
                },
                "security_incident": {
                    "immediate_response": [
                        "Ensure safety of all staff and visitors",
                        "Contact law enforcement if required",
                        "Secure the facility and control access",
                        "Document incident details for investigation"
                    ],
                    "follow_up": [
                        "Review security procedures and improvements",
                        "Provide staff debriefing and support",
                        "Coordinate with insurance and legal counsel",
                        "Implement enhanced security measures if needed"
                    ]
                },
                "equipment_failure": {
                    "critical_systems": [
                        "Refrigeration system failure - immediate repair or temporary solution",
                        "HVAC system failure - climate control and air quality management",
                        "Vehicle breakdown - backup transportation arrangement",
                        "Communication system failure - alternative communication methods"
                    ],
                    "backup_procedures": [
                        "Activate backup equipment and systems",
                        "Contact emergency repair services",
                        "Implement manual procedures if necessary",
                        "Communicate with families about any service impacts"
                    ]
                }
            },
            "safety_protocols": {
                "evacuation_procedures": [
                    "Clear evacuation routes marked and maintained",
                    "Staff trained on evacuation procedures",
                    "Emergency assembly point established",
                    "Special procedures for families and visitors"
                ],
                "emergency_equipment": [
                    "Fire extinguishers and suppression systems maintained",
                    "First aid supplies readily available",
                    "Emergency communication devices charged and ready",
                    "Personal protective equipment available"
                ]
            },
            "business_continuity": {
                "essential_services": "Maintain essential funeral services during emergency",
                "alternative_locations": "Arrangements with partner facilities if needed",
                "communication_plan": "Keep families informed of any service changes",
                "recovery_planning": "Plan for returning to normal operations"
            }
        }

    async def coordinate_inter_agency_response(
        self,
        context: RunContextWrapper,
        agencies_involved: Optional[str] = None,
        coordination_needs: Optional[str] = None,
        communication_requirements: Optional[str] = None,
        jurisdictional_issues: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate with multiple agencies during emergency response situations.
        
        Args:
            context: The conversation context
            agencies_involved: Agencies participating in response
            coordination_needs: Specific coordination requirements
            communication_requirements: Communication needs and protocols
            jurisdictional_issues: Any jurisdictional complications
            
        Returns:
            Inter-agency coordination plan and communication protocols
        """
        return {
            "inter_agency_coordination": "Multi-agency response coordination activated",
            "primary_agencies": {
                "law_enforcement": {
                    "local_police": "Scene security, traffic control, investigation support",
                    "state_police": "Major incident investigation, resource coordination",
                    "federal_agencies": "Federal jurisdiction cases, specialized investigation",
                    "coordination_role": "Crime scene management, evidence preservation"
                },
                "emergency_medical": {
                    "local_ems": "Medical emergency response, victim care",
                    "hospital_systems": "Victim treatment, family support",
                    "medical_examiner": "Death investigation, autopsy coordination",
                    "coordination_role": "Medical care, victim identification"
                },
                "emergency_management": {
                    "county_eoc": "Resource coordination, incident command",
                    "state_emergency": "State resource allocation, coordination",
                    "federal_fema": "Federal resources, disaster declaration",
                    "coordination_role": "Overall incident management, resource allocation"
                }
            },
            "coordination_protocols": {
                "incident_command": [
                    "Participate in Incident Command System structure",
                    "Maintain clear chain of command and communication",
                    "Coordinate resources through proper channels",
                    "Follow unified command procedures"
                ],
                "information_sharing": [
                    "Share relevant information with appropriate agencies",
                    "Maintain confidentiality and privacy requirements",
                    "Coordinate public information release",
                    "Document all inter-agency communications"
                ],
                "resource_coordination": [
                    "Request resources through proper channels",
                    "Share resources when possible and appropriate",
                    "Coordinate logistics and supply management",
                    "Maintain accountability for all resources"
                ]
            },
            "communication_management": {
                "primary_communication": "Designated liaison for all agency communication",
                "backup_communication": "Alternative communication methods available",
                "secure_channels": "Encrypted communication for sensitive information",
                "public_communication": "Coordinated public information through designated spokesperson"
            },
            "jurisdictional_coordination": {
                "authority_clarification": "Clear understanding of each agency's authority",
                "boundary_issues": "Coordination across jurisdictional boundaries",
                "legal_requirements": "Compliance with all applicable laws and regulations",
                "conflict_resolution": "Procedures for resolving jurisdictional conflicts"
            }
        }

    async def provide_family_crisis_support(
        self,
        context: RunContextWrapper,
        crisis_type: Optional[str] = None,
        family_needs: Optional[str] = None,
        immediate_support: Optional[str] = None,
        long_term_planning: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide specialized support to families during crisis situations.
        
        Args:
            context: The conversation context
            crisis_type: Type of crisis affecting the family
            family_needs: Immediate and ongoing family support needs
            immediate_support: Immediate support interventions needed
            long_term_planning: Long-term support and planning needs
            
        Returns:
            Family crisis support plan and resource coordination
        """
        return {
            "family_crisis_support": f"Comprehensive support for {crisis_type or 'family crisis'}",
            "immediate_intervention": {
                "crisis_counseling": [
                    "Emergency grief counseling referral",
                    "Trauma-informed support services",
                    "Child and adolescent crisis support",
                    "Family crisis intervention services"
                ],
                "practical_support": [
                    "Emergency childcare arrangements",
                    "Transportation assistance",
                    "Temporary lodging if needed",
                    "Meal and basic needs support"
                ],
                "communication_support": [
                    "Help with death notification to extended family",
                    "Coordinate with employers and schools",
                    "Assist with media communication if needed",
                    "Social media and obituary assistance"
                ]
            },
            "specialized_crisis_support": {
                "sudden_death": {
                    "shock_support": "Specialized support for sudden loss trauma",
                    "investigation_support": "Support during death investigation process",
                    "media_protection": "Protection from unwanted media attention",
                    "legal_guidance": "Referral to appropriate legal counsel"
                },
                "traumatic_circumstances": {
                    "trauma_counseling": "Specialized trauma therapy referrals",
                    "ptsd_support": "Post-traumatic stress support resources",
                    "family_therapy": "Family therapy for trauma processing",
                    "long_term_therapy": "Long-term therapeutic support planning"
                },
                "multiple_losses": {
                    "mass_casualty_support": "Specialized support for multiple family losses",
                    "survivor_guilt": "Support for survivor guilt and trauma",
                    "community_support": "Connect with community support networks",
                    "memorial_planning": "Complex memorial and tribute planning"
                }
            },
            "resource_coordination": {
                "mental_health_services": [
                    "Emergency psychiatric services if needed",
                    "Crisis hotlines and 24/7 support",
                    "Local mental health providers",
                    "Support groups for specific types of loss"
                ],
                "financial_assistance": [
                    "Emergency financial assistance programs",
                    "Victim compensation programs",
                    "Insurance claim assistance",
                    "Fundraising and community support coordination"
                ],
                "legal_services": [
                    "Estate planning and probate assistance",
                    "Victim rights advocacy",
                    "Insurance and benefit claim support",
                    "Legal representation if needed"
                ],
                "community_resources": [
                    "Faith community support and pastoral care",
                    "Employer assistance programs",
                    "School counseling and support services",
                    "Volunteer support networks"
                ]
            },
            "follow_up_care": {
                "short_term": "Weekly check-ins for first month",
                "medium_term": "Monthly contact for first year", 
                "long_term": "Annual anniversary support and contact",
                "crisis_availability": "24/7 availability for crisis situations"
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

# Create the emergency agent instance
emergency_agent = EmergencyAgent()

# Expose the agent for importing by other modules
__all__ = ["emergency_agent", "EmergencyAgent"]
