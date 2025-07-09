import asyncio
from app.db.database import get_db_context
from sqlalchemy import text

async def debug_crm_issue():
    async with get_db_context() as db:
        try:
            # Check super_admin users
            print("=== SUPER_ADMIN USERS ===")
            result = await db.execute(text("""
                SELECT u.id, u.email, u.tenant_id, t.name as tenant_name
                FROM users u
                JOIN tenants t ON u.tenant_id = t.id
                WHERE u.role = 'super_admin'
                ORDER BY u.email
            """))
            super_admins = result.fetchall()
            for admin in super_admins:
                print(f"{admin.email} - Tenant: {admin.tenant_name} (ID: {admin.tenant_id})")
            
            # Check if contacts table exists and has data
            print("\n=== CONTACTS TABLE CHECK ===")
            result = await db.execute(text("""
                SELECT COUNT(*) as total_contacts FROM contacts
            """))
            total = result.fetchone()
            print(f"Total contacts in database: {total.total_contacts}")
            
            # Check contacts for Springfield Memorial Cemetery specifically
            print("\n=== SPRINGFIELD MEMORIAL CEMETERY CONTACTS ===")
            springfield_tenant_id = 'c7156bfd-4fb1-4588-b217-817a159c65d0'
            result = await db.execute(text("""
                SELECT COUNT(*) as count FROM contacts 
                WHERE tenant_id = :tenant_id
            """), {'tenant_id': springfield_tenant_id})
            count = result.fetchone()
            print(f"Contacts for Springfield Memorial Cemetery: {count.count}")
            
            # Sample a few contacts
            result = await db.execute(text("""
                SELECT id, business_name, contact_name, status, created_at
                FROM contacts 
                WHERE tenant_id = :tenant_id
                ORDER BY created_at DESC
                LIMIT 5
            """), {'tenant_id': springfield_tenant_id})
            contacts = result.fetchall()
            if contacts:
                print("\nSample contacts:")
                for contact in contacts:
                    print(f"  - {contact.business_name} / {contact.contact_name} - Status: {contact.status}")
            
            # Check if there are any API-level issues
            print("\n=== POTENTIAL API ISSUES ===")
            
            # Check for any contacts with NULL tenant_id
            result = await db.execute(text("""
                SELECT COUNT(*) as null_tenant_count FROM contacts WHERE tenant_id IS NULL
            """))
            null_count = result.fetchone()
            print(f"Contacts with NULL tenant_id: {null_count.null_tenant_count}")
            
            # Check unique tenants with contacts
            result = await db.execute(text("""
                SELECT DISTINCT c.tenant_id, t.name, COUNT(*) as contact_count
                FROM contacts c
                JOIN tenants t ON c.tenant_id = t.id
                GROUP BY c.tenant_id, t.name
            """))
            tenant_contacts = result.fetchall()
            print("\nContacts by tenant:")
            for tc in tenant_contacts:
                print(f"  - {tc.name}: {tc.contact_count} contacts")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_crm_issue())