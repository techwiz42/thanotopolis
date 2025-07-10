#!/usr/bin/env python3
"""Initialize the development database with all tables."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.db.database import engine, init_db
from app.models.models import Base
from sqlalchemy import text

async def create_all_tables():
    """Create all tables in the database."""
    try:
        # Create all tables
        await init_db()
        print("✓ All tables created successfully")
        
        # Mark alembic as up-to-date with the latest revision
        async with engine.begin() as conn:
            # Create alembic version table if it doesn't exist
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            
            # Clear any existing versions
            await conn.execute(text("DELETE FROM alembic_version"))
            
            # Insert the latest revision to mark database as current
            # Using the head revision from the migration history
            await conn.execute(text("""
                INSERT INTO alembic_version (version_num) 
                VALUES ('122b7567de22')
            """))
            
        print("✓ Database marked as up-to-date with migrations")
        
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_all_tables())