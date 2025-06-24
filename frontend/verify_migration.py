#!/usr/bin/env python3
"""
Script to verify the call messages migration was successful.
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path

async def verify_migration():
    """Verify the call messages table was created successfully."""
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="thanotopolis"
        )
        
        print("✅ Connected to database successfully")
        
        # Check if call_messages table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'call_messages'
            );
        """)
        
        if table_exists:
            print("✅ call_messages table exists")
        else:
            print("❌ call_messages table does not exist")
            return False
        
        # Check table structure
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'call_messages'
            ORDER BY ordinal_position;
        """)
        
        print("\n📋 Table Structure:")
        print("-" * 60)
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            print(f"  {col['column_name']:<20} {col['data_type']:<15} {nullable}{default}")
        
        # Check indexes
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes 
            WHERE tablename = 'call_messages'
            ORDER BY indexname;
        """)
        
        print("\n📊 Indexes:")
        print("-" * 60)
        for idx in indexes:
            print(f"  {idx['indexname']}")
            print(f"    {idx['indexdef']}")
            print()
        
        # Check constraints
        constraints = await conn.fetch("""
            SELECT conname, contype, pg_get_constraintdef(oid) as definition
            FROM pg_constraint 
            WHERE conrelid = 'call_messages'::regclass
            ORDER BY conname;
        """)
        
        print("\n🔒 Constraints:")
        print("-" * 60)
        for const in constraints:
            const_type = {
                'p': 'PRIMARY KEY',
                'f': 'FOREIGN KEY', 
                'c': 'CHECK',
                'u': 'UNIQUE'
            }.get(const['contype'], const['contype'])
            
            print(f"  {const['conname']} ({const_type})")
            print(f"    {const['definition']}")
            print()
        
        # Check if phone_calls table still exists and has the right structure
        phone_calls_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'phone_calls'
            );
        """)
        
        if phone_calls_exists:
            print("✅ phone_calls table still exists")
            
            # Check phone_calls.id type
            id_type = await conn.fetchval("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'phone_calls' 
                AND column_name = 'id';
            """)
            print(f"✅ phone_calls.id type: {id_type}")
            
        else:
            print("❌ phone_calls table does not exist")
        
        # Test the foreign key relationship
        try:
            await conn.execute("""
                INSERT INTO call_messages (id, call_id, content, sender, timestamp, message_type)
                VALUES (
                    gen_random_uuid(),
                    gen_random_uuid(),  -- This should fail due to FK constraint
                    'Test message',
                    '{"identifier": "test", "type": "system", "name": "Test"}',
                    NOW(),
                    'system'
                );
            """)
            print("⚠️  Foreign key constraint may not be working (insert succeeded)")
        except Exception as e:
            if "violates foreign key constraint" in str(e):
                print("✅ Foreign key constraint is working correctly")
            else:
                print(f"❓ Unexpected error: {e}")
        
        # Check if we can query both tables together
        join_test = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM phone_calls p 
            LEFT JOIN call_messages cm ON p.id = cm.call_id
        """)
        
        print(f"✅ Join query successful: {join_test} phone_calls found")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🔍 Verifying Call Messages Migration")
    print("=" * 50)
    
    success = await verify_migration()
    
    if success:
        print("\n🎉 Migration verification completed successfully!")
        print("\nNext steps:")
        print("1. Update your backend models to include CallMessage")
        print("2. Add API endpoints for call message management")
        print("3. Test the frontend integration")
    else:
        print("\n💥 Migration verification failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)