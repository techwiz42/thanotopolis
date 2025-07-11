# backend/app/api/calendar.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, date, timedelta
from typing import List, Optional
from uuid import UUID
import json
import logging

from app.db.database import get_db
from app.models import CalendarEvent, CalendarEventAttendee, User, Contact, Tenant
from app.auth.auth import get_current_user
from app.services.calendar_invitation_service import calendar_invitation_service
from app.schemas.calendar_schemas import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventResponse,
    CalendarEventList,
    CalendarEventAttendeeCreate,
    CalendarEventAttendeeUpdate,
    CalendarEventAttendeeResponse,
    CalendarEventAttendeeList,
    AttendeeInvitationRequest,
    RSVPResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/events", response_model=CalendarEventList)
async def list_calendar_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    contact_id: Optional[UUID] = Query(None, description="Filter by contact"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List calendar events for the current tenant with optional filters"""
    query = select(CalendarEvent).where(
        CalendarEvent.tenant_id == current_user.tenant_id
    )
    
    # Apply filters
    if start_date:
        query = query.where(CalendarEvent.start_time >= start_date)
    if end_date:
        query = query.where(CalendarEvent.end_time <= end_date)
    if user_id:
        query = query.where(CalendarEvent.user_id == user_id)
    if contact_id:
        query = query.where(CalendarEvent.contact_id == contact_id)
    if event_type:
        query = query.where(CalendarEvent.event_type == event_type)
    if status:
        query = query.where(CalendarEvent.status == status)
    
    # Order by start time
    query = query.order_by(CalendarEvent.start_time)
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Get total count
    count_query = select(func.count()).select_from(CalendarEvent).where(
        CalendarEvent.tenant_id == current_user.tenant_id
    )
    if start_date:
        count_query = count_query.where(CalendarEvent.start_time >= start_date)
    if end_date:
        count_query = count_query.where(CalendarEvent.end_time <= end_date)
    if user_id:
        count_query = count_query.where(CalendarEvent.user_id == user_id)
    if contact_id:
        count_query = count_query.where(CalendarEvent.contact_id == contact_id)
    if event_type:
        count_query = count_query.where(CalendarEvent.event_type == event_type)
    if status:
        count_query = count_query.where(CalendarEvent.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    return CalendarEventList(
        events=[CalendarEventResponse.from_orm(event) for event in events],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/events/range", response_model=List[CalendarEventResponse])
async def get_events_in_range(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start: datetime = Query(..., description="Range start"),
    end: datetime = Query(..., description="Range end"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
):
    """Get all events within a specific date range"""
    query = select(CalendarEvent).where(
        and_(
            CalendarEvent.tenant_id == current_user.tenant_id,
            or_(
                # Event starts within range
                and_(
                    CalendarEvent.start_time >= start,
                    CalendarEvent.start_time < end
                ),
                # Event ends within range
                and_(
                    CalendarEvent.end_time > start,
                    CalendarEvent.end_time <= end
                ),
                # Event spans the entire range
                and_(
                    CalendarEvent.start_time <= start,
                    CalendarEvent.end_time >= end
                )
            )
        )
    )
    
    if user_id:
        query = query.where(CalendarEvent.user_id == user_id)
    
    query = query.order_by(CalendarEvent.start_time)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return [CalendarEventResponse.from_orm(event) for event in events]


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
async def get_calendar_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific calendar event"""
    query = select(CalendarEvent).where(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == current_user.tenant_id
        )
    )
    
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return CalendarEventResponse.from_orm(event)


@router.post("/events", response_model=CalendarEventResponse)
async def create_calendar_event(
    event_data: CalendarEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new calendar event"""
    # Validate contact if provided
    if event_data.contact_id:
        contact_query = select(Contact).where(
            and_(
                Contact.id == event_data.contact_id,
                Contact.tenant_id == current_user.tenant_id
            )
        )
        contact_result = await db.execute(contact_query)
        if not contact_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Invalid contact ID")
    
    # Validate times
    if event_data.end_time <= event_data.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    # Create event
    event = CalendarEvent(
        tenant_id=current_user.tenant_id,
        user_id=event_data.user_id or current_user.id,
        contact_id=event_data.contact_id,
        title=event_data.title,
        description=event_data.description,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        all_day=event_data.all_day,
        location=event_data.location,
        event_type=event_data.event_type,
        status=event_data.status or 'confirmed',
        event_metadata=json.dumps(event_data.event_metadata) if event_data.event_metadata else None,
        created_by_user_id=current_user.id
    )
    
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return CalendarEventResponse.from_orm(event)


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_calendar_event(
    event_id: UUID,
    event_data: CalendarEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a calendar event"""
    query = select(CalendarEvent).where(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == current_user.tenant_id
        )
    )
    
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Validate contact if being updated
    if event_data.contact_id is not None:
        if event_data.contact_id:  # If not null, validate it exists
            contact_query = select(Contact).where(
                and_(
                    Contact.id == event_data.contact_id,
                    Contact.tenant_id == current_user.tenant_id
                )
            )
            contact_result = await db.execute(contact_query)
            if not contact_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Invalid contact ID")
    
    # Validate times if being updated
    if event_data.start_time or event_data.end_time:
        start_time = event_data.start_time or event.start_time
        end_time = event_data.end_time or event.end_time
        if end_time <= start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time")
    
    # Update fields
    update_data = event_data.dict(exclude_unset=True)
    if 'event_metadata' in update_data and update_data['event_metadata'] is not None:
        update_data['event_metadata'] = json.dumps(update_data['event_metadata'])
    
    for field, value in update_data.items():
        setattr(event, field, value)
    
    await db.commit()
    await db.refresh(event)
    
    return CalendarEventResponse.from_orm(event)


@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a calendar event"""
    query = select(CalendarEvent).where(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == current_user.tenant_id
        )
    )
    
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    await db.delete(event)
    await db.commit()
    
    return {"detail": "Event deleted successfully"}


@router.get("/events/stats/summary")
async def get_calendar_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000, le=2100),
):
    """Get calendar statistics for the current tenant"""
    # Default to current month/year if not provided
    if not month or not year:
        now = datetime.now()
        month = month or now.month
        year = year or now.year
    
    # Calculate date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Get event counts by type
    type_query = select(
        CalendarEvent.event_type,
        func.count(CalendarEvent.id).label('count')
    ).where(
        and_(
            CalendarEvent.tenant_id == current_user.tenant_id,
            CalendarEvent.start_time >= start_date,
            CalendarEvent.start_time < end_date
        )
    ).group_by(CalendarEvent.event_type)
    
    type_result = await db.execute(type_query)
    events_by_type = {row[0]: row[1] for row in type_result}
    
    # Get event counts by status
    status_query = select(
        CalendarEvent.status,
        func.count(CalendarEvent.id).label('count')
    ).where(
        and_(
            CalendarEvent.tenant_id == current_user.tenant_id,
            CalendarEvent.start_time >= start_date,
            CalendarEvent.start_time < end_date
        )
    ).group_by(CalendarEvent.status)
    
    status_result = await db.execute(status_query)
    events_by_status = {row[0]: row[1] for row in status_result}
    
    # Get total events
    total_query = select(func.count(CalendarEvent.id)).where(
        and_(
            CalendarEvent.tenant_id == current_user.tenant_id,
            CalendarEvent.start_time >= start_date,
            CalendarEvent.start_time < end_date
        )
    )
    
    total_result = await db.execute(total_query)
    total_events = total_result.scalar() or 0
    
    return {
        "month": month,
        "year": year,
        "total_events": total_events,
        "events_by_type": events_by_type,
        "events_by_status": events_by_status,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }


# Attendee Management Endpoints

@router.get("/events/{event_id}/attendees", response_model=CalendarEventAttendeeList)
async def list_event_attendees(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all attendees for a specific event"""
    # Verify event exists and user has access
    event_query = select(CalendarEvent).where(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == current_user.tenant_id
        )
    )
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get attendees
    query = select(CalendarEventAttendee).where(
        CalendarEventAttendee.event_id == event_id
    ).order_by(CalendarEventAttendee.created_at)
    
    result = await db.execute(query)
    attendees = result.scalars().all()
    
    # Load relationships for proper attendee_name and attendee_email
    for attendee in attendees:
        if attendee.user_id:
            user_query = select(User).where(User.id == attendee.user_id)
            user_result = await db.execute(user_query)
            attendee.user = user_result.scalar_one_or_none()
        if attendee.contact_id:
            contact_query = select(Contact).where(Contact.id == attendee.contact_id)
            contact_result = await db.execute(contact_query)
            attendee.contact = contact_result.scalar_one_or_none()
    
    return CalendarEventAttendeeList(
        attendees=[CalendarEventAttendeeResponse.from_orm(attendee) for attendee in attendees],
        total=len(attendees)
    )


@router.post("/events/{event_id}/attendees", response_model=CalendarEventAttendeeResponse)
async def add_event_attendee(
    event_id: UUID,
    attendee_data: CalendarEventAttendeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an attendee to an event"""
    # Verify event exists and user has access
    event_query = select(CalendarEvent).where(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == current_user.tenant_id
        )
    )
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Validate attendee data based on type
    if attendee_data.attendee_type == 'user' and attendee_data.user_id:
        # Verify user exists and belongs to same tenant
        user_query = select(User).where(
            and_(
                User.id == attendee_data.user_id,
                User.tenant_id == current_user.tenant_id
            )
        )
        user_result = await db.execute(user_query)
        if not user_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Invalid user ID")
    
    elif attendee_data.attendee_type == 'contact' and attendee_data.contact_id:
        # Verify contact exists and belongs to same tenant
        contact_query = select(Contact).where(
            and_(
                Contact.id == attendee_data.contact_id,
                Contact.tenant_id == current_user.tenant_id
            )
        )
        contact_result = await db.execute(contact_query)
        if not contact_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Invalid contact ID")
    
    # Check for duplicate attendees
    existing_query = select(CalendarEventAttendee).where(
        CalendarEventAttendee.event_id == event_id
    )
    
    if attendee_data.attendee_type == 'user':
        existing_query = existing_query.where(
            and_(
                CalendarEventAttendee.attendee_type == 'user',
                CalendarEventAttendee.user_id == attendee_data.user_id
            )
        )
    elif attendee_data.attendee_type == 'contact':
        existing_query = existing_query.where(
            and_(
                CalendarEventAttendee.attendee_type == 'contact',
                CalendarEventAttendee.contact_id == attendee_data.contact_id
            )
        )
    elif attendee_data.attendee_type == 'external':
        existing_query = existing_query.where(
            and_(
                CalendarEventAttendee.attendee_type == 'external',
                CalendarEventAttendee.external_email == attendee_data.external_email
            )
        )
    
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Attendee already exists for this event")
    
    # Create attendee
    attendee = CalendarEventAttendee(
        event_id=event_id,
        attendee_type=attendee_data.attendee_type,
        user_id=attendee_data.user_id,
        contact_id=attendee_data.contact_id,
        external_email=attendee_data.external_email,
        external_name=attendee_data.external_name,
    )
    
    db.add(attendee)
    await db.commit()
    await db.refresh(attendee)
    
    # Load relationships for response
    if attendee.user_id:
        user_query = select(User).where(User.id == attendee.user_id)
        user_result = await db.execute(user_query)
        attendee.user = user_result.scalar_one_or_none()
    if attendee.contact_id:
        contact_query = select(Contact).where(Contact.id == attendee.contact_id)
        contact_result = await db.execute(contact_query)
        attendee.contact = contact_result.scalar_one_or_none()
    
    return CalendarEventAttendeeResponse.from_orm(attendee)


@router.delete("/events/{event_id}/attendees/{attendee_id}")
async def remove_event_attendee(
    event_id: UUID,
    attendee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an attendee from an event"""
    # Verify event exists and user has access
    event_query = select(CalendarEvent).where(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == current_user.tenant_id
        )
    )
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Find attendee
    attendee_query = select(CalendarEventAttendee).where(
        and_(
            CalendarEventAttendee.id == attendee_id,
            CalendarEventAttendee.event_id == event_id
        )
    )
    attendee_result = await db.execute(attendee_query)
    attendee = attendee_result.scalar_one_or_none()
    
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    await db.delete(attendee)
    await db.commit()
    
    return {"detail": "Attendee removed successfully"}


@router.post("/events/{event_id}/send-invitations")
async def send_event_invitations(
    event_id: UUID,
    invitation_request: AttendeeInvitationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send invitations to specified attendees"""
    # Verify event exists and user has access
    event_query = select(CalendarEvent).where(
        and_(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == current_user.tenant_id
        )
    )
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get attendees to send invitations to
    attendees_query = select(CalendarEventAttendee).where(
        and_(
            CalendarEventAttendee.event_id == event_id,
            CalendarEventAttendee.id.in_(invitation_request.attendee_ids)
        )
    )
    attendees_result = await db.execute(attendees_query)
    attendees = attendees_result.scalars().all()
    
    if len(attendees) != len(invitation_request.attendee_ids):
        raise HTTPException(status_code=400, detail="Some attendee IDs not found")
    
    sent_count = 0
    failed_count = 0
    
    # Load relationships and send invitations
    for attendee in attendees:
        try:
            # Load user/contact relationships for email address
            if attendee.user_id:
                user_query = select(User).where(User.id == attendee.user_id)
                user_result = await db.execute(user_query)
                attendee.user = user_result.scalar_one_or_none()
            if attendee.contact_id:
                contact_query = select(Contact).where(Contact.id == attendee.contact_id)
                contact_result = await db.execute(contact_query)
                attendee.contact = contact_result.scalar_one_or_none()
            
            if invitation_request.send_invitations and attendee.attendee_email:
                # Get organizer and tenant for invitation
                organizer_query = select(User).where(User.id == event.user_id)
                organizer_result = await db.execute(organizer_query)
                organizer = organizer_result.scalar_one_or_none()
                
                tenant_query = select(Tenant).where(Tenant.id == current_user.tenant_id)
                tenant_result = await db.execute(tenant_query)
                tenant = tenant_result.scalar_one_or_none()
                
                if organizer and tenant:
                    # Send invitation email
                    success = await calendar_invitation_service.send_invitation(
                        event=event,
                        attendee=attendee,
                        organizer=organizer,
                        tenant=tenant,
                        custom_message=invitation_request.custom_message
                    )
                    
                    if success:
                        attendee.invitation_status = 'sent'
                        attendee.invited_at = datetime.now()
                        sent_count += 1
                    else:
                        attendee.invitation_status = 'failed'
                        failed_count += 1
                else:
                    attendee.invitation_status = 'failed'
                    failed_count += 1
            else:
                attendee.invitation_status = 'pending'
                
        except Exception as e:
            attendee.invitation_status = 'failed'
            failed_count += 1
    
    await db.commit()
    
    return {
        "detail": f"Invitations processed: {sent_count} sent, {failed_count} failed",
        "sent_count": sent_count,
        "failed_count": failed_count
    }


# Public RSVP Endpoints (no authentication required)

@router.get("/rsvp/{invitation_token}")
async def get_rsvp_details(
    invitation_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get RSVP details for an invitation token (public endpoint)"""
    # Find attendee by invitation token
    attendee_query = select(CalendarEventAttendee).where(
        CalendarEventAttendee.invitation_token == invitation_token
    )
    attendee_result = await db.execute(attendee_query)
    attendee = attendee_result.scalar_one_or_none()
    
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    
    # Get event details
    event_query = select(CalendarEvent).where(
        CalendarEvent.id == attendee.event_id
    )
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Load relationships for attendee name/email
    if attendee.user_id:
        user_query = select(User).where(User.id == attendee.user_id)
        user_result = await db.execute(user_query)
        attendee.user = user_result.scalar_one_or_none()
    if attendee.contact_id:
        contact_query = select(Contact).where(Contact.id == attendee.contact_id)
        contact_result = await db.execute(contact_query)
        attendee.contact = contact_result.scalar_one_or_none()
    
    return {
        "attendee": CalendarEventAttendeeResponse.from_orm(attendee),
        "event": {
            "id": str(event.id),
            "title": event.title,
            "description": event.description,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "location": event.location,
            "all_day": event.all_day
        }
    }


@router.post("/rsvp/{invitation_token}/respond")
async def respond_to_invitation(
    invitation_token: str,
    rsvp_response: RSVPResponse,
    db: AsyncSession = Depends(get_db),
):
    """Respond to an event invitation (public endpoint)"""
    # Find attendee by invitation token
    attendee_query = select(CalendarEventAttendee).where(
        CalendarEventAttendee.invitation_token == invitation_token
    )
    attendee_result = await db.execute(attendee_query)
    attendee = attendee_result.scalar_one_or_none()
    
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    
    # Update response
    attendee.response_status = rsvp_response.response_status
    attendee.responded_at = datetime.now()
    
    # Allow external attendees to update their name
    if attendee.attendee_type == 'external' and rsvp_response.attendee_name:
        attendee.external_name = rsvp_response.attendee_name
    
    await db.commit()
    
    # Send confirmation email
    try:
        # Get event details
        event_query = select(CalendarEvent).where(CalendarEvent.id == attendee.event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()
        
        if event:
            # Get organizer and tenant
            organizer_query = select(User).where(User.id == event.user_id)
            organizer_result = await db.execute(organizer_query)
            organizer = organizer_result.scalar_one_or_none()
            
            tenant_query = select(Tenant).where(Tenant.id == event.tenant_id)
            tenant_result = await db.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            if organizer and tenant:
                await calendar_invitation_service.send_rsvp_confirmation(
                    event=event,
                    attendee=attendee,
                    organizer=organizer,
                    tenant=tenant
                )
    except Exception as e:
        # Don't fail the RSVP if email fails
        logger.error(f"Failed to send RSVP confirmation email: {e}")
    
    return {
        "detail": f"RSVP response recorded: {rsvp_response.response_status}",
        "response_status": rsvp_response.response_status,
        "responded_at": attendee.responded_at.isoformat()
    }


@router.get("/events/{event_id}/ics")
async def download_event_ics(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download event as ICS calendar file (public endpoint)"""
    # Get event
    event_query = select(CalendarEvent).where(CalendarEvent.id == event_id)
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get organizer
    organizer_query = select(User).where(User.id == event.user_id)
    organizer_result = await db.execute(organizer_query)
    organizer = organizer_result.scalar_one_or_none()
    
    if not organizer:
        raise HTTPException(status_code=404, detail="Event organizer not found")
    
    # Generate ICS content
    ics_content = calendar_invitation_service.generate_ics_content(event, organizer)
    
    # Return as downloadable file
    filename = f"{event.title.replace(' ', '_')}_{event.start_time.strftime('%Y%m%d')}.ics"
    
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/calendar; charset=utf-8"
        }
    )