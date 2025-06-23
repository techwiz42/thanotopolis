#!/usr/bin/env python3
"""
Debug script to test the telephony webhook flow and understand why calls aren't being created
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the backend directory to the Python path
sys.path.append('/home/peter/thanotopolis/backend')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db_context
from app.services.telephony_service import telephony_service
from app.models.models import TelephonyConfiguration, PhoneCall, CallStatus

async def debug_webhook_flow():
    """Debug the webhook flow step by step"""
    
    async with get_db_context() as db:
        print("🔍 TELEPHONY WEBHOOK DEBUG")
        print("=" * 60)
        
        # Step 1: Check telephony configuration
        print("\n1. CHECKING TELEPHONY CONFIGURATION")
        print("-" * 40)
        
        config_query = select(TelephonyConfiguration)
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if not config:
            print("❌ No telephony configuration found!")
            return
            
        print(f"✅ Configuration found:")
        print(f"   Organization Phone: {config.organization_phone_number}")
        print(f"   Platform Phone: {config.platform_phone_number}")
        print(f"   Verification Status: {config.verification_status}")
        print(f"   Call Forwarding: {'Enabled' if config.call_forwarding_enabled else 'Disabled'}")
        print(f"   Is Enabled: {'Yes' if config.is_enabled else 'No'}")
        
        # Step 2: Test the normalization function
        print("\n2. TESTING PHONE NUMBER NORMALIZATION")
        print("-" * 40)
        
        test_numbers = [
            "+18884374952",  # E.164 format
            "18884374952",   # Without +
            "8884374952",    # Without country code
            "(888) 437-4952", # Formatted
        ]
        
        for number in test_numbers:
            normalized = telephony_service._normalize_phone_number(number)
            print(f"   {number} → {normalized}")
            
        # Step 3: Check for existing calls
        print("\n3. CHECKING RECENT PHONE CALLS")
        print("-" * 40)
        
        calls_query = select(PhoneCall).order_by(PhoneCall.created_at.desc()).limit(5)
        calls_result = await db.execute(calls_query)
        calls = calls_result.scalars().all()
        
        if calls:
            print(f"Found {len(calls)} recent calls:")
            for call in calls:
                print(f"\n   Call ID: {call.id}")
                print(f"   Call SID: {call.call_sid}")
                print(f"   Status: {call.status}")
                print(f"   Customer: {call.customer_phone_number}")
                print(f"   Platform: {call.platform_phone_number}")
                print(f"   Created: {call.created_at}")
        else:
            print("No phone calls found in database")
            
        # Step 4: Simulate an incoming call
        print("\n4. SIMULATING INCOMING CALL WEBHOOK")
        print("-" * 40)
        
        # Use the actual Twilio number from the environment
        actual_twilio_number = os.getenv("TWILIO_PHONE_NUMBER", "+18884374952")
        test_call_sid = f"CAtest_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        customer_number = "+14245330093"
        
        print(f"Simulating call:")
        print(f"   Call SID: {test_call_sid}")
        print(f"   From: {customer_number}")
        print(f"   To: {actual_twilio_number}")
        
        try:
            # First, update the platform number if needed
            if config.platform_phone_number != actual_twilio_number:
                print(f"\n⚠️  Platform number mismatch detected!")
                print(f"   Database: {config.platform_phone_number}")
                print(f"   Actual Twilio: {actual_twilio_number}")
                print(f"   Updating database to match...")
                
                config.platform_phone_number = actual_twilio_number
                await db.commit()
                await db.refresh(config)
                print(f"   ✅ Updated platform number")
            
            # Now try to handle the incoming call
            phone_call = await telephony_service.handle_incoming_call(
                db=db,
                call_sid=test_call_sid,
                customer_number=customer_number,
                platform_number=actual_twilio_number,
                call_metadata={
                    "call_status": "ringing",
                    "webhook_data": {
                        "CallSid": test_call_sid,
                        "From": customer_number,
                        "To": actual_twilio_number,
                        "CallStatus": "ringing",
                        "Direction": "inbound"
                    }
                }
            )
            
            print(f"\n✅ Phone call created successfully!")
            print(f"   Call ID: {phone_call.id}")
            print(f"   Telephony Config ID: {phone_call.telephony_config_id}")
            print(f"   Status: {phone_call.status}")
            
            # Test updating the call status
            print("\n5. TESTING CALL STATUS UPDATE")
            print("-" * 40)
            
            updated_call = await telephony_service.update_call_status(
                db=db,
                call_sid=test_call_sid,
                status=CallStatus.COMPLETED,
                additional_data={"test": "successful"}
            )
            
            print(f"✅ Call status updated to: {updated_call.status}")
            
        except ValueError as e:
            print(f"\n❌ ValueError: {e}")
            print("\nPossible causes:")
            print("   - Platform phone number mismatch")
            print("   - Telephony not enabled")
            print("   - Phone not verified")
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            
        # Step 6: Check the actual error case
        print("\n6. TESTING PROBLEMATIC CALL SID")
        print("-" * 40)
        
        problem_sid = "CAb7e287d7c3a203d3e7387508b63954c4"
        print(f"Looking for call with SID: {problem_sid}")
        
        problem_query = select(PhoneCall).where(PhoneCall.call_sid == problem_sid)
        problem_result = await db.execute(problem_query)
        problem_call = problem_result.scalar_one_or_none()
        
        if problem_call:
            print(f"✅ Found the problematic call:")
            print(f"   ID: {problem_call.id}")
            print(f"   Status: {problem_call.status}")
            print(f"   Created: {problem_call.created_at}")
        else:
            print(f"❌ Call not found in database")
            print("\nThis suggests the incoming-call webhook failed to create the call record")
            
        print("\n" + "=" * 60)
        print("Debug complete")

if __name__ == "__main__":
    asyncio.run(debug_webhook_flow())