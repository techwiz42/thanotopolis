# backend/app/models/calendar_models.py
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .models import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    
    title = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    all_day = Column(Boolean, default=False)
    location = Column(String)
    
    # Event types: 'appointment', 'service', 'meeting', 'call', 'reminder', 'other'
    event_type = Column(String, default='appointment')
    
    # Status: 'confirmed', 'tentative', 'cancelled'
    status = Column(String, default='confirmed')
    
    # Event metadata for additional info (e.g., video call link, phone number, etc.)
    event_metadata = Column(Text)  # JSON string for flexibility
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    tenant = relationship("Tenant", back_populates="calendar_events")
    user = relationship("User", foreign_keys=[user_id], back_populates="calendar_events")
    creator = relationship("User", foreign_keys=[created_by_user_id])
    contact = relationship("Contact", back_populates="calendar_events")
    attendees = relationship("CalendarEventAttendee", back_populates="event", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_calendar_events_tenant_id', 'tenant_id'),
        Index('idx_calendar_events_user_id', 'user_id'),
        Index('idx_calendar_events_start_time', 'start_time'),
        Index('idx_calendar_events_contact_id', 'contact_id'),
        Index('idx_calendar_events_status', 'status'),
        Index('idx_calendar_events_event_type', 'event_type'),
    )
    
    def to_dict(self):
        """Convert calendar event to dictionary"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'user_id': str(self.user_id),
            'contact_id': str(self.contact_id) if self.contact_id else None,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'all_day': self.all_day,
            'location': self.location,
            'event_type': self.event_type,
            'status': self.status,
            'event_metadata': self.event_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by_user_id': str(self.created_by_user_id) if self.created_by_user_id else None,
        }


class CalendarEventAttendee(Base):
    __tablename__ = "calendar_event_attendees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    
    # Attendee can be a user, contact, or external person
    attendee_type = Column(String, nullable=False)  # 'user', 'contact', 'external'
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # For internal users
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)  # For CRM contacts
    external_email = Column(String, nullable=True)  # For external invitees
    external_name = Column(String, nullable=True)  # For external invitees
    
    # Invitation tracking
    invitation_status = Column(String, default='pending')  # pending, sent, delivered, failed
    response_status = Column(String, default='no_response')  # no_response, accepted, declined, tentative
    invitation_token = Column(String, unique=True)  # Unique token for RSVP links
    
    # Timestamps
    invited_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    event = relationship("CalendarEvent", back_populates="attendees")
    user = relationship("User", foreign_keys=[user_id])
    contact = relationship("Contact", foreign_keys=[contact_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_calendar_attendees_event_id', 'event_id'),
        Index('idx_calendar_attendees_user_id', 'user_id'),
        Index('idx_calendar_attendees_contact_id', 'contact_id'),
        Index('idx_calendar_attendees_invitation_token', 'invitation_token'),
        Index('idx_calendar_attendees_invitation_status', 'invitation_status'),
        Index('idx_calendar_attendees_response_status', 'response_status'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.invitation_token:
            self.invitation_token = str(uuid.uuid4())
    
    @property
    def attendee_email(self):
        """Get the email address for this attendee"""
        if self.attendee_type == 'user' and self.user:
            return self.user.email
        elif self.attendee_type == 'contact' and self.contact:
            return self.contact.contact_email
        elif self.attendee_type == 'external':
            return self.external_email
        return None
    
    @property
    def attendee_name(self):
        """Get the name for this attendee"""
        if self.attendee_type == 'user' and self.user:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        elif self.attendee_type == 'contact' and self.contact:
            return self.contact.contact_name
        elif self.attendee_type == 'external':
            return self.external_name
        return None
    
    def to_dict(self):
        """Convert attendee to dictionary"""
        return {
            'id': str(self.id),
            'event_id': str(self.event_id),
            'attendee_type': self.attendee_type,
            'user_id': str(self.user_id) if self.user_id else None,
            'contact_id': str(self.contact_id) if self.contact_id else None,
            'external_email': self.external_email,
            'external_name': self.external_name,
            'invitation_status': self.invitation_status,
            'response_status': self.response_status,
            'invitation_token': self.invitation_token,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'attendee_email': self.attendee_email,
            'attendee_name': self.attendee_name,
        }