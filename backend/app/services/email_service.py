"""
SendGrid Email Service with Template Support and Open Tracking
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import uuid
from jinja2 import Template, Environment, BaseLoader
import sendgrid
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent, HtmlContent, Personalization
from sendgrid import SendGridAPIClient

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailTemplateService:
    """Service for managing email templates with variable substitution"""
    
    def __init__(self):
        self.jinja_env = Environment(loader=BaseLoader())
    
    def extract_variables(self, template_content: str) -> List[str]:
        """Extract template variables from template content"""
        # Find all Jinja2 variables {{ variable_name }}
        pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
        variables = re.findall(pattern, template_content)
        return list(set(variables))  # Remove duplicates
    
    def render_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Render template with provided variables"""
        try:
            template = self.jinja_env.from_string(template_content)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Template rendering error: {str(e)}")
            raise ValueError(f"Template rendering failed: {str(e)}")
    
    def validate_template(self, template_content: str) -> bool:
        """Validate template syntax"""
        try:
            self.jinja_env.from_string(template_content)
            return True
        except Exception as e:
            logger.error(f"Template validation error: {str(e)}")
            return False

class SendGridEmailService:
    """SendGrid email service with template support"""
    
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY not found in environment variables")
            self.client = None
        else:
            self.client = SendGridAPIClient(api_key=self.api_key)
        
        self.template_service = EmailTemplateService()
        self.from_email = 'pete@cyberiad.ai'  # Verified SendGrid sender
        self.from_name = 'Thanotopolis CRM'
    
    def is_configured(self) -> bool:
        """Check if SendGrid is properly configured"""
        return self.client is not None
    
    def generate_tracking_pixel(self, tracking_id: str) -> str:
        """Generate tracking pixel HTML for email open tracking"""
        # Use API_URL if available, otherwise construct from host/port
        if settings.API_URL:
            # API_URL should already include the /api prefix
            backend_url = settings.API_URL.rstrip('/')
            tracking_url = f"{backend_url}/crm/email-tracking/open/{tracking_id}"
        else:
            backend_url = f"http://{settings.API_HOST}:{settings.API_PORT}"
            tracking_url = f"{backend_url}/api/crm/email-tracking/open/{tracking_id}"
        return f'<img src="{tracking_url}" width="1" height="1" style="display: none;" alt="" />'
    
    def inject_tracking_pixel(self, html_content: str, tracking_id: str) -> str:
        """Inject tracking pixel into HTML content"""
        tracking_pixel = self.generate_tracking_pixel(tracking_id)
        
        # Try to inject before closing body tag
        if "</body>" in html_content:
            return html_content.replace("</body>", f"{tracking_pixel}</body>")
        else:
            # If no body tag, append to end
            return f"{html_content}{tracking_pixel}"
    
    def inject_click_tracking(self, html_content: str, tracking_id: str) -> str:
        """Inject click tracking into all links in HTML content"""
        if not tracking_id:
            return html_content
            
        # Find all href attributes and wrap them with tracking
        import re
        
        def replace_link(match):
            original_url = match.group(1)
            # Skip tracking pixel URLs and mailto links
            if "email-tracking/open" in original_url or original_url.startswith("mailto:"):
                return match.group(0)
            
            if settings.API_URL:
                # API_URL should already include the /api prefix
                backend_url = settings.API_URL.rstrip('/')
                tracking_url = f"{backend_url}/crm/email-tracking/click/{tracking_id}?url={original_url}"
            else:
                backend_url = f"http://{settings.API_HOST}:{settings.API_PORT}"
                tracking_url = f"{backend_url}/api/crm/email-tracking/click/{tracking_id}?url={original_url}"
            return f'href="{tracking_url}"'
        
        # Replace all href attributes
        pattern = r'href="([^"]*)"'
        return re.sub(pattern, replace_link, html_content)
    
    def inject_unsubscribe_link(self, html_content: str, contact_id: str) -> str:
        """Inject unsubscribe link into HTML content"""
        if not contact_id:
            return html_content
            
        # Build unsubscribe URL
        backend_url = settings.API_URL or f"http://{settings.API_HOST}:{settings.API_PORT}"
        if settings.API_URL:
            backend_url = settings.API_URL.rstrip('/')
            unsubscribe_url = f"{backend_url}/crm/unsubscribe/{contact_id}"
        else:
            unsubscribe_url = f"{backend_url}/api/crm/unsubscribe/{contact_id}"
        
        # Create unsubscribe footer
        unsubscribe_footer = f'''
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 12px; text-align: center;">
            <p>If you no longer wish to receive these emails, you can <a href="{unsubscribe_url}" style="color: #666; text-decoration: underline;">unsubscribe here</a>.</p>
        </div>
        '''
        
        # Try to inject before closing body tag
        if "</body>" in html_content:
            return html_content.replace("</body>", f"{unsubscribe_footer}</body>")
        else:
            # If no body tag, append to end
            return f"{html_content}{unsubscribe_footer}"
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        to_name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        tracking_id: Optional[str] = None,
        track_opens: bool = True,
        track_clicks: bool = True
    ) -> Dict[str, Any]:
        """Send a single email"""
        
        if not self.is_configured():
            raise ValueError("SendGrid is not configured. Please set SENDGRID_API_KEY.")
        
        try:
            # Inject tracking if enabled
            processed_html = html_content
            if tracking_id:
                if track_opens:
                    processed_html = self.inject_tracking_pixel(processed_html, tracking_id)
                if track_clicks:
                    processed_html = self.inject_click_tracking(processed_html, tracking_id)
            
            # Create mail object
            mail = Mail()
            
            # Set from
            mail.from_email = From(
                email=from_email or self.from_email,
                name=from_name or self.from_name
            )
            
            # Set to
            mail.to = To(email=to_email, name=to_name)
            
            # Set subject
            mail.subject = Subject(subject)
            
            # Set content
            mail.content = [
                PlainTextContent(text_content or self._html_to_text(html_content)),
                HtmlContent(processed_html)
            ]
            
            # Send email
            response = self.client.send(mail)
            
            logger.info(f"Email sent successfully to {to_email}. Status: {response.status_code}")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get('X-Message-Id'),
                "to_email": to_email,
                "subject": subject,
                "tracking_id": tracking_id
            }
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "to_email": to_email,
                "subject": subject
            }
    
    async def send_template_email(
        self,
        to_email: str,
        subject_template: str,
        html_template: str,
        template_variables: Dict[str, Any],
        text_template: Optional[str] = None,
        to_name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        tracking_id: Optional[str] = None,
        track_opens: bool = True,
        track_clicks: bool = True,
        contact_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email using templates with variable substitution"""
        
        try:
            # Render templates
            rendered_subject = self.template_service.render_template(subject_template, template_variables)
            rendered_html = self.template_service.render_template(html_template, template_variables)
            rendered_text = None
            
            if text_template:
                rendered_text = self.template_service.render_template(text_template, template_variables)
            
            # Inject unsubscribe link into HTML content
            if contact_id:
                rendered_html = self.inject_unsubscribe_link(rendered_html, contact_id)
            
            # Send email
            return await self.send_email(
                to_email=to_email,
                subject=rendered_subject,
                html_content=rendered_html,
                text_content=rendered_text,
                to_name=to_name,
                from_email=from_email,
                from_name=from_name,
                tracking_id=tracking_id,
                track_opens=track_opens,
                track_clicks=track_clicks
            )
            
        except Exception as e:
            logger.error(f"Failed to send template email to {to_email}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "to_email": to_email,
                "subject": subject_template
            }
    
    async def send_bulk_emails(
        self,
        recipients: List[Dict[str, str]],  # [{"email": "...", "name": "..."}]
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send bulk emails to multiple recipients"""
        
        if not self.is_configured():
            raise ValueError("SendGrid is not configured. Please set SENDGRID_API_KEY.")
        
        if not recipients:
            return {
                "success": False,
                "error": "No recipients provided",
                "total_recipients": 0,
                "successful_sends": 0,
                "failed_sends": 0
            }
        
        # Limit to 1000 recipients per batch (SendGrid limit)
        if len(recipients) > 1000:
            logger.warning(f"Bulk email batch size ({len(recipients)}) exceeds limit. Truncating to 1000.")
            recipients = recipients[:1000]
        
        try:
            mail = Mail()
            
            # Set from
            mail.from_email = From(
                email=from_email or self.from_email,
                name=from_name or self.from_name
            )
            
            # Set subject
            mail.subject = Subject(subject)
            
            # Set content
            mail.content = [
                PlainTextContent(text_content or self._html_to_text(html_content)),
                HtmlContent(html_content)
            ]
            
            # Add all recipients in a single personalization
            personalization = Personalization()
            for recipient in recipients:
                personalization.add_to(To(
                    email=recipient["email"],
                    name=recipient.get("name")
                ))
            
            mail.personalization = [personalization]
            
            # Send email
            response = self.client.send(mail)
            
            logger.info(f"Bulk email sent to {len(recipients)} recipients. Status: {response.status_code}")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get('X-Message-Id'),
                "total_recipients": len(recipients),
                "successful_sends": len(recipients),
                "failed_sends": 0,
                "subject": subject
            }
            
        except Exception as e:
            logger.error(f"Failed to send bulk email: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_recipients": len(recipients),
                "successful_sends": 0,
                "failed_sends": len(recipients),
                "subject": subject
            }
    
    async def send_bulk_template_emails(
        self,
        recipients: List[Dict[str, Any]],  # [{"email": "...", "name": "...", "variables": {...}}]
        subject_template: str,
        html_template: str,
        text_template: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send bulk emails with personalized templates"""
        
        if not recipients:
            return {
                "success": False,
                "error": "No recipients provided",
                "total_recipients": 0,
                "successful_sends": 0,
                "failed_sends": 0
            }
        
        results = []
        successful_sends = 0
        failed_sends = 0
        
        for recipient in recipients:
            email = recipient.get("email")
            name = recipient.get("name")
            variables = recipient.get("variables", {})
            
            if not email:
                failed_sends += 1
                results.append({
                    "email": email,
                    "success": False,
                    "error": "No email address provided"
                })
                continue
            
            # Send individual template email
            result = await self.send_template_email(
                to_email=email,
                subject_template=subject_template,
                html_template=html_template,
                template_variables=variables,
                text_template=text_template,
                to_name=name,
                from_email=from_email,
                from_name=from_name
            )
            
            results.append(result)
            
            if result.get("success"):
                successful_sends += 1
            else:
                failed_sends += 1
        
        return {
            "success": successful_sends > 0,
            "total_recipients": len(recipients),
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "results": results
        }
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        # Basic HTML to text conversion
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Replace HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

# Default email templates
DEFAULT_TEMPLATES = {
    "contact_welcome": {
        "name": "Contact Welcome",
        "subject": "Welcome to {{ organization_name }}!",
        "html_content": """
        <html>
        <body>
            <h2>Welcome {{ contact_name }}!</h2>
            <p>Thank you for your interest in {{ organization_name }}. We're excited to work with {{ business_name }}.</p>
            <p>Your contact information:</p>
            <ul>
                <li><strong>Business:</strong> {{ business_name }}</li>
                <li><strong>Role:</strong> {{ contact_role }}</li>
                <li><strong>Email:</strong> {{ contact_email }}</li>
                {% if phone %}<li><strong>Phone:</strong> {{ phone }}</li>{% endif %}
            </ul>
            <p>We'll be in touch soon!</p>
            <p>Best regards,<br>{{ organization_name }} Team</p>
        </body>
        </html>
        """,
        "text_content": """
        Welcome {{ contact_name }}!
        
        Thank you for your interest in {{ organization_name }}. We're excited to work with {{ business_name }}.
        
        Your contact information:
        - Business: {{ business_name }}
        - Role: {{ contact_role }}
        - Email: {{ contact_email }}
        {% if phone %}- Phone: {{ phone }}{% endif %}
        
        We'll be in touch soon!
        
        Best regards,
        {{ organization_name }} Team
        """,
        "variables": ["contact_name", "organization_name", "business_name", "contact_role", "contact_email", "phone"]
    },
    "follow_up": {
        "name": "Follow Up",
        "subject": "Following up on our conversation - {{ business_name }}",
        "html_content": """
        <html>
        <body>
            <h2>Hi {{ contact_name }},</h2>
            <p>I wanted to follow up on our recent conversation about {{ subject }}.</p>
            {% if notes %}
            <p><strong>Notes from our conversation:</strong></p>
            <p>{{ notes }}</p>
            {% endif %}
            <p>{{ message }}</p>
            <p>Please let me know if you have any questions or would like to schedule another call.</p>
            <p>Best regards,<br>{{ sender_name }}<br>{{ organization_name }}</p>
        </body>
        </html>
        """,
        "text_content": """
        Hi {{ contact_name }},
        
        I wanted to follow up on our recent conversation about {{ subject }}.
        
        {% if notes %}Notes from our conversation:
        {{ notes }}
        {% endif %}
        
        {{ message }}
        
        Please let me know if you have any questions or would like to schedule another call.
        
        Best regards,
        {{ sender_name }}
        {{ organization_name }}
        """,
        "variables": ["contact_name", "business_name", "subject", "notes", "message", "sender_name", "organization_name"]
    },
    "invoice_reminder": {
        "name": "Invoice Reminder",
        "subject": "Invoice Reminder - {{ business_name }}",
        "html_content": """
        <html>
        <body>
            <h2>Invoice Reminder</h2>
            <p>Dear {{ contact_name }},</p>
            <p>This is a friendly reminder that invoice #{{ invoice_number }} for {{ business_name }} is due on {{ due_date }}.</p>
            <p><strong>Amount Due:</strong> ${{ amount_due }}</p>
            {% if payment_link %}
            <p><a href="{{ payment_link }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Pay Invoice</a></p>
            {% endif %}
            <p>If you have already paid this invoice, please disregard this message.</p>
            <p>Thank you,<br>{{ organization_name }} Billing Team</p>
        </body>
        </html>
        """,
        "text_content": """
        Invoice Reminder
        
        Dear {{ contact_name }},
        
        This is a friendly reminder that invoice #{{ invoice_number }} for {{ business_name }} is due on {{ due_date }}.
        
        Amount Due: ${{ amount_due }}
        
        {% if payment_link %}Pay online: {{ payment_link }}{% endif %}
        
        If you have already paid this invoice, please disregard this message.
        
        Thank you,
        {{ organization_name }} Billing Team
        """,
        "variables": ["contact_name", "business_name", "invoice_number", "due_date", "amount_due", "payment_link", "organization_name"]
    }
}

# Global email service instance
email_service = SendGridEmailService()