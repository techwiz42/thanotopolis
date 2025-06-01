from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
from agents import function_tool, ModelSettings, RunContextWrapper
from app.core.config import settings
from app.agents.base_agent import BaseAgent, BaseAgentHooks

logger = logging.getLogger(__name__)

class InventoryAgentHooks(BaseAgentHooks):
    """Custom hooks for the inventory and facilities management agent."""

    async def init_context(self, context: RunContextWrapper[Any]) -> None:
        """Initialize context for the InventoryAgent."""
        await super().init_context(context)
        logger.info(f"Initialized context for InventoryAgent")

class InventoryAgent(BaseAgent):
    """
    A specialized agent for managing inventory, facilities, equipment, and vendor relationships
    for funeral homes and cemeteries.
    """
    
    def __init__(self, name="INVENTORY"):
        # Define inventory management instructions
        inventory_instructions = """You are an inventory and facilities management specialist for funeral homes and cemeteries. Your expertise ensures efficient operations through proper inventory control, facility maintenance, and vendor management.

## YOUR RESPONSIBILITIES

**INVENTORY MANAGEMENT**: Oversee all funeral merchandise and supplies:
- Casket and urn inventory tracking and rotation
- Burial vaults and grave liners stock management
- Embalming supplies and chemicals inventory
- Office supplies and administrative materials
- Floral arrangement supplies and preservation materials
- Memorial products and personalization items

**FACILITY MAINTENANCE**: Ensure all facilities are properly maintained:
- Funeral home building maintenance and repairs
- Chapel and viewing room upkeep and decoration
- Preparation room equipment and sanitation
- Reception areas and family comfort amenities
- Cemetery grounds maintenance and landscaping
- Roadways, pathways, and accessibility features

**EQUIPMENT MANAGEMENT**: Maintain all operational equipment:
- Funeral vehicles (hearses, family cars, utility vehicles)
- Preparation room equipment and tools
- Audio/visual equipment for services
- Grounds maintenance equipment and machinery
- Office equipment and technology systems
- Safety equipment and emergency supplies

**CEMETERY OPERATIONS**: Manage cemetery-specific needs:
- Plot availability tracking and mapping
- Grave site preparation and maintenance
- Memorial installation and maintenance
- Seasonal decoration policies and coordination
- Security systems and access control
- Environmental compliance and conservation

**VENDOR RELATIONSHIPS**: Coordinate with suppliers and service providers:
- Merchandise vendors and distributors
- Maintenance contractors and service providers
- Equipment suppliers and repair services
- Utility companies and service providers
- Emergency services and backup systems

## YOUR APPROACH

You maintain an organized, proactive, and cost-effective approach while:
- Ensuring adequate inventory levels to meet family needs without over-stocking
- Maintaining facilities to the highest standards of appearance and functionality
- Prioritizing safety and compliance in all equipment and facility operations
- Building strong relationships with reliable vendors and service providers
- Planning for seasonal variations and special event requirements
- Implementing sustainable and environmentally responsible practices

## MANAGEMENT PRINCIPLES

**Preparedness**: Maintain adequate inventory and equipment for uninterrupted service
**Quality Control**: Ensure all facilities and equipment meet professional standards
**Cost Efficiency**: Optimize purchasing and maintenance for best value
**Safety First**: Prioritize safety in all facility and equipment operations
**Environmental Stewardship**: Implement sustainable practices where possible

You ensure that all operational aspects support the delivery of dignified funeral services while maintaining efficiency and cost-effectiveness."""

        # Initialize with inventory and facilities capabilities
        super().__init__(
            name=name,
            instructions=inventory_instructions,
            functions=[
                function_tool(self.manage_inventory_levels),
                function_tool(self.schedule_facility_maintenance),
                function_tool(self.track_equipment_status),
                function_tool(self.coordinate_vendor_relationships),
                function_tool(self.monitor_cemetery_operations)
            ],
            tool_choice="auto",
            parallel_tool_calls=True,
            max_tokens=1024,
            hooks=InventoryAgentHooks()
        )
        
        # Agent description
        self.description = ("Specialist in inventory management, facility maintenance, "
                          "equipment oversight, and vendor coordination for funeral operations")

    async def manage_inventory_levels(
        self,
        context: RunContextWrapper,
        inventory_category: Optional[str] = None,
        current_levels: Optional[str] = None,
        reorder_needs: Optional[str] = None,
        seasonal_adjustments: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manage inventory levels for all funeral merchandise and operational supplies.
        
        Args:
            context: The conversation context
            inventory_category: Specific category to focus on (caskets, urns, supplies, etc.)
            current_levels: Current inventory status
            reorder_needs: Items needing reorder or restocking
            seasonal_adjustments: Seasonal inventory adjustments needed
            
        Returns:
            Inventory management plan and reorder recommendations
        """
        logger.info(f"Managing inventory for category: {inventory_category}")
        
        return {
            "inventory_management": f"Comprehensive inventory review for {inventory_category or 'all categories'}",
            "inventory_categories": {
                "caskets": {
                    "current_stock": "18 caskets across price ranges",
                    "reorder_level": "Reorder when below 12 units",
                    "popular_models": "Track sales velocity of different styles",
                    "storage_requirements": "Climate-controlled storage, proper handling"
                },
                "urns_and_containers": {
                    "current_stock": "45 urns and cremation containers",
                    "reorder_level": "Reorder when below 30 units",
                    "variety_needs": "Maintain diverse selection for different preferences",
                    "display_rotation": "Rotate display models quarterly"
                },
                "embalming_supplies": {
                    "current_stock": "3-month supply of chemicals and supplies",
                    "reorder_level": "Reorder at 1-month remaining supply",
                    "expiration_tracking": "Monitor expiration dates for all chemicals",
                    "safety_compliance": "Maintain OSHA-compliant storage and handling"
                },
                "memorial_products": {
                    "current_stock": "Memorial books, cards, and keepsake items",
                    "reorder_level": "Reorder based on seasonal demand",
                    "customization_supplies": "Materials for personalizing services",
                    "trend_monitoring": "Stay current with memorial product trends"
                }
            },
            "reorder_recommendations": {
                "immediate_needs": [
                    "Standard burial caskets - order 6 units",
                    "Cremation urns - order 15 assorted styles",
                    "Embalming fluid - order 2-month supply"
                ],
                "upcoming_needs": [
                    "Holiday memorial items (seasonal)",
                    "Flowers and arrangement supplies",
                    "Office and administrative supplies"
                ],
                "long_term_planning": [
                    "Annual casket inventory assessment",
                    "Technology upgrades for tracking systems",
                    "Storage optimization improvements"
                ]
            },
            "cost_optimization": {
                "volume_purchasing": "Negotiate better pricing through consolidated orders",
                "vendor_relationships": "Leverage relationships for favorable terms",
                "inventory_turnover": "Optimize inventory levels to reduce carrying costs",
                "waste_reduction": "Minimize expired or obsolete inventory"
            },
            "quality_control": [
                "Regular inspection of all inventory items",
                "Proper storage conditions maintenance",
                "First-in-first-out rotation procedures",
                "Damage prevention and handling protocols"
            ]
        }

    async def schedule_facility_maintenance(
        self,
        context: RunContextWrapper,
        facility_area: Optional[str] = None,
        maintenance_type: Optional[str] = None,
        urgency_level: Optional[str] = None,
        budget_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule and coordinate facility maintenance to ensure professional appearance and functionality.
        
        Args:
            context: The conversation context
            facility_area: Specific area needing maintenance (chapel, preparation room, etc.)
            maintenance_type: Type of maintenance (routine, repair, upgrade, etc.)
            urgency_level: How urgent the maintenance need is
            budget_considerations: Budget constraints or considerations
            
        Returns:
            Facility maintenance schedule and coordination plan
        """
        return {
            "facility_maintenance": f"Scheduling maintenance for {facility_area or 'all facility areas'}",
            "maintenance_areas": {
                "public_spaces": {
                    "chapel_and_sanctuary": [
                        "Sound system maintenance and testing",
                        "Lighting inspection and bulb replacement",
                        "Carpet cleaning and furniture maintenance",
                        "Temperature control system servicing"
                    ],
                    "viewing_rooms": [
                        "Deep cleaning and sanitization",
                        "Furniture inspection and repair",
                        "Curtain and drape cleaning",
                        "Air filtration system maintenance"
                    ],
                    "reception_areas": [
                        "Kitchen equipment servicing",
                        "Furniture and fixture maintenance",
                        "Flooring care and refinishing",
                        "Restroom deep cleaning and supply"
                    ]
                },
                "operational_areas": {
                    "preparation_rooms": [
                        "Equipment calibration and maintenance",
                        "Ventilation system inspection",
                        "Plumbing and drainage maintenance",
                        "Safety equipment testing and compliance"
                    ],
                    "storage_areas": [
                        "Climate control system maintenance",
                        "Security system testing",
                        "Inventory organization and cleaning",
                        "Fire suppression system inspection"
                    ]
                },
                "exterior_maintenance": {
                    "building_exterior": [
                        "Exterior cleaning and pressure washing",
                        "Roof inspection and gutter cleaning",
                        "Parking lot maintenance and striping",
                        "Landscaping and grounds upkeep"
                    ],
                    "signage_and_lighting": [
                        "Sign cleaning and maintenance",
                        "Exterior lighting inspection",
                        "Security lighting functionality",
                        "Emergency lighting testing"
                    ]
                }
            },
            "maintenance_scheduling": {
                "routine_maintenance": "Monthly and quarterly scheduled maintenance",
                "seasonal_preparation": "Prepare facilities for seasonal changes",
                "emergency_repairs": "Immediate response for urgent repair needs",
                "preventive_maintenance": "Proactive maintenance to prevent problems"
            },
            "vendor_coordination": [
                "Schedule maintenance with trusted contractors",
                "Coordinate timing to minimize service disruption",
                "Supervise work quality and completion",
                "Maintain service records and warranties"
            ],
            "budget_management": {
                "maintenance_budget": "Track maintenance costs against annual budget",
                "cost_optimization": "Negotiate competitive pricing for regular services",
                "emergency_fund": "Maintain reserve for unexpected repairs",
                "capital_improvements": "Plan for major facility upgrades"
            }
        }

    async def track_equipment_status(
        self,
        context: RunContextWrapper,
        equipment_category: Optional[str] = None,
        maintenance_schedule: Optional[str] = None,
        replacement_planning: Optional[str] = None,
        safety_compliance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track status and maintenance of all operational equipment.
        
        Args:
            context: The conversation context
            equipment_category: Specific equipment category to focus on
            maintenance_schedule: Current maintenance schedule status
            replacement_planning: Equipment replacement planning needs
            safety_compliance: Safety and compliance status
            
        Returns:
            Equipment status report and maintenance recommendations
        """
        return {
            "equipment_tracking": f"Status monitoring for {equipment_category or 'all equipment'}",
            "equipment_categories": {
                "vehicles": {
                    "hearses": {
                        "fleet_size": "3 hearses (1 primary, 2 backup)",
                        "maintenance_status": "All vehicles current on scheduled maintenance",
                        "inspection_due": "Annual state inspection due for Vehicle #2",
                        "replacement_planning": "Consider replacement of 2018 model in 2026"
                    },
                    "family_cars": {
                        "fleet_size": "2 family limousines",
                        "maintenance_status": "Recent service completed on both vehicles",
                        "fuel_efficiency": "Monitor fuel costs and efficiency",
                        "appearance_standards": "Monthly detail cleaning scheduled"
                    }
                },
                "preparation_equipment": {
                    "embalming_equipment": {
                        "aspirator_machines": "2 units - last serviced 3 months ago",
                        "injection_machines": "3 units - annual calibration due",
                        "ventilation_systems": "Monthly filter replacement scheduled",
                        "safety_equipment": "Eyewash stations and safety showers tested monthly"
                    },
                    "cooling_systems": {
                        "refrigeration_units": "4 units - temperature monitoring daily",
                        "backup_power": "Generator tested monthly",
                        "alarm_systems": "Temperature alarms tested weekly",
                        "maintenance_contracts": "Service contracts current with providers"
                    }
                },
                "audio_visual_equipment": {
                    "sound_systems": "Chapel and viewing room systems tested weekly",
                    "presentation_equipment": "Projectors and screens maintained monthly",
                    "streaming_equipment": "Live streaming technology updated annually",
                    "backup_systems": "Backup equipment available for all critical systems"
                }
            },
            "maintenance_tracking": {
                "scheduled_maintenance": [
                    "Vehicle maintenance - monthly for all fleet vehicles",
                    "HVAC systems - quarterly professional service",
                    "Equipment calibration - annual for precision equipment",
                    "Safety systems - monthly testing and inspection"
                ],
                "replacement_schedule": [
                    "Hearse #1 replacement planned for 2026",
                    "Sound system upgrade scheduled for next budget cycle",
                    "Preparation room equipment refresh in 3-year plan",
                    "Computer and technology equipment on 4-year cycle"
                ]
            },
            "compliance_monitoring": [
                "OSHA safety equipment compliance",
                "Vehicle registration and inspection compliance",
                "Equipment calibration and certification records",
                "Insurance coverage for all equipment and vehicles"
            ],
            "performance_optimization": {
                "efficiency_tracking": "Monitor equipment performance and efficiency",
                "cost_analysis": "Track maintenance costs vs. replacement costs",
                "technology_updates": "Stay current with industry technology advances",
                "staff_training": "Ensure staff trained on all equipment operation"
            }
        }

    async def coordinate_vendor_relationships(
        self,
        context: RunContextWrapper,
        vendor_category: Optional[str] = None,
        service_needs: Optional[str] = None,
        contract_review: Optional[str] = None,
        performance_evaluation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinate relationships with vendors and service providers.
        
        Args:
            context: The conversation context
            vendor_category: Type of vendor (supplier, service provider, contractor)
            service_needs: Specific service needs or requirements
            contract_review: Contract review and renewal needs
            performance_evaluation: Vendor performance evaluation
            
        Returns:
            Vendor relationship management plan and recommendations
        """
        return {
            "vendor_coordination": f"Managing relationships with {vendor_category or 'all vendor categories'}",
            "vendor_categories": {
                "merchandise_suppliers": {
                    "casket_suppliers": {
                        "primary_vendor": "ABC Casket Company - 15-year relationship",
                        "contract_status": "Annual contract expires December 2024",
                        "performance_rating": "Excellent - reliable delivery and quality",
                        "pricing_review": "Annual pricing negotiation scheduled"
                    },
                    "urn_suppliers": {
                        "primary_vendor": "Memorial Products Inc.",
                        "specialty_vendors": "Local artisan suppliers for custom urns",
                        "inventory_management": "Just-in-time delivery system",
                        "quality_standards": "Maintain high quality standards for all products"
                    }
                },
                "service_providers": {
                    "maintenance_contractors": [
                        "HVAC maintenance - Johnson Services (monthly service)",
                        "Landscaping - Green Thumb Landscaping (weekly service)",
                        "Cleaning services - Professional Cleaners (daily service)",
                        "Security monitoring - SecureWatch (24/7 monitoring)"
                    ],
                    "professional_services": [
                        "Legal services - Smith & Associates (retainer agreement)",
                        "Accounting services - CPA Firm (monthly financial services)",
                        "Insurance broker - Insurance Partners (annual policy review)",
                        "IT support - TechSupport Plus (managed IT services)"
                    ]
                },
                "emergency_services": {
                    "backup_providers": "Maintain relationships with backup service providers",
                    "24_hour_services": "Ensure 24/7 availability for critical services",
                    "emergency_contacts": "Maintain updated emergency contact database",
                    "service_agreements": "Establish emergency service rate agreements"
                }
            },
            "relationship_management": {
                "regular_communication": "Scheduled meetings with key vendors quarterly",
                "performance_reviews": "Annual vendor performance evaluations",
                "contract_negotiations": "Proactive contract review and renewal",
                "vendor_development": "Work with vendors to improve service delivery"
            },
            "cost_management": {
                "competitive_bidding": "Regular competitive bidding for major contracts",
                "volume_discounts": "Leverage purchasing volume for better pricing",
                "payment_terms": "Negotiate favorable payment terms and conditions",
                "cost_benchmarking": "Compare vendor costs with industry standards"
            },
            "quality_assurance": [
                "Establish clear quality standards and expectations",
                "Regular quality audits and inspections",
                "Feedback systems for continuous improvement",
                "Vendor scorecards for performance tracking"
            ]
        }

    async def monitor_cemetery_operations(
        self,
        context: RunContextWrapper,
        operational_area: Optional[str] = None,
        maintenance_needs: Optional[str] = None,
        plot_management: Optional[str] = None,
        seasonal_considerations: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Monitor and coordinate cemetery operations including grounds, plots, and memorials.
        
        Args:
            context: The conversation context
            operational_area: Specific cemetery area to focus on
            maintenance_needs: Maintenance requirements or issues
            plot_management: Plot availability and management needs
            seasonal_considerations: Seasonal operational considerations
            
        Returns:
            Cemetery operations status and management recommendations
        """
        return {
            "cemetery_operations": f"Monitoring operations for {operational_area or 'all cemetery areas'}",
            "grounds_management": {
                "landscaping_maintenance": {
                    "grass_care": "Weekly mowing during growing season",
                    "tree_maintenance": "Annual pruning and health assessment",
                    "flower_beds": "Seasonal planting and maintenance",
                    "irrigation_system": "Automated system with weekly inspection"
                },
                "infrastructure_maintenance": {
                    "roadways": "Monthly inspection and repair as needed",
                    "pathways": "Accessible pathways maintained for safety",
                    "drainage": "Proper drainage maintenance for weather protection",
                    "fencing_gates": "Security fencing and gate maintenance"
                },
                "environmental_stewardship": {
                    "water_conservation": "Efficient irrigation and water management",
                    "chemical_reduction": "Minimize chemical fertilizers and pesticides",
                    "native_plantings": "Use native plants to reduce maintenance needs",
                    "wildlife_protection": "Maintain habitat for local wildlife"
                }
            },
            "plot_management": {
                "availability_tracking": {
                    "plot_inventory": "Current availability: 45% of plots remain",
                    "section_planning": "Development plan for new sections",
                    "plot_mapping": "Digital mapping system for accurate record keeping",
                    "reservation_system": "Pre-need plot sales and reservation tracking"
                },
                "burial_coordination": {
                    "grave_preparation": "Coordinate grave opening with burial schedules",
                    "memorial_installation": "Schedule and oversee headstone installation",
                    "plot_maintenance": "Individual plot care and maintenance",
                    "family_services": "Assist families with plot selection and care"
                }
            },
            "memorial_management": {
                "headstone_monuments": {
                    "installation_oversight": "Supervise all memorial installations",
                    "maintenance_inspection": "Annual inspection of all memorials",
                    "repair_coordination": "Coordinate memorial repairs with families",
                    "design_standards": "Maintain cemetery design and aesthetic standards"
                },
                "special_memorials": {
                    "memorial_gardens": "Maintain dedicated memorial garden areas",
                    "cremation_gardens": "Specialized areas for cremated remains",
                    "veteran_sections": "Honor guard and veteran memorial areas",
                    "children_areas": "Specialized sections for infant and child burials"
                }
            },
            "seasonal_operations": {
                "spring_preparation": "Ground preparation after winter, landscaping renewal",
                "summer_maintenance": "Intensive grounds care during growing season",
                "fall_cleanup": "Leaf removal, winterization of irrigation systems",
                "winter_operations": "Snow removal, weather protection, limited access management"
            },
            "regulatory_compliance": [
                "Cemetery licensing and permit compliance",
                "Environmental regulations and monitoring",
                "Health department requirements",
                "Accessibility standards compliance",
                "Record keeping and reporting requirements"
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

# Create the inventory agent instance
inventory_agent = InventoryAgent()

# Expose the agent for importing by other modules
__all__ = ["inventory_agent", "InventoryAgent"]
