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
from openai import AsyncOpenAI
import logging

from app.db.database import get_db
from app.auth.auth import get_current_active_user, require_admin_user, get_current_user
from app.models.models import User, TelephonyConfiguration, PhoneCall, CallStatus, CallMessage
from app.services.telephony_service import telephony_service
from app.core.config import settings
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, desc, asc
# Telephony schemas are defined in this file

# Import Pydantic models for this module
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

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

# Call Message Models
class CallMessageSender(BaseModel):
    identifier: str
    name: Optional[str] = None
    type: str  # 'customer', 'agent', 'system', 'operator'
    phone_number: Optional[str] = None

class CallMessageMetadata(BaseModel):
    audio_start_time: Optional[float] = None
    audio_end_time: Optional[float] = None
    confidence_score: Optional[float] = None
    language: Optional[str] = None
    recording_segment_url: Optional[str] = None
    is_automated: Optional[bool] = None
    system_event_type: Optional[str] = None

class CallMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    sender: CallMessageSender
    timestamp: datetime
    message_type: str = Field(..., pattern=r'^(transcript|system|summary|note)$')
    metadata: Optional[CallMessageMetadata] = None

class CallMessageUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[CallMessageMetadata] = None

class CallMessageResponse(BaseModel):
    id: UUID
    call_id: UUID
    content: str
    sender: CallMessageSender
    timestamp: datetime
    message_type: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CallMessagesListResponse(BaseModel):
    messages: List[CallMessageResponse]
    total: int
    call_id: UUID

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
        
        # Choose WebSocket endpoint based on Voice Agent feature flag and rollout
        use_voice_agent = False
        if getattr(settings, 'USE_VOICE_AGENT', False):
            # Check rollout percentage
            rollout_percentage = getattr(settings, 'VOICE_AGENT_ROLLOUT_PERCENTAGE', 0)
            if rollout_percentage >= 100:
                use_voice_agent = True
            elif rollout_percentage > 0:
                # Random rollout based on call SID hash
                import hashlib
                hash_value = int(hashlib.md5(call_sid.encode()).hexdigest()[:8], 16)
                use_voice_agent = (hash_value % 100) < rollout_percentage
        
        if use_voice_agent:
            websocket_url = f"wss://{host}/api/ws/telephony/voice-agent/stream"
            logger.info(f"📞 Using Voice Agent for call {call_sid}")
        else:
            websocket_url = f"wss://{host}/api/ws/telephony/stream/{phone_call.id}"
            logger.info(f"📞 Using traditional TTS for call {call_sid}")
        
        logger.info(f"📞 Sending TwiML response with WebSocket URL: {websocket_url}")
        
        # Pass additional parameters through custom parameters
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{websocket_url}">
            <Parameter name="call_sid" value="{call_sid}" />
            <Parameter name="tenant_id" value="{str(config.tenant_id)}" />
            <Parameter name="from" value="{customer_number}" />
            <Parameter name="to" value="{platform_number}" />
            <Parameter name="org_phone" value="{config.organization_phone_number}" />
        </Stream>
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


# Call Messages API Endpoints

@router.get("/calls/{call_id}/messages", response_model=CallMessagesListResponse)
async def get_call_messages(
    call_id: UUID,
    message_type: Optional[str] = None,
    sender_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "timestamp",
    order_dir: str = "asc",
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all messages for a specific call."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            PhoneCall.telephony_config.has(TelephonyConfiguration.tenant_id == current_user.tenant_id)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Build messages query
    query = select(CallMessage).where(CallMessage.call_id == call_id)
    
    # Apply filters
    if message_type:
        query = query.where(CallMessage.message_type == message_type)
    
    if sender_type:
        query = query.where(CallMessage.sender['type'].astext == sender_type)
    
    # Apply ordering
    if order_by == "timestamp":
        order_column = CallMessage.timestamp
    elif order_by == "created_at":
        order_column = CallMessage.created_at
    else:
        order_column = CallMessage.timestamp
    
    if order_dir == "desc":
        query = query.order_by(desc(order_column))
    else:
        query = query.order_by(asc(order_column))
    
    # Get total count
    count_query = select(CallMessage).where(CallMessage.call_id == call_id)
    if message_type:
        count_query = count_query.where(CallMessage.message_type == message_type)
    if sender_type:
        count_query = count_query.where(CallMessage.sender['type'].astext == sender_type)
    
    total_result = await db.execute(count_query)
    total = len(total_result.all())
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Process messages with error handling for legacy data
    processed_messages = []
    for msg in messages:
        try:
            # Ensure sender has required identifier field
            sender_data = dict(msg.sender) if msg.sender else {}
            if "identifier" not in sender_data:
                # Add identifier based on message type and available data
                if sender_data.get("type") == "agent":
                    sender_data["identifier"] = "voice_agent"
                elif sender_data.get("phone_number"):
                    sender_data["identifier"] = sender_data["phone_number"]
                else:
                    sender_data["identifier"] = "unknown"
            
            # Ensure all required fields are present
            if "type" not in sender_data:
                sender_data["type"] = "agent" if "agent" in sender_data.get("name", "").lower() else "customer"
            if "name" not in sender_data:
                sender_data["name"] = "AI Agent" if sender_data["type"] == "agent" else "Caller"
            
            processed_messages.append(CallMessageResponse(
                id=msg.id,
                call_id=msg.call_id,
                content=msg.content,
                sender=CallMessageSender(**sender_data),
                timestamp=msg.timestamp,
                message_type=msg.message_type,
                metadata=msg.message_metadata,
                created_at=msg.created_at,
            ))
        except Exception as e:
            # Log the error but don't break the entire response
            logger.error(f"Error processing message {msg.id}: {e}")
            logger.error(f"Message sender data: {msg.sender}")
            continue
    
    return CallMessagesListResponse(
        messages=processed_messages,
        total=total,
        call_id=call_id,
    )


@router.post("/calls/{call_id}/messages", response_model=CallMessageResponse)
async def create_call_message(
    call_id: UUID,
    message_data: CallMessageCreate,
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Add a new message to a call."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            PhoneCall.telephony_config.has(TelephonyConfiguration.tenant_id == current_user.tenant_id)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Create new message
    new_message = CallMessage(
        call_id=call_id,
        content=message_data.content,
        sender=message_data.sender.dict(),
        timestamp=message_data.timestamp,
        message_type=message_data.message_type,
        message_metadata=message_data.metadata.dict() if message_data.metadata else None,
    )
    
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    
    return CallMessageResponse(
        id=new_message.id,
        call_id=new_message.call_id,
        content=new_message.content,
        sender=CallMessageSender(**new_message.sender),
        timestamp=new_message.timestamp,
        message_type=new_message.message_type,
        metadata=new_message.message_metadata,
        created_at=new_message.created_at,
    )


@router.patch("/calls/{call_id}/messages/{message_id}", response_model=CallMessageResponse)
async def update_call_message(
    call_id: UUID,
    message_id: UUID,
    update_data: CallMessageUpdate,
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update a call message."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            PhoneCall.telephony_config.has(TelephonyConfiguration.tenant_id == current_user.tenant_id)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Get message
    message_query = select(CallMessage).where(
        and_(
            CallMessage.id == message_id,
            CallMessage.call_id == call_id
        )
    )
    result = await db.execute(message_query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Update fields
    if update_data.content is not None:
        message.content = update_data.content
    
    if update_data.metadata is not None:
        message.message_metadata = update_data.metadata.dict()
    
    await db.commit()
    await db.refresh(message)
    
    return CallMessageResponse(
        id=message.id,
        call_id=message.call_id,
        content=message.content,
        sender=CallMessageSender(**message.sender),
        timestamp=message.timestamp,
        message_type=message.message_type,
        metadata=message.message_metadata,
        created_at=message.created_at,
    )


@router.delete("/calls/{call_id}/messages/{message_id}")
async def delete_call_message(
    call_id: UUID,
    message_id: UUID,
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a call message."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            PhoneCall.telephony_config.has(TelephonyConfiguration.tenant_id == current_user.tenant_id)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Get message
    message_query = select(CallMessage).where(
        and_(
            CallMessage.id == message_id,
            CallMessage.call_id == call_id
        )
    )
    result = await db.execute(message_query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Delete message
    await db.delete(message)
    await db.commit()
    
    return {"detail": "Message deleted successfully"}


@router.get("/calls/{call_id}/messages/transcript")
async def get_call_transcript(
    call_id: UUID,
    format: str = "text",
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get formatted transcript for a call."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            PhoneCall.telephony_config.has(TelephonyConfiguration.tenant_id == current_user.tenant_id)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Get transcript messages
    messages_query = (
        select(CallMessage)
        .where(
            and_(
                CallMessage.call_id == call_id,
                CallMessage.message_type == 'transcript'
            )
        )
        .order_by(asc(CallMessage.timestamp))
    )
    
    result = await db.execute(messages_query)
    messages = result.scalars().all()
    
    if format == "json":
        return {
            "call_id": str(call_id),
            "format": "json",
            "messages": [
                {
                    "timestamp": msg.timestamp.isoformat(),
                    "sender": msg.sender,
                    "content": msg.content,
                    "metadata": msg.message_metadata,
                }
                for msg in messages
            ]
        }
    else:
        # Text format
        transcript_lines = []
        for msg in messages:
            sender_name = msg.get_sender_name()
            timestamp_str = msg.timestamp.strftime("%H:%M:%S")
            transcript_lines.append(f"[{timestamp_str}] {sender_name}: {msg.content}")
        
        return {
            "call_id": str(call_id),
            "format": "text",
            "transcript": "\n".join(transcript_lines)
        }


@router.get("/calls/{call_id}/messages/summary")
async def get_call_summary(
    call_id: UUID,
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get summary for a call."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            PhoneCall.telephony_config.has(TelephonyConfiguration.tenant_id == current_user.tenant_id)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Get summary message
    summary_query = (
        select(CallMessage)
        .where(
            and_(
                CallMessage.call_id == call_id,
                CallMessage.message_type == 'summary'
            )
        )
        .order_by(desc(CallMessage.created_at))
        .limit(1)
    )
    
    result = await db.execute(summary_query)
    summary_message = result.scalar_one_or_none()
    
    if not summary_message:
        return {
            "call_id": str(call_id),
            "summary": None,
            "message": "No summary available for this call"
        }
    
    return {
        "call_id": str(call_id),
        "summary": summary_message.content,
        "created_at": summary_message.created_at.isoformat(),
        "metadata": summary_message.message_metadata,
    }


@router.post("/calls/{call_id}/generate-summary")
async def generate_call_summary(
    call_id: UUID,
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Generate a summary for a call based on its transcript messages."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            PhoneCall.telephony_config.has(TelephonyConfiguration.tenant_id == current_user.tenant_id)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Check if summary already exists
    existing_summary_query = select(CallMessage).where(
        and_(
            CallMessage.call_id == call_id,
            CallMessage.message_type == 'summary'
        )
    )
    existing_result = await db.execute(existing_summary_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Summary already exists for this call")
    
    # Get transcript messages
    transcript_query = (
        select(CallMessage)
        .where(
            and_(
                CallMessage.call_id == call_id,
                CallMessage.message_type == 'transcript'
            )
        )
        .order_by(CallMessage.timestamp)
    )
    
    result = await db.execute(transcript_query)
    transcript_messages = result.scalars().all()
    
    if not transcript_messages:
        raise HTTPException(status_code=400, detail="No transcript messages found for this call")
    
    # Build conversation text
    conversation_lines = []
    for msg in transcript_messages:
        sender_name = msg.sender.get('name', 'Unknown')
        if msg.sender.get('type') == 'customer':
            sender_name = f"Customer ({msg.sender.get('phone_number', 'Unknown')})"
        elif msg.sender.get('type') == 'agent':
            sender_name = "AI Agent"
        
        conversation_lines.append(f"{sender_name}: {msg.content}")
    
    conversation_text = "\n".join(conversation_lines)
    
    # Generate summary using AI service
    try:
        duration_info = ""
        if call.duration_seconds:
            minutes = call.duration_seconds // 60
            seconds = call.duration_seconds % 60
            duration_info = f" The call lasted {minutes} minutes and {seconds} seconds."
        
        message_count = len(transcript_messages)
        customer_messages = [m for m in transcript_messages if m.sender.get('type') == 'customer']
        agent_messages = [m for m in transcript_messages if m.sender.get('type') == 'agent']
        
        # Generate AI summary if transcript has content
        if conversation_text.strip():
            try:
                # Initialize OpenAI client
                client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    organization=getattr(settings, 'OPENAI_ORG_ID', None)
                )
                
                # Generate summary using OpenAI
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an AI assistant that creates concise, informative summaries of phone conversations. "
                                "Focus on the main topics discussed, any questions asked, issues raised, and resolutions provided. "
                                "Keep the summary brief but comprehensive, highlighting the key points of the conversation. "
                                "Do not include call metadata like duration or timestamps in the summary."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Please summarize the following phone conversation:\n\n{conversation_text}"
                        }
                    ],
                    temperature=0.3,
                    max_tokens=300
                )
                
                ai_summary = response.choices[0].message.content.strip()
                
                # Combine AI summary with metadata
                summary_content = (
                    f"Call Summary - {call.created_at.strftime('%B %d, %Y at %I:%M %p')}\n\n"
                    f"{ai_summary}\n\n"
                    f"Call Details:{duration_info} {message_count} messages exchanged "
                    f"({len(customer_messages)} from customer, {len(agent_messages)} from agent)."
                )
                generation_method = "ai_generated"
                
            except Exception as e:
                logger.error(f"Error generating AI summary: {e}")
                # Fall back to basic summary
                summary_content = (
                    f"Call between customer {call.customer_phone_number} and organization "
                    f"on {call.created_at.strftime('%B %d, %Y at %I:%M %p')}.{duration_info} "
                    f"The conversation included {message_count} messages "
                    f"({len(customer_messages)} from customer, {len(agent_messages)} from agent). "
                    f"Unable to generate AI summary due to an error."
                )
                generation_method = "basic_fallback"
        else:
            # No transcript content available
            summary_content = (
                f"Call between customer {call.customer_phone_number} and organization "
                f"on {call.created_at.strftime('%B %d, %Y at %I:%M %p')}.{duration_info} "
                f"The conversation included {message_count} messages "
                f"({len(customer_messages)} from customer, {len(agent_messages)} from agent). "
                f"No conversation transcript available for summary."
            )
            generation_method = "no_transcript"
        
        # Create summary message
        summary_message = CallMessage(
            call_id=call_id,
            content=summary_content,
            sender={
                "identifier": "system",
                "name": "AI Summarizer",
                "type": "system"
            },
            timestamp=datetime.utcnow(),
            message_type='summary',
            message_metadata={
                "is_automated": True,
                "generation_method": generation_method,
                "message_count": message_count,
                "customer_message_count": len(customer_messages),
                "agent_message_count": len(agent_messages)
            }
        )
        
        db.add(summary_message)
        
        # Also update the phone_call summary field
        call.summary = summary_content
        
        await db.commit()
        await db.refresh(summary_message)
        
        return {
            "success": True,
            "call_id": str(call_id),
            "summary": summary_content,
            "message_id": str(summary_message.id),
            "created_at": summary_message.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating summary for call {call_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/calls/{call_id}/messages/bulk")
async def create_bulk_call_messages(
    call_id: UUID,
    messages_data: List[CallMessageCreate],
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create multiple messages at once (useful for STT processing)."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            PhoneCall.telephony_config.has(TelephonyConfiguration.tenant_id == current_user.tenant_id)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Create messages
    new_messages = []
    for message_data in messages_data:
        new_message = CallMessage(
            call_id=call_id,
            content=message_data.content,
            sender=message_data.sender.dict(),
            timestamp=message_data.timestamp,
            message_type=message_data.message_type,
            message_metadata=message_data.metadata.dict() if message_data.metadata else None,
        )
        new_messages.append(new_message)
        db.add(new_message)
    
    await db.commit()
    
    return {
        "call_id": str(call_id),
        "created_count": len(new_messages),
        "message_ids": [str(msg.id) for msg in new_messages],
    }


# Test endpoint for creating simulated calls
@router.post("/test/simulate-call")
async def simulate_test_call(
    customer_number: str = "+1234567890",
    current_user: User = Depends(require_org_admin_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a test phone call for frontend testing"""
    
    try:
        # Get user's telephony configuration
        config_query = select(TelephonyConfiguration).where(
            TelephonyConfiguration.tenant_id == current_user.tenant_id
        )
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(
                status_code=404, 
                detail="No telephony configuration found. Please set up telephony first."
            )
        
        # Generate test call data
        import uuid
        import time
        call_sid = f"CA{uuid.uuid4().hex[:32]}"
        
        # Create test phone call record
        test_call = await telephony_service.handle_incoming_call(
            db=db,
            call_sid=call_sid,
            customer_number=customer_number,
            platform_number=config.platform_phone_number,
            call_metadata={
                "is_test_call": True,
                "created_by": str(current_user.id),
                "created_for_testing": True
            }
        )
        
        return {
            "success": True,
            "call_id": str(test_call.id),
            "call_sid": call_sid,
            "customer_number": customer_number,
            "organization_number": config.organization_phone_number,
            "platform_number": config.platform_phone_number,
            "websocket_url": f"ws://localhost:8000/api/ws/telephony/stream/{test_call.id}",
            "message": "Test call created successfully. Connect to the WebSocket URL to start the telephony session."
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating test call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create test call: {str(e)}")


import logging
logger = logging.getLogger(__name__)
