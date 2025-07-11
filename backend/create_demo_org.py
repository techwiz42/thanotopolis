#!/usr/bin/env python3
"""
Script to create demo organization and user if they don't exist.
Creates organization 'demo' with user demo@example.com / password demo123
"""

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from passlib.context import CryptContext
import uuid
from datetime import datetime, timezone

# Add the project root to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import Tenant, User
from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_demo_org_and_user():
    """Create demo organization and user if they don't exist"""
    
    # Use the imported settings instance
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    
    # Create async session
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db:
        try:
            print("🔍 Checking for existing demo organization...")
            
            # Check if demo organization exists
            demo_org_query = select(Tenant).where(Tenant.name == 'demo')
            result = await db.execute(demo_org_query)
            demo_org = result.scalar_one_or_none()
            
            if demo_org:
                print(f"✅ Demo organization already exists: {demo_org.name} (ID: {demo_org.id})")
            else:
                print("🏗️ Creating demo organization...")
                
                # Create demo organization
                demo_org = Tenant(
                    id=str(uuid.uuid4()),
                    name='demo',
                    subdomain='demo',
                    is_active=True,
                    is_demo=True,  # Mark as demo for billing exemption
                    description='Demo organization for testing'
                )
                
                db.add(demo_org)
                await db.flush()  # Get the ID
                print(f"✅ Created demo organization: {demo_org.name} (ID: {demo_org.id})")
            
            print("🔍 Checking for existing demo user...")
            
            # Check if demo user exists
            demo_user_query = select(User).where(User.email == 'demo@example.com')
            result = await db.execute(demo_user_query)
            demo_user = result.scalar_one_or_none()
            
            if demo_user:
                print(f"✅ Demo user already exists: {demo_user.email} (ID: {demo_user.id})")
                
                # Ensure user is linked to demo organization
                if demo_user.tenant_id != demo_org.id:
                    print(f"🔄 Updating demo user tenant_id to demo organization...")
                    demo_user.tenant_id = demo_org.id
                    await db.flush()
                    print(f"✅ Updated demo user tenant assignment")
            else:
                print("👤 Creating demo user...")
                
                # Hash the password
                hashed_password = pwd_context.hash('demo123')
                
                # Create demo user
                demo_user = User(
                    id=str(uuid.uuid4()),
                    email='demo@example.com',
                    username='demo',
                    hashed_password=hashed_password,
                    first_name='Demo',
                    last_name='User',
                    role='member',  # Ordinary user role
                    is_active=True,
                    tenant_id=demo_org.id
                )
                
                db.add(demo_user)
                await db.flush()
                print(f"✅ Created demo user: {demo_user.email} (ID: {demo_user.id})")
            
            # Commit all changes
            await db.commit()
            
            print("\n🎉 Demo organization and user setup complete!")
            print("📋 Demo credentials:")
            print(f"   Organization: {demo_org.name}")
            print(f"   Email: demo@example.com")
            print(f"   Password: demo123")
            print(f"   Role: admin")
            print(f"   Access URL: https://dev.thanotopolis.com")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating demo organization/user: {e}")
            await db.rollback()
            return False
        
        finally:
            await engine.dispose()

if __name__ == "__main__":
    print("🚀 Starting demo organization and user creation...")
    success = asyncio.run(create_demo_org_and_user())
    
    if success:
        print("✅ Demo setup completed successfully!")
        sys.exit(0)
    else:
        print("❌ Demo setup failed!")
        sys.exit(1)