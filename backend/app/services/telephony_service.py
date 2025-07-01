# backend/app/services/telephony_service.py
"""
Telephony service for managing phone verification and call handling
"""

import asyncio
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, and_, or_
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException

from app.models.models import (
    TelephonyConfiguration, PhoneVerificationAttempt, PhoneCall,
    PhoneVerificationStatus, CallStatus, CallDirection, Tenant, UsageRecord
)
from app.core.config import settings
from app.services.usage_service import usage_service

logger = logging.getLogger(__name__)

class TelephonyService:
    """Service for managing telephony operations"""
    
    def __init__(self):
        # Initialize Twilio client if credentials are available
        self.twilio_client = None
        if hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN'):
            try:
                self.twilio_client = TwilioClient(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("✅ Twilio client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio client: {e}")
        else:
            logger.warning("⚠️  Twilio credentials not configured, using mock mode")
    
    async def setup_organization_phone(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        organization_phone_number: str,
        welcome_message: Optional[str] = None,
        business_hours: Optional[Dict] = None
    ) -> TelephonyConfiguration:
        """Set up telephony configuration for an organization with their existing phone number"""
        
        # Validate phone number format
        normalized_phone = self._normalize_phone_number(organization_phone_number)
        if not normalized_phone:
            raise ValueError("Invalid phone number format")
        
        # Check if this organization already has telephony configured
        config_query = select(TelephonyConfiguration).where(
            TelephonyConfiguration.tenant_id == tenant_id
        )
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if config:
            # Update existing configuration
            config.organization_phone_number = normalized_phone
            config.formatted_phone_number = self._format_phone_number(normalized_phone)
            
            # Auto-verify if organization number matches platform number (Twilio-purchased number)
            is_twilio_purchased = (normalized_phone == config.platform_phone_number)
            config.verification_status = PhoneVerificationStatus.VERIFIED.value if is_twilio_purchased else PhoneVerificationStatus.PENDING.value
            config.call_forwarding_enabled = is_twilio_purchased or config.call_forwarding_enabled  # Preserve existing state or auto-enable
            
            config.welcome_message = welcome_message or config.welcome_message
            config.business_hours = business_hours or config.business_hours
        else:
            # Assign a platform phone number for this organization
            platform_number = await self._assign_platform_phone_number(db, tenant_id)
            
            # Auto-verify if organization number matches platform number (Twilio-purchased number)
            is_twilio_purchased = (normalized_phone == platform_number)
            verification_status = PhoneVerificationStatus.VERIFIED.value if is_twilio_purchased else PhoneVerificationStatus.PENDING.value
            call_forwarding_enabled = is_twilio_purchased  # Auto-enable for Twilio numbers
            
            # Create new configuration
            config = TelephonyConfiguration(
                tenant_id=tenant_id,
                organization_phone_number=normalized_phone,
                formatted_phone_number=self._format_phone_number(normalized_phone),
                country_code=self._extract_country_code(normalized_phone),
                platform_phone_number=platform_number,
                welcome_message=welcome_message or "Hello! Thank you for calling. How can our AI assistant help you today?",
                business_hours=business_hours or self._default_business_hours(),
                verification_status=verification_status,
                call_forwarding_enabled=call_forwarding_enabled,
                forwarding_instructions=self._generate_forwarding_instructions(platform_number)
            )
            db.add(config)
        
        await db.commit()
        await db.refresh(config)
        
        # Log verification status
        if config.verification_status == PhoneVerificationStatus.VERIFIED.value and normalized_phone == config.platform_phone_number:
            logger.info(f"📞 Phone configuration created/updated for tenant {tenant_id}: {normalized_phone} -> {config.platform_phone_number} (auto-verified as Twilio-purchased number)")
        else:
            logger.info(f"📞 Phone configuration created/updated for tenant {tenant_id}: {normalized_phone} -> {config.platform_phone_number} (verification required)")
        
        return config
    
    async def initiate_phone_verification(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        verification_method: str = "sms"
    ) -> PhoneVerificationAttempt:
        """Initiate phone number verification for the organization's existing phone number"""
        
        # Get telephony configuration
        config_query = select(TelephonyConfiguration).where(
            TelephonyConfiguration.tenant_id == tenant_id
        )
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if not config:
            raise ValueError("No telephony configuration found for organization")
        
        # Generate verification code
        verification_code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
        
        # Create verification attempt
        verification = PhoneVerificationAttempt(
            telephony_config_id=config.id,
            verification_code=verification_code,
            verification_method=verification_method,
            organization_phone_number=config.organization_phone_number,  # Verify the org's number
            expires_at=datetime.utcnow() + timedelta(minutes=10)  # 10-minute expiry
        )
        
        db.add(verification)
        await db.commit()
        await db.refresh(verification)
        
        # Send verification code to the organization's phone number
        success = await self._send_verification_code(
            config.organization_phone_number,  # Send to org's number
            verification_code,
            verification_method
        )
        
        if not success:
            verification.status = PhoneVerificationStatus.FAILED.value
            await db.commit()
            raise RuntimeError("Failed to send verification code")
        
        logger.info(f"📨 Verification code sent to organization number {config.organization_phone_number} via {verification_method}")
        return verification
    
    async def verify_phone_number(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        verification_code: str
    ) -> bool:
        """Verify organization's phone number ownership with provided code"""
        
        # Get the latest verification attempt
        verification_query = select(PhoneVerificationAttempt).join(
            TelephonyConfiguration
        ).where(
            and_(
                TelephonyConfiguration.tenant_id == tenant_id,
                PhoneVerificationAttempt.status == PhoneVerificationStatus.PENDING.value,
                PhoneVerificationAttempt.expires_at > datetime.utcnow()
            )
        ).order_by(PhoneVerificationAttempt.created_at.desc())
        
        verification_result = await db.execute(verification_query)
        verification = verification_result.scalar_one_or_none()
        
        if not verification:
            raise ValueError("No valid verification attempt found")
        
        # Increment attempt count
        verification.attempts_count += 1
        
        # Check if code matches
        if verification.verification_code == verification_code:
            # Verification successful
            verification.status = PhoneVerificationStatus.VERIFIED.value
            verification.verified_at = datetime.utcnow()
            
            # Update telephony configuration - enable call forwarding
            config_update = update(TelephonyConfiguration).where(
                TelephonyConfiguration.id == verification.telephony_config_id
            ).values(
                verification_status=PhoneVerificationStatus.VERIFIED.value,
                call_forwarding_enabled=True  # Enable forwarding after verification
            )
            
            await db.execute(config_update)
            await db.commit()
            
            logger.info(f"✅ Organization phone number verified for tenant {tenant_id}")
            return True
        else:
            # Check if max attempts reached
            if verification.attempts_count >= verification.max_attempts:
                verification.status = PhoneVerificationStatus.FAILED.value
            
            await db.commit()
            logger.warning(f"❌ Invalid verification code for tenant {tenant_id}")
            return False
    
    async def handle_incoming_call(
        self,
        db: AsyncSession,
        call_sid: str,
        customer_number: str,  # The actual caller
        platform_number: str,  # Our Twilio number that received the call
        call_metadata: Optional[Dict] = None
    ) -> PhoneCall:
        """Handle incoming phone call to our platform number"""
        
        # Find telephony configuration by platform phone number
        # Handle case where multiple configs might exist for same number
        config_query = select(TelephonyConfiguration).where(
            TelephonyConfiguration.platform_phone_number == self._normalize_phone_number(platform_number)
        ).order_by(TelephonyConfiguration.created_at.desc())
        config_result = await db.execute(config_query)
        configs = config_result.scalars().all()
        
        if not configs:
            config = None
        else:
            # Use the most recently created verified config, or the most recent one
            verified_configs = [c for c in configs if c.verification_status == PhoneVerificationStatus.VERIFIED.value]
            config = verified_configs[0] if verified_configs else configs[0]
            
            # Log warning if duplicates exist
            if len(configs) > 1:
                self.logger.warning(
                    f"Multiple telephony configurations found for platform number {platform_number}. "
                    f"Using config {config.id} for tenant {config.tenant_id}"
                )
        
        if not config:
            raise ValueError(f"No organization found for platform number {platform_number}")
        
        # Check if organization has telephony enabled and verified
        if not config.is_enabled:
            raise ValueError("Telephony is disabled for this organization")
        
        if config.verification_status != PhoneVerificationStatus.VERIFIED.value:
            raise ValueError("Organization phone number not verified")
        
        # Check concurrent call limits
        active_calls_query = select(PhoneCall).where(
            and_(
                PhoneCall.telephony_config_id == config.id,
                PhoneCall.status.in_([
                    CallStatus.INCOMING.value,
                    CallStatus.RINGING.value,
                    CallStatus.ANSWERED.value,
                    CallStatus.IN_PROGRESS.value
                ])
            )
        )
        active_calls_result = await db.execute(active_calls_query)
        active_calls_count = len(active_calls_result.all())
        
        if active_calls_count >= config.max_concurrent_calls:
            raise ValueError("Maximum concurrent calls reached for this organization")
        
        # Create phone call record
        phone_call = PhoneCall(
            telephony_config_id=config.id,
            call_sid=call_sid,
            customer_phone_number=self._normalize_phone_number(customer_number),
            organization_phone_number=config.organization_phone_number,
            platform_phone_number=self._normalize_phone_number(platform_number),
            direction=CallDirection.INBOUND.value,
            status=CallStatus.INCOMING.value,
            call_metadata=call_metadata or {},
            start_time=datetime.utcnow()
        )
        
        db.add(phone_call)
        await db.commit()
        await db.refresh(phone_call)
        
        logger.info(f"📞 Incoming call recorded: {call_sid} from {customer_number} to {config.organization_phone_number} (via {platform_number})")
        return phone_call
    
    async def update_call_status(
        self,
        db: AsyncSession,
        call_sid: str,
        status: CallStatus,
        additional_data: Optional[Dict] = None
    ) -> PhoneCall:
        """Update call status and metadata"""
        
        # Find call by SID
        call_query = select(PhoneCall).where(PhoneCall.call_sid == call_sid)
        call_result = await db.execute(call_query)
        call = call_result.scalar_one_or_none()
        
        if not call:
            raise ValueError(f"Call not found: {call_sid}")
        
        # Update status
        call.status = status.value
        
        # Update timestamps based on status
        now = datetime.now(timezone.utc)
        if status == CallStatus.ANSWERED and not call.answer_time:
            call.answer_time = now
        elif status in [CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.NO_ANSWER]:
            call.end_time = now
            if call.answer_time:
                # Ensure both timestamps are timezone-aware
                answer_time = call.answer_time
                if answer_time.tzinfo is None:
                    answer_time = answer_time.replace(tzinfo=timezone.utc)
                call.duration_seconds = int((now - answer_time).total_seconds())
        
        # Update metadata
        if additional_data:
            current_metadata = call.call_metadata or {}
            current_metadata.update(additional_data)
            call.call_metadata = current_metadata
        
        await db.commit()
        await db.refresh(call)
        
        # Record usage if call completed (but not for voice agent calls - they handle their own usage)
        if status == CallStatus.COMPLETED and call.duration_seconds:
            # Check if this is a voice agent call by looking for existing usage records with voice_agent_type
            existing_usage = await db.execute(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.additional_data.op('->>')('call_id') == str(call.id),
                        UsageRecord.additional_data.op('->>')('voice_agent_type') == 'deepgram_integrated'
                    )
                ).limit(1)
            )
            voice_agent_usage = existing_usage.scalar_one_or_none()
            
            if not voice_agent_usage:
                # Not a voice agent call, record usage normally
                await self._record_call_usage(db, call)
            else:
                logger.info(f"📞 Call {call.call_sid} usage already handled by voice agent, skipping duplicate recording")
        
        logger.info(f"📞 Call {call_sid} status updated to {status.value}")
        return call
    
    async def get_organization_calls(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[CallStatus] = None
    ) -> List[PhoneCall]:
        """Get calls for an organization"""
        
        query = select(PhoneCall).join(TelephonyConfiguration).where(
            TelephonyConfiguration.tenant_id == tenant_id
        )
        
        if status_filter:
            query = query.where(PhoneCall.status == status_filter.value)
        
        query = query.order_by(PhoneCall.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    def _normalize_phone_number(self, phone_number: str) -> Optional[str]:
        """Normalize phone number to E.164 format"""
        if not phone_number:
            return None
        
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Check for minimum valid length
        if len(digits) < 7:  # Minimum valid phone number length
            return None
        
        # Add country code if missing (assume US +1 for now)
        if len(digits) == 10:
            digits = '1' + digits
        
        return '+' + digits if digits else None
    
    def _format_phone_number(self, normalized_number: str) -> str:
        """Format phone number for display"""
        if not normalized_number:
            return ""
        
        digits = normalized_number.replace('+', '')
        if len(digits) == 11 and digits.startswith('1'):
            # US format
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
        
        return normalized_number
    
    def _extract_country_code(self, normalized_number: str) -> str:
        """Extract country code from normalized number"""
        if not normalized_number:
            return "US"
        
        if normalized_number.startswith('+1'):
            return "US"
        
        # Add more country code mappings as needed
        return "US"
    
    async def _assign_platform_phone_number(self, db: AsyncSession, tenant_id: UUID) -> str:
        """Assign a platform phone number for the organization to forward calls to"""
        
        # In a full implementation, this would:
        # 1. Check available phone numbers in our Twilio pool
        # 2. Assign one to this organization
        # 3. Configure Twilio webhooks for that number
        
        # For now, generate a unique number based on tenant ID
        # In production, you'd have a pool of purchased Twilio numbers
        base_number = settings.TWILIO_PHONE_NUMBER or "+15551234567"
        
        # Generate a unique extension or use a pool of numbers
        # This is a simplified implementation
        tenant_hash = str(tenant_id)[:8]
        
        # In reality, you'd maintain a pool of purchased numbers and assign one
        # For demo purposes, we'll create a virtual number
        platform_number = f"+1555{tenant_hash[:7]}"
        
        logger.info(f"📞 Assigned platform number {platform_number} to tenant {tenant_id}")
        return platform_number
    
    def _generate_forwarding_instructions(self, platform_number: str) -> str:
        """Generate instructions for organization to set up call forwarding"""
        
        formatted_number = self._format_phone_number(platform_number)
        
        return f"""
To activate AI phone support, please set up call forwarding on your business phone:

**Your AI Platform Number: {formatted_number}**

FORWARDING SETUP INSTRUCTIONS:

1. **For Most Phone Providers:**
   - Contact your phone provider's customer service
   - Request to set up "call forwarding" or "call diversion"
   - Forward calls to: {formatted_number}
   
2. **For VoIP Systems (RingCentral, 8x8, etc.):**
   - Log into your admin portal
   - Go to Call Handling > Call Forwarding
   - Set forwarding destination to: {formatted_number}
   
3. **For Traditional Landlines:**
   - Contact your local phone company
   - Request call forwarding service
   - Provide forwarding number: {formatted_number}

4. **Conditional Forwarding Options:**
   - Forward all calls: Immediately routes to AI
   - Forward when busy: AI handles overflow calls
   - Forward when no answer: AI handles missed calls
   - Forward outside business hours: AI provides after-hours support

**Important Notes:**
- Keep your original number - customers will still dial it
- Forwarding charges may apply from your phone provider
- Test the setup by calling your business number
- You can disable forwarding anytime through your provider

**Need Help?** Contact our support team for assistance with your specific phone system.
        """.strip()
    
    async def get_forwarding_instructions(
        self,
        db: AsyncSession,
        tenant_id: UUID
    ) -> str:
        """Get call forwarding instructions for an organization"""
        
        config_query = select(TelephonyConfiguration).where(
            TelephonyConfiguration.tenant_id == tenant_id
        )
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if not config:
            raise ValueError("No telephony configuration found for organization")
        
        return config.forwarding_instructions or self._generate_forwarding_instructions(config.platform_phone_number)
    
    def _default_business_hours(self) -> Dict:
        """Default business hours configuration"""
        return {
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
            "thursday": {"start": "09:00", "end": "17:00"},
            "friday": {"start": "09:00", "end": "17:00"},
            "saturday": {"start": "10:00", "end": "14:00"},
            "sunday": {"start": "closed", "end": "closed"}
        }
    
    async def _send_verification_code(
        self,
        organization_phone_number: str,
        verification_code: str,
        method: str
    ) -> bool:
        """Send verification code to organization's phone number to prove ownership"""
        
        if not self.twilio_client:
            # Mock mode for development
            logger.info(f"🧪 MOCK: Verification code {verification_code} would be sent to organization number {organization_phone_number} via {method}")
            return True
        
        try:
            message_body = f"Your AI Platform verification code is: {verification_code}. This code expires in 10 minutes. Enter this code to verify ownership of your business phone number."
            
            if method == "sms":
                message = self.twilio_client.messages.create(
                    body=message_body,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=organization_phone_number
                )
                logger.info(f"📨 Verification SMS sent to organization: {message.sid}")
            else:
                # Voice call verification
                call = self.twilio_client.calls.create(
                    twiml=f'<Response><Say>Your AI Platform verification code is: {" ".join(verification_code)}. Please enter this code to verify your business phone number.</Say></Response>',
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=organization_phone_number
                )
                logger.info(f"📞 Verification call made to organization: {call.sid}")
            
            return True
            
        except TwilioException as e:
            logger.error(f"❌ Twilio error sending verification to {organization_phone_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending verification to {organization_phone_number}: {e}")
            return False
    
    async def _record_call_usage(self, db: AsyncSession, call: PhoneCall) -> None:
        """Record usage metrics for completed call"""
        
        try:
            # Get tenant from telephony config
            config_query = select(TelephonyConfiguration).where(
                TelephonyConfiguration.id == call.telephony_config_id
            )
            config_result = await db.execute(config_query)
            config = config_result.scalar_one_or_none()
            
            if config:
                # Get STT/TTS word counts for this call from usage records
                from sqlalchemy import and_
                usage_query = select(UsageRecord).where(
                    and_(
                        UsageRecord.tenant_id == config.tenant_id,
                        UsageRecord.additional_data.op('->>')('call_id') == str(call.id),
                        UsageRecord.usage_type.in_(['stt_words', 'tts_words'])
                    )
                )
                usage_result = await db.execute(usage_query)
                usage_records = usage_result.scalars().all()
                
                # Calculate total words (STT + TTS)
                total_words = sum(record.amount for record in usage_records)
                
                # Calculate cost: $1.00 base + $1.00 per 1000 words
                cost_cents = 100 + int((total_words / 1000) * 100)
                
                # Update the call record with the calculated cost
                call.cost_cents = cost_cents
                await db.commit()
                
                # Record call duration usage (separate from cost calculation)
                duration_minutes = call.duration_seconds / 60.0  # Convert to minutes
                
                await usage_service.record_usage(
                    db=db,
                    tenant_id=config.tenant_id,
                    usage_type="telephony_minutes",
                    amount=int(duration_minutes),  # Amount should be int for minutes
                    cost_cents=cost_cents,
                    additional_data={"call_id": str(call.id), "call_sid": call.call_sid}
                )
                
                logger.info(f"💰 Usage recorded for call {call.call_sid}: {total_words} words, cost: {cost_cents} cents (${cost_cents/100:.2f})")
        
        except Exception as e:
            logger.error(f"❌ Failed to record call usage: {e}")

# Create service instance
telephony_service = TelephonyService()
