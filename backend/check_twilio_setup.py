#!/usr/bin/env python3
"""
Check Twilio configuration for telephony app
"""

import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

def check_twilio_setup():
    """Check Twilio account setup and configuration"""
    
    # Load credentials from environment
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not all([account_sid, auth_token, twilio_phone]):
        print("❌ Missing Twilio credentials in environment")
        return False
    
    print(f"🔑 Account SID: {account_sid}")
    print(f"📱 Phone Number: {twilio_phone}")
    
    try:
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Test account access
        account = client.api.accounts(account_sid).fetch()
        print(f"✅ Account Status: {account.status}")
        print(f"💰 Account Balance: ${account.balance}")
        
        # List phone numbers
        print("\n📞 Phone Numbers:")
        phone_numbers = client.incoming_phone_numbers.list()
        
        if not phone_numbers:
            print("❌ No phone numbers found in account")
            return False
        
        webhook_base = "https://thanotopolis.com/api/telephony/webhook"
        
        for number in phone_numbers:
            print(f"  📱 {number.phone_number}")
            print(f"     Friendly Name: {number.friendly_name}")
            print(f"     Voice URL: {number.voice_url}")
            print(f"     Voice Method: {number.voice_method}")
            print(f"     Status URL: {getattr(number, 'status_callback_url', 'Not set')}")
            print(f"     Status Method: {getattr(number, 'status_callback_method', 'Not set')}")
            
            # Check if webhook is configured
            if number.voice_url:
                if "thanotopolis.com" in number.voice_url:
                    print(f"     ✅ Webhook configured for production")
                elif "localhost" in number.voice_url or "ngrok" in number.voice_url:
                    print(f"     ⚠️  Webhook configured for development")
                else:
                    print(f"     ❓ Webhook configured for unknown endpoint")
            else:
                print(f"     ❌ No webhook configured!")
                
                # Auto-configure webhook for production
                print(f"     🔧 Configuring webhook...")
                try:
                    client.incoming_phone_numbers(number.sid).update(
                        voice_url=f"{webhook_base}/incoming-call",
                        voice_method="POST",
                        status_callback=f"{webhook_base}/call-status",
                        status_callback_method="POST"
                    )
                    print(f"     ✅ Webhook configured successfully")
                except Exception as e:
                    print(f"     ❌ Failed to configure webhook: {e}")
                    # Try with minimal configuration
                    try:
                        client.incoming_phone_numbers(number.sid).update(
                            voice_url=f"{webhook_base}/incoming-call",
                            voice_method="POST"
                        )
                        print(f"     ✅ Voice webhook configured (status callback skipped)")
                    except Exception as e2:
                        print(f"     ❌ Even basic webhook configuration failed: {e2}")
            
            print()
        
        # Test webhook connectivity
        print("🌐 Testing webhook connectivity...")
        import requests
        
        webhook_url = f"{webhook_base}/incoming-call"
        test_data = {
            "CallSid": "CAtest123",
            "From": "+12345551234",
            "To": twilio_phone,
            "CallStatus": "ringing"
        }
        
        try:
            response = requests.post(webhook_url, data=test_data, timeout=10)
            if response.status_code == 200:
                print(f"✅ Webhook responding correctly (200)")
                if "<?xml" in response.text:
                    print(f"✅ TwiML response format correct")
                else:
                    print(f"❌ Invalid TwiML response format")
            else:
                print(f"❌ Webhook error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Webhook connectivity error: {e}")
        
        return True
        
    except TwilioException as e:
        print(f"❌ Twilio API error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Checking Twilio Setup for Thanotopolis Telephony...")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('/home/peter/thanotopolis/backend/.env')
    
    success = check_twilio_setup()
    
    print("=" * 60)
    if success:
        print("✅ Twilio setup check completed")
    else:
        print("❌ Twilio setup has issues that need attention")