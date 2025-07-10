#!/usr/bin/env python3
"""
Check current billing exemption status for organizations.
This script shows which organizations are marked as demo and exempt from billing.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent / "backend"))

from app.db.database import get_db_context
from app.models.models import Tenant
from sqlalchemy import select

async def check_exemptions():
    """Check current demo status of all organizations"""
    
    async with get_db_context() as db:
        # Get all tenants
        result = await db.execute(select(Tenant).order_by(Tenant.name))
        tenants = result.scalars().all()
        
        print("🏢 All Organizations in Database:")
        print("=" * 50)
        
        demo_count = 0
        billing_count = 0
        
        for tenant in tenants:
            status = "✅ EXEMPT (Demo)" if tenant.is_demo else "💰 BILLING ACTIVE"
            print(f"  {tenant.name:20} - {status}")
            
            if tenant.is_demo:
                demo_count += 1
            else:
                billing_count += 1
        
        print("=" * 50)
        print(f"📊 Summary:")
        print(f"  Demo Accounts (Exempt): {demo_count}")
        print(f"  Billing Accounts: {billing_count}")
        print(f"  Total Organizations: {demo_count + billing_count}")
        
        print(f"\n🎯 Organizations that should be exempt:")
        should_be_demo = ["demo", "cyberiad"]
        
        for name in should_be_demo:
            found = False
            for tenant in tenants:
                if name.lower() in tenant.name.lower():
                    found = True
                    status = "✅ Already exempt" if tenant.is_demo else "❌ NEEDS UPDATE"
                    print(f"  {tenant.name} - {status}")
            
            if not found:
                print(f"  {name} - ⚠️  NOT FOUND in database")

if __name__ == "__main__":
    print("🔍 Checking billing exemption status...\n")
    asyncio.run(check_exemptions())