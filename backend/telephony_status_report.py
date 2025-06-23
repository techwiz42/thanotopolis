#!/usr/bin/env python3
"""
Telephony System Status Report
"""

import asyncio
import os
import requests
from dotenv import load_dotenv
from twilio.rest import Client
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.models.models import TelephonyConfiguration, PhoneCall

load_dotenv('/home/peter/thanotopolis/backend/.env')

async def generate_status_report():
    """Generate a comprehensive status report for the telephony system"""
    
    print("📞 THANOTOPOLIS TELEPHONY STATUS REPORT")
    print("=" * 60)
    print()
    
    # 1. Environment Configuration
    print("1. 🔧 ENVIRONMENT CONFIGURATION")
    print("-" * 40)
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
    telephony_enabled = os.getenv("TELEPHONY_ENABLED", "false").lower() == "true"
    
    print(f"Telephony Enabled: {'✅ YES' if telephony_enabled else '❌ NO'}")
    print(f"Twilio Account SID: {'✅ Configured' if account_sid else '❌ Missing'}")
    print(f"Twilio Auth Token: {'✅ Configured' if auth_token else '❌ Missing'}")
    print(f"Twilio Phone Number: {twilio_phone if twilio_phone else '❌ Missing'}")
    print()
    
    # 2. Database Configuration
    print("2. 🗄️  DATABASE CONFIGURATION")
    print("-" * 40)
    
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/thanotopolis')
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(select(TelephonyConfiguration))
        config = result.scalar_one_or_none()
        
        if config:
            print(f"✅ Configuration Found")
            print(f"   Organization Phone: {config.organization_phone_number}")
            print(f"   Platform Phone: {config.platform_phone_number}")
            print(f"   Verification Status: {config.verification_status}")
            print(f"   Call Forwarding: {'✅ Enabled' if config.call_forwarding_enabled else '❌ Disabled'}")
            print(f"   System Enabled: {'✅ YES' if config.is_enabled else '❌ NO'}")
            
            # Check if platform phone matches Twilio phone
            if config.platform_phone_number == twilio_phone:
                print(f"   ✅ Platform phone matches Twilio number")
            else:
                print(f"   ⚠️  Platform phone mismatch:")
                print(f"      Database: {config.platform_phone_number}")
                print(f"      Twilio: {twilio_phone}")
        else:
            print("❌ No telephony configuration found in database")
            config = None
    
    await engine.dispose()
    print()
    
    # 3. Twilio Account Status
    print("3. ☁️  TWILIO ACCOUNT STATUS")
    print("-" * 40)
    
    if account_sid and auth_token:
        try:
            client = Client(account_sid, auth_token)
            account = client.api.accounts(account_sid).fetch()
            
            print(f"✅ Account Active: {account.status}")
            print(f"💰 Account Balance: ${account.balance}")
            
            # Check phone numbers
            phone_numbers = client.incoming_phone_numbers.list()
            print(f"📱 Phone Numbers: {len(phone_numbers)} configured")
            
            for number in phone_numbers:
                print(f"   📞 {number.phone_number}")
                if number.voice_url:
                    if "thanotopolis.com" in number.voice_url:
                        print(f"      ✅ Webhook: Production ({number.voice_url})")
                    else:
                        print(f"      ⚠️  Webhook: Other ({number.voice_url})")
                else:
                    print(f"      ❌ Webhook: Not configured")
        
        except Exception as e:
            print(f"❌ Twilio API Error: {e}")
    else:
        print("❌ Cannot check Twilio - credentials missing")
    
    print()
    
    # 4. Webhook Connectivity
    print("4. 🌐 WEBHOOK CONNECTIVITY")
    print("-" * 40)
    
    webhook_url = "https://thanotopolis.com/api/telephony/webhook/incoming-call"
    local_webhook = "http://localhost:8000/api/telephony/webhook/incoming-call"
    
    # Test production webhook
    try:
        response = requests.post(webhook_url, data={
            "CallSid": "CAtest_prod",
            "From": "+12345551234",
            "To": twilio_phone or "+18884374952",
            "CallStatus": "ringing"
        }, timeout=10)
        
        if response.status_code == 200 and "<?xml" in response.text:
            print(f"✅ Production webhook responding correctly")
        else:
            print(f"❌ Production webhook error: {response.status_code}")
    except Exception as e:
        print(f"❌ Production webhook unreachable: {e}")
    
    # Test local webhook  
    try:
        response = requests.post(local_webhook, data={
            "CallSid": "CAtest_local",
            "From": "+12345551234", 
            "To": twilio_phone or "+18884374952",
            "CallStatus": "ringing"
        }, timeout=5)
        
        if response.status_code == 200 and "<?xml" in response.text:
            print(f"✅ Local webhook responding correctly")
        else:
            print(f"❌ Local webhook error: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Local webhook unavailable: {e}")
    
    print()
    
    # 5. Recent Call Activity
    print("5. 📊 RECENT CALL ACTIVITY")
    print("-" * 40)
    
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/thanotopolis')
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(
            select(PhoneCall)
            .order_by(PhoneCall.created_at.desc())
            .limit(5)
        )
        calls = result.scalars().all()
        
        if calls:
            print(f"📞 {len(calls)} recent calls found:")
            for call in calls:
                print(f"   {call.created_at.strftime('%Y-%m-%d %H:%M')} - {call.call_sid}")
                print(f"      From: {call.customer_phone_number} → {call.platform_phone_number}")
                print(f"      Status: {call.status}")
        else:
            print("📞 No call records found")
    
    await engine.dispose()
    print()
    
    # 6. Summary
    print("6. 📝 SUMMARY & RECOMMENDATIONS")
    print("-" * 40)
    
    if config and config.verification_status == "verified" and config.call_forwarding_enabled:
        print("✅ TELEPHONY SYSTEM IS OPERATIONAL")
        print()
        print("📋 Next Steps:")
        print("   1. Set up call forwarding from your business phone to:")
        print(f"      {config.platform_phone_number}")
        print("   2. Test by calling your business number")
        print("   3. Monitor call logs in the admin dashboard")
        
        if config.platform_phone_number != twilio_phone:
            print("   ⚠️  IMPORTANT: Update platform phone number in database")
            
    else:
        print("⚠️  TELEPHONY SYSTEM NEEDS CONFIGURATION")
        print()
        print("📋 Required Actions:")
        if not config:
            print("   1. ❌ Set up telephony configuration in admin panel")
        elif config.verification_status != "verified":
            print("   1. ❌ Complete phone number verification")
        elif not config.call_forwarding_enabled:
            print("   1. ❌ Enable call forwarding in configuration")
    
    print()
    print("=" * 60)
    print("📞 Report completed")

if __name__ == "__main__":
    asyncio.run(generate_status_report())