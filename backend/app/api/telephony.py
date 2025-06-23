# backend/app/api/telephony.py
"""
Telephony API endpoints for phone number management and call handling
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.db.database import get_db
from app.auth.auth import get_current_active_user, require_admin_user, get_current_user
from app.models.models import User, TelephonyConfiguration, PhoneCall, CallStatus
from app.services.telephony_service import telephony_service
# Telephony schemas are defined in this file

# Import Pydantic models for this module
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List

# Response models
class TelephonyConfigResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    organization_phone_number: str
    formatted_phone_number: Optional[str]
    platform_phone_number: Optional[str]
    country_code: str
    verification_status: str
    call_forwarding_enabled: bool
    welcome_message: Optional[str]
    is_enabled: bool
    business_hours: Optional[Dict[str, Any]]
    timezone: str
    max_concurrent_calls: int
    call_timeout_seconds: int
    record_calls: bool
    transcript_calls: bool
    forwarding_instructions: Optional[str]
    integration_method: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class PhoneCallResponse(BaseModel):
    id: UUID
    call_sid: str
    customer_phone_number: str
    organization_phone_number: str
    platform_phone_number: str
    direction: str
    status: str
    start_time: Optional[datetime]
    answer_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    cost_cents: int
    cost_currency: str
    recording_url: Optional[str]
    transcript: Optional[str]
    summary: Optional[str]
    call_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CallsListResponse(BaseModel):
    calls: List[PhoneCallResponse]
    total: int
    page: int
    per_page: int

class PhoneVerificationResponse(BaseModel):
    success: bool
    message: str
    verification_id: Optional[UUID] = None

# Request models
class TelephonySetupRequest(BaseModel):
    organization_phone_number: str = Field(..., description="Your existing business phone number")
    welcome_message: Optional[str] = Field(None, description="Custom welcome message for callers")
    business_hours: Optional[Dict[str, Any]] = Field(None, description="Business hours configuration")
    voice_id: Optional[str] = Field(None, description="ElevenLabs voice ID")
    max_concurrent_calls: Optional[int] = Field(5, description="Maximum concurrent calls")

class PhoneVerificationRequest(BaseModel):
    verification_code: str = Field(..., description="6-digit verification code")

class TelephonyUpdateRequest(BaseModel):
    welcome_message: Optional[str] = None
    business_hours: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None
    max_concurrent_calls: Optional[int] = None
    voice_id: Optional[str] = None
    record_calls: Optional[bool] = None
    transcript_calls: Optional[bool] = None

async def require_org_admin_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Check if user is organization admin or higher"""
    if current_user.role not in ["org_admin", "admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins or system admins can perform this action"
        )
    return current_user


router = APIRouter(prefix="/telephony", tags=["telephony"])

@router.post("/setup", response_model=TelephonyConfigResponse)
async def setup_telephony(
    setup_data: TelephonySetupRequest,
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Set up telephony configuration for organization with their existing phone number"""
    
    try:
        config = await telephony_service.setup_organization_phone(
            db=db,
            tenant_id=current_user.tenant_id,
            organization_phone_number=setup_data.organization_phone_number,
            welcome_message=setup_data.welcome_message,
            business_hours=setup_data.business_hours
        )
        
        # Update additional settings if provided
        if setup_data.voice_id:
            config.voice_id = setup_data.voice_id
        if setup_data.max_concurrent_calls:
            config.max_concurrent_calls = setup_data.max_concurrent_calls
        
        await db.commit()
        await db.refresh(config)
        
        return config
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set up telephony: {str(e)}")

@router.get("/forwarding-instructions", response_model=dict)
async def get_forwarding_instructions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get call forwarding instructions for organization"""
    
    try:
        instructions = await telephony_service.get_forwarding_instructions(
            db=db,
            tenant_id=current_user.tenant_id
        )
        
        return {"instructions": instructions}
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/verify/initiate", response_model=PhoneVerificationResponse)
async def initiate_verification(
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Initiate phone number verification"""
    
    try:
        verification = await telephony_service.initiate_phone_verification(
            db=db,
            tenant_id=current_user.tenant_id,
            verification_method="sms"
        )
        
        return PhoneVerificationResponse(
            success=True,
            message="Verification code sent successfully",
            verification_id=verification.id
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify/confirm", response_model=PhoneVerificationResponse)
async def confirm_verification(
    verification_data: PhoneVerificationRequest,
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Confirm phone number verification with code"""
    
    try:
        success = await telephony_service.verify_phone_number(
            db=db,
            tenant_id=current_user.tenant_id,
            verification_code=verification_data.verification_code
        )
        
        if success:
            return PhoneVerificationResponse(
                success=True,
                message="Phone number verified successfully"
            )
        else:
            return PhoneVerificationResponse(
                success=False,
                message="Invalid verification code"
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/config", response_model=TelephonyConfigResponse)
async def get_telephony_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get telephony configuration for current organization"""
    
    query = select(TelephonyConfiguration).where(
        TelephonyConfiguration.tenant_id == current_user.tenant_id
    )
    result = await db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Telephony not configured for this organization")
    
    return config

@router.patch("/config", response_model=TelephonyConfigResponse)
async def update_telephony_config(
    update_data: TelephonyUpdateRequest,
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update telephony configuration"""
    
    query = select(TelephonyConfiguration).where(
        TelephonyConfiguration.tenant_id == current_user.tenant_id
    )
    result = await db.execute(query)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Telephony not configured for this organization")
    
    # Update fields
    if update_data.welcome_message is not None:
        config.welcome_message = update_data.welcome_message
    if update_data.business_hours is not None:
        config.business_hours = update_data.business_hours
    if update_data.is_enabled is not None:
        config.is_enabled = update_data.is_enabled
    if update_data.max_concurrent_calls is not None:
        config.max_concurrent_calls = update_data.max_concurrent_calls
    if update_data.voice_id is not None:
        config.voice_id = update_data.voice_id
    if update_data.record_calls is not None:
        config.record_calls = update_data.record_calls
    if update_data.transcript_calls is not None:
        config.transcript_calls = update_data.transcript_calls
    
    await db.commit()
    await db.refresh(config)
    
    return config

@router.get("/calls", response_model=CallsListResponse)
async def get_calls(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get call history for organization"""
    
    try:
        status_filter = CallStatus(status) if status else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    offset = (page - 1) * per_page
    
    calls = await telephony_service.get_organization_calls(
        db=db,
        tenant_id=current_user.tenant_id,
        limit=per_page,
        offset=offset,
        status_filter=status_filter
    )
    
    # Get total count
    from sqlalchemy import func
    count_query = select(func.count(PhoneCall.id)).join(TelephonyConfiguration).where(
        TelephonyConfiguration.tenant_id == current_user.tenant_id
    )
    if status_filter:
        count_query = count_query.where(PhoneCall.status == status_filter.value)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return CallsListResponse(
        calls=calls,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/calls/{call_id}", response_model=PhoneCallResponse)
async def get_call(
    call_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific call details"""
    
    query = select(PhoneCall).join(TelephonyConfiguration).where(
        PhoneCall.id == call_id,
        TelephonyConfiguration.tenant_id == current_user.tenant_id
    )
    result = await db.execute(query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return call

# Webhook endpoints for telephony provider (Twilio)
@router.post("/webhook/incoming-call")
async def handle_incoming_call_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle incoming call webhook from Twilio"""
    
    try:
        # Parse Twilio webhook data
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        customer_number = form_data.get("From")  # The actual caller
        platform_number = form_data.get("To")   # Our Twilio number that received the call
        call_status = form_data.get("CallStatus")
        
        if not all([call_sid, customer_number, platform_number]):
            raise HTTPException(status_code=400, detail="Missing required call data")
        
        # Handle the incoming call - this maps the platform number to the organization
        phone_call = await telephony_service.handle_incoming_call(
            db=db,
            call_sid=call_sid,
            customer_number=customer_number,
            platform_number=platform_number,
            call_metadata={
                "call_status": call_status,
                "webhook_data": dict(form_data)
            }
        )
        
        # Get telephony configuration for welcome message
        config_query = select(TelephonyConfiguration).where(
            TelephonyConfiguration.id == phone_call.telephony_config_id
        )
        config_result = await db.execute(config_query)
        config = config_result.scalar_one()
        
        # Generate TwiML response that immediately starts the WebSocket stream
        # The AI agent will handle the welcome message through ElevenLabs voice
        host = request.headers.get('host', 'localhost')
        websocket_url = f"wss://{host}/api/ws/telephony/stream/{phone_call.id}"
        
        logger.info(f"📞 Sending TwiML response with WebSocket URL: {websocket_url}")
        
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{websocket_url}" />
    </Connect>
</Response>"""
        
        logger.info(f"📞 TwiML Response: {twiml_response}")
        return Response(content=twiml_response, media_type="application/xml")
        
    except ValueError as e:
        return Response(content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, this service is not available.</Say><Hangup/></Response>', media_type="application/xml")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Webhook Error: {e}")
        print(f"❌ Traceback: {error_details}")
        logger.error(f"❌ Error handling incoming call: {e}")
        logger.error(f"❌ Traceback: {error_details}")
        return Response(content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, there was an error. Please try again later.</Say><Hangup/></Response>', media_type="application/xml")

@router.post("/webhook/call-status")
async def handle_call_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle call status updates from Twilio"""
    
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
        call_duration = form_data.get("CallDuration")
        recording_url = form_data.get("RecordingUrl")
        
        if not call_sid:
            raise HTTPException(status_code=400, detail="Missing CallSid")
        
        # Map Twilio status to our CallStatus enum
        status_mapping = {
            "queued": CallStatus.INCOMING,
            "ringing": CallStatus.RINGING,
            "in-progress": CallStatus.IN_PROGRESS,
            "completed": CallStatus.COMPLETED,
            "failed": CallStatus.FAILED,
            "busy": CallStatus.BUSY,
            "no-answer": CallStatus.NO_ANSWER
        }
        
        our_status = status_mapping.get(call_status, CallStatus.FAILED)
        
        # Prepare additional data
        additional_data = {
            "twilio_status": call_status,
            "webhook_data": dict(form_data)
        }
        
        if call_duration:
            additional_data["twilio_duration"] = call_duration
        if recording_url:
            additional_data["recording_url"] = recording_url
        
        # Update call status
        await telephony_service.update_call_status(
            db=db,
            call_sid=call_sid,
            status=our_status,
            additional_data=additional_data
        )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Error handling call status webhook: {e}")
        return {"status": "error", "message": str(e)}

import logging
logger = logging.getLogger(__name__)
