#!/usr/bin/env python3
"""
Debug script to test Twilio client initialization and SMS sending
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/home/peter/thanotopolis/backend/.env')

# Add the backend directory to Python path
sys.path.append('/home/peter/thanotopolis/backend')

from app.core.config import settings
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException

def test_twilio_config():
    """Test Twilio configuration and client initialization"""
    
    print("=== Twilio Configuration Debug ===")
    print(f"TWILIO_ACCOUNT_SID: {settings.TWILIO_ACCOUNT_SID}")
    print(f"TWILIO_AUTH_TOKEN: {settings.TWILIO_AUTH_TOKEN[:10]}..." if settings.TWILIO_AUTH_TOKEN else "None")
    print(f"TWILIO_PHONE_NUMBER: {settings.TWILIO_PHONE_NUMBER}")
    
    # Check if credentials are available
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("❌ Twilio credentials not found in settings")
        return False
    
    # Test client initialization
    print("\n=== Testing Twilio Client Initialization ===")
    try:
        client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        print("✅ Twilio client initialized successfully")
        
        # Test account info
        account = client.api.account.fetch()
        print(f"✅ Account SID: {account.sid}")
        print(f"✅ Account Status: {account.status}")
        
        return client
    except Exception as e:
        print(f"❌ Failed to initialize Twilio client: {e}")
        return None

def test_sms_sending(client, to_number="+14245330093"):
    """Test SMS sending"""
    
    print(f"\n=== Testing SMS Sending to {to_number} ===")
    
    if not client:
        print("❌ No valid Twilio client available")
        return
    
    try:
        message = client.messages.create(
            body="Test verification code: 123456. This is a test from your AI Platform setup.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_number
        )
        print(f"✅ SMS sent successfully!")
        print(f"✅ Message SID: {message.sid}")
        print(f"✅ Status: {message.status}")
        
    except TwilioException as e:
        print(f"❌ Twilio error: {e}")
        print(f"❌ Error code: {e.code}")
        print(f"❌ Error message: {e.msg}")
    except Exception as e:
        print(f"❌ General error: {e}")

def test_call_making(client, to_number="+14245330093"):
    """Test voice call making"""
    
    print(f"\n=== Testing Voice Call to {to_number} ===")
    
    if not client:
        print("❌ No valid Twilio client available")
        return
    
    try:
        call = client.calls.create(
            twiml='<Response><Say>Test verification code is: 1 2 3 4 5 6. This is a test from your AI Platform setup.</Say></Response>',
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_number
        )
        print(f"✅ Call initiated successfully!")
        print(f"✅ Call SID: {call.sid}")
        print(f"✅ Status: {call.status}")
        
    except TwilioException as e:
        print(f"❌ Twilio error: {e}")
        print(f"❌ Error code: {e.code}")
        print(f"❌ Error message: {e.msg}")
    except Exception as e:
        print(f"❌ General error: {e}")

if __name__ == "__main__":
    # Test configuration
    client = test_twilio_config()
    
    # Test SMS sending
    if client:
        test_sms_sending(client)
        
        # Uncomment to test voice calls
        # test_call_making(client)
    
    print("\n=== Debug Complete ===")