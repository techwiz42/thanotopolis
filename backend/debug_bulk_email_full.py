#!/usr/bin/env python3
"""
Debug the full bulk email flow to find where it's breaking
"""

import sys
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

# Add the backend directory to the Python path
sys.path.insert(0, '/home/peter/thanotopolis/backend')

from app.models.models import EmailCampaign, EmailRecipient, Tenant, User, EmailTemplate, Contact, ContactInteraction
from app.db.database import get_db
from sqlalchemy import select, and_

async def debug_bulk_email_full():
    """Debug the full bulk email flow"""
    
    # Get a database session
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Get Cyberiad A.I. tenant
        tenant = await db.scalar(select(Tenant).where(Tenant.name == "Cyberiad A.I."))
        if not tenant:
            print("Cyberiad A.I. tenant not found")
            return
            
        print(f"Using tenant: {tenant.name}")
        
        # Get first user for that tenant
        user = await db.scalar(select(User).where(User.tenant_id == tenant.id).limit(1))
        if not user:
            print("No user found for tenant")
            return
            
        print(f"Using user: {user.email}")
        
        # Get email template
        template = await db.scalar(select(EmailTemplate).where(EmailTemplate.tenant_id == tenant.id).limit(1))
        if not template:
            print("No template found")
            return
            
        print(f"Using template: {template.name}")
        
        # Get contacts with email
        contacts = await db.execute(
            select(Contact).where(
                and_(
                    Contact.tenant_id == tenant.id,
                    Contact.contact_email.is_not(None),
                    Contact.contact_email != ""
                )
            )
        )
        contacts_list = contacts.scalars().all()
        
        if not contacts_list:
            print("No contacts with email found")
            return
            
        print(f"Found {len(contacts_list)} contacts with email")
        for contact in contacts_list:
            print(f"  - {contact.contact_name} ({contact.contact_email})")
        
        # Simulate the bulk email process
        print("\\nSimulating bulk email process...")
        
        # Step 1: Create campaign
        campaign = EmailCampaign(
            tenant_id=tenant.id,
            name=f"Bulk Email: {template.name}",
            subject=template.subject,
            html_content=template.html_content,
            text_content=template.text_content,
            status="sending",
            recipient_count=len(contacts_list),
            track_opens=True,
            track_clicks=True,
            created_by_user_id=user.id,
            sent_at=datetime.now(timezone.utc)
        )
        
        print("1. Adding campaign to database...")
        db.add(campaign)
        
        print("2. Committing campaign...")
        await db.commit()
        
        print("3. Refreshing campaign...")
        await db.refresh(campaign)
        
        print(f"4. Campaign created with ID: {campaign.id}")
        
        # Step 2: Create recipients
        print("\\n5. Creating recipients...")
        for i, contact in enumerate(contacts_list):
            tracking_id = str(uuid4())
            
            recipient = EmailRecipient(
                campaign_id=campaign.id,
                contact_id=contact.id,
                email_address=contact.contact_email,
                name=contact.contact_name,
                tracking_id=tracking_id,
                status="pending"
            )
            db.add(recipient)
            print(f"   Added recipient {i+1}: {contact.contact_name}")
            
            # Simulate successful send
            recipient.status = "sent"
            recipient.sent_at = datetime.now(timezone.utc)
            
            # Create interaction
            interaction = ContactInteraction(
                contact_id=contact.id,
                user_id=user.id,
                interaction_type="email",
                subject=f"Bulk Email: {template.subject}",
                content=f"Sent email using template '{template.name}'",
                interaction_date=datetime.now(timezone.utc),
                metadata={
                    "template_id": str(template.id), 
                    "bulk_email": True,
                    "tracking_id": tracking_id,
                    "campaign_id": str(campaign.id)
                }
            )
            db.add(interaction)
            print(f"   Added interaction for {contact.contact_name}")
        
        # Step 3: Update campaign statistics
        print("\\n6. Updating campaign statistics...")
        campaign.sent_count = len(contacts_list)
        campaign.status = "sent"
        
        # Step 4: Final commit
        print("7. Final commit...")
        await db.commit()
        
        print("\\n8. Verifying campaign is in database...")
        check_campaign = await db.scalar(select(EmailCampaign).where(EmailCampaign.id == campaign.id))
        if check_campaign:
            print("✅ Campaign found in database after final commit!")
            print(f"   Name: {check_campaign.name}")
            print(f"   Status: {check_campaign.status}")
            print(f"   Sent Count: {check_campaign.sent_count}")
        else:
            print("❌ Campaign NOT found in database after final commit!")
            
        # Check recipients
        recipients = await db.execute(select(EmailRecipient).where(EmailRecipient.campaign_id == campaign.id))
        recipients_list = recipients.scalars().all()
        print(f"   Recipients in DB: {len(recipients_list)}")
        
        # Check interactions
        interactions = await db.execute(select(ContactInteraction).where(ContactInteraction.metadata["campaign_id"].astext == str(campaign.id)))
        interactions_list = interactions.scalars().all()
        print(f"   Interactions in DB: {len(interactions_list)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(debug_bulk_email_full())