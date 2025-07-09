import asyncio
from app.db.database import get_db_context
from sqlalchemy import text

async def check_user_tenants():
    async with get_db_context() as db:
        try:
            # Get all users and their tenant associations
            result = await db.execute(text("""
                SELECT u.id, u.email, u.first_name, u.last_name, u.role, u.tenant_id, t.name as tenant_name
                FROM users u
                LEFT JOIN tenants t ON u.tenant_id = t.id
                ORDER BY t.name, u.email
            """))
            users = result.fetchall()
            
            print('=== USERS BY TENANT ===')
            current_tenant = None
            for user in users:
                if user.tenant_name != current_tenant:
                    current_tenant = user.tenant_name
                    print(f'\nTenant: {current_tenant} (ID: {user.tenant_id})')
                print(f'  - {user.email} ({user.first_name} {user.last_name}) - Role: {user.role}')
            
            # Check which tenant has the 63 contacts
            print('\n=== TENANT WITH CONTACTS ===')
            result = await db.execute(text("""
                SELECT t.id, t.name, COUNT(c.id) as contact_count
                FROM tenants t
                LEFT JOIN contacts c ON t.id = c.tenant_id
                GROUP BY t.id, t.name
                HAVING COUNT(c.id) > 0
            """))
            tenants_with_contacts = result.fetchall()
            for tenant in tenants_with_contacts:
                print(f'{tenant.name}: {tenant.contact_count} contacts (Tenant ID: {tenant.id})')
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_user_tenants())