#!/usr/bin/env python3
"""
Debug bulk email campaign creation
"""

import sys
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

# Add the backend directory to the Python path
sys.path.insert(0, '/home/peter/thanotopolis/backend')

from app.models.models import EmailCampaign, EmailRecipient, Tenant, User, EmailTemplate, Contact
from app.db.database import get_db
from sqlalchemy import select

async def debug_bulk_email():
    """Debug bulk email campaign creation"""
    
    # Get a database session
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Get first tenant
        tenant = await db.scalar(select(Tenant).limit(1))
        if not tenant:
            print("No tenant found")
            return
            
        print(f"Using tenant: {tenant.name}")
        
        # Get first user for that tenant
        user = await db.scalar(select(User).where(User.tenant_id == tenant.id).limit(1))
        if not user:
            print("No user found for tenant")
            return
            
        print(f"Using user: {user.email}")
        
        # Create a test campaign
        campaign = EmailCampaign(
            tenant_id=tenant.id,
            name="Test Campaign",
            subject="Test Subject",
            html_content="<p>Test content</p>",
            text_content="Test content",
            status="sending",
            recipient_count=1,
            track_opens=True,
            track_clicks=True,
            created_by_user_id=user.id,
            sent_at=datetime.now(timezone.utc)
        )
        
        print("Adding campaign to database...")
        db.add(campaign)
        
        print("Committing campaign...")
        await db.commit()
        
        print("Refreshing campaign...")
        await db.refresh(campaign)
        
        print(f"Campaign created with ID: {campaign.id}")
        
        # Check if it's actually in the database
        check_campaign = await db.scalar(select(EmailCampaign).where(EmailCampaign.id == campaign.id))
        if check_campaign:
            print("✅ Campaign found in database after commit!")
            print(f"   Name: {check_campaign.name}")
            print(f"   Status: {check_campaign.status}")
            print(f"   Created: {check_campaign.created_at}")
        else:
            print("❌ Campaign NOT found in database after commit!")
            
        # Now check all campaigns in the database
        all_campaigns = await db.execute(select(EmailCampaign))
        campaigns = all_campaigns.scalars().all()
        print(f"Total campaigns in database: {len(campaigns)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(debug_bulk_email())