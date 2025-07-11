# backend/app/schemas/calendar_schemas.py
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
import json


class CalendarEventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    location: Optional[str] = None
    event_type: str = Field(default='appointment', pattern='^(appointment|service|meeting|call|reminder|other)$')
    status: str = Field(default='confirmed', pattern='^(confirmed|tentative|cancelled)$')
    event_metadata: Optional[Dict[str, Any]] = None
    contact_id: Optional[UUID] = None
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class CalendarEventCreate(CalendarEventBase):
    user_id: Optional[UUID] = None  # If not provided, defaults to current user


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    location: Optional[str] = None
    event_type: Optional[str] = Field(None, pattern='^(appointment|service|meeting|call|reminder|other)$')
    status: Optional[str] = Field(None, pattern='^(confirmed|tentative|cancelled)$')
    event_metadata: Optional[Dict[str, Any]] = None
    contact_id: Optional[UUID] = None


class CalendarEventResponse(CalendarEventBase):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[UUID] = None
    
    # Contact info (will be populated when needed)
    contact_name: Optional[str] = None
    contact_business: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, event):
        data = {
            'id': event.id,
            'tenant_id': event.tenant_id,
            'user_id': event.user_id,
            'contact_id': event.contact_id,
            'title': event.title,
            'description': event.description,
            'start_time': event.start_time,
            'end_time': event.end_time,
            'all_day': event.all_day,
            'location': event.location,
            'event_type': event.event_type,
            'status': event.status,
            'event_metadata': json.loads(event.event_metadata) if event.event_metadata else None,
            'created_at': event.created_at,
            'updated_at': event.updated_at,
            'created_by_user_id': event.created_by_user_id,
        }
        
        # Add contact info if available
        if hasattr(event, 'contact') and event.contact:
            data['contact_name'] = event.contact.contact_name
            data['contact_business'] = event.contact.business_name
            
        return cls(**data)


class CalendarEventList(BaseModel):
    events: List[CalendarEventResponse]
    total: int
    skip: int
    limit: int


# Attendee Schemas
class CalendarEventAttendeeBase(BaseModel):
    attendee_type: str = Field(..., pattern='^(user|contact|external)$')
    user_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    external_email: Optional[str] = None
    external_name: Optional[str] = None
    
    @validator('user_id')
    def validate_user_attendee(cls, v, values):
        if values.get('attendee_type') == 'user' and v is None:
            raise ValueError('user_id is required for user attendees')
        return v
    
    @validator('contact_id')
    def validate_contact_attendee(cls, v, values):
        if values.get('attendee_type') == 'contact' and v is None:
            raise ValueError('contact_id is required for contact attendees')
        return v
    
    @validator('external_email')
    def validate_external_attendee(cls, v, values):
        if values.get('attendee_type') == 'external' and not v:
            raise ValueError('external_email is required for external attendees')
        return v


class CalendarEventAttendeeCreate(CalendarEventAttendeeBase):
    pass


class CalendarEventAttendeeUpdate(BaseModel):
    response_status: Optional[str] = Field(None, pattern='^(no_response|accepted|declined|tentative)$')


class CalendarEventAttendeeResponse(CalendarEventAttendeeBase):
    id: UUID
    event_id: UUID
    invitation_status: str
    response_status: str
    invitation_token: str
    invited_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    attendee_email: Optional[str] = None
    attendee_name: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, attendee):
        data = {
            'id': attendee.id,
            'event_id': attendee.event_id,
            'attendee_type': attendee.attendee_type,
            'user_id': attendee.user_id,
            'contact_id': attendee.contact_id,
            'external_email': attendee.external_email,
            'external_name': attendee.external_name,
            'invitation_status': attendee.invitation_status,
            'response_status': attendee.response_status,
            'invitation_token': attendee.invitation_token,
            'invited_at': attendee.invited_at,
            'responded_at': attendee.responded_at,
            'created_at': attendee.created_at,
            'updated_at': attendee.updated_at,
            'attendee_email': attendee.attendee_email,
            'attendee_name': attendee.attendee_name,
        }
        
        return cls(**data)


class CalendarEventAttendeeList(BaseModel):
    attendees: List[CalendarEventAttendeeResponse]
    total: int


class AttendeeInvitationRequest(BaseModel):
    attendee_ids: List[UUID] = Field(..., min_items=1)
    send_invitations: bool = True
    custom_message: Optional[str] = None


class RSVPResponse(BaseModel):
    response_status: str = Field(..., pattern='^(accepted|declined|tentative)$')
    attendee_name: Optional[str] = None  # Allow external attendees to update their name