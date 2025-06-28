#!/usr/bin/env python3
"""
Script to create an admin user
Usage: python create_admin_user.py
"""

import asyncio
import sys
from getpass import getpass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add the app directory to Python path
sys.path.append('/home/peter/thanotopolis/backend')

from app.db.database import AsyncSessionLocal
from app.models.models import User, Tenant
from app.auth.auth import AuthService


async def create_admin_user():
    """Create an admin user interactively"""
    
    print("=== Admin User Creation ===")
    print()
    
    # Get user input
    email = input("Admin email: ").strip()
    if not email:
        print("Error: Email is required")
        return
    
    username = input("Admin username: ").strip()
    if not username:
        print("Error: Username is required")
        return
    
    password = getpass("Admin password: ").strip()
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        return
    
    confirm_password = getpass("Confirm password: ").strip()
    if password != confirm_password:
        print("Error: Passwords do not match")
        return
    
    first_name = input("First name (optional): ").strip() or None
    last_name = input("Last name (optional): ").strip() or None
    
    print()
    print("Available roles:")
    print("1. admin - Can manage users and view analytics for their tenant")
    print("2. super_admin - Can manage all tenants and system-wide settings")
    
    role_choice = input("Choose role (1-2): ").strip()
    if role_choice == "1":
        role = "admin"
    elif role_choice == "2":
        role = "super_admin"
    else:
        print("Error: Invalid role choice")
        return
    
    print()
    
    # Create async session
    async with AsyncSessionLocal() as db:
        try:
            # Check if user already exists
            existing_user = await db.execute(
                select(User).where(User.email == email)
            )
            existing_user_obj = existing_user.scalars().first()
            if existing_user_obj:
                print(f"Error: User with email {email} already exists")
                print(f"Existing user: {existing_user_obj.username} (ID: {existing_user_obj.id})")
                return
            
            existing_username = await db.execute(
                select(User).where(User.username == username)
            )
            existing_username_obj = existing_username.scalars().first()
            if existing_username_obj:
                print(f"Error: User with username {username} already exists")
                print(f"Existing user: {existing_username_obj.email} (ID: {existing_username_obj.id})")
                return
            
            # For super_admin, we need to get a tenant (or use the first one)
            # For regular admin, they'll be associated with a specific tenant
            if role == "super_admin":
                # Get first tenant or create a default one
                tenant_result = await db.execute(select(Tenant).limit(1))
                tenant = tenant_result.scalar_one_or_none()
                
                if not tenant:
                    print("No tenants found. Creating default tenant...")
                    tenant = Tenant(
                        name="Default Organization",
                        subdomain="default",
                        access_code="ADMIN123"
                    )
                    db.add(tenant)
                    await db.flush()
                    print(f"Created default tenant: {tenant.name}")
            else:
                # For admin role, show available tenants
                tenants_result = await db.execute(select(Tenant))
                tenants = tenants_result.scalars().all()
                
                if not tenants:
                    print("No tenants found. Creating default tenant...")
                    tenant = Tenant(
                        name="Default Organization", 
                        subdomain="default",
                        access_code="ADMIN123"
                    )
                    db.add(tenant)
                    await db.flush()
                else:
                    print("Available tenants:")
                    for i, t in enumerate(tenants, 1):
                        print(f"{i}. {t.name} ({t.subdomain})")
                    
                    choice = input(f"Choose tenant (1-{len(tenants)}): ").strip()
                    try:
                        tenant_index = int(choice) - 1
                        if 0 <= tenant_index < len(tenants):
                            tenant = tenants[tenant_index]
                        else:
                            print("Error: Invalid tenant choice")
                            return
                    except ValueError:
                        print("Error: Invalid input")
                        return
            
            # Create the admin user
            hashed_password = AuthService.get_password_hash(password)
            
            admin_user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
                is_verified=True,
                tenant_id=tenant.id
            )
            
            db.add(admin_user)
            await db.commit()
            
            print()
            print("✅ Admin user created successfully!")
            print(f"Email: {email}")
            print(f"Username: {username}")
            print(f"Role: {role}")
            print(f"Tenant: {tenant.name} ({tenant.subdomain})")
            print()
            print("You can now log in to the admin interface.")
            
        except Exception as e:
            await db.rollback()
            print(f"Error creating admin user: {e}")
            raise


async def list_existing_admins():
    """List existing admin users"""
    async with AsyncSessionLocal() as db:
        try:
            # Get all admin users
            result = await db.execute(
                select(User, Tenant).join(Tenant).where(
                    User.role.in_(["admin", "super_admin"])
                )
            )
            admins = result.all()
            
            if not admins:
                print("No admin users found.")
                return
            
            print("Existing admin users:")
            print("-" * 60)
            for user, tenant in admins:
                print(f"Email: {user.email}")
                print(f"Username: {user.username}")
                print(f"Role: {user.role}")
                print(f"Tenant: {tenant.name} ({tenant.subdomain})")
                print(f"Active: {user.is_active}")
                print(f"Verified: {user.is_verified}")
                print(f"ID: {user.id}")
                print("-" * 60)
                
        except Exception as e:
            print(f"Error listing admin users: {e}")


async def find_duplicates():
    """Find and optionally clean up duplicate users"""
    async with AsyncSessionLocal() as db:
        try:
            # Find duplicate emails
            email_result = await db.execute(
                select(User.email, User.id, User.username, User.is_active, User.created_at)
                .order_by(User.email, User.created_at)
            )
            users = email_result.all()
            
            # Group by email
            email_groups = {}
            for user in users:
                email = user.email
                if email not in email_groups:
                    email_groups[email] = []
                email_groups[email].append(user)
            
            # Find duplicates
            duplicates = {email: users for email, users in email_groups.items() if len(users) > 1}
            
            if not duplicates:
                print("No duplicate users found.")
                return
            
            print("Found duplicate users:")
            print("=" * 80)
            
            for email, duplicate_users in duplicates.items():
                print(f"\nEmail: {email}")
                print("-" * 40)
                for i, user in enumerate(duplicate_users, 1):
                    print(f"  {i}. ID: {user.id} | Username: {user.username} | Active: {user.is_active} | Created: {user.created_at}")
                
                # Ask if user wants to clean up
                print(f"\nFound {len(duplicate_users)} users with email {email}")
                cleanup = input("Do you want to clean up duplicates? (y/N): ").strip().lower()
                
                if cleanup == 'y':
                    # Keep the oldest active user, or oldest if none are active
                    active_users = [u for u in duplicate_users if u.is_active]
                    if active_users:
                        keep_user = min(active_users, key=lambda x: x.created_at)
                    else:
                        keep_user = min(duplicate_users, key=lambda x: x.created_at)
                    
                    users_to_delete = [u for u in duplicate_users if u.id != keep_user.id]
                    
                    print(f"Keeping user: ID {keep_user.id} | Username: {keep_user.username}")
                    print(f"Deleting {len(users_to_delete)} duplicate users...")
                    
                    for user_to_delete in users_to_delete:
                        delete_result = await db.execute(
                            select(User).where(User.id == user_to_delete.id)
                        )
                        user_obj = delete_result.scalar_one()
                        await db.delete(user_obj)
                        print(f"  Deleted: ID {user_to_delete.id} | Username: {user_to_delete.username}")
                    
                    await db.commit()
                    print("Cleanup completed!")
                else:
                    print("Skipping cleanup for this email.")
            
        except Exception as e:
            await db.rollback()
            print(f"Error finding duplicates: {e}")
            raise


async def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            await list_existing_admins()
        elif sys.argv[1] == "--duplicates":
            await find_duplicates()
        elif sys.argv[1] == "--help":
            print("Usage: python create_admin_user.py [OPTIONS]")
            print()
            print("Options:")
            print("  (no args)     Create a new admin user")
            print("  --list        List existing admin users")
            print("  --duplicates  Find and clean up duplicate users")
            print("  --help        Show this help message")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for available options")
    else:
        await create_admin_user()


if __name__ == "__main__":
    asyncio.run(main())