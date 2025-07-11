"""
Calendar Invitation Service
Handles sending email invitations, RSVP tracking, and calendar integration
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import quote
import uuid

from app.services.email_service import SendGridEmailService
from app.models import CalendarEvent, CalendarEventAttendee, User, Contact, Tenant
from app.core.config import settings

logger = logging.getLogger(__name__)

class CalendarInvitationService:
    """Service for sending calendar invitations and managing RSVPs"""
    
    def __init__(self):
        self.email_service = SendGridEmailService()
        self.base_url = settings.FRONTEND_URL or "https://dev.thanotopolis.com"
        
    def _load_template(self, template_name: str) -> str:
        """Load email template from file"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'templates', 
            template_name
        )
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Template not found: {template_path}")
            return ""
    
    def _format_event_date(self, start_time: datetime, end_time: datetime, all_day: bool = False) -> str:
        """Format event date for display"""
        if all_day:
            if start_time.date() == end_time.date():
                return start_time.strftime("%A, %B %d, %Y")
            else:
                return f"{start_time.strftime('%A, %B %d')} - {end_time.strftime('%A, %B %d, %Y')}"
        else:
            if start_time.date() == end_time.date():
                return start_time.strftime("%A, %B %d, %Y")
            else:
                return f"{start_time.strftime('%A, %B %d')} - {end_time.strftime('%A, %B %d, %Y')}"
    
    def _format_event_time(self, start_time: datetime, end_time: datetime, all_day: bool = False) -> str:
        """Format event time for display"""
        if all_day:
            return "All day"
        else:
            return f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
    
    def _generate_rsvp_urls(self, invitation_token: str) -> Dict[str, str]:
        """Generate RSVP URLs for different responses"""
        rsvp_base = f"{self.base_url}/rsvp/{invitation_token}"
        
        return {
            'rsvp_page_url': rsvp_base,
            'rsvp_accept_url': f"{rsvp_base}/respond?status=accepted",
            'rsvp_decline_url': f"{rsvp_base}/respond?status=declined",
            'rsvp_tentative_url': f"{rsvp_base}/respond?status=tentative"
        }
    
    def _generate_calendar_urls(self, event: CalendarEvent) -> Dict[str, str]:
        """Generate calendar integration URLs"""
        # URL encode event details
        title = quote(event.title)
        description = quote(event.description or "")
        location = quote(event.location or "")
        
        # Format dates for calendar URLs
        start_time = event.start_time.strftime("%Y%m%dT%H%M%SZ")
        end_time = event.end_time.strftime("%Y%m%dT%H%M%SZ")
        
        # Google Calendar URL
        google_url = (
            f"https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={title}"
            f"&dates={start_time}/{end_time}"
            f"&details={description}"
            f"&location={location}"
        )
        
        # Outlook Calendar URL
        outlook_url = (
            f"https://outlook.live.com/calendar/0/deeplink/compose"
            f"?subject={title}"
            f"&startdt={start_time}"
            f"&enddt={end_time}"
            f"&body={description}"
            f"&location={location}"
        )
        
        # ICS download URL (we'll implement this endpoint)
        ics_url = f"{self.base_url}/api/calendar/events/{event.id}/ics"
        
        return {
            'google_calendar_url': google_url,
            'outlook_calendar_url': outlook_url,
            'ics_download_url': ics_url
        }
    
    def _prepare_template_variables(self, 
                                  event: CalendarEvent, 
                                  attendee: CalendarEventAttendee,
                                  organizer: User,
                                  tenant: Tenant,
                                  custom_message: str = None) -> Dict[str, str]:
        """Prepare template variables for email rendering"""
        
        # Get RSVP URLs
        rsvp_urls = self._generate_rsvp_urls(attendee.invitation_token)
        
        # Get calendar URLs
        calendar_urls = self._generate_calendar_urls(event)
        
        # Calculate RSVP deadline (default to 1 day before event)
        rsvp_deadline = (event.start_time - timedelta(days=1)).strftime("%B %d, %Y")
        
        return {
            # Event details
            'event_title': event.title,
            'event_description': event.description or "",
            'event_date': self._format_event_date(event.start_time, event.end_time, event.all_day),
            'event_time': self._format_event_time(event.start_time, event.end_time, event.all_day),
            'event_location': event.location or "",
            
            # Organizer details
            'organizer_name': f"{organizer.first_name} {organizer.last_name}".strip(),
            'organizer_email': organizer.email,
            
            # Organization details
            'organization_name': tenant.name,
            
            # RSVP details
            'rsvp_deadline': rsvp_deadline,
            'custom_message': custom_message or "",
            
            # URLs
            **rsvp_urls,
            **calendar_urls,
            
            # Attendee details
            'attendee_name': attendee.attendee_name or "",
            'attendee_email': attendee.attendee_email or "",
        }
    
    async def send_invitation(self, 
                            event: CalendarEvent, 
                            attendee: CalendarEventAttendee,
                            organizer: User,
                            tenant: Tenant,
                            custom_message: str = None) -> bool:
        """Send email invitation to an attendee"""
        
        if not self.email_service.is_configured():
            logger.warning("Email service not configured, cannot send invitation")
            return False
        
        if not attendee.attendee_email:
            logger.warning(f"No email address for attendee {attendee.id}")
            return False
        
        try:
            # Prepare template variables
            template_vars = self._prepare_template_variables(
                event, attendee, organizer, tenant, custom_message
            )
            
            # Load and render templates
            html_template = self._load_template('calendar_invitation.html')
            text_template = self._load_template('calendar_invitation.txt')
            
            if not html_template or not text_template:
                logger.error("Failed to load invitation templates")
                return False
            
            # Render templates
            html_content = self.email_service.template_service.render_template(
                html_template, template_vars
            )
            text_content = self.email_service.template_service.render_template(
                text_template, template_vars
            )
            
            # Create subject
            subject = f"Invitation: {event.title} - {template_vars['event_date']}"
            
            # Send email
            success = await self.email_service.send_email(
                to_email=attendee.attendee_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_name=f"{organizer.first_name} {organizer.last_name}".strip(),
                tracking_id=str(attendee.id)  # Use attendee ID for tracking
            )
            
            if success:
                logger.info(f"Invitation sent successfully to {attendee.attendee_email}")
                return True
            else:
                logger.error(f"Failed to send invitation to {attendee.attendee_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending invitation: {str(e)}")
            return False
    
    async def send_rsvp_confirmation(self,
                                   event: CalendarEvent,
                                   attendee: CalendarEventAttendee,
                                   organizer: User,
                                   tenant: Tenant) -> bool:
        """Send RSVP confirmation email to attendee"""
        
        if not self.email_service.is_configured():
            logger.warning("Email service not configured, cannot send confirmation")
            return False
        
        if not attendee.attendee_email:
            logger.warning(f"No email address for attendee {attendee.id}")
            return False
        
        try:
            # Prepare template variables
            template_vars = self._prepare_template_variables(
                event, attendee, organizer, tenant
            )
            
            # Add RSVP-specific variables
            template_vars.update({
                'response_status': attendee.response_status,
                'responded_at': attendee.responded_at.strftime("%A, %B %d, %Y at %I:%M %p") if attendee.responded_at else ""
            })
            
            # Load template
            html_template = self._load_template('rsvp_confirmation.html')
            
            if not html_template:
                logger.error("Failed to load RSVP confirmation template")
                return False
            
            # Render template
            html_content = self.email_service.template_service.render_template(
                html_template, template_vars
            )
            
            # Create subject based on response
            response_text = {
                'accepted': 'confirmed your attendance',
                'declined': 'declined the invitation',
                'tentative': 'marked as tentative'
            }.get(attendee.response_status, 'updated your RSVP')
            
            subject = f"RSVP Confirmation: You {response_text} for {event.title}"
            
            # Send email
            success = await self.email_service.send_email(
                to_email=attendee.attendee_email,
                subject=subject,
                html_content=html_content,
                from_name=f"{organizer.first_name} {organizer.last_name}".strip(),
                tracking_id=f"{attendee.id}_confirmation"
            )
            
            if success:
                logger.info(f"RSVP confirmation sent to {attendee.attendee_email}")
                return True
            else:
                logger.error(f"Failed to send RSVP confirmation to {attendee.attendee_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending RSVP confirmation: {str(e)}")
            return False
    
    async def send_bulk_invitations(self,
                                  event: CalendarEvent,
                                  attendees: List[CalendarEventAttendee],
                                  organizer: User,
                                  tenant: Tenant,
                                  custom_message: str = None) -> Dict[str, int]:
        """Send invitations to multiple attendees"""
        
        results = {
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for attendee in attendees:
            if not attendee.attendee_email:
                results['skipped'] += 1
                continue
            
            success = await self.send_invitation(
                event, attendee, organizer, tenant, custom_message
            )
            
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"Bulk invitation results: {results}")
        return results
    
    def generate_ics_content(self, event: CalendarEvent, organizer: User) -> str:
        """Generate ICS calendar file content"""
        
        # Generate unique UID for this event
        uid = f"{event.id}@{settings.API_HOST}"
        
        # Format dates for ICS (UTC)
        start_time = event.start_time.strftime("%Y%m%dT%H%M%SZ")
        end_time = event.end_time.strftime("%Y%m%dT%H%M%SZ")
        created_time = event.created_at.strftime("%Y%m%dT%H%M%SZ")
        
        # Escape special characters in text fields
        def escape_ics_text(text: str) -> str:
            if not text:
                return ""
            return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
        
        title = escape_ics_text(event.title)
        description = escape_ics_text(event.description or "")
        location = escape_ics_text(event.location or "")
        organizer_name = escape_ics_text(f"{organizer.first_name} {organizer.last_name}".strip())
        
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Thanotopolis//Calendar//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
DTSTART:{start_time}
DTEND:{end_time}
DTSTAMP:{created_time}
ORGANIZER;CN={organizer_name}:mailto:{organizer.email}
SUMMARY:{title}
DESCRIPTION:{description}
LOCATION:{location}
STATUS:CONFIRMED
SEQUENCE:0
BEGIN:VALARM
TRIGGER:-PT15M
DESCRIPTION:Reminder
ACTION:DISPLAY
END:VALARM
END:VEVENT
END:VCALENDAR"""
        
        return ics_content.strip()


# Global instance
calendar_invitation_service = CalendarInvitationService()