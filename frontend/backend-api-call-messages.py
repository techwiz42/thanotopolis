"""
FastAPI endpoints for call messages management.
This file shows the backend API endpoints needed to support the new frontend structure.

Place this in your backend at: app/api/v1/telephony/call_messages.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, asc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# Adjust these imports based on your backend structure
from app.db.database import get_db
from app.models.call_messages import CallMessage, PhoneCall
from app.core.security import get_current_user
from app.models.user import User
from app.core.tenant import get_tenant_filter
from pydantic import BaseModel, Field


# Pydantic models for request/response
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
    message_type: str = Field(..., regex=r'^(transcript|system|summary|note)$')
    metadata: Optional[CallMessageMetadata] = None


class CallMessageUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[CallMessageMetadata] = None


class CallMessageResponse(BaseModel):
    id: str
    call_id: str
    content: str
    sender: CallMessageSender
    timestamp: datetime
    message_type: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CallMessagesListResponse(BaseModel):
    messages: List[CallMessageResponse]
    total: int
    call_id: str


# Router setup
router = APIRouter(prefix="/telephony/calls", tags=["call-messages"])


@router.get("/{call_id}/messages", response_model=CallMessagesListResponse)
async def get_call_messages(
    call_id: str = Path(..., description="Call ID"),
    message_type: Optional[str] = Query(None, regex=r'^(transcript|system|summary|note)$'),
    sender_type: Optional[str] = Query(None, regex=r'^(customer|agent|system|operator)$'),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    order_by: str = Query("timestamp", regex=r'^(timestamp|created_at)$'),
    order_dir: str = Query("asc", regex=r'^(asc|desc)$'),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CallMessagesListResponse:
    """Get all messages for a specific call."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            get_tenant_filter(PhoneCall, current_user)
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
    order_column = getattr(CallMessage, order_by)
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
    
    return CallMessagesListResponse(
        messages=[
            CallMessageResponse(
                id=msg.id,
                call_id=msg.call_id,
                content=msg.content,
                sender=CallMessageSender(**msg.sender),
                timestamp=msg.timestamp,
                message_type=msg.message_type,
                metadata=msg.metadata,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
        total=total,
        call_id=call_id,
    )


@router.post("/{call_id}/messages", response_model=CallMessageResponse)
async def create_call_message(
    call_id: str = Path(..., description="Call ID"),
    message_data: CallMessageCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CallMessageResponse:
    """Add a new message to a call."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            get_tenant_filter(PhoneCall, current_user)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Create new message
    new_message = CallMessage(
        id=str(uuid.uuid4()),
        call_id=call_id,
        content=message_data.content,
        sender=message_data.sender.dict(),
        timestamp=message_data.timestamp,
        message_type=message_data.message_type,
        metadata=message_data.metadata.dict() if message_data.metadata else None,
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
        metadata=new_message.metadata,
        created_at=new_message.created_at,
    )


@router.patch("/{call_id}/messages/{message_id}", response_model=CallMessageResponse)
async def update_call_message(
    call_id: str = Path(..., description="Call ID"),
    message_id: str = Path(..., description="Message ID"),
    update_data: CallMessageUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CallMessageResponse:
    """Update a call message."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            get_tenant_filter(PhoneCall, current_user)
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
        message.metadata = update_data.metadata.dict()
    
    await db.commit()
    await db.refresh(message)
    
    return CallMessageResponse(
        id=message.id,
        call_id=message.call_id,
        content=message.content,
        sender=CallMessageSender(**message.sender),
        timestamp=message.timestamp,
        message_type=message.message_type,
        metadata=message.metadata,
        created_at=message.created_at,
    )


@router.delete("/{call_id}/messages/{message_id}")
async def delete_call_message(
    call_id: str = Path(..., description="Call ID"),
    message_id: str = Path(..., description="Message ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a call message."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            get_tenant_filter(PhoneCall, current_user)
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


@router.get("/{call_id}/messages/transcript", response_model=Dict[str, str])
async def get_call_transcript(
    call_id: str = Path(..., description="Call ID"),
    format: str = Query("text", regex=r'^(text|json)$'),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get formatted transcript for a call."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            get_tenant_filter(PhoneCall, current_user)
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
            "call_id": call_id,
            "format": "json",
            "messages": [
                {
                    "timestamp": msg.timestamp.isoformat(),
                    "sender": msg.sender,
                    "content": msg.content,
                    "metadata": msg.metadata,
                }
                for msg in messages
            ]
        }
    else:
        # Text format
        transcript_lines = []
        for msg in messages:
            sender_name = msg.sender.get('name') or msg.sender.get('identifier', 'Unknown')
            timestamp_str = msg.timestamp.strftime("%H:%M:%S")
            transcript_lines.append(f"[{timestamp_str}] {sender_name}: {msg.content}")
        
        return {
            "call_id": call_id,
            "format": "text",
            "transcript": "\n".join(transcript_lines)
        }


@router.get("/{call_id}/messages/summary", response_model=Dict[str, Any])
async def get_call_summary(
    call_id: str = Path(..., description="Call ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get summary for a call."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            get_tenant_filter(PhoneCall, current_user)
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
            "call_id": call_id,
            "summary": None,
            "message": "No summary available for this call"
        }
    
    return {
        "call_id": call_id,
        "summary": summary_message.content,
        "created_at": summary_message.created_at.isoformat(),
        "metadata": summary_message.metadata,
    }


# Bulk operations for STT processing
@router.post("/{call_id}/messages/bulk", response_model=Dict[str, Any])
async def create_bulk_call_messages(
    call_id: str = Path(..., description="Call ID"),
    messages_data: List[CallMessageCreate] = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create multiple messages at once (useful for STT processing)."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            get_tenant_filter(PhoneCall, current_user)
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
            id=str(uuid.uuid4()),
            call_id=call_id,
            content=message_data.content,
            sender=message_data.sender.dict(),
            timestamp=message_data.timestamp,
            message_type=message_data.message_type,
            metadata=message_data.metadata.dict() if message_data.metadata else None,
        )
        new_messages.append(new_message)
        db.add(new_message)
    
    await db.commit()
    
    return {
        "call_id": call_id,
        "created_count": len(new_messages),
        "message_ids": [msg.id for msg in new_messages],
    }


# Analytics endpoint
@router.get("/{call_id}/messages/analytics", response_model=Dict[str, Any])
async def get_call_messages_analytics(
    call_id: str = Path(..., description="Call ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get analytics for call messages."""
    
    # Verify call exists and user has access
    call_query = select(PhoneCall).where(
        and_(
            PhoneCall.id == call_id,
            get_tenant_filter(PhoneCall, current_user)
        )
    )
    result = await db.execute(call_query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Get all messages
    messages_query = select(CallMessage).where(CallMessage.call_id == call_id)
    result = await db.execute(messages_query)
    messages = result.scalars().all()
    
    # Calculate analytics
    total_messages = len(messages)
    message_types = {}
    sender_types = {}
    languages = {}
    confidence_scores = []
    audio_messages = 0
    
    for msg in messages:
        # Message type breakdown
        msg_type = msg.message_type
        message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        # Sender type breakdown
        sender_type = msg.sender.get('type', 'unknown')
        sender_types[sender_type] = sender_types.get(sender_type, 0) + 1
        
        # Language breakdown
        if msg.metadata and 'language' in msg.metadata:
            lang = msg.metadata['language']
            languages[lang] = languages.get(lang, 0) + 1
        
        # Confidence scores
        if msg.metadata and 'confidence_score' in msg.metadata:
            confidence_scores.append(msg.metadata['confidence_score'])
        
        # Audio segments
        if msg.has_audio_segment:
            audio_messages += 1
    
    # Calculate confidence stats
    confidence_stats = None
    if confidence_scores:
        confidence_stats = {
            'average': sum(confidence_scores) / len(confidence_scores),
            'min': min(confidence_scores),
            'max': max(confidence_scores),
            'count': len(confidence_scores),
        }
    
    return {
        "call_id": call_id,
        "total_messages": total_messages,
        "message_types": message_types,
        "sender_types": sender_types,
        "languages": languages,
        "confidence_stats": confidence_stats,
        "audio_messages": audio_messages,
        "audio_percentage": (audio_messages / total_messages * 100) if total_messages > 0 else 0,
    }