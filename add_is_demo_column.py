#!/usr/bin/env python3
"""
Add is_demo column to tenants table in DEV database only.
This is a direct database update for development environment.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent / "backend"))

from app.db.database import engine
from sqlalchemy import text

async def add_is_demo_column():
    """Add is_demo column to tenants table"""
    
    async with engine.begin() as conn:
        # Check if column already exists
        check_sql = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'tenants' AND column_name = 'is_demo'
        """)
        
        result = await conn.execute(check_sql)
        exists = result.fetchone()
        
        if exists:
            print("✅ is_demo column already exists")
            return
        
        # Add the column
        add_column_sql = text("""
        ALTER TABLE tenants 
        ADD COLUMN is_demo BOOLEAN DEFAULT FALSE NOT NULL
        """)
        
        await conn.execute(add_column_sql)
        print("✅ Added is_demo column to tenants table")
        
        # Show current tenants
        show_tenants_sql = text("SELECT name, is_demo FROM tenants ORDER BY name")
        result = await conn.execute(show_tenants_sql)
        tenants = result.fetchall()
        
        print(f"\n📋 Current tenants in dev database:")
        for tenant in tenants:
            status = "EXEMPT" if tenant.is_demo else "BILLING"
            print(f"  {tenant.name:20} - {status}")

if __name__ == "__main__":
    print("🔧 Adding is_demo column to DEV database...")
    asyncio.run(add_is_demo_column())