#!/usr/bin/env python3
"""
Setup script for test database.
Creates the test_thanotopolis database and applies migrations.
"""
import asyncio
import asyncpg
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.models import Base

# Test database configuration
TEST_DB_NAME = "test_thanotopolis"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

# Connection URLs
ADMIN_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"
TEST_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TEST_DB_NAME}"


async def create_test_database():
    """Create the test database if it doesn't exist."""
    try:
        # Connect to postgres database to create test database
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database="postgres"
        )
        
        # Check if test database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
        )
        
        if not result:
            # Create test database
            await conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")
            print(f"✅ Created test database: {TEST_DB_NAME}")
        else:
            print(f"✅ Test database already exists: {TEST_DB_NAME}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error creating test database: {e}")
        raise


async def create_test_tables():
    """Create all tables in the test database."""
    try:
        # Connect to test database and create tables
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        
        async with engine.begin() as conn:
            # Drop all tables first with CASCADE
            try:
                # Drop with cascade to handle foreign key dependencies
                await conn.execute(text("DROP SCHEMA public CASCADE"))
                await conn.execute(text("CREATE SCHEMA public"))
                print("✅ Dropped existing schema and recreated")
            except Exception as e:
                print(f"⚠️  Schema drop failed: {e}")
                # Try regular drop_all as fallback
                await conn.run_sync(Base.metadata.drop_all)
                print("✅ Dropped existing tables (fallback)")
            
            # Install required extensions
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                print("✅ Installed pgvector extension")
            except Exception as e:
                print(f"⚠️  pgvector extension install failed: {e}")
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Created all tables")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise


async def main():
    """Main setup function."""
    print("🔧 Setting up test database...")
    
    try:
        await create_test_database()
        await create_test_tables()
        
        print("✅ Test database setup completed successfully!")
        print(f"📊 Database URL: {TEST_DATABASE_URL}")
        
    except Exception as e:
        print(f"❌ Test database setup failed: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())