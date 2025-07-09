#!/usr/bin/env python3
"""
Check existing campaigns in the database
"""

import sys
import os
import asyncio
from datetime import datetime, timezone

# Add the backend directory to the Python path
sys.path.insert(0, '/home/peter/thanotopolis/backend')

from app.models.models import EmailCampaign, EmailRecipient, Tenant, User, EmailTemplate, Contact
from app.db.database import get_db
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

async def check_campaigns():
    """Check existing campaigns in the database"""
    
    # Get a database session
    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    
    try:
        # Get all tenants
        tenants_result = await db.execute(select(Tenant))
        tenants = tenants_result.scalars().all()
        
        print(f"Found {len(tenants)} tenants:")
        for tenant in tenants:
            print(f"\n=== Tenant: {tenant.name} (ID: {tenant.id}) ===")
            
            # Get campaigns for this tenant
            campaigns_result = await db.execute(
                select(EmailCampaign).where(EmailCampaign.tenant_id == tenant.id)
            )
            campaigns = campaigns_result.scalars().all()
            
            print(f"Campaigns: {len(campaigns)}")
            for campaign in campaigns:
                print(f"  - {campaign.name} (Status: {campaign.status})")
                print(f"    Recipients: {campaign.recipient_count}, Sent: {campaign.sent_count}")
                print(f"    Created: {campaign.created_at}")
                print(f"    Sent At: {campaign.sent_at}")
                
                # Check recipients
                recipients_result = await db.execute(
                    select(EmailRecipient).where(EmailRecipient.campaign_id == campaign.id)
                )
                recipients = recipients_result.scalars().all()
                print(f"    Recipients in DB: {len(recipients)}")
                
                print()
            
            # Check email templates
            templates_result = await db.execute(
                select(EmailTemplate).where(EmailTemplate.tenant_id == tenant.id)
            )
            templates = templates_result.scalars().all()
            print(f"Email Templates: {len(templates)}")
            for template in templates:
                print(f"  - {template.name}")
            
            # Check contacts
            contacts_result = await db.execute(
                select(Contact).where(Contact.tenant_id == tenant.id)
            )
            contacts = contacts_result.scalars().all()
            print(f"Contacts: {len(contacts)}")
            
            print()
        
    except Exception as e:
        print(f"Error during check: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_campaigns())