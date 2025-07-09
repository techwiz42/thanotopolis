import asyncio
import sys
sys.path.append('.')

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import EmailTemplate, Tenant

async def check_templates():
    async with AsyncSessionLocal() as db:
        # Get all templates
        templates = await db.execute(select(EmailTemplate))
        templates_list = templates.scalars().all()
        
        print(f'Total templates in database: {len(templates_list)}')
        
        for template in templates_list:
            # Get tenant name
            tenant = await db.scalar(select(Tenant).where(Tenant.id == template.tenant_id))
            tenant_name = tenant.name if tenant else 'Unknown'
            print(f'\nTemplate: {template.name}')
            print(f'  Tenant: {tenant_name} (ID: {template.tenant_id})')
            print(f'  Subject: {template.subject}')
            print(f'  Active: {template.is_active}')
            print(f'  Created by user: {template.created_by_user_id}')

if __name__ == "__main__":
    asyncio.run(check_templates())