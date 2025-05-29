#!/usr/bin/env python3
"""
Setup test database for pytest
Run this before running tests: python setup_test_db.py
"""
import asyncio
import asyncpg
import sys
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def create_test_database():
    """Create the test database if it doesn't exist."""
    # Connection parameters
    db_user = "postgres"
    db_password = "postgres"
    db_host = "localhost"
    db_port = 5432
    test_db_name = "test_thanotopolis"
    
    # Connect to PostgreSQL server (not a specific database)
    dsn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/postgres"
    
    print(f"Connecting to PostgreSQL server...")
    
    try:
        # Use asyncpg to create database
        conn = await asyncpg.connect(dsn)
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = $1)",
            test_db_name
        )
        
        if exists:
            print(f"Database '{test_db_name}' already exists.")
        else:
            # Create database
            await conn.execute(f'CREATE DATABASE "{test_db_name}"')
            print(f"Database '{test_db_name}' created successfully.")
        
        await conn.close()
        
        # Now connect to the test database and create extensions if needed
        test_dsn = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{test_db_name}"
        engine = create_async_engine(test_dsn)
        
        async with engine.begin() as conn:
            # Create uuid-ossp extension if needed
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            print("Extensions created/verified.")
        
        await engine.dispose()
        
        print(f"\nTest database setup complete!")
        print(f"DATABASE_URL: {test_dsn}")
        
    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"Error: Could not connect to PostgreSQL server.")
        print(f"Make sure PostgreSQL is running and accessible at {db_host}:{db_port}")
        sys.exit(1)
    except asyncpg.exceptions.InvalidPasswordError:
        print(f"Error: Invalid password for user '{db_user}'")
        print(f"Update the connection parameters in this script.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_test_database())
