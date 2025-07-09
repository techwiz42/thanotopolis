#!/usr/bin/env python3
"""
Rollback manual database changes so we can apply them via Alembic
"""

import sys
import asyncio

# Add the backend directory to the Python path
sys.path.insert(0, '/home/peter/thanotopolis/backend')

from app.db.database import engine
from sqlalchemy import text

async def rollback_manual_changes():
    """Rollback the manual database changes"""
    
    # SQL to remove the manually added columns
    sql_commands = [
        "DROP INDEX IF EXISTS idx_contacts_is_unsubscribed;",
        "ALTER TABLE contacts DROP COLUMN IF EXISTS unsubscribe_reason;",
        "ALTER TABLE contacts DROP COLUMN IF EXISTS unsubscribed_at;",
        "ALTER TABLE contacts DROP COLUMN IF EXISTS is_unsubscribed;"
    ]
    
    async with engine.begin() as conn:
        for sql in sql_commands:
            try:
                await conn.execute(text(sql))
                print(f"✅ Executed: {sql}")
            except Exception as e:
                print(f"⚠️  Error (may be expected): {e}")
                print(f"   SQL: {sql}")
                
        print("\\n🔄 Manual changes rolled back!")
        print("\\nNext steps:")
        print("1. Run: alembic upgrade head")
        print("2. This will apply the proper migration")

if __name__ == "__main__":
    asyncio.run(rollback_manual_changes())