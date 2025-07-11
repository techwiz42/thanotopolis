# backend/app/services/voice/voice_calendar.py
"""
Voice Calendar Service for Voice Agent
Handles real-time calendar availability checking and appointment booking
"""

import json
import logging
from datetime import datetime, timedelta, time, date
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models import CalendarEvent, User, Contact
from app.services.voice.scheduling_intent import SchedulingPreferences, SchedulingIntent, UrgencyLevel
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TimeSlot:
    """Represents an available time slot"""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    confidence: float = 1.0  # How confident we are this slot is good
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_minutes': self.duration_minutes,
            'confidence': self.confidence
        }
    
    def to_natural_language(self) -> str:
        """Convert to natural language description"""
        date_str = self.start_time.strftime("%A, %B %d")
        time_str = self.start_time.strftime("%I:%M %p")
        return f"{date_str} at {time_str}"


@dataclass
class CalendarAvailability:
    """Calendar availability information"""
    available_slots: List[TimeSlot]
    total_slots_checked: int
    business_hours: Dict[str, Any]
    next_available: Optional[TimeSlot] = None
    
    def has_availability(self) -> bool:
        return len(self.available_slots) > 0
    
    def get_best_slots(self, count: int = 3) -> List[TimeSlot]:
        """Get the best available slots"""
        return sorted(self.available_slots, key=lambda x: x.confidence, reverse=True)[:count]


class VoiceCalendarService:
    """Service for handling calendar operations during voice conversations"""
    
    def __init__(self):
        # Default business hours (9 AM - 5 PM, Monday-Friday)
        self.default_business_hours = {
            'monday': {'start': '09:00', 'end': '17:00'},
            'tuesday': {'start': '09:00', 'end': '17:00'},
            'wednesday': {'start': '09:00', 'end': '17:00'},
            'thursday': {'start': '09:00', 'end': '17:00'},
            'friday': {'start': '09:00', 'end': '17:00'},
            'saturday': {'start': '10:00', 'end': '14:00'},
            'sunday': {'start': 'closed', 'end': 'closed'}
        }
        
        # Default appointment durations by service type
        self.default_durations = {
            'consultation': 60,
            'service': 120,
            'meeting': 30,
            'appointment': 60,
            'follow_up': 30,
            'default': 60
        }
    
    async def check_availability(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        preferences: SchedulingPreferences,
        days_to_check: int = 14
    ) -> CalendarAvailability:
        """
        Check calendar availability based on scheduling preferences
        
        Args:
            db: Database session
            tenant_id: Organization ID
            user_id: User to check availability for
            preferences: Scheduling preferences
            days_to_check: Number of days to look ahead
            
        Returns:
            CalendarAvailability object
        """
        try:
            # Get business hours (could be from organization settings in future)
            business_hours = self.default_business_hours
            
            # Determine search date range
            start_date = datetime.now().date()
            if preferences.preferred_date:
                start_date = preferences.preferred_date.date()
            elif preferences.urgency == UrgencyLevel.URGENT:
                days_to_check = 3  # Urgent requests check fewer days
            
            end_date = start_date + timedelta(days=days_to_check)
            
            # Get existing appointments in the date range
            existing_events = await self._get_existing_events(
                db, tenant_id, user_id, start_date, end_date
            )
            
            # Generate available time slots
            available_slots = await self._generate_available_slots(
                business_hours, existing_events, start_date, end_date, preferences
            )
            
            # Score and filter slots based on preferences
            from app.services.voice.scheduling_intent import get_scheduling_intent_service
            intent_service = get_scheduling_intent_service()
            
            # Convert TimeSlots to tuples for scoring
            slot_tuples = [(slot.start_time, slot.end_time) for slot in available_slots]
            scored_slots = intent_service.get_suggested_times(preferences, slot_tuples)
            
            # Convert back to TimeSlot objects with confidence scores
            final_slots = []
            for i, (start_time, end_time) in enumerate(scored_slots[:10]):  # Top 10 slots
                confidence = 1.0 - (i * 0.1)  # Decrease confidence for lower ranked slots
                duration = int((end_time - start_time).total_seconds() / 60)
                slot = TimeSlot(start_time, end_time, duration, max(confidence, 0.1))
                final_slots.append(slot)
            
            # Determine next available slot
            next_available = final_slots[0] if final_slots else None
            
            availability = CalendarAvailability(
                available_slots=final_slots,
                total_slots_checked=len(available_slots),
                business_hours=business_hours,
                next_available=next_available
            )
            
            logger.info(f"Found {len(final_slots)} available slots for user {user_id}")
            return availability
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return CalendarAvailability([], 0, self.default_business_hours)
    
    async def _get_existing_events(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[CalendarEvent]:
        """Get existing calendar events in date range"""
        try:
            start_datetime = datetime.combine(start_date, time.min)
            end_datetime = datetime.combine(end_date, time.max)
            
            query = select(CalendarEvent).where(
                and_(
                    CalendarEvent.tenant_id == tenant_id,
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.status != 'cancelled',
                    or_(
                        # Event starts in range
                        and_(
                            CalendarEvent.start_time >= start_datetime,
                            CalendarEvent.start_time < end_datetime
                        ),
                        # Event ends in range
                        and_(
                            CalendarEvent.end_time > start_datetime,
                            CalendarEvent.end_time <= end_datetime
                        ),
                        # Event spans range
                        and_(
                            CalendarEvent.start_time <= start_datetime,
                            CalendarEvent.end_time >= end_datetime
                        )
                    )
                )
            ).order_by(CalendarEvent.start_time)
            
            result = await db.execute(query)
            events = result.scalars().all()
            
            logger.debug(f"Found {len(events)} existing events in date range")
            return events
            
        except Exception as e:
            logger.error(f"Error getting existing events: {e}")
            return []
    
    async def _generate_available_slots(
        self,
        business_hours: Dict[str, Any],
        existing_events: List[CalendarEvent],
        start_date: date,
        end_date: date,
        preferences: SchedulingPreferences
    ) -> List[TimeSlot]:
        """Generate available time slots within business hours"""
        slots = []
        
        # Determine appointment duration
        duration_minutes = preferences.estimated_duration or self.default_durations.get(
            preferences.service_type, self.default_durations['default']
        )
        
        current_date = start_date
        while current_date < end_date:
            # Get business hours for this day
            day_name = current_date.strftime('%A').lower()
            day_hours = business_hours.get(day_name, {'start': 'closed', 'end': 'closed'})
            
            if day_hours['start'] == 'closed':
                current_date += timedelta(days=1)
                continue
            
            # Parse business hours
            try:
                start_time = datetime.strptime(day_hours['start'], '%H:%M').time()
                end_time = datetime.strptime(day_hours['end'], '%H:%M').time()
            except ValueError:
                current_date += timedelta(days=1)
                continue
            
            # Generate slots for this day
            day_slots = self._generate_day_slots(
                current_date, start_time, end_time, duration_minutes, existing_events
            )
            slots.extend(day_slots)
            
            current_date += timedelta(days=1)
        
        return slots
    
    def _generate_day_slots(
        self,
        day_date: date,
        start_time: time,
        end_time: time,
        duration_minutes: int,
        existing_events: List[CalendarEvent]
    ) -> List[TimeSlot]:
        """Generate available slots for a specific day"""
        slots = []
        
        # Create datetime objects for the day
        day_start = datetime.combine(day_date, start_time)
        day_end = datetime.combine(day_date, end_time)
        
        # Get events for this day
        day_events = [
            event for event in existing_events
            if event.start_time.date() == day_date
        ]
        
        # Sort events by start time
        day_events.sort(key=lambda x: x.start_time)
        
        # Generate slots between events
        current_time = day_start
        slot_duration = timedelta(minutes=duration_minutes)
        
        for event in day_events:
            # Check if there's a gap before this event
            if current_time + slot_duration <= event.start_time:
                # Generate slots in this gap
                while current_time + slot_duration <= event.start_time:
                    slot_end = current_time + slot_duration
                    if slot_end <= day_end:  # Ensure slot fits in business hours
                        slot = TimeSlot(
                            start_time=current_time,
                            end_time=slot_end,
                            duration_minutes=duration_minutes
                        )
                        slots.append(slot)
                    current_time += timedelta(minutes=30)  # 30-minute increments
            
            # Move current time to after this event
            current_time = max(current_time, event.end_time)
        
        # Generate slots after the last event
        while current_time + slot_duration <= day_end:
            slot_end = current_time + slot_duration
            slot = TimeSlot(
                start_time=current_time,
                end_time=slot_end,
                duration_minutes=duration_minutes
            )
            slots.append(slot)
            current_time += timedelta(minutes=30)
        
        return slots
    
    async def book_appointment(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        contact_id: Optional[UUID],
        time_slot: TimeSlot,
        preferences: SchedulingPreferences,
        customer_notes: Optional[str] = None
    ) -> Optional[CalendarEvent]:
        """
        Book an appointment in the specified time slot
        
        Args:
            db: Database session
            tenant_id: Organization ID
            user_id: User booking the appointment
            contact_id: Contact ID if available
            time_slot: Selected time slot
            preferences: Scheduling preferences
            customer_notes: Additional notes from the conversation
            
        Returns:
            Created CalendarEvent or None if booking failed
        """
        try:
            # Verify the time slot is still available
            if not await self._is_slot_available(db, tenant_id, user_id, time_slot):
                logger.warning(f"Time slot no longer available: {time_slot.start_time}")
                return None
            
            # Build event title and description
            title = self._generate_event_title(preferences)
            description = self._generate_event_description(preferences, customer_notes)
            
            # Create calendar event
            event = CalendarEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                contact_id=contact_id,
                title=title,
                description=description,
                start_time=time_slot.start_time,
                end_time=time_slot.end_time,
                event_type=preferences.service_type or 'appointment',
                status='confirmed',
                location=self._get_location_from_preferences(preferences),
                event_metadata=json.dumps({
                    'booked_via_voice': True,
                    'scheduling_preferences': preferences.to_dict(),
                    'customer_notes': customer_notes,
                    'urgency': preferences.urgency.value
                }),
                created_by_user_id=user_id
            )
            
            db.add(event)
            await db.commit()
            await db.refresh(event)
            
            logger.info(f"Booked appointment: {event.id} for {time_slot.start_time}")
            return event
            
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            await db.rollback()
            return None
    
    async def _is_slot_available(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        time_slot: TimeSlot
    ) -> bool:
        """Check if a time slot is still available"""
        try:
            # Check for conflicting events
            query = select(func.count(CalendarEvent.id)).where(
                and_(
                    CalendarEvent.tenant_id == tenant_id,
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.status != 'cancelled',
                    or_(
                        # Event overlaps with start of slot
                        and_(
                            CalendarEvent.start_time <= time_slot.start_time,
                            CalendarEvent.end_time > time_slot.start_time
                        ),
                        # Event overlaps with end of slot
                        and_(
                            CalendarEvent.start_time < time_slot.end_time,
                            CalendarEvent.end_time >= time_slot.end_time
                        ),
                        # Event is completely within slot
                        and_(
                            CalendarEvent.start_time >= time_slot.start_time,
                            CalendarEvent.end_time <= time_slot.end_time
                        )
                    )
                )
            )
            
            result = await db.execute(query)
            conflict_count = result.scalar()
            
            return conflict_count == 0
            
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            return False
    
    def _generate_event_title(self, preferences: SchedulingPreferences) -> str:
        """Generate appropriate event title"""
        if preferences.service_type:
            return f"{preferences.service_type.title()} Appointment"
        else:
            return "Phone Consultation"
    
    def _generate_event_description(
        self, 
        preferences: SchedulingPreferences,
        customer_notes: Optional[str]
    ) -> str:
        """Generate event description from preferences and notes"""
        parts = ["Appointment scheduled via voice call."]
        
        if preferences.service_type:
            parts.append(f"Service: {preferences.service_type}")
        
        if preferences.urgency != UrgencyLevel.NORMAL:
            parts.append(f"Urgency: {preferences.urgency.value}")
        
        if preferences.special_requirements:
            parts.append("Special requirements:")
            for req in preferences.special_requirements:
                parts.append(f"- {req}")
        
        if customer_notes:
            parts.append(f"Customer notes: {customer_notes}")
        
        return "\n".join(parts)
    
    def _get_location_from_preferences(self, preferences: SchedulingPreferences) -> Optional[str]:
        """Get location string from preferences"""
        if preferences.location_preference:
            location_map = {
                'phone': 'Phone Call',
                'video': 'Video Call',
                'office': 'Office Visit',
                'onsite': 'On-site Visit'
            }
            return location_map.get(preferences.location_preference, preferences.location_preference)
        return None
    
    async def get_calendar_summary(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Get a summary of upcoming calendar events
        
        Args:
            db: Database session
            tenant_id: Organization ID
            user_id: User ID
            days_ahead: Number of days to look ahead
            
        Returns:
            Calendar summary dictionary
        """
        try:
            # Get date range
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=days_ahead)
            
            # Query upcoming events
            query = select(CalendarEvent).where(
                and_(
                    CalendarEvent.tenant_id == tenant_id,
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.start_time >= start_date,
                    CalendarEvent.start_time < end_date,
                    CalendarEvent.status != 'cancelled'
                )
            ).order_by(CalendarEvent.start_time)
            
            result = await db.execute(query)
            events = result.scalars().all()
            
            # Build summary
            summary = {
                'total_events': len(events),
                'today_events': 0,
                'this_week_events': 0,
                'next_available': None,
                'upcoming_events': []
            }
            
            today = datetime.now().date()
            week_end = today + timedelta(days=7)
            
            for event in events:
                event_date = event.start_time.date()
                
                if event_date == today:
                    summary['today_events'] += 1
                
                if event_date <= week_end:
                    summary['this_week_events'] += 1
                
                # Add to upcoming events list
                summary['upcoming_events'].append({
                    'id': str(event.id),
                    'title': event.title,
                    'start_time': event.start_time.isoformat(),
                    'end_time': event.end_time.isoformat(),
                    'event_type': event.event_type,
                    'status': event.status
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting calendar summary: {e}")
            return {
                'total_events': 0,
                'today_events': 0,
                'this_week_events': 0,
                'next_available': None,
                'upcoming_events': []
            }
    
    def format_availability_for_voice(self, availability: CalendarAvailability) -> str:
        """
        Format availability information for voice response
        
        Args:
            availability: CalendarAvailability object
            
        Returns:
            Natural language description of availability
        """
        if not availability.has_availability():
            return "I don't see any available time slots in the next two weeks. Would you like me to check further out or see if we can arrange something outside normal business hours?"
        
        best_slots = availability.get_best_slots(3)
        
        if len(best_slots) == 1:
            slot = best_slots[0]
            return f"I have availability {slot.to_natural_language()}. Would that work for you?"
        
        elif len(best_slots) == 2:
            slot1, slot2 = best_slots[:2]
            return f"I have a couple of options: {slot1.to_natural_language()} or {slot2.to_natural_language()}. Which would you prefer?"
        
        else:
            slot1, slot2, slot3 = best_slots[:3]
            return f"I have several options available: {slot1.to_natural_language()}, {slot2.to_natural_language()}, or {slot3.to_natural_language()}. Which time works best for you?"
    
    def format_booking_confirmation(self, event: CalendarEvent) -> str:
        """
        Format booking confirmation for voice response
        
        Args:
            event: Booked CalendarEvent
            
        Returns:
            Natural language confirmation message
        """
        date_str = event.start_time.strftime("%A, %B %d")
        time_str = event.start_time.strftime("%I:%M %p")
        
        return f"Perfect! I've scheduled your {event.event_type} for {date_str} at {time_str}. You should receive a confirmation shortly. Is there anything else I can help you with today?"


# Service singleton
_voice_calendar_service: Optional[VoiceCalendarService] = None


def get_voice_calendar_service() -> VoiceCalendarService:
    """Get VoiceCalendarService singleton"""
    global _voice_calendar_service
    if _voice_calendar_service is None:
        _voice_calendar_service = VoiceCalendarService()
    return _voice_calendar_service