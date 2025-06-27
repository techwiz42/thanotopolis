#!/usr/bin/env python3
"""
Check user roles in the database
"""

import psycopg2

def check_users():
    """Check user roles and tenant info"""
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="thanotopolis",
            user="postgres",
            password="postgres",
            port=5432
        )
        cursor = conn.cursor()
        
        print("🔍 Checking Users and Roles")
        print("=" * 40)
        
        # Get all users with their roles and tenant info
        cursor.execute("""
            SELECT u.email, u.role, u.tenant_id, t.name as tenant_name
            FROM users u
            LEFT JOIN tenants t ON u.tenant_id = t.id
            ORDER BY u.created_at DESC
        """)
        
        users = cursor.fetchall()
        print(f"Found {len(users)} users:")
        
        for user in users:
            email, role, tenant_id, tenant_name = user
            print(f"\n  Email: {email}")
            print(f"  Role: {role}")
            print(f"  Tenant ID: {tenant_id}")
            print(f"  Tenant Name: {tenant_name}")
            
            # Check if this user has telephony access
            has_telephony_access = role in ['org_admin', 'admin', 'super_admin']
            print(f"  Can access telephony API: {'✅' if has_telephony_access else '❌'}")
        
        print("\n🔍 Checking Call Message Access by Tenant")
        print("=" * 45)
        
        # Check which calls belong to which tenant
        cursor.execute("""
            SELECT pc.id as call_id, pc.customer_phone_number, tc.tenant_id, t.name as tenant_name,
                   (SELECT COUNT(*) FROM call_messages cm WHERE cm.call_id = pc.id) as message_count
            FROM phone_calls pc
            JOIN telephony_configurations tc ON pc.telephony_config_id = tc.id
            JOIN tenants t ON tc.tenant_id = t.id
            ORDER BY pc.created_at DESC
            LIMIT 5
        """)
        
        calls = cursor.fetchall()
        print(f"Recent calls with tenant info:")
        
        for call in calls:
            call_id, phone, tenant_id, tenant_name, msg_count = call
            print(f"\n  Call ID: {call_id}")
            print(f"  Customer Phone: {phone}")
            print(f"  Tenant: {tenant_name} ({tenant_id})")
            print(f"  Messages: {msg_count}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    check_users()

if __name__ == "__main__":
    main()