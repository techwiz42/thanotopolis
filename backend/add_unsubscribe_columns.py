#!/usr/bin/env python3
"""
Add unsubscribe columns to contacts table
"""

import sys
import asyncio
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, '/home/peter/thanotopolis/backend')

from app.db.database import engine

async def add_unsubscribe_columns():
    """Add unsubscribe columns to the contacts table"""
    
    # SQL to add the new columns
    sql_commands = [
        """
        ALTER TABLE contacts 
        ADD COLUMN is_unsubscribed BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE contacts 
        ADD COLUMN unsubscribed_at TIMESTAMP WITH TIME ZONE;
        """,
        """
        ALTER TABLE contacts 
        ADD COLUMN unsubscribe_reason VARCHAR(255);
        """,
        """
        CREATE INDEX idx_contacts_is_unsubscribed ON contacts (is_unsubscribed);
        """
    ]
    
    async with engine.begin() as conn:
        for sql in sql_commands:
            try:
                await conn.execute(text(sql))
                print(f"✅ Executed: {sql.strip()}")
            except Exception as e:
                print(f"❌ Error executing SQL: {e}")
                print(f"   SQL: {sql.strip()}")
                
        print("\\n🎉 Migration completed!")

if __name__ == "__main__":
    from sqlalchemy import text
    asyncio.run(add_unsubscribe_columns())