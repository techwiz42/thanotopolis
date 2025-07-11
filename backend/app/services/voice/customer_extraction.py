# backend/app/services/voice/customer_extraction.py
"""
Customer Information Extraction Service for Voice Agent
Extracts customer contact information from natural conversation flow
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import Contact, User
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CustomerData:
    """Structured customer data extracted from voice conversation"""
    # Core identification
    contact_name: Optional[str] = None
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    
    # Location information
    city: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    
    # Service context
    service_type: Optional[str] = None
    service_notes: Optional[str] = None
    urgency: Optional[str] = None  # 'urgent', 'normal', 'low'
    
    # Cemetery-specific fields (for cemetery organizations)
    deceased_name: Optional[str] = None
    relationship_to_deceased: Optional[str] = None
    family_name: Optional[str] = None
    
    # Metadata
    extraction_confidence: float = 0.0
    extracted_from_conversation: List[str] = None
    
    def __post_init__(self):
        if self.extracted_from_conversation is None:
            self.extracted_from_conversation = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def is_sufficient_for_contact(self) -> bool:
        """Check if we have enough information to create a contact"""
        # Minimum requirements: name and (phone OR email)
        has_name = bool(self.contact_name or self.business_name)
        has_contact_method = bool(self.phone_number or self.email)
        return has_name and has_contact_method
    
    def get_confidence_score(self) -> float:
        """Calculate overall confidence based on extracted fields"""
        score = 0.0
        field_weights = {
            'contact_name': 0.3,
            'business_name': 0.2,
            'phone_number': 0.2,
            'email': 0.2,
            'city': 0.05,
            'state': 0.05
        }
        
        for field, weight in field_weights.items():
            if getattr(self, field):
                score += weight
        
        return min(score, 1.0)


class CustomerExtractionService:
    """Service for extracting customer information from voice conversations"""
    
    def __init__(self):
        self.extraction_prompt = self._build_extraction_prompt()
        
    def _build_extraction_prompt(self) -> str:
        """Build the extraction prompt for the LLM"""
        return """
You are an expert information extraction specialist for a customer service voice agent. 
Your job is to extract customer contact information from natural conversation snippets.

Extract the following information when mentioned:
- contact_name: Person's first and last name
- business_name: Company or business name  
- phone_number: Phone number in any format
- email: Email address
- city: City name
- state: State or province
- address: Full street address
- service_type: Type of service they're calling about
- service_notes: What specifically they need help with
- urgency: How urgent their request is (urgent/normal/low)
- deceased_name: Name of deceased person (for cemetery services)
- relationship_to_deceased: Caller's relationship to deceased
- family_name: Family surname if different from contact

IMPORTANT EXTRACTION RULES:
1. Only extract information that is explicitly stated
2. Do not infer or guess information
3. Normalize phone numbers to standard format (+1XXXXXXXXXX)
4. Convert partial information to complete forms when possible
5. Assign confidence scores (0.0-1.0) based on clarity

Return ONLY valid JSON in this exact format:
{
    "contact_name": "string or null",
    "business_name": "string or null", 
    "phone_number": "string or null",
    "email": "string or null",
    "city": "string or null",
    "state": "string or null",
    "address": "string or null",
    "service_type": "string or null",
    "service_notes": "string or null",
    "urgency": "string or null",
    "deceased_name": "string or null",
    "relationship_to_deceased": "string or null",
    "family_name": "string or null",
    "extraction_confidence": 0.0
}
"""

    async def extract_customer_data(
        self, 
        conversation_text: str,
        existing_data: Optional[CustomerData] = None
    ) -> CustomerData:
        """
        Extract customer information from conversation text
        
        Args:
            conversation_text: The conversation text to analyze
            existing_data: Previously extracted data to merge with
            
        Returns:
            CustomerData object with extracted information
        """
        try:
            # Import here to avoid circular imports
            from app.services.llm_service import llm_service
            
            # Prepare extraction prompt with conversation
            full_prompt = f"{self.extraction_prompt}\n\nConversation to analyze:\n{conversation_text}"
            
            # Get extraction from LLM
            response = await llm_service.get_completion(
                prompt=full_prompt,
                model="gpt-4o-mini",  # Fast model for extraction
                temperature=0.1,  # Low temperature for consistency
                max_tokens=500
            )
            
            # Parse JSON response
            extracted_data = self._parse_extraction_response(response)
            
            # Create CustomerData object
            new_data = CustomerData(**extracted_data)
            new_data.extracted_from_conversation.append(conversation_text[:200])  # Keep snippet
            
            # Merge with existing data if provided
            if existing_data:
                merged_data = self._merge_customer_data(existing_data, new_data)
                logger.info(f"Merged customer data: confidence={merged_data.get_confidence_score():.2f}")
                return merged_data
            else:
                logger.info(f"Extracted new customer data: confidence={new_data.get_confidence_score():.2f}")
                return new_data
                
        except Exception as e:
            logger.error(f"Error extracting customer data: {e}")
            # Return existing data or empty data on error
            return existing_data or CustomerData()
    
    def _parse_extraction_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response and extract JSON data"""
        try:
            # Clean up response - remove markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            data = json.loads(cleaned_response)
            
            # Validate and normalize data
            return self._normalize_extracted_data(data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            logger.error(f"Response was: {response}")
            return {}
        except Exception as e:
            logger.error(f"Error processing extraction response: {e}")
            return {}
    
    def _normalize_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate extracted data"""
        normalized = {}
        
        # Normalize phone number
        if data.get('phone_number'):
            normalized['phone_number'] = self._normalize_phone_number(data['phone_number'])
        
        # Normalize email
        if data.get('email'):
            email = data['email'].lower().strip()
            if self._is_valid_email(email):
                normalized['email'] = email
        
        # Normalize names (title case)
        for name_field in ['contact_name', 'business_name', 'deceased_name', 'family_name']:
            if data.get(name_field):
                normalized[name_field] = data[name_field].strip().title()
        
        # Normalize location (title case)
        for location_field in ['city', 'state']:
            if data.get(location_field):
                normalized[location_field] = data[location_field].strip().title()
        
        # Normalize urgency
        if data.get('urgency'):
            urgency = data['urgency'].lower().strip()
            if urgency in ['urgent', 'high', 'emergency']:
                normalized['urgency'] = 'urgent'
            elif urgency in ['normal', 'medium', 'regular']:
                normalized['urgency'] = 'normal'
            elif urgency in ['low', 'whenever', 'no rush']:
                normalized['urgency'] = 'low'
        
        # Copy other fields as-is
        for field in ['address', 'service_type', 'service_notes', 'relationship_to_deceased']:
            if data.get(field):
                normalized[field] = data[field].strip()
        
        # Handle confidence
        if 'extraction_confidence' in data:
            try:
                normalized['extraction_confidence'] = float(data['extraction_confidence'])
            except (ValueError, TypeError):
                normalized['extraction_confidence'] = 0.0
        
        return normalized
    
    def _normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number to E.164 format"""
        if not phone:
            return None
            
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Handle different formats
        if len(digits) == 10:
            # US number without country code
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            # US number with country code
            return f"+{digits}"
        elif len(digits) >= 7:
            # International or other format
            return f"+{digits}"
        
        return None
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _merge_customer_data(self, existing: CustomerData, new: CustomerData) -> CustomerData:
        """Merge new data with existing data, preferring more recent/confident data"""
        merged = CustomerData()
        
        # Merge conversation history
        merged.extracted_from_conversation = (
            existing.extracted_from_conversation + new.extracted_from_conversation
        )
        
        # For each field, use new data if it exists, otherwise keep existing
        for field in CustomerData.__dataclass_fields__.keys():
            if field == 'extracted_from_conversation':
                continue  # Already handled above
                
            existing_value = getattr(existing, field)
            new_value = getattr(new, field)
            
            # Use new value if it exists and is not None/empty
            if new_value and str(new_value).strip():
                setattr(merged, field, new_value)
            else:
                setattr(merged, field, existing_value)
        
        # Update confidence to be the maximum of both
        merged.extraction_confidence = max(
            existing.extraction_confidence, 
            new.extraction_confidence
        )
        
        return merged
    
    async def find_existing_contact(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        customer_data: CustomerData
    ) -> Optional[Contact]:
        """
        Find existing contact matching the customer data
        
        Args:
            db: Database session
            tenant_id: Organization ID
            customer_data: Extracted customer data
            
        Returns:
            Matching Contact object or None
        """
        try:
            # Build query conditions
            conditions = [Contact.tenant_id == tenant_id]
            
            # Search by phone number (primary match)
            if customer_data.phone_number:
                phone_condition = Contact.phone == customer_data.phone_number
                conditions.append(phone_condition)
                
                query = select(Contact).where(and_(*conditions))
                result = await db.execute(query)
                contact = result.scalar_one_or_none()
                if contact:
                    logger.info(f"Found existing contact by phone: {contact.id}")
                    return contact
                
                # Remove phone condition for next search
                conditions.pop()
            
            # Search by email (secondary match)
            if customer_data.email:
                email_condition = Contact.contact_email == customer_data.email
                conditions.append(email_condition)
                
                query = select(Contact).where(and_(*conditions))
                result = await db.execute(query)
                contact = result.scalar_one_or_none()
                if contact:
                    logger.info(f"Found existing contact by email: {contact.id}")
                    return contact
                
                # Remove email condition for next search
                conditions.pop()
            
            # Search by name combination (tertiary match)
            if customer_data.contact_name and customer_data.business_name:
                name_conditions = [
                    Contact.contact_name.ilike(f"%{customer_data.contact_name}%"),
                    Contact.business_name.ilike(f"%{customer_data.business_name}%")
                ]
                conditions.extend(name_conditions)
                
                query = select(Contact).where(and_(*conditions))
                result = await db.execute(query)
                contact = result.scalar_one_or_none()
                if contact:
                    logger.info(f"Found existing contact by name: {contact.id}")
                    return contact
            
            logger.info("No existing contact found")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for existing contact: {e}")
            return None
    
    async def create_contact_from_data(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        customer_data: CustomerData
    ) -> Optional[Contact]:
        """
        Create a new contact from extracted customer data
        
        Args:
            db: Database session
            tenant_id: Organization ID
            user_id: User creating the contact
            customer_data: Extracted customer data
            
        Returns:
            Created Contact object or None
        """
        try:
            if not customer_data.is_sufficient_for_contact():
                logger.warning("Insufficient data to create contact")
                return None
            
            # Create custom fields for extracted data
            custom_fields = {}
            if customer_data.service_type:
                custom_fields['service_type'] = customer_data.service_type
            if customer_data.service_notes:
                custom_fields['service_notes'] = customer_data.service_notes
            if customer_data.urgency:
                custom_fields['urgency'] = customer_data.urgency
            if customer_data.deceased_name:
                custom_fields['deceased_name'] = customer_data.deceased_name
            if customer_data.relationship_to_deceased:
                custom_fields['relationship_to_deceased'] = customer_data.relationship_to_deceased
            if customer_data.family_name:
                custom_fields['family_name'] = customer_data.family_name
            
            # Add extraction metadata
            custom_fields['extracted_from_voice'] = True
            custom_fields['extraction_confidence'] = customer_data.extraction_confidence
            custom_fields['conversation_snippets'] = customer_data.extracted_from_conversation
            
            # Create contact
            contact = Contact(
                tenant_id=tenant_id,
                business_name=customer_data.business_name or "Voice Call Contact",
                contact_name=customer_data.contact_name or "Unknown Caller",
                contact_email=customer_data.email,
                phone=customer_data.phone_number,
                city=customer_data.city,
                state=customer_data.state,
                address=customer_data.address,
                status='lead',  # New voice contacts start as leads
                notes=f"Contact created from voice call. Service: {customer_data.service_type or 'General inquiry'}",
                custom_fields=custom_fields,
                created_by_user_id=user_id
            )
            
            db.add(contact)
            await db.commit()
            await db.refresh(contact)
            
            logger.info(f"Created new contact from voice data: {contact.id}")
            return contact
            
        except Exception as e:
            logger.error(f"Error creating contact from customer data: {e}")
            await db.rollback()
            return None
    
    async def update_contact_from_data(
        self,
        db: AsyncSession,
        contact: Contact,
        customer_data: CustomerData
    ) -> Contact:
        """
        Update existing contact with new customer data
        
        Args:
            db: Database session
            contact: Existing contact to update
            customer_data: New customer data
            
        Returns:
            Updated Contact object
        """
        try:
            updated = False
            
            # Update fields if new data is available
            if customer_data.business_name and not contact.business_name:
                contact.business_name = customer_data.business_name
                updated = True
            
            if customer_data.contact_name and not contact.contact_name:
                contact.contact_name = customer_data.contact_name
                updated = True
            
            if customer_data.email and not contact.contact_email:
                contact.contact_email = customer_data.email
                updated = True
            
            if customer_data.phone_number and not contact.phone:
                contact.phone = customer_data.phone_number
                updated = True
            
            if customer_data.city and not contact.city:
                contact.city = customer_data.city
                updated = True
            
            if customer_data.state and not contact.state:
                contact.state = customer_data.state
                updated = True
            
            if customer_data.address and not contact.address:
                contact.address = customer_data.address
                updated = True
            
            # Update custom fields
            custom_fields = contact.custom_fields or {}
            
            # Add new service information
            if customer_data.service_type:
                custom_fields['latest_service_type'] = customer_data.service_type
            if customer_data.service_notes:
                custom_fields['latest_service_notes'] = customer_data.service_notes
            if customer_data.urgency:
                custom_fields['latest_urgency'] = customer_data.urgency
            
            # Add extraction metadata
            custom_fields['last_voice_update'] = customer_data.extraction_confidence
            
            # Append conversation snippets
            existing_snippets = custom_fields.get('conversation_snippets', [])
            if isinstance(existing_snippets, list):
                existing_snippets.extend(customer_data.extracted_from_conversation)
            else:
                existing_snippets = customer_data.extracted_from_conversation
            custom_fields['conversation_snippets'] = existing_snippets[-10:]  # Keep last 10
            
            contact.custom_fields = custom_fields
            updated = True
            
            if updated:
                await db.commit()
                await db.refresh(contact)
                logger.info(f"Updated existing contact with voice data: {contact.id}")
            
            return contact
            
        except Exception as e:
            logger.error(f"Error updating contact with customer data: {e}")
            await db.rollback()
            return contact


# Service singleton
_customer_extraction_service: Optional[CustomerExtractionService] = None


def get_customer_extraction_service() -> CustomerExtractionService:
    """Get CustomerExtractionService singleton"""
    global _customer_extraction_service
    if _customer_extraction_service is None:
        _customer_extraction_service = CustomerExtractionService()
    return _customer_extraction_service