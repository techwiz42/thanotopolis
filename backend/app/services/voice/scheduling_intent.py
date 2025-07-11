# backend/app/services/voice/scheduling_intent.py
"""
Scheduling Intent Detection Service for Voice Agent
Detects scheduling intent and preferences from natural conversation
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, time
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class SchedulingIntent(Enum):
    """Types of scheduling intent detected"""
    SCHEDULE_APPOINTMENT = "schedule_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    CHECK_AVAILABILITY = "check_availability"
    NONE = "none"


class TimePreference(Enum):
    """Time of day preferences"""
    MORNING = "morning"      # 8-12
    AFTERNOON = "afternoon"  # 12-17
    EVENING = "evening"      # 17-20
    SPECIFIC_TIME = "specific_time"
    FLEXIBLE = "flexible"


class UrgencyLevel(Enum):
    """Urgency levels for appointments"""
    URGENT = "urgent"        # ASAP, emergency
    SOON = "soon"           # This week
    NORMAL = "normal"       # Within 2 weeks
    FLEXIBLE = "flexible"   # Anytime


@dataclass
class SchedulingPreferences:
    """Structured scheduling preferences extracted from conversation"""
    intent: SchedulingIntent = SchedulingIntent.NONE
    
    # Time preferences
    preferred_date: Optional[datetime] = None
    preferred_time: Optional[time] = None
    time_preference: TimePreference = TimePreference.FLEXIBLE
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    
    # Service details
    service_type: Optional[str] = None
    estimated_duration: Optional[int] = None  # minutes
    
    # Availability constraints
    available_days: List[str] = None  # ['monday', 'tuesday', etc.]
    unavailable_dates: List[datetime] = None
    preferred_time_range: Optional[Tuple[time, time]] = None
    
    # Special requirements
    special_requirements: List[str] = None
    location_preference: Optional[str] = None  # 'onsite', 'office', 'phone', 'video'
    
    # Metadata
    detection_confidence: float = 0.0
    extracted_phrases: List[str] = None
    
    def __post_init__(self):
        if self.available_days is None:
            self.available_days = []
        if self.unavailable_dates is None:
            self.unavailable_dates = []
        if self.special_requirements is None:
            self.special_requirements = []
        if self.extracted_phrases is None:
            self.extracted_phrases = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        
        # Convert enum values to strings
        data['intent'] = self.intent.value
        data['time_preference'] = self.time_preference.value
        data['urgency'] = self.urgency.value
        
        # Convert datetime/time objects to strings
        if self.preferred_date:
            data['preferred_date'] = self.preferred_date.isoformat()
        if self.preferred_time:
            data['preferred_time'] = self.preferred_time.isoformat()
        if self.preferred_time_range:
            data['preferred_time_range'] = [
                self.preferred_time_range[0].isoformat(),
                self.preferred_time_range[1].isoformat()
            ]
        if self.unavailable_dates:
            data['unavailable_dates'] = [d.isoformat() for d in self.unavailable_dates]
        
        return data
    
    def has_scheduling_intent(self) -> bool:
        """Check if any scheduling intent was detected"""
        return self.intent != SchedulingIntent.NONE
    
    def is_time_specific(self) -> bool:
        """Check if specific time was requested"""
        return (self.preferred_date is not None or 
                self.preferred_time is not None or
                self.time_preference == TimePreference.SPECIFIC_TIME)


class SchedulingIntentService:
    """Service for detecting scheduling intent and preferences from voice conversations"""
    
    def __init__(self):
        self.intent_detection_prompt = self._build_intent_detection_prompt()
        self.preference_extraction_prompt = self._build_preference_extraction_prompt()
        
        # Common scheduling phrases for quick detection
        self.scheduling_keywords = [
            # Schedule intent
            'schedule', 'book', 'appointment', 'meeting', 'set up', 'arrange',
            'when can', 'available', 'free time', 'open slot',
            
            # Reschedule intent  
            'reschedule', 'change', 'move', 'different time', 'another day',
            
            # Cancel intent
            'cancel', 'cancel appointment', 'not coming', "can't make it",
            
            # Time references
            'today', 'tomorrow', 'next week', 'monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday', 'sunday', 'morning', 'afternoon',
            'evening', 'am', 'pm', "o'clock", 'urgent', 'asap', 'emergency'
        ]
    
    def _build_intent_detection_prompt(self) -> str:
        """Build prompt for detecting scheduling intent"""
        return """
You are an expert at detecting scheduling intent from natural conversation.
Analyze the conversation and determine if the person wants to schedule, reschedule, cancel, or check availability.

Intent types:
- schedule_appointment: Wants to book a new appointment
- reschedule_appointment: Wants to change existing appointment
- cancel_appointment: Wants to cancel appointment
- check_availability: Just checking when someone is available
- none: No scheduling intent detected

Return ONLY valid JSON:
{
    "intent": "intent_type",
    "confidence": 0.0-1.0
}
"""
    
    def _build_preference_extraction_prompt(self) -> str:
        """Build prompt for extracting scheduling preferences"""
        return """
You are an expert at extracting scheduling preferences from natural conversation.
Extract specific scheduling details when mentioned.

Extract:
- preferred_date: Specific date mentioned (YYYY-MM-DD format)
- preferred_time: Specific time mentioned (HH:MM format, 24-hour)
- time_preference: "morning", "afternoon", "evening", "specific_time", or "flexible"
- urgency: "urgent", "soon", "normal", or "flexible"
- service_type: Type of service/appointment
- estimated_duration: Duration in minutes
- available_days: Days of week they're available ["monday", "tuesday", etc.]
- unavailable_dates: Dates they can't do (YYYY-MM-DD format)
- preferred_time_range: Start and end times (HH:MM format)
- special_requirements: Any special needs mentioned
- location_preference: "onsite", "office", "phone", "video", or null

IMPORTANT:
- Only extract explicitly mentioned information
- Use relative dates (today, tomorrow, next week) based on current date
- Convert times to 24-hour format
- Be conservative - don't guess

Return ONLY valid JSON:
{
    "preferred_date": "2025-07-15 or null",
    "preferred_time": "14:30 or null",
    "time_preference": "string",
    "urgency": "string", 
    "service_type": "string or null",
    "estimated_duration": 60,
    "available_days": [],
    "unavailable_dates": [],
    "preferred_time_range": ["09:00", "17:00"] or null,
    "special_requirements": [],
    "location_preference": "string or null",
    "detection_confidence": 0.0-1.0
}
"""
    
    async def detect_scheduling_intent(self, conversation_text: str) -> SchedulingIntent:
        """
        Quick detection of scheduling intent using keywords and LLM
        
        Args:
            conversation_text: Text to analyze
            
        Returns:
            Detected SchedulingIntent
        """
        try:
            # Quick keyword check first
            text_lower = conversation_text.lower()
            
            # Check for scheduling keywords
            has_scheduling_keywords = any(keyword in text_lower for keyword in self.scheduling_keywords)
            
            if not has_scheduling_keywords:
                return SchedulingIntent.NONE
            
            # Use LLM for more precise intent detection
            from app.services.llm_service import llm_service
            
            prompt = f"{self.intent_detection_prompt}\n\nConversation:\n{conversation_text}"
            
            response = await llm_service.get_completion(
                prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.1,
                max_tokens=100
            )
            
            # Parse response
            data = self._parse_json_response(response)
            intent_str = data.get('intent', 'none')
            confidence = data.get('confidence', 0.0)
            
            # Convert to enum
            try:
                intent = SchedulingIntent(intent_str)
                if confidence < 0.5:  # Low confidence
                    intent = SchedulingIntent.NONE
                return intent
            except ValueError:
                return SchedulingIntent.NONE
                
        except Exception as e:
            logger.error(f"Error detecting scheduling intent: {e}")
            return SchedulingIntent.NONE
    
    async def extract_scheduling_preferences(
        self, 
        conversation_text: str,
        existing_preferences: Optional[SchedulingPreferences] = None
    ) -> SchedulingPreferences:
        """
        Extract detailed scheduling preferences from conversation
        
        Args:
            conversation_text: Text to analyze
            existing_preferences: Previously extracted preferences to merge
            
        Returns:
            SchedulingPreferences object
        """
        try:
            # Detect intent first
            intent = await self.detect_scheduling_intent(conversation_text)
            
            if intent == SchedulingIntent.NONE:
                # Return existing or empty preferences
                return existing_preferences or SchedulingPreferences()
            
            # Extract detailed preferences using LLM
            from app.services.llm_service import llm_service
            
            # Add current date context for relative date parsing
            current_date = datetime.now().strftime("%Y-%m-%d (%A)")
            prompt = f"{self.preference_extraction_prompt}\n\nCurrent date: {current_date}\n\nConversation:\n{conversation_text}"
            
            response = await llm_service.get_completion(
                prompt=prompt,
                model="gpt-4o-mini", 
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse response
            data = self._parse_json_response(response)
            
            # Create preferences object
            preferences = self._build_preferences_from_data(data, intent)
            preferences.extracted_phrases.append(conversation_text[:200])
            
            # Merge with existing preferences if provided
            if existing_preferences:
                preferences = self._merge_preferences(existing_preferences, preferences)
            
            logger.info(f"Extracted scheduling preferences: intent={preferences.intent.value}, confidence={preferences.detection_confidence:.2f}")
            return preferences
            
        except Exception as e:
            logger.error(f"Error extracting scheduling preferences: {e}")
            return existing_preferences or SchedulingPreferences()
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response"""
        try:
            # Clean up response
            cleaned = response.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response}")
            return {}
    
    def _build_preferences_from_data(self, data: Dict[str, Any], intent: SchedulingIntent) -> SchedulingPreferences:
        """Build SchedulingPreferences object from extracted data"""
        preferences = SchedulingPreferences()
        preferences.intent = intent
        
        # Parse date
        if data.get('preferred_date'):
            try:
                preferences.preferred_date = datetime.fromisoformat(data['preferred_date'])
            except (ValueError, TypeError):
                pass
        
        # Parse time
        if data.get('preferred_time'):
            try:
                time_str = data['preferred_time']
                preferences.preferred_time = datetime.strptime(time_str, "%H:%M").time()
            except (ValueError, TypeError):
                pass
        
        # Parse time preference
        time_pref_str = data.get('time_preference', 'flexible')
        try:
            preferences.time_preference = TimePreference(time_pref_str)
        except ValueError:
            preferences.time_preference = TimePreference.FLEXIBLE
        
        # Parse urgency
        urgency_str = data.get('urgency', 'normal')
        try:
            preferences.urgency = UrgencyLevel(urgency_str)
        except ValueError:
            preferences.urgency = UrgencyLevel.NORMAL
        
        # Parse time range
        if data.get('preferred_time_range') and isinstance(data['preferred_time_range'], list):
            try:
                start_time = datetime.strptime(data['preferred_time_range'][0], "%H:%M").time()
                end_time = datetime.strptime(data['preferred_time_range'][1], "%H:%M").time()
                preferences.preferred_time_range = (start_time, end_time)
            except (ValueError, TypeError, IndexError):
                pass
        
        # Parse unavailable dates
        if data.get('unavailable_dates') and isinstance(data['unavailable_dates'], list):
            unavailable = []
            for date_str in data['unavailable_dates']:
                try:
                    unavailable.append(datetime.fromisoformat(date_str))
                except (ValueError, TypeError):
                    pass
            preferences.unavailable_dates = unavailable
        
        # Simple field assignments
        preferences.service_type = data.get('service_type')
        preferences.estimated_duration = data.get('estimated_duration')
        preferences.location_preference = data.get('location_preference')
        preferences.detection_confidence = data.get('detection_confidence', 0.0)
        
        # Parse lists
        if data.get('available_days') and isinstance(data['available_days'], list):
            preferences.available_days = [day.lower() for day in data['available_days']]
        
        if data.get('special_requirements') and isinstance(data['special_requirements'], list):
            preferences.special_requirements = data['special_requirements']
        
        return preferences
    
    def _merge_preferences(
        self, 
        existing: SchedulingPreferences, 
        new: SchedulingPreferences
    ) -> SchedulingPreferences:
        """Merge new preferences with existing ones"""
        merged = SchedulingPreferences()
        
        # Use most recent intent
        merged.intent = new.intent if new.intent != SchedulingIntent.NONE else existing.intent
        
        # Merge extracted phrases
        merged.extracted_phrases = existing.extracted_phrases + new.extracted_phrases
        
        # For each field, prefer new data if available
        for field in ['preferred_date', 'preferred_time', 'service_type', 
                     'estimated_duration', 'location_preference']:
            new_value = getattr(new, field)
            existing_value = getattr(existing, field)
            setattr(merged, field, new_value if new_value is not None else existing_value)
        
        # Use new enum values if they're not default
        merged.time_preference = (new.time_preference if new.time_preference != TimePreference.FLEXIBLE 
                                 else existing.time_preference)
        merged.urgency = (new.urgency if new.urgency != UrgencyLevel.NORMAL 
                         else existing.urgency)
        
        # Merge lists
        merged.available_days = list(set(existing.available_days + new.available_days))
        merged.unavailable_dates = list(set(existing.unavailable_dates + new.unavailable_dates))
        merged.special_requirements = list(set(existing.special_requirements + new.special_requirements))
        
        # Use new time range if provided
        merged.preferred_time_range = new.preferred_time_range or existing.preferred_time_range
        
        # Use higher confidence
        merged.detection_confidence = max(existing.detection_confidence, new.detection_confidence)
        
        return merged
    
    def get_suggested_times(
        self, 
        preferences: SchedulingPreferences,
        available_slots: List[Tuple[datetime, datetime]]
    ) -> List[Tuple[datetime, datetime]]:
        """
        Filter and rank available time slots based on preferences
        
        Args:
            preferences: Scheduling preferences
            available_slots: List of (start_time, end_time) tuples
            
        Returns:
            Filtered and ranked time slots
        """
        if not available_slots:
            return []
        
        scored_slots = []
        
        for start_time, end_time in available_slots:
            score = self._score_time_slot(start_time, end_time, preferences)
            if score > 0:  # Only include viable slots
                scored_slots.append((start_time, end_time, score))
        
        # Sort by score (descending)
        scored_slots.sort(key=lambda x: x[2], reverse=True)
        
        # Return just the time slots (remove scores)
        return [(start, end) for start, end, score in scored_slots]
    
    def _score_time_slot(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        preferences: SchedulingPreferences
    ) -> float:
        """Score a time slot based on how well it matches preferences"""
        score = 1.0  # Base score
        
        # Check unavailable dates
        if any(start_time.date() == unavail.date() for unavail in preferences.unavailable_dates):
            return 0.0  # Completely unavailable
        
        # Check available days
        if preferences.available_days:
            weekday = start_time.strftime('%A').lower()
            if weekday not in preferences.available_days:
                score *= 0.3  # Heavily penalize unavailable days
        
        # Check preferred date
        if preferences.preferred_date:
            if start_time.date() == preferences.preferred_date.date():
                score *= 2.0  # Boost exact date match
            else:
                days_diff = abs((start_time.date() - preferences.preferred_date.date()).days)
                if days_diff <= 3:
                    score *= (1.5 - days_diff * 0.1)  # Slight boost for nearby dates
        
        # Check preferred time
        if preferences.preferred_time:
            time_diff = abs((start_time.time().hour * 60 + start_time.time().minute) - 
                           (preferences.preferred_time.hour * 60 + preferences.preferred_time.minute))
            if time_diff <= 30:  # Within 30 minutes
                score *= 2.0
            elif time_diff <= 120:  # Within 2 hours
                score *= 1.5
        
        # Check time preference
        hour = start_time.hour
        if preferences.time_preference == TimePreference.MORNING and 8 <= hour < 12:
            score *= 1.5
        elif preferences.time_preference == TimePreference.AFTERNOON and 12 <= hour < 17:
            score *= 1.5
        elif preferences.time_preference == TimePreference.EVENING and 17 <= hour < 20:
            score *= 1.5
        
        # Check preferred time range
        if preferences.preferred_time_range:
            start_minutes = preferences.preferred_time_range[0].hour * 60 + preferences.preferred_time_range[0].minute
            end_minutes = preferences.preferred_time_range[1].hour * 60 + preferences.preferred_time_range[1].minute
            slot_minutes = start_time.hour * 60 + start_time.minute
            
            if start_minutes <= slot_minutes <= end_minutes:
                score *= 1.8  # Within preferred range
        
        # Apply urgency scoring
        if preferences.urgency == UrgencyLevel.URGENT:
            # Prefer sooner slots for urgent requests
            days_out = (start_time.date() - datetime.now().date()).days
            if days_out == 0:
                score *= 3.0  # Today
            elif days_out <= 1:
                score *= 2.0  # Tomorrow
            elif days_out <= 3:
                score *= 1.5  # This week
        
        return score


# Service singleton
_scheduling_intent_service: Optional[SchedulingIntentService] = None


def get_scheduling_intent_service() -> SchedulingIntentService:
    """Get SchedulingIntentService singleton"""
    global _scheduling_intent_service
    if _scheduling_intent_service is None:
        _scheduling_intent_service = SchedulingIntentService()
    return _scheduling_intent_service