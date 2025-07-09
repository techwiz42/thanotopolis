#!/usr/bin/env python3
"""
Check users and their roles/tenants
"""

import sys
import os
import asyncio

# Add the backend directory to the Python path
sys.path.insert(0, '/home/peter/thanotopolis/backend')

from app.models.models import User, Tenant
from app.db.database import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def check_users():
    """Check users and their roles/tenants"""
    
    # Get a database session
    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    
    try:
        # Get all users
        users_result = await db.execute(select(User))
        users = users_result.scalars().all()
        
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"\n=== User: {user.email} ===")
            print(f"  Name: {user.first_name} {user.last_name}")
            print(f"  Role: {user.role}")
            print(f"  Tenant ID: {user.tenant_id}")
            print(f"  Active: {user.is_active}")
            print(f"  Created: {user.created_at}")
            
            # Get tenant info
            if user.tenant_id:
                tenant = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id))
                if tenant:
                    print(f"  Tenant: {tenant.name}")
                else:
                    print(f"  Tenant: NOT FOUND (ID: {user.tenant_id})")
            else:
                print(f"  Tenant: None")
        
    except Exception as e:
        print(f"Error during check: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_users())