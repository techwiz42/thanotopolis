#!/usr/bin/env python3
"""
Manual phone verification bypass script

This script allows admins to manually mark phone numbers as verified 
without going through the SMS/call verification process.
"""

import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/home/peter/thanotopolis/backend/.env')

# Add the backend directory to Python path
sys.path.append('/home/peter/thanotopolis/backend')

from app.db.database import get_db_context
from app.models.models import TelephonyConfiguration, PhoneVerificationStatus
from sqlalchemy.future import select
from sqlalchemy import update
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def list_telephony_configs():
    """List all telephony configurations and their verification status"""
    
    print("=== Current Telephony Configurations ===")
    
    async with get_db_context() as db:
        config_query = select(TelephonyConfiguration)
        config_result = await db.execute(config_query)
        configs = config_result.scalars().all()
        
        if not configs:
            print("❌ No telephony configurations found")
            return []
        
        for i, config in enumerate(configs, 1):
            print(f"\n{i}. Tenant ID: {config.tenant_id}")
            print(f"   Organization Phone: {config.organization_phone_number}")
            print(f"   Formatted Phone: {config.formatted_phone_number}")
            print(f"   Platform Number: {config.platform_phone_number}")
            print(f"   Verification Status: {config.verification_status}")
            print(f"   Call Forwarding: {config.call_forwarding_enabled}")
            print(f"   Enabled: {config.is_enabled}")
        
        return configs

async def manual_verify_phone(tenant_id_str: str = None, phone_number: str = None):
    """Manually mark a phone number as verified"""
    
    async with get_db_context() as db:
        if tenant_id_str:
            # Find by tenant ID
            config_query = select(TelephonyConfiguration).where(
                TelephonyConfiguration.tenant_id == tenant_id_str
            )
        elif phone_number:
            # Find by phone number
            config_query = select(TelephonyConfiguration).where(
                TelephonyConfiguration.organization_phone_number == phone_number
            )
        else:
            print("❌ Must provide either tenant_id or phone_number")
            return False
        
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if not config:
            print("❌ No telephony configuration found")
            return False
        
        print(f"📞 Found configuration:")
        print(f"   Tenant ID: {config.tenant_id}")
        print(f"   Organization Phone: {config.organization_phone_number}")
        print(f"   Current Status: {config.verification_status}")
        print(f"   Call Forwarding: {config.call_forwarding_enabled}")
        
        # Update verification status
        update_query = update(TelephonyConfiguration).where(
            TelephonyConfiguration.id == config.id
        ).values(
            verification_status=PhoneVerificationStatus.VERIFIED.value,
            call_forwarding_enabled=True
        )
        
        await db.execute(update_query)
        await db.commit()
        
        print("✅ Phone number manually verified!")
        print("✅ Call forwarding enabled!")
        
        return True

async def manual_unverify_phone(tenant_id_str: str = None, phone_number: str = None):
    """Manually mark a phone number as unverified (for testing)"""
    
    async with get_db_context() as db:
        if tenant_id_str:
            # Find by tenant ID
            config_query = select(TelephonyConfiguration).where(
                TelephonyConfiguration.tenant_id == tenant_id_str
            )
        elif phone_number:
            # Find by phone number
            config_query = select(TelephonyConfiguration).where(
                TelephonyConfiguration.organization_phone_number == phone_number
            )
        else:
            print("❌ Must provide either tenant_id or phone_number")
            return False
        
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if not config:
            print("❌ No telephony configuration found")
            return False
        
        print(f"📞 Found configuration:")
        print(f"   Tenant ID: {config.tenant_id}")
        print(f"   Organization Phone: {config.organization_phone_number}")
        print(f"   Current Status: {config.verification_status}")
        print(f"   Call Forwarding: {config.call_forwarding_enabled}")
        
        # Update verification status
        update_query = update(TelephonyConfiguration).where(
            TelephonyConfiguration.id == config.id
        ).values(
            verification_status=PhoneVerificationStatus.PENDING.value,
            call_forwarding_enabled=False
        )
        
        await db.execute(update_query)
        await db.commit()
        
        print("⚠️  Phone number manually unverified!")
        print("⚠️  Call forwarding disabled!")
        
        return True

async def interactive_menu():
    """Interactive menu for manual verification operations"""
    
    while True:
        print("\n" + "="*50)
        print("MANUAL PHONE VERIFICATION TOOL")
        print("="*50)
        print("1. List all telephony configurations")
        print("2. Verify phone by tenant ID")
        print("3. Verify phone by phone number")
        print("4. Unverify phone by tenant ID")
        print("5. Unverify phone by phone number")
        print("6. Exit")
        print("-" * 50)
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            await list_telephony_configs()
        
        elif choice == "2":
            tenant_id = input("Enter tenant ID: ").strip()
            if tenant_id:
                await manual_verify_phone(tenant_id_str=tenant_id)
            else:
                print("❌ Invalid tenant ID")
        
        elif choice == "3":
            phone_number = input("Enter phone number: ").strip()
            if phone_number:
                await manual_verify_phone(phone_number=phone_number)
            else:
                print("❌ Invalid phone number")
        
        elif choice == "4":
            tenant_id = input("Enter tenant ID: ").strip()
            if tenant_id:
                await manual_unverify_phone(tenant_id_str=tenant_id)
            else:
                print("❌ Invalid tenant ID")
        
        elif choice == "5":
            phone_number = input("Enter phone number: ").strip()
            if phone_number:
                await manual_unverify_phone(phone_number=phone_number)
            else:
                print("❌ Invalid phone number")
        
        elif choice == "6":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")

async def main():
    """Main function"""
    
    print("🚀 Manual Phone Verification Tool")
    print("This tool allows you to bypass phone verification for testing or admin purposes.\n")
    
    # Check if command line arguments provided
    if len(sys.argv) >= 2:
        operation = sys.argv[1].lower()  # verify, unverify, or list
        identifier = sys.argv[2] if len(sys.argv) >= 3 else None  # tenant_id or phone_number
        
        if operation == "verify" and identifier:
            # Try as tenant ID first, then as phone number
            if len(identifier) == 36 and '-' in identifier:  # UUID format
                success = await manual_verify_phone(tenant_id_str=identifier)
            else:
                success = await manual_verify_phone(phone_number=identifier)
            
            if success:
                print("\n✅ Verification completed successfully!")
            else:
                print("\n❌ Verification failed!")
        
        elif operation == "unverify" and identifier:
            # Try as tenant ID first, then as phone number
            if len(identifier) == 36 and '-' in identifier:  # UUID format
                success = await manual_unverify_phone(tenant_id_str=identifier)
            else:
                success = await manual_unverify_phone(phone_number=identifier)
            
            if success:
                print("\n✅ Unverification completed successfully!")
            else:
                print("\n❌ Unverification failed!")
        
        elif operation == "list":
            await list_telephony_configs()
        
        else:
            print(f"❌ Invalid operation: {operation}")
            print("Usage: python manual_verify_phone.py [verify|unverify|list] [tenant_id_or_phone_number]")
    
    else:
        # Interactive mode
        await interactive_menu()

if __name__ == "__main__":
    asyncio.run(main())