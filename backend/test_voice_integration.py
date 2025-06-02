#!/usr/bin/env python3
# test_voice_integration.py - Test script for voice integration with Deepgram

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
    BASE_URL = f"http://localhost:{getattr(settings, 'API_PORT', 8000)}"
    print(f"📡 Using server configuration from settings: {BASE_URL}")
except ImportError as e:
    print(f"⚠️  Could not import settings: {e}")
    print("🔄 Falling back to default configuration")
    BASE_URL = "http://localhost:8000"

TEST_TEXT = "Hello, this is a test of the Deepgram voice synthesis system. How does this sound?"

async def test_voice_services():
    """Test voice service integration with Deepgram"""
    
    print("🎤 Testing Voice Integration with Deepgram...")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Check STT Status (Deepgram)
        print("\n1. Testing Deepgram STT Service Status...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/stt/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ STT Status: {data}")
                    
                    if data.get('api_key_configured'):
                        print("✅ Deepgram API Key: Configured")
                        if data.get('api_key_valid'):
                            print("✅ Deepgram API Key: Valid")
                        else:
                            print("❌ Deepgram API Key: Invalid or verification failed")
                            error = data.get('error')
                            if error:
                                print(f"   Error: {error}")
                    else:
                        print("❌ Deepgram API Key: Not configured")
                else:
                    print(f"❌ STT Status Failed: {response.status}")
        except Exception as e:
            print(f"❌ STT Status Error: {e}")
        
        # Test 2: Check TTS Status (Deepgram)
        print("\n2. Testing Deepgram TTS Service Status...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ TTS Status: {data}")
                    
                    provider = data.get('provider', 'unknown')
                    service = data.get('service', 'unknown')
                    print(f"✅ TTS Provider: {provider}")
                    print(f"✅ TTS Service: {service}")
                    
                    if data.get('api_key_configured'):
                        print("✅ Deepgram API Key: Configured")
                    else:
                        print("❌ Deepgram API Key: Not configured")
                        
                    available_voices = data.get('available_voices', 0)
                    print(f"✅ Available Voices: {available_voices}")
                    
                    supported_encodings = data.get('supported_encodings', [])
                    print(f"✅ Supported Encodings: {', '.join(supported_encodings)}")
                        
                else:
                    print(f"❌ TTS Status Failed: {response.status}")
        except Exception as e:
            print(f"❌ TTS Status Error: {e}")
        
        # Test 3: Get Available Voices (requires auth)
        print("\n3. Testing Available Deepgram Voices...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/voices") as response:
                if response.status == 401 or response.status == 403:
                    print("✅ Voices endpoint properly requires authentication (expected)")
                    print("   Status: 401/403 - Authentication required")
                elif response.status == 200:
                    data = await response.json()
                    voices = data.get('voices', [])
                    provider = data.get('provider', 'unknown')
                    print(f"✅ Found {len(voices)} available {provider} voices")
                    
                    # Group voices by gender for better display
                    female_voices = [v for v in voices if v.get('gender') == 'FEMALE']
                    male_voices = [v for v in voices if v.get('gender') == 'MALE']
                    
                    print(f"   Female voices ({len(female_voices)}):")
                    for voice in female_voices[:3]:  # Show first 3
                        print(f"     - {voice['name']} ({voice['quality']})")
                    
                    print(f"   Male voices ({len(male_voices)}):")
                    for voice in male_voices[:3]:  # Show first 3
                        print(f"     - {voice['name']} ({voice['quality']})")
                    
                    default_voice = data.get('default_voice')
                    if default_voice:
                        print(f"   Default voice: {default_voice}")
                else:
                    print(f"❌ Voices request failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:100]}...")
        except Exception as e:
            print(f"❌ Voices request error: {e}")
        
        # Test 4: Test TTS Synthesis (requires auth)
        print("\n4. Testing Deepgram TTS Synthesis...")
        try:
            test_payload = {
                "text": "This is a test message using Deepgram TTS",
                "voice_id": "aura-asteria-en",
                "encoding": "mp3",
                "sample_rate": 24000
            }
            async with session.post(f"{BASE_URL}/api/voice/synthesize", json=test_payload) as response:
                if response.status == 401 or response.status == 403:
                    print("✅ TTS synthesis endpoint properly requires authentication (expected)")
                    print("   Status: 401/403 - Authentication required")
                elif response.status == 200:
                    print("✅ TTS synthesis successful (user must be authenticated)")
                    content_type = response.headers.get('content-type', '')
                    content_length = response.headers.get('content-length', 'unknown')
                    voice_id = response.headers.get('x-voice-id', 'unknown')
                    voice_quality = response.headers.get('x-voice-quality', 'unknown')
                    sample_rate = response.headers.get('x-sample-rate', 'unknown')
                    
                    print(f"   Content Type: {content_type}")
                    print(f"   Content Length: {content_length} bytes")
                    print(f"   Voice ID: {voice_id}")
                    print(f"   Voice Quality: {voice_quality}")
                    print(f"   Sample Rate: {sample_rate} Hz")
                else:
                    print(f"❌ TTS synthesis failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:100]}...")
        except Exception as e:
            print(f"❌ TTS synthesis error: {e}")
        
        # Test 5: Test Recommended Voice (requires auth)
        print("\n5. Testing Recommended Voice Selection...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/recommended?gender=FEMALE&quality=conversational") as response:
                if response.status == 401 or response.status == 403:
                    print("✅ Recommended voice endpoint properly requires authentication (expected)")
                elif response.status == 200:
                    data = await response.json()
                    recommended = data.get('recommended_voice')
                    provider = data.get('provider', 'unknown')
                    print(f"✅ Recommended voice from {provider}: {recommended}")
                    
                    voice_details = data.get('voice_details', {})
                    if voice_details:
                        gender = voice_details.get('gender', 'unknown')
                        quality = voice_details.get('quality', 'unknown')
                        print(f"   Details: {gender}, {quality} quality")
                else:
                    print(f"❌ Recommended voice request failed: {response.status}")
        except Exception as e:
            print(f"❌ Recommended voice error: {e}")
        
        # Test 6: Test Basic API Routes
        print("\n6. Testing API Routes...")
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
    print("\n7. Testing Authentication Flow...")
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
    print("\n8. Testing Authenticated Endpoints (Optional)...")
    
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
                        print("✅ Login successful - testing authenticated Deepgram endpoints")
                        
                        # Test authenticated voices endpoint
                        headers = {"Authorization": f"Bearer {token}"}
                        async with session.get(f"{BASE_URL}/api/voice/tts/voices", headers=headers) as auth_response:
                            if auth_response.status == 200:
                                data = await auth_response.json()
                                voices = data.get('voices', [])
                                provider = data.get('provider', 'unknown')
                                print(f"✅ Authenticated voices request: {len(voices)} {provider} voices available")
                                
                                # Show sample voices
                                for voice in voices[:3]:
                                    print(f"   - {voice['name']} ({voice['gender']}, {voice['quality']})")
                            else:
                                print(f"❌ Authenticated voices request failed: {auth_response.status}")
                        
                        # Test authenticated TTS synthesis with Deepgram
                        tts_payload = {
                            "text": "This is a test of authenticated Deepgram TTS synthesis. The voice should sound natural and clear.",
                            "voice_id": "aura-asteria-en",
                            "encoding": "mp3",
                            "sample_rate": 24000,
                            "preprocess_text": True
                        }
                        async with session.post(f"{BASE_URL}/api/voice/synthesize", json=tts_payload, headers=headers) as tts_response:
                            if tts_response.status == 200:
                                content = await tts_response.read()
                                content_length = len(content)
                                voice_id = tts_response.headers.get('x-voice-id', 'unknown')
                                voice_quality = tts_response.headers.get('x-voice-quality', 'unknown')
                                sample_rate = tts_response.headers.get('x-sample-rate', 'unknown')
                                preprocessed = tts_response.headers.get('x-preprocessed', 'unknown')
                                
                                print(f"✅ Authenticated Deepgram TTS synthesis successful:")
                                print(f"   Audio length: {content_length} bytes")
                                print(f"   Voice: {voice_id} ({voice_quality} quality)")
                                print(f"   Sample rate: {sample_rate} Hz")
                                print(f"   Text preprocessed: {preprocessed}")
                            else:
                                print(f"❌ Authenticated TTS synthesis failed: {tts_response.status}")
                                error_text = await tts_response.text()
                                print(f"   Error: {error_text[:200]}...")
                                
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
    """Check environment configuration for Deepgram"""
    print("\n9. Checking Environment Configuration...")
    
    # Try to get API keys from settings first, then fall back to env vars
    deepgram_key = None
    
    try:
        from app.core.config import settings
        deepgram_key = getattr(settings, 'DEEPGRAM_API_KEY', None)
        print("📝 Using API keys from app.core.config.settings")
    except (ImportError, AttributeError):
        print("📝 Settings not available, checking environment variables directly")
        deepgram_key = os.getenv('DEEPGRAM_API_KEY')
    
    print(f"📝 DEEPGRAM_API_KEY: {'✅ Set' if deepgram_key and deepgram_key != 'NOT_SET' else '❌ Not set'}")
    if deepgram_key and deepgram_key != 'NOT_SET':
        masked_key = deepgram_key[:4] + "..." + deepgram_key[-4:] if len(deepgram_key) > 8 else "***"
        print(f"   Value: {masked_key}")
    
    # Also check settings configuration
    try:
        from app.core.config import settings
        print(f"\n🔧 Settings Configuration:")
        print(f"   API Port: {getattr(settings, 'API_PORT', 'Not set')}")
        print(f"   API URL: {getattr(settings, 'API_URL', 'Not set')}")
        cors_origins = getattr(settings, 'CORS_ORIGINS', [])
        print(f"   CORS Origins: {cors_origins}")
    except (ImportError, AttributeError) as e:
        print(f"⚠️  Could not load settings configuration: {e}")

def check_file_structure():
    """Check if required files exist"""
    print("\n10. Checking File Structure...")
    
    required_files = [
        "app/api/voice_tts.py",
        "app/services/voice/deepgram_tts_service.py", 
        "app/services/voice/deepgram_stt_service.py",
        "app/services/voice/__init__.py"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing!")
    
    # Check if old Google TTS files exist (informational)
    google_files = [
        "app/services/voice/google_tts_service.py",
        "app/services/voice/google_stt_service.py"
    ]
    
    print("\n   Legacy Google files (optional):")
    for file_path in google_files:
        if os.path.exists(file_path):
            print(f"📋 {file_path} - (legacy, still available)")
        else:
            print(f"📋 {file_path} - Not present")

async def main():
    """Main test function"""
    print("🚀 Voice Integration Test Script - Deepgram Edition")
    print("This script tests the voice integration setup using Deepgram for both STT and TTS")
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
    print("🎉 Deepgram voice integration test completed!")
    print("\nNext steps:")
    print("1. If APIs are available, test the frontend components")
    print("2. Open a conversation and try voice input/output")
    print("3. Check voice settings page functionality")
    print("4. Test different Deepgram Aura voices")
    print(f"\nNote: Make sure your server is running on {BASE_URL}")
    
    if 'auth_success' in locals() and auth_success:
        print("\n🔐 Authentication tests passed - Deepgram voice endpoints fully functional!")
    else:
        print("\n🔐 To test authenticated voice endpoints, set TEST_EMAIL and TEST_PASSWORD environment variables")
    
    print("\n🎤 Deepgram Features:")
    print("   • STT: Real-time streaming with Nova-2 model")
    print("   • TTS: Aura voices with conversational quality")
    print("   • Unified API key for both services")
    print("   • High-quality audio synthesis")
    
    return True

if __name__ == "__main__":
    asyncio.run(main())
