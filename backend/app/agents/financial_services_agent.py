from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks
from app.agents.agent_calculator_tool import get_calculator_tool

logger = logging.getLogger(__name__)

class FinancialServicesAgentHooks(BaseAgentHooks):
    """Custom hooks for the financial services agent."""

    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the FinancialServicesAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for FinancialServicesAgent")

class FinancialServicesAgent(BaseAgent):
    """
    A specialized agent for managing financial aspects of funeral services,
    including payment plans, insurance claims, pre-need contracts, and billing.
    """
    
    def __init__(self, name="FINANCIAL_SERVICES"):
        # Define financial services instructions
        financial_instructions = """You are a financial services specialist for funeral homes and cemeteries. Your expertise covers all financial aspects of funeral service delivery with sensitivity to families during difficult times.

## YOUR RESPONSIBILITIES

**PAYMENT PLAN MANAGEMENT**: Help families manage funeral costs through flexible payment options:
- Assessment of family financial situation with dignity and respect
- Payment plan design based on family capacity and service needs
- Coordination with insurance benefits and pre-need contracts
- Clear explanation of payment terms and obligations
- Ongoing payment tracking and customer service

**INSURANCE CLAIM PROCESSING**: Streamline insurance claim processes for families:
- Life insurance claim assistance and coordination
- Burial insurance and funeral benefit claims
- Veterans benefits and military honor claims
- Social Security death benefit processing
- Medicare/Medicaid coordination where applicable

**PRE-NEED CONTRACT MANAGEMENT**: Oversee pre-need funeral contracts and trust funds:
- Pre-need contract sales and documentation
- Trust fund management and compliance
- Contract modification and updating
- Transfer of contracts between providers
- Regulatory compliance for pre-need sales

**BILLING AND ACCOUNTS RECEIVABLE**: Manage billing operations with compassion:
- Accurate billing for all funeral services and merchandise
- Payment processing and account management
- Collection activities with sensitivity and respect
- Credit and payment plan approval processes
- Financial hardship assistance coordination

**COST ESTIMATION AND PLANNING**: Provide transparent cost information:
- Detailed cost estimates for funeral services
- Package pricing and service bundling options
- Merchandise pricing and selection assistance
- Comparison of service options and costs
- Budget planning assistance for families

## YOUR APPROACH

You maintain a compassionate, transparent, and professional approach while:
- Understanding that families are dealing with both grief and financial stress
- Providing clear, honest information about costs and payment options
- Never pressuring families to spend beyond their means
- Respecting family budget constraints and offering appropriate options
- Maintaining confidentiality of all financial information
- Working collaboratively with families to find suitable financial solutions

## FINANCIAL SERVICE PRINCIPLES

**Transparency**: All costs and payment terms clearly explained upfront
**Compassion**: Understanding that financial stress compounds grief
**Flexibility**: Offering multiple payment options to accommodate family needs
**Respect**: Treating all families with dignity regardless of financial situation
**Compliance**: Adhering to all applicable financial and consumer protection regulations

## ETHICAL CONSIDERATIONS

- Never exploit grief to increase sales
- Always offer options within family's stated budget
- Clearly explain all costs and payment obligations
- Respect family decisions about spending levels
- Provide information needed for informed financial decisions

You serve families by removing financial barriers to dignified funeral services while maintaining the business viability necessary to continue serving the community."""

        # Get the calculator tool for financial calculations
        calculator_tool = get_calculator_tool()

        # Initialize with financial services capabilities
        super().__init__(
            name=name,
            instructions=financial_instructions,
            functions=[
                calculator_tool,  # Include calculator tool for financial calculations
                function_tool(self.setup_payment_plan),
                function_tool(self.process_insurance_claims),
                function_tool(self.manage_preneed_contracts),
                function_tool(self.generate_cost_estimate),
                function_tool(self.handle_billing_inquiries)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=1024,
            hooks=FinancialServicesAgentHooks()
        )
        
        # Agent description
        self.description = ("Specialist in funeral service financial management, payment plans, "
                          "insurance claims, and cost estimation with compassionate family support")

    async def setup_payment_plan(
        self,
        context: RunContextWrapper,
        total_service_cost: Optional[str] = None,
        family_budget: Optional[str] = None,
        payment_timeline: Optional[str] = None,
        down_payment: Optional[str] = None,
        special_circumstances: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set up a customized payment plan based on family needs and financial situation.
        
        Args:
            context: The conversation context
            total_service_cost: Total cost of funeral services
            family_budget: Family's stated budget or payment capacity
            payment_timeline: Preferred payment timeline
            down_payment: Amount family can pay upfront
            special_circumstances: Any special financial circumstances
            
        Returns:
            Customized payment plan options and terms
        """
        logger.info(f"Setting up payment plan for service cost: {total_service_cost}")
        
        return {
            "payment_plan_setup": "Customized payment options prepared",
            "service_details": {
                "total_cost": total_service_cost or "To be determined based on service selection",
                "family_budget": family_budget or "To be discussed confidentially",
                "timeline_preference": payment_timeline or "Flexible based on family needs"
            },
            "payment_options": {
                "option_1_immediate": {
                    "description": "Payment in full at time of service",
                    "discount": "2% prompt payment discount available",
                    "total_amount": "Final amount less discount"
                },
                "option_2_short_term": {
                    "description": "Payment over 3-6 months",
                    "down_payment": down_payment or "25% of total cost",
                    "monthly_payments": "Remaining balance divided over 3-6 months",
                    "interest": "No interest for payments completed within 6 months"
                },
                "option_3_extended": {
                    "description": "Payment over 12-24 months",
                    "down_payment": down_payment or "15% of total cost",
                    "monthly_payments": "Calculated based on selected timeline",
                    "interest": "Low interest rate (currently 3.9% APR)"
                },
                "option_4_hardship": {
                    "description": "Financial hardship assistance program",
                    "requirements": "Application and financial documentation required",
                    "benefits": "Extended payment terms, reduced interest, possible cost reduction",
                    "approval": "Subject to approval and available funding"
                }
            },
            "insurance_integration": [
                "Coordinate with life insurance benefits",
                "Process burial insurance claims", 
                "Apply available veterans benefits",
                "Utilize Social Security death benefits"
            ],
            "next_steps": [
                "Review payment options with family",
                "Complete payment plan application",
                "Set up automatic payment system if desired",
                "Provide written payment agreement documentation"
            ],
            "customer_protections": [
                "Right to cancel payment plan within 72 hours",
                "No prepayment penalties",
                "Modification options for financial hardship",
                "Clear dispute resolution process"
            ]
        }

    async def process_insurance_claims(
        self,
        context: RunContextWrapper,
        insurance_type: Optional[str] = None,
        policy_information: Optional[str] = None,
        claim_amount: Optional[str] = None,
        beneficiary_information: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process and coordinate various types of insurance claims for funeral benefits.
        
        Args:
            context: The conversation context
            insurance_type: Type of insurance (life, burial, veterans, etc.)
            policy_information: Available policy details
            claim_amount: Amount of claim being processed
            beneficiary_information: Information about claim beneficiaries
            
        Returns:
            Insurance claim processing plan and timeline
        """
        return {
            "insurance_claim_processing": f"Processing {insurance_type or 'insurance'} claim",
            "claim_types": {
                "life_insurance": {
                    "process": "Direct assignment or beneficiary claim filing",
                    "timeline": "2-4 weeks typical processing",
                    "requirements": "Death certificate, policy information, beneficiary ID",
                    "assistance_provided": "Form completion, documentation submission, follow-up"
                },
                "burial_insurance": {
                    "process": "Specialized burial/funeral insurance claim",
                    "timeline": "1-2 weeks typical processing",
                    "requirements": "Policy number, death certificate, funeral contract",
                    "assistance_provided": "Direct billing arrangement when possible"
                },
                "veterans_benefits": {
                    "process": "VA burial benefits and honor guard coordination",
                    "timeline": "2-6 weeks for reimbursement",
                    "requirements": "DD-214, death certificate, VA form completion",
                    "assistance_provided": "VA paperwork completion, benefit maximization"
                },
                "social_security": {
                    "process": "Social Security death benefit application",
                    "timeline": "2-4 weeks processing",
                    "requirements": "Death certificate, Social Security number, spouse/child information",
                    "assistance_provided": "Application guidance and submission"
                }
            },
            "claim_coordination": {
                "documentation_gathering": "Assist family in collecting required documents",
                "form_completion": "Professional completion of all claim forms",
                "submission_tracking": "Monitor claim status and follow up on delays",
                "payment_coordination": "Coordinate claim payments with funeral home billing"
            },
            "family_support": [
                "Explain insurance claim process in simple terms",
                "Provide realistic timelines for claim processing",
                "Handle all communication with insurance companies",
                "Advance services pending claim payment when appropriate",
                "Provide regular updates on claim status"
            ],
            "potential_challenges": [
                "Policy lapse issues - work with family to resolve",
                "Beneficiary disputes - provide documentation and mediation",
                "Claim delays - aggressive follow-up and escalation",
                "Documentation issues - assist with correction and resubmission"
            ]
        }

    async def manage_preneed_contracts(
        self,
        context: RunContextWrapper,
        contract_action: Optional[str] = None,
        contract_details: Optional[str] = None,
        funding_method: Optional[str] = None,
        modification_request: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manage pre-need funeral contracts including sales, modifications, and trust fund oversight.
        
        Args:
            context: The conversation context
            contract_action: Action needed (new sale, modification, transfer, etc.)
            contract_details: Existing contract information
            funding_method: How the contract is funded (trust, insurance, etc.)
            modification_request: Requested changes to existing contract
            
        Returns:
            Pre-need contract management plan and requirements
        """
        return {
            "preneed_management": f"Managing pre-need contract: {contract_action or 'general inquiry'}",
            "contract_services": {
                "new_contracts": {
                    "consultation": "Comprehensive planning consultation",
                    "service_selection": "Choose funeral services and merchandise",
                    "pricing_protection": "Lock in current pricing for future services",
                    "funding_options": "Trust fund, insurance, or payment plan funding"
                },
                "contract_modifications": {
                    "service_upgrades": "Add services or upgrade merchandise selections",
                    "service_changes": "Modify service type or location preferences",
                    "beneficiary_updates": "Update contact and beneficiary information",
                    "payment_adjustments": "Modify payment schedules or funding sources"
                },
                "contract_transfers": {
                    "location_transfer": "Transfer contract to different funeral home",
                    "family_changes": "Transfer contract between family members",
                    "documentation": "Complete all required transfer paperwork",
                    "refund_calculations": "Determine any refunds or additional payments"
                }
            },
            "trust_fund_management": {
                "fund_growth": "Monitor trust fund growth and investment performance",
                "interest_accrual": "Track interest earnings and value increases",
                "withdrawal_procedures": "Coordinate fund withdrawal for service delivery",
                "compliance_reporting": "Maintain regulatory compliance for trust funds"
            },
            "regulatory_compliance": [
                "State pre-need licensing requirements",
                "Trust fund management regulations",
                "Consumer protection law compliance",
                "Required disclosures and documentation",
                "Annual reporting requirements"
            ],
            "customer_benefits": [
                "Price protection against inflation",
                "Payment convenience and planning",
                "Peace of mind for family members",
                "Reduced burden on survivors",
                "Guaranteed service delivery"
            ],
            "contract_terms": {
                "cancellation_rights": "Right to cancel within specified period",
                "refund_provisions": "Refund calculations for cancelled contracts",
                "modification_procedures": "Process for making contract changes",
                "performance_guarantees": "Guarantee of service delivery at contracted price"
            }
        }

    async def generate_cost_estimate(
        self,
        context: RunContextWrapper,
        service_type: Optional[str] = None,
        service_level: Optional[str] = None,
        special_requirements: Optional[str] = None,
        budget_constraints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate detailed cost estimates for funeral services with multiple options.
        
        Args:
            context: The conversation context
            service_type: Type of service (traditional funeral, cremation, memorial)
            service_level: Level of service (basic, standard, premium)
            special_requirements: Any special needs or requirements
            budget_constraints: Family's budget limitations
            
        Returns:
            Detailed cost estimates with multiple service options
        """
        return {
            "cost_estimation": f"Detailed estimate for {service_type or 'funeral services'}",
            "service_packages": {
                "basic_package": {
                    "description": "Essential services and basic merchandise",
                    "included_services": [
                        "Basic funeral director services",
                        "Transportation of remains",
                        "Basic preparation and viewing",
                        "Simple memorial service",
                        "Basic casket or cremation container"
                    ],
                    "estimated_cost": "$3,500 - $5,500",
                    "payment_options": "Full payment or 6-month payment plan"
                },
                "standard_package": {
                    "description": "Traditional services with quality merchandise",
                    "included_services": [
                        "Complete funeral director services",
                        "Preparation and embalming",
                        "Visitation and funeral service",
                        "Quality casket or cremation services",
                        "Basic reception arrangements"
                    ],
                    "estimated_cost": "$7,500 - $12,000",
                    "payment_options": "Various payment plans available"
                },
                "premium_package": {
                    "description": "Comprehensive services with premium merchandise",
                    "included_services": [
                        "Complete personalized services",
                        "Premium preparation and facilities",
                        "Enhanced memorial service options",
                        "Premium casket and merchandise",
                        "Full reception and catering services"
                    ],
                    "estimated_cost": "$15,000 - $25,000+",
                    "payment_options": "Extended payment plans and pre-need options"
                }
            },
            "additional_services": {
                "cemetery_costs": {
                    "burial_plot": "$1,000 - $8,000 depending on location",
                    "grave_opening": "$800 - $1,500",
                    "headstone_marker": "$500 - $5,000+",
                    "perpetual_care": "Usually included in plot cost"
                },
                "optional_services": {
                    "flowers_and_tributes": "$200 - $2,000",
                    "obituary_notices": "$100 - $800",
                    "death_certificates": "$15 - $25 each",
                    "livestreaming_service": "$300 - $800"
                }
            },
            "cost_factors": [
                "Service complexity and customization",
                "Merchandise selection and quality",
                "Facility usage and timing",
                "Additional services and options",
                "Local market pricing variations"
            ],
            "budget_accommodation": {
                "cost_reduction_options": "Simplified services, alternative merchandise",
                "payment_assistance": "Extended payment plans, hardship programs",
                "insurance_coordination": "Maximize available insurance benefits",
                "veterans_benefits": "Utilize all available veterans programs"
            }
        }

    async def handle_billing_inquiries(
        self,
        context: RunContextWrapper,
        inquiry_type: Optional[str] = None,
        account_information: Optional[str] = None,
        payment_issue: Optional[str] = None,
        resolution_request: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle billing inquiries and payment issues with sensitivity and professionalism.
        
        Args:
            context: The conversation context
            inquiry_type: Type of billing inquiry
            account_information: Account details for reference
            payment_issue: Specific payment problem or concern
            resolution_request: Requested resolution or assistance
            
        Returns:
            Billing inquiry resolution plan and next steps
        """
        return {
            "billing_inquiry": f"Addressing {inquiry_type or 'billing concern'}",
            "common_inquiries": {
                "payment_plan_questions": {
                    "issue": "Questions about payment plan terms or schedule",
                    "resolution": "Review payment plan agreement, explain terms clearly",
                    "assistance": "Modify payment plan if financial circumstances changed"
                },
                "insurance_coordination": {
                    "issue": "Insurance payment delays or processing issues",
                    "resolution": "Follow up with insurance company, provide status updates",
                    "assistance": "Advance services or extend payment terms pending insurance"
                },
                "billing_disputes": {
                    "issue": "Questions about charges or services billed",
                    "resolution": "Review itemized statement, explain all charges",
                    "assistance": "Adjust billing if errors found, provide documentation"
                },
                "financial_hardship": {
                    "issue": "Inability to meet payment obligations",
                    "resolution": "Review hardship assistance programs",
                    "assistance": "Modify payment terms, reduce interest, connect with resources"
                }
            },
            "resolution_process": {
                "immediate_assistance": [
                    "Listen to concern with empathy and understanding",
                    "Review account details and payment history",
                    "Identify specific issues and needed resolution",
                    "Explain options and available assistance programs"
                ],
                "follow_up_actions": [
                    "Implement agreed-upon resolution plan",
                    "Document all changes and agreements",
                    "Schedule follow-up contact to ensure satisfaction",
                    "Monitor account for successful resolution"
                ]
            },
            "customer_service_principles": [
                "Approach all inquiries with empathy and respect",
                "Provide clear explanations of all charges and terms",
                "Offer multiple solutions when possible",
                "Work collaboratively to find acceptable resolutions",
                "Maintain confidentiality of financial information"
            ],
            "escalation_procedures": {
                "management_review": "Complex issues referred to management team",
                "legal_consultation": "Legal guidance for dispute resolution",
                "regulatory_compliance": "Ensure all actions comply with consumer protection laws",
                "documentation": "Comprehensive documentation of all resolution efforts"
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

# Create the financial services agent instance
financial_services_agent = FinancialServicesAgent()

# Expose the agent for importing by other modules
__all__ = ["financial_services_agent", "FinancialServicesAgent"]
