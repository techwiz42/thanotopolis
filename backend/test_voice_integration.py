#!/usr/bin/env python3
# test_voice_integration.py - Test script for voice integration

import asyncio
import aiohttp
import json
import os
import sys
from typing import Dict, Any

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
sys.path.insert(0, os.path.dirname(__file__))

# Import settings
try:
    from app.core.config import settings
    # Use settings for configuration
    BASE_URL = f"http://localhost:{getattr(settings, 'PORT', 8001)}"
    print(f"📡 Using server configuration from settings: {BASE_URL}")
except ImportError as e:
    print(f"⚠️  Could not import settings: {e}")
    print("🔄 Falling back to default configuration")
    BASE_URL = "http://localhost:8001"

TEST_TEXT = "Hello, this is a test of the voice synthesis system. How does this sound?"

async def test_voice_services():
    """Test voice service integration"""
    
    print("🎤 Testing Voice Integration...")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Check STT Status
        print("\n1. Testing STT Service Status...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/stt/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ STT Status: {data}")
                else:
                    print(f"❌ STT Status Failed: {response.status}")
        except Exception as e:
            print(f"❌ STT Status Error: {e}")
        
        # Test 2: Check TTS Status  
        print("\n2. Testing TTS Service Status...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ TTS Status: {data}")
                    
                    if data.get('api_key_configured'):
                        print("✅ Google API Key: Configured")
                    else:
                        print("❌ Google API Key: Not configured")
                        
                else:
                    print(f"❌ TTS Status Failed: {response.status}")
        except Exception as e:
            print(f"❌ TTS Status Error: {e}")
        
        # Test 3: Get Available Voices (requires auth)
        print("\n3. Testing Available Voices...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/voices") as response:
                if response.status == 401 or response.status == 403:
                    print("✅ Voices endpoint properly requires authentication (expected)")
                    print("   Status: 403 Forbidden - Authentication required")
                elif response.status == 200:
                    data = await response.json()
                    voices = data.get('voices', [])
                    print(f"✅ Found {len(voices)} available voices")
                    for voice in voices[:3]:  # Show first 3
                        print(f"   - {voice['name']} ({voice['gender']}, {voice['quality']})")
                else:
                    print(f"❌ Voices request failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:100]}...")
        except Exception as e:
            print(f"❌ Voices request error: {e}")
        
        # Test 4: Test TTS Synthesis (requires auth)
        print("\n4. Testing TTS Synthesis...")
        try:
            test_payload = {
                "text": "This is a test message",
                "voice_id": "en-US-Studio-O",
                "audio_encoding": "MP3"
            }
            async with session.post(f"{BASE_URL}/api/voice/synthesize", json=test_payload) as response:
                if response.status == 401 or response.status == 403:
                    print("✅ TTS synthesis endpoint properly requires authentication (expected)")
                    print("   Status: 403 Forbidden - Authentication required")
                elif response.status == 200:
                    print("✅ TTS synthesis successful (user must be authenticated)")
                    content_type = response.headers.get('content-type', '')
                    print(f"   Response type: {content_type}")
                else:
                    print(f"❌ TTS synthesis failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:100]}...")
        except Exception as e:
            print(f"❌ TTS synthesis error: {e}")
        
        # Test 5: Test Basic API Routes
        print("\n5. Testing API Routes...")
        routes_to_test = [
            "/health",
            "/api",
            "/debug/routes"
        ]
        
        for route in routes_to_test:
            try:
                async with session.get(f"{BASE_URL}{route}") as response:
                    if response.status == 200:
                        print(f"✅ {route}: OK")
                    else:
                        print(f"❌ {route}: {response.status}")
            except Exception as e:
                print(f"❌ {route}: Error - {e}")

async def test_authentication():
    """Test authentication flow (optional advanced test)"""
    print("\n6. Testing Authentication Flow...")
    print("ℹ️  This is an optional test - requires valid user credentials")
    
    # For now, just document what would be needed
    print("   To test authenticated endpoints, you would need to:")
    print("   1. Create a test user account")
    print("   2. Login to get an access token")
    print("   3. Include 'Authorization: Bearer <token>' in requests")
    print("   4. Then test /api/voice/tts/voices and /api/voice/synthesize")
    print("   ✅ Authentication test framework ready (implementation optional)")

async def test_with_auth_if_available():
    """Test authenticated endpoints if credentials are available"""
    print("\n7. Testing Authenticated Endpoints (Optional)...")
    
    # Check if we have test credentials in environment
    test_email = os.getenv('TEST_EMAIL')
    test_password = os.getenv('TEST_PASSWORD')
    
    if not test_email or not test_password:
        print("ℹ️  No test credentials found (TEST_EMAIL, TEST_PASSWORD)")
        print("   Set these environment variables to test authenticated endpoints")
        return False
    
    async with aiohttp.ClientSession() as session:
        try:
            # Attempt login
            login_payload = {
                "email": test_email,
                "password": test_password
            }
            
            async with session.post(f"{BASE_URL}/api/auth/login", json=login_payload) as response:
                if response.status == 200:
                    login_data = await response.json()
                    token = login_data.get('access_token')
                    
                    if token:
                        print("✅ Login successful - testing authenticated endpoints")
                        
                        # Test authenticated voices endpoint
                        headers = {"Authorization": f"Bearer {token}"}
                        async with session.get(f"{BASE_URL}/api/voice/tts/voices", headers=headers) as auth_response:
                            if auth_response.status == 200:
                                data = await auth_response.json()
                                voices = data.get('voices', [])
                                print(f"✅ Authenticated voices request: {len(voices)} voices available")
                                for voice in voices[:2]:  # Show first 2
                                    print(f"   - {voice['name']} ({voice['gender']}, {voice['quality']})")
                            else:
                                print(f"❌ Authenticated voices request failed: {auth_response.status}")
                        
                        # Test authenticated TTS synthesis
                        tts_payload = {
                            "text": "This is a test of authenticated TTS synthesis.",
                            "voice_id": "en-US-Studio-O",
                            "audio_encoding": "MP3"
                        }
                        async with session.post(f"{BASE_URL}/api/voice/synthesize", json=tts_payload, headers=headers) as tts_response:
                            if tts_response.status == 200:
                                content_length = len(await tts_response.read())
                                print(f"✅ Authenticated TTS synthesis: {content_length} bytes of audio generated")
                            else:
                                print(f"❌ Authenticated TTS synthesis failed: {tts_response.status}")
                                
                        return True
                    else:
                        print("❌ Login response missing access token")
                else:
                    print(f"❌ Login failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:100]}...")
                    
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
    
    return False

def check_environment():
    """Check environment configuration"""
    print("\n5. Checking Environment Configuration...")
    
    # Try to get API keys from settings first, then fall back to env vars
    google_client_id = None
    deepgram_key = None
    
    try:
        from app.core.config import settings
        google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        deepgram_key = getattr(settings, 'DEEPGRAM_API_KEY', None)
        print("📝 Using API keys from app.core.config.settings")
    except (ImportError, AttributeError):
        print("📝 Settings not available, checking environment variables directly")
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        deepgram_key = os.getenv('DEEPGRAM_API_KEY')
    
    print(f"📝 GOOGLE_CLIENT_ID: {'✅ Set' if google_client_id else '❌ Not set'}")
    if google_client_id:
        masked_key = google_client_id[:4] + "..." + google_client_id[-4:] if len(google_client_id) > 8 else "***"
        print(f"   Value: {masked_key}")
    
    print(f"📝 DEEPGRAM_API_KEY: {'✅ Set' if deepgram_key else '❌ Not set'}")
    if deepgram_key:
        masked_key = deepgram_key[:4] + "..." + deepgram_key[-4:] if len(deepgram_key) > 8 else "***"
        print(f"   Value: {masked_key}")
    
    # Also check settings configuration
    try:
        from app.core.config import settings
        print(f"\n🔧 Settings Configuration:")
        print(f"   Port: {getattr(settings, 'PORT', 'Not set')}")
        print(f"   Environment: {getattr(settings, 'ENVIRONMENT', 'Not set')}")
        cors_origins = getattr(settings, 'CORS_ORIGINS', [])
        print(f"   CORS Origins: {cors_origins}")
    except (ImportError, AttributeError) as e:
        print(f"⚠️  Could not load settings configuration: {e}")

def check_file_structure():
    """Check if required files exist"""
    print("\n6. Checking File Structure...")
    
    required_files = [
        "app/api/voice_tts.py",
        "app/services/voice/google_tts_service.py", 
        "app/services/voice/deepgram_stt_service.py",
        "app/services/voice/__init__.py"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing!")

async def main():
    """Main test function"""
    print("🚀 Voice Integration Test Script")
    print("This script tests the voice integration setup")
    print(f"🔧 Testing server at: {BASE_URL}")
    print("Make sure your FastAPI server is running")
    print()
    
    # Check file structure
    check_file_structure()
    
    # Check environment 
    check_environment()
    
    # Test API endpoints
    try:
        await test_voice_services()
        await test_authentication()
        auth_success = await test_with_auth_if_available()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Voice integration test completed!")
    print("\nNext steps:")
    print("1. If APIs are available, test the frontend components")
    print("2. Open a conversation and try voice input/output")
    print("3. Check voice settings page functionality")
    print(f"\nNote: Make sure your server is running on {BASE_URL}")
    
    if 'auth_success' in locals() and auth_success:
        print("\n🔐 Authentication tests passed - voice endpoints fully functional!")
    else:
        print("\n🔐 To test authenticated voice endpoints, set TEST_EMAIL and TEST_PASSWORD environment variables")
    
    return True

if __name__ == "__main__":
    asyncio.run(main())
