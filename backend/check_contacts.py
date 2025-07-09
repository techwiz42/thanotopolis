import asyncio
from app.db.database import get_db_context
from sqlalchemy import text

async def check_contacts():
    async with get_db_context() as db:
        try:
            # Get all tenants
            result = await db.execute(text('SELECT id, name FROM tenants ORDER BY name'))
            tenants = result.fetchall()
            print('=== TENANTS ===')
            for tenant in tenants:
                print(f'Tenant ID: {tenant.id}, Name: {tenant.name}')
            
            print('\n=== CONTACTS BY TENANT ===')
            # Check contacts for each tenant
            for tenant in tenants:
                result = await db.execute(text('SELECT COUNT(*) as count FROM contacts WHERE tenant_id = :tenant_id'), {'tenant_id': tenant.id})
                count = result.fetchone().count
                print(f'Tenant {tenant.name}: {count} contacts')
                
                # Show sample contact if exists
                if count > 0:
                    result = await db.execute(text('SELECT id, business_name, contact_name, created_at FROM contacts WHERE tenant_id = :tenant_id LIMIT 3'), {'tenant_id': tenant.id})
                    samples = result.fetchall()
                    for sample in samples:
                        print(f'  - {sample.business_name} / {sample.contact_name} (created: {sample.created_at})')
            
            # Also check total contacts
            result = await db.execute(text('SELECT COUNT(*) as total FROM contacts'))
            total = result.fetchone().total
            print(f'\n=== TOTAL CONTACTS IN DATABASE: {total} ===')
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_contacts())