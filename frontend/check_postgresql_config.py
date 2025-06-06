#!/usr/bin/env python3
"""
PostgreSQL Configuration Checker
Verifies that PostgreSQL is configured to handle the increased connection pool size.
"""
import asyncio
import asyncpg
import os
from pathlib import Path

async def check_postgresql_config():
    """Check PostgreSQL configuration for connection limits"""
    
    # Try to get database URL from environment or use default
    database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/thanotopolis")
    
    # Parse the URL to get connection info
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        print("🔍 Checking PostgreSQL Configuration...")
        print("=" * 50)
        
        # Connect to PostgreSQL
        conn = await asyncpg.connect(database_url)
        
        # Check max_connections setting
        max_connections = await conn.fetchval("SHOW max_connections")
        print(f"📊 PostgreSQL max_connections: {max_connections}")
        
        # Check current connection count
        current_connections = await conn.fetchval(
            "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
        )
        print(f"🔗 Current active connections: {current_connections}")
        
        # Calculate our pool requirements
        our_pool_size = 50
        our_max_overflow = 100
        our_total_capacity = our_pool_size + our_max_overflow
        
        print(f"\n🎯 Our Connection Pool Configuration:")
        print(f"   Base pool size: {our_pool_size}")
        print(f"   Max overflow: {our_max_overflow}")
        print(f"   Total capacity: {our_total_capacity}")
        
        # Check if PostgreSQL can handle our pool
        available_connections = int(max_connections) - int(current_connections)
        
        print(f"\n⚖️  Capacity Analysis:")
        print(f"   PostgreSQL available: {available_connections}")
        print(f"   Our pool needs: {our_total_capacity}")
        
        if available_connections >= our_total_capacity:
            print("✅ PostgreSQL can handle our connection pool!")
            print(f"   Headroom: {available_connections - our_total_capacity} connections")
        else:
            print("⚠️  PostgreSQL max_connections may be too low!")
            recommended = int(max_connections) + (our_total_capacity - available_connections) + 50
            print(f"   Recommended max_connections: {recommended}")
            print(f"   Current max_connections: {max_connections}")
            
        # Check other relevant settings
        try:
            shared_buffers = await conn.fetchval("SHOW shared_buffers")
            print(f"\n📋 Additional Settings:")
            print(f"   shared_buffers: {shared_buffers}")
        except:
            pass
            
        try:
            effective_cache_size = await conn.fetchval("SHOW effective_cache_size")
            print(f"   effective_cache_size: {effective_cache_size}")
        except:
            pass
        
        # Test connection creation
        print(f"\n🧪 Testing Connection Creation Speed...")
        import time
        start_time = time.time()
        
        # Create and close 10 connections to test speed
        test_connections = []
        for i in range(10):
            test_conn = await asyncpg.connect(database_url)
            test_connections.append(test_conn)
        
        for test_conn in test_connections:
            await test_conn.close()
            
        creation_time = (time.time() - start_time) / 10
        print(f"   Average connection creation time: {creation_time:.3f}s")
        
        if creation_time < 0.1:
            print("   ✅ Connection creation is fast")
        elif creation_time < 0.5:
            print("   ⚠️  Connection creation is moderate")
        else:
            print("   ❌ Connection creation is slow - check network/PostgreSQL performance")
        
        await conn.close()
        
        print(f"\n💡 Recommendations:")
        if available_connections < our_total_capacity:
            print(f"   1. Increase PostgreSQL max_connections to at least {recommended}")
            print(f"      Edit postgresql.conf: max_connections = {recommended}")
            print(f"      Then restart PostgreSQL: sudo systemctl restart postgresql")
        else:
            print(f"   1. PostgreSQL configuration looks good!")
            
        print(f"   2. Monitor connection pool usage with: GET /api/admin/pool-stats")
        print(f"   3. Watch for connection pool warnings in application logs")
        print(f"   4. Consider connection pooling with PgBouncer for production")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking PostgreSQL configuration: {e}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. Make sure PostgreSQL is running")
        print(f"   2. Check DATABASE_URL environment variable")
        print(f"   3. Verify database credentials and permissions")
        print(f"   4. Check network connectivity to database")
        return False

def print_postgresql_config_instructions():
    """Print instructions for configuring PostgreSQL"""
    print("\n📝 PostgreSQL Configuration Instructions:")
    print("=" * 50)
    print("If max_connections needs to be increased:")
    print()
    print("1. Find your postgresql.conf file:")
    print("   sudo find /etc -name postgresql.conf 2>/dev/null")
    print("   # or")
    print("   sudo find /usr/local -name postgresql.conf 2>/dev/null")
    print()
    print("2. Edit the configuration:")
    print("   sudo nano /etc/postgresql/*/main/postgresql.conf")
    print()
    print("3. Find and update these settings:")
    print("   max_connections = 300                    # Increased from default 100")
    print("   shared_buffers = 256MB                   # 25% of RAM (adjust as needed)")
    print("   effective_cache_size = 1GB               # 75% of RAM (adjust as needed)")
    print()
    print("4. Restart PostgreSQL:")
    print("   sudo systemctl restart postgresql")
    print()
    print("5. Verify the changes:")
    print("   python3 check_postgresql_config.py")

if __name__ == "__main__":
    print("🐘 PostgreSQL Connection Pool Configuration Checker")
    print("=" * 60)
    
    try:
        result = asyncio.run(check_postgresql_config())
        if not result:
            print_postgresql_config_instructions()
    except KeyboardInterrupt:
        print("\n⏸️  Check cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print_postgresql_config_instructions()