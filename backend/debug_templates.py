#!/usr/bin/env python3
"""
Debug script to check email templates and tenant filtering
"""
import asyncio
import sys
sys.path.append('.')

from sqlalchemy import select, text
from app.db.database import AsyncSessionLocal
from app.models.models import EmailTemplate, Tenant, User

async def debug_templates():
    async with AsyncSessionLocal() as db:
        print("=== EMAIL TEMPLATE DEBUGGING ===\n")
        
        # 1. Get all templates
        templates = await db.execute(select(EmailTemplate))
        templates_list = templates.scalars().all()
        
        print(f"Total templates in database: {len(templates_list)}")
        
        for template in templates_list:
            # Get tenant info
            tenant = await db.scalar(select(Tenant).where(Tenant.id == template.tenant_id))
            tenant_name = tenant.name if tenant else 'Unknown'
            
            # Get creator info
            creator = await db.scalar(select(User).where(User.id == template.created_by_user_id))
            creator_email = creator.email if creator else 'Unknown'
            
            print(f"\nTemplate: {template.name}")
            print(f"  ID: {template.id}")
            print(f"  Tenant: {tenant_name} (ID: {template.tenant_id})")
            print(f"  Created by: {creator_email} (ID: {template.created_by_user_id})")
            print(f"  Subject: {template.subject}")
            print(f"  Active: {template.is_active}")
            print(f"  Variables: {template.variables}")
        
        print("\n=== TENANT INFORMATION ===\n")
        
        # 2. Get all tenants
        tenants = await db.execute(select(Tenant))
        tenants_list = tenants.scalars().all()
        
        for tenant in tenants_list:
            print(f"\nTenant: {tenant.name}")
            print(f"  ID: {tenant.id}")
            print(f"  Subdomain: {tenant.subdomain}")
            print(f"  Active: {tenant.is_active}")
            
            # Count templates for this tenant
            template_count = await db.scalar(
                select(func.count(EmailTemplate.id)).where(EmailTemplate.tenant_id == tenant.id)
            )
            print(f"  Email Templates: {template_count}")
        
        print("\n=== USER TENANT ASSOCIATIONS ===\n")
        
        # 3. Get users and their tenants
        users = await db.execute(select(User).limit(10))
        users_list = users.scalars().all()
        
        for user in users_list:
            tenant = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id))
            tenant_name = tenant.name if tenant else 'NO TENANT'
            print(f"\nUser: {user.email}")
            print(f"  Tenant: {tenant_name} (ID: {user.tenant_id})")
            print(f"  Role: {user.role}")
        
        print("\n=== RAW SQL CHECK ===\n")
        
        # 4. Raw SQL to verify data
        result = await db.execute(text("""
            SELECT 
                et.name as template_name,
                et.tenant_id,
                t.name as tenant_name,
                u.email as creator_email
            FROM email_templates et
            LEFT JOIN tenants t ON et.tenant_id = t.id
            LEFT JOIN users u ON et.created_by_user_id = u.id
        """))
        
        for row in result:
            print(f"\nTemplate: {row.template_name}")
            print(f"  Tenant ID: {row.tenant_id}")
            print(f"  Tenant Name: {row.tenant_name}")
            print(f"  Creator: {row.creator_email}")

if __name__ == "__main__":
    from sqlalchemy import func
    asyncio.run(debug_templates())