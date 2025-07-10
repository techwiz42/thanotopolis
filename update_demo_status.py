#!/usr/bin/env python3
"""
Update demo status for organizations that should be exempt from billing.
Run this on PRODUCTION database to mark demo and cyberiad as demo accounts.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent / "backend"))

from app.db.database import get_db_context
from app.models.models import Tenant
from sqlalchemy import select

async def update_demo_status():
    """Mark demo and cyberiad organizations as demo accounts"""
    
    async with get_db_context() as db:
        # Find organizations that should be demo
        demo_names = ["demo", "cyberiad"]
        
        for name in demo_names:
            # Query for tenant by name (case insensitive)
            result = await db.execute(
                select(Tenant).where(Tenant.name.ilike(f"%{name}%"))
            )
            tenants = result.scalars().all()
            
            print(f"\nSearching for organizations containing '{name}':")
            for tenant in tenants:
                print(f"  Found: {tenant.name} (ID: {tenant.id}) - is_demo: {tenant.is_demo}")
                
                if not tenant.is_demo:
                    tenant.is_demo = True
                    print(f"  ✅ Updated {tenant.name} to is_demo=True")
                else:
                    print(f"  ℹ️  {tenant.name} already marked as demo")
        
        # Commit changes
        await db.commit()
        print(f"\n✅ Demo status update completed!")
        
        # Show all demo accounts
        print(f"\nAll demo accounts:")
        result = await db.execute(select(Tenant).where(Tenant.is_demo == True))
        demo_tenants = result.scalars().all()
        
        for tenant in demo_tenants:
            print(f"  - {tenant.name} (ID: {tenant.id}) - EXEMPT from billing")

if __name__ == "__main__":
    print("🔧 Updating demo status for billing exemption...")
    print("This will mark 'demo' and 'cyberiad' organizations as demo accounts.")
    print("Demo accounts are exempt from all billing charges.")
    print("")
    
    response = input("Continue? (y/N): ").lower().strip()
    if response == 'y':
        asyncio.run(update_demo_status())
    else:
        print("Cancelled.")