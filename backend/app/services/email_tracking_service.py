"""
Email Tracking Service for CRM
Handles email campaign creation, tracking, and analytics
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
import uuid

from app.db.database import get_db
from app.models.models import (
    EmailCampaign, EmailRecipient, EmailEvent, EmailEventType,
    Contact, User, Tenant
)
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

class EmailTrackingService:
    """Service for managing email campaigns and tracking"""
    
    def __init__(self):
        self.email_service = email_service
    
    async def create_campaign(
        self,
        db: AsyncSession,
        tenant_id: str,
        name: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
        track_opens: bool = True,
        track_clicks: bool = True
    ) -> EmailCampaign:
        """Create a new email campaign"""
        
        campaign = EmailCampaign(
            tenant_id=tenant_id,
            name=name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            created_by_user_id=created_by_user_id,
            track_opens=track_opens,
            track_clicks=track_clicks,
            status="draft"
        )
        
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        
        logger.info(f"Created email campaign {campaign.id} for tenant {tenant_id}")
        return campaign
    
    async def add_recipients(
        self,
        db: AsyncSession,
        campaign_id: str,
        recipients: List[Dict[str, Any]]
    ) -> List[EmailRecipient]:
        """Add recipients to a campaign"""
        
        recipient_objects = []
        for recipient_data in recipients:
            tracking_id = str(uuid.uuid4())
            
            recipient = EmailRecipient(
                campaign_id=campaign_id,
                contact_id=recipient_data.get("contact_id"),
                email_address=recipient_data["email"],
                name=recipient_data.get("name"),
                tracking_id=tracking_id,
                status="pending"
            )
            
            recipient_objects.append(recipient)
            db.add(recipient)
        
        # Update campaign recipient count
        campaign = await db.get(EmailCampaign, campaign_id)
        if campaign:
            campaign.recipient_count = len(recipient_objects)
            campaign.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"Added {len(recipient_objects)} recipients to campaign {campaign_id}")
        return recipient_objects
    
    async def send_campaign(
        self,
        db: AsyncSession,
        campaign_id: str,
        template_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send an email campaign to all recipients"""
        
        # Get campaign with recipients
        stmt = select(EmailCampaign).options(
            selectinload(EmailCampaign.recipients)
        ).where(EmailCampaign.id == campaign_id)
        
        result = await db.execute(stmt)
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        if campaign.status != "draft":
            raise ValueError(f"Campaign {campaign_id} is not in draft status")
        
        # Update campaign status
        campaign.status = "sending"
        campaign.sent_at = datetime.now(timezone.utc)
        
        results = []
        successful_sends = 0
        failed_sends = 0
        
        for recipient in campaign.recipients:
            try:
                # Prepare template variables with recipient data
                variables = template_variables or {}
                variables.update({
                    "recipient_name": recipient.name,
                    "recipient_email": recipient.email_address
                })
                
                # Send email with tracking
                result = await self.email_service.send_template_email(
                    to_email=recipient.email_address,
                    subject_template=campaign.subject,
                    html_template=campaign.html_content,
                    template_variables=variables,
                    text_template=campaign.text_content,
                    to_name=recipient.name,
                    tracking_id=recipient.tracking_id,
                    track_opens=campaign.track_opens,
                    track_clicks=campaign.track_clicks
                )
                
                if result.get("success"):
                    recipient.status = "sent"
                    recipient.sent_at = datetime.now(timezone.utc)
                    recipient.sendgrid_message_id = result.get("message_id")
                    successful_sends += 1
                else:
                    recipient.status = "failed"
                    recipient.error_message = result.get("error", "Unknown error")
                    failed_sends += 1
                
                results.append({
                    "recipient_id": str(recipient.id),
                    "email": recipient.email_address,
                    "success": result.get("success", False),
                    "error": result.get("error")
                })
                
            except Exception as e:
                logger.error(f"Failed to send email to {recipient.email_address}: {str(e)}")
                recipient.status = "failed"
                recipient.error_message = str(e)
                failed_sends += 1
                
                results.append({
                    "recipient_id": str(recipient.id),
                    "email": recipient.email_address,
                    "success": False,
                    "error": str(e)
                })
        
        # Update campaign statistics
        campaign.sent_count = successful_sends
        campaign.status = "sent" if failed_sends == 0 else "partial"
        
        await db.commit()
        
        logger.info(f"Campaign {campaign_id} sent: {successful_sends} successful, {failed_sends} failed")
        
        return {
            "success": successful_sends > 0,
            "campaign_id": campaign_id,
            "total_recipients": len(campaign.recipients),
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "results": results
        }
    
    async def track_email_open(
        self,
        db: AsyncSession,
        tracking_id: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Track email open event"""
        
        # Find recipient by tracking ID
        stmt = select(EmailRecipient).where(EmailRecipient.tracking_id == tracking_id)
        result = await db.execute(stmt)
        recipient = result.scalar_one_or_none()
        
        if not recipient:
            logger.warning(f"No recipient found for tracking ID {tracking_id}")
            return False
        
        # Check if this is the first open
        is_first_open = recipient.first_opened_at is None
        
        # Update recipient open tracking
        now = datetime.now(timezone.utc)
        recipient.last_opened_at = now
        recipient.open_count += 1
        
        if is_first_open:
            recipient.first_opened_at = now
            recipient.opened_at = now
        
        # Create event record
        event = EmailEvent(
            recipient_id=recipient.id,
            event_type=EmailEventType.OPENED,
            timestamp=now,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        db.add(event)
        
        # Update campaign statistics if first open
        if is_first_open:
            campaign = await db.get(EmailCampaign, recipient.campaign_id)
            if campaign:
                campaign.opened_count += 1
        
        await db.commit()
        
        logger.info(f"Tracked email open for recipient {recipient.id} (first: {is_first_open})")
        return True
    
    async def track_email_click(
        self,
        db: AsyncSession,
        tracking_id: str,
        url: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[str]:
        """Track email click event and return original URL"""
        
        # Find recipient by tracking ID
        stmt = select(EmailRecipient).where(EmailRecipient.tracking_id == tracking_id)
        result = await db.execute(stmt)
        recipient = result.scalar_one_or_none()
        
        if not recipient:
            logger.warning(f"No recipient found for tracking ID {tracking_id}")
            return url
        
        # Check if this is the first click
        is_first_click = recipient.first_clicked_at is None
        
        # Update recipient click tracking
        now = datetime.now(timezone.utc)
        recipient.last_clicked_at = now
        recipient.click_count += 1
        
        if is_first_click:
            recipient.first_clicked_at = now
            recipient.clicked_at = now
        
        # Create event record
        event = EmailEvent(
            recipient_id=recipient.id,
            event_type=EmailEventType.CLICKED,
            timestamp=now,
            user_agent=user_agent,
            ip_address=ip_address,
            url=url
        )
        
        db.add(event)
        
        # Update campaign statistics if first click
        if is_first_click:
            campaign = await db.get(EmailCampaign, recipient.campaign_id)
            if campaign:
                campaign.clicked_count += 1
        
        await db.commit()
        
        logger.info(f"Tracked email click for recipient {recipient.id} to {url} (first: {is_first_click})")
        return url
    
    async def get_campaign_analytics(
        self,
        db: AsyncSession,
        campaign_id: str
    ) -> Dict[str, Any]:
        """Get analytics for a specific campaign"""
        
        # Get campaign with recipients
        stmt = select(EmailCampaign).options(
            selectinload(EmailCampaign.recipients).selectinload(EmailRecipient.events)
        ).where(EmailCampaign.id == campaign_id)
        
        result = await db.execute(stmt)
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # Calculate metrics
        total_recipients = len(campaign.recipients)
        sent_count = len([r for r in campaign.recipients if r.status == "sent"])
        opened_count = len([r for r in campaign.recipients if r.opened_at is not None])
        clicked_count = len([r for r in campaign.recipients if r.clicked_at is not None])
        bounced_count = len([r for r in campaign.recipients if r.status == "bounced"])
        
        # Calculate unsubscribe count by checking if contacts are now unsubscribed
        # We need to query the contacts table to see current unsubscribe status
        unsubscribed_count = 0
        if campaign.recipients:
            from app.models.models import Contact
            contact_ids = [r.contact_id for r in campaign.recipients if r.contact_id]
            if contact_ids:
                unsubscribed_contacts = await db.execute(
                    select(Contact.id).where(
                        and_(
                            Contact.id.in_(contact_ids),
                            Contact.is_unsubscribed == True
                        )
                    )
                )
                unsubscribed_count = len(unsubscribed_contacts.scalars().all())
        
        # Calculate rates
        open_rate = (opened_count / sent_count * 100) if sent_count > 0 else 0
        click_rate = (clicked_count / sent_count * 100) if sent_count > 0 else 0
        click_through_rate = (clicked_count / opened_count * 100) if opened_count > 0 else 0
        bounce_rate = (bounced_count / sent_count * 100) if sent_count > 0 else 0
        unsubscribe_rate = (unsubscribed_count / sent_count * 100) if sent_count > 0 else 0
        
        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "status": campaign.status,
            "created_at": campaign.created_at,
            "sent_at": campaign.sent_at,
            "metrics": {
                "total_recipients": total_recipients,
                "sent_count": sent_count,
                "opened_count": opened_count,
                "clicked_count": clicked_count,
                "bounced_count": bounced_count,
                "unsubscribed_count": unsubscribed_count,
                "open_rate": round(open_rate, 2),
                "click_rate": round(click_rate, 2),
                "click_through_rate": round(click_through_rate, 2),
                "bounce_rate": round(bounce_rate, 2),
                "unsubscribe_rate": round(unsubscribe_rate, 2)
            }
        }
    
    async def get_recipient_analytics(
        self,
        db: AsyncSession,
        recipient_id: str
    ) -> Dict[str, Any]:
        """Get analytics for a specific recipient"""
        
        # Get recipient with events
        stmt = select(EmailRecipient).options(
            selectinload(EmailRecipient.events),
            selectinload(EmailRecipient.contact)
        ).where(EmailRecipient.id == recipient_id)
        
        result = await db.execute(stmt)
        recipient = result.scalar_one_or_none()
        
        if not recipient:
            raise ValueError(f"Recipient {recipient_id} not found")
        
        # Get event timeline
        events = []
        for event in recipient.events:
            events.append({
                "event_type": event.event_type.value,
                "timestamp": event.timestamp,
                "user_agent": event.user_agent,
                "ip_address": event.ip_address,
                "url": event.url
            })
        
        return {
            "recipient_id": recipient_id,
            "email": recipient.email_address,
            "name": recipient.name,
            "contact_id": recipient.contact_id,
            "status": recipient.status,
            "sent_at": recipient.sent_at,
            "opened_at": recipient.opened_at,
            "clicked_at": recipient.clicked_at,
            "open_count": recipient.open_count,
            "click_count": recipient.click_count,
            "events": events
        }

# Global email tracking service instance
email_tracking_service = EmailTrackingService()