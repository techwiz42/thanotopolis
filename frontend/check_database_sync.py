#!/usr/bin/env python3
"""
Check database for call messages table and data
"""

import psycopg2
import os
from urllib.parse import urlparse

def check_database():
    """Check database for call messages"""
    
    # Database connection info
    # Assuming default PostgreSQL settings - adjust as needed
    db_configs = [
        {
            "host": "localhost",
            "database": "thanotopolis",
            "user": "postgres", 
            "password": "postgres",
            "port": 5432
        },
        {
            "host": "localhost",
            "database": "thanotopolis_dev",
            "user": "postgres",
            "password": "postgres", 
            "port": 5432
        }
    ]
    
    for config in db_configs:
        try:
            print(f"\n🔍 Trying database: {config['database']}")
            
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            
            # Check if call_messages table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'call_messages'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            print(f"✅ Connected to {config['database']}")
            print(f"call_messages table exists: {table_exists}")
            
            if table_exists:
                # Check table structure
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'call_messages'
                    ORDER BY ordinal_position;
                """)
                
                print("\nTable structure:")
                for row in cursor.fetchall():
                    print(f"  {row[0]}: {row[1]} (nullable: {row[2]})")
                
                # Check if there are any call messages
                cursor.execute("SELECT COUNT(*) FROM call_messages")
                count = cursor.fetchone()[0]
                print(f"\nTotal call messages in database: {count}")
                
                # Check if there are any phone calls
                cursor.execute("SELECT COUNT(*) FROM phone_calls")
                call_count = cursor.fetchone()[0]
                print(f"Total phone calls in database: {call_count}")
                
                if call_count > 0:
                    # Get sample call data
                    cursor.execute("SELECT id, customer_phone_number, status, created_at FROM phone_calls ORDER BY created_at DESC LIMIT 3")
                    calls = cursor.fetchall()
                    
                    print(f"\nRecent phone calls:")
                    for call in calls:
                        call_id, phone, status, created = call
                        print(f"  ID: {call_id}")
                        print(f"  Phone: {phone}")
                        print(f"  Status: {status}")
                        print(f"  Created: {created}")
                        
                        # Check messages for this call
                        cursor.execute("""
                            SELECT COUNT(*), message_type
                            FROM call_messages 
                            WHERE call_id = %s
                            GROUP BY message_type
                        """, (call_id,))
                        
                        message_counts = cursor.fetchall()
                        if message_counts:
                            print(f"  Messages: {dict(message_counts)}")
                        else:
                            print(f"  Messages: 0")
                        print()
                
                # Check for any telephony configurations
                try:
                    cursor.execute("SELECT COUNT(*) FROM telephony_configurations")
                    config_count = cursor.fetchone()[0]
                    print(f"Telephony configurations: {config_count}")
                    
                    if config_count > 0:
                        cursor.execute("SELECT tenant_id, organization_phone_number, verification_status FROM telephony_configurations LIMIT 3")
                        configs = cursor.fetchall()
                        print("Sample configurations:")
                        for cfg in configs:
                            print(f"  Tenant: {cfg[0]}, Phone: {cfg[1]}, Status: {cfg[2]}")
                            
                except Exception as e:
                    print(f"Could not check telephony configs: {e}")
            
            cursor.close()
            conn.close()
            return True
            
        except psycopg2.OperationalError as e:
            print(f"❌ Could not connect to {config['database']}: {e}")
            continue
        except Exception as e:
            print(f"❌ Error with {config['database']}: {e}")
            continue
    
    print("❌ Could not connect to any database")
    return False

def check_permissions():
    """Check common permission issues"""
    
    print("\n🔐 Checking Permission Requirements")
    print("=" * 40)
    
    print("The API endpoint requires users with roles:")
    print("  - org_admin")
    print("  - admin") 
    print("  - super_admin")
    print("\nRegular users cannot access call messages API")
    
    print("\n📋 To check user role in database:")
    print("  SELECT email, role FROM users WHERE email = 'your-email@example.com';")

def main():
    """Main function"""
    print("🔧 Database Check for Call Messages")
    print("=" * 50)
    
    success = check_database()
    check_permissions()
    
    if success:
        print("\n✅ Database check completed")
    else:
        print("\n❌ Could not access database")
        print("\nTry checking:")
        print("1. PostgreSQL is running")
        print("2. Database name is correct") 
        print("3. Database credentials are correct")
        print("4. Database host/port are correct")

if __name__ == "__main__":
    main()