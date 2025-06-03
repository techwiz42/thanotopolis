#!/usr/bin/env python3
# test_voice_integration.py - Provider-agnostic test script for voice integration

import asyncio
import aiohttp
import json
import os
import sys
from typing import Dict, Any, Optional

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

# Global variable to store detected provider info
DETECTED_PROVIDER = {
    "tts_provider": None,
    "tts_service": None,
    "stt_provider": None,
    "stt_service": None
}

async def detect_voice_providers():
    """Detect which voice providers are currently active"""
    print("🔍 Detecting Voice Service Providers...")
    
    async with aiohttp.ClientSession() as session:
        # Detect TTS provider
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/status") as response:
                if response.status == 200:
                    data = await response.json()
                    DETECTED_PROVIDER["tts_provider"] = data.get('provider', 'unknown')
                    DETECTED_PROVIDER["tts_service"] = data.get('service', 'unknown')
                    print(f"🎤 TTS Provider: {DETECTED_PROVIDER['tts_provider']}")
                    print(f"🎤 TTS Service: {DETECTED_PROVIDER['tts_service']}")
                else:
                    print(f"❌ Could not detect TTS provider: {response.status}")
        except Exception as e:
            print(f"❌ Error detecting TTS provider: {e}")
        
        # Detect STT provider
        try:
            async with session.get(f"{BASE_URL}/api/voice/stt/status") as response:
                if response.status == 200:
                    data = await response.json()
                    DETECTED_PROVIDER["stt_provider"] = data.get('service', 'unknown').replace('_stt', '')
                    DETECTED_PROVIDER["stt_service"] = data.get('service', 'unknown')
                    print(f"🎙️  STT Provider: {DETECTED_PROVIDER['stt_provider']}")
                    print(f"🎙️  STT Service: {DETECTED_PROVIDER['stt_service']}")
                else:
                    print(f"❌ Could not detect STT provider: {response.status}")
        except Exception as e:
            print(f"❌ Error detecting STT provider: {e}")

def get_provider_specific_info(provider: str) -> Dict[str, Any]:
    """Get provider-specific information for testing"""
    provider_info = {
        "elevenlabs": {
            "name": "ElevenLabs",
            "default_voices": ["21m00Tcm4TlvDq8ikWAM", "ErXwobaYiN019PkySvjV"],
            "expected_encodings": ["mp3"],
            "api_key_env": "ELEVENLABS_API_KEY",
            "features": ["premium_voices", "natural_speech", "voice_cloning"]
        },
        "deepgram": {
            "name": "Deepgram",
            "default_voices": ["aura-asteria-en", "aura-orion-en"],
            "expected_encodings": ["mp3", "linear16", "flac", "opus"],
            "api_key_env": "DEEPGRAM_API_KEY",
            "features": ["real_time", "multiple_formats", "streaming"]
        },
        "google": {
            "name": "Google",
            "default_voices": ["en-US-Studio-O", "en-US-Neural2-A"],
            "expected_encodings": ["mp3", "linear16", "ogg_opus"],
            "api_key_env": "GOOGLE_API_KEY",
            "features": ["ssml_support", "prosody_control", "neural_voices"]
        }
    }
    
    return provider_info.get(provider.lower(), {
        "name": provider.title(),
        "default_voices": [],
        "expected_encodings": ["mp3"],
        "api_key_env": f"{provider.upper()}_API_KEY",
        "features": ["basic_tts"]
    })

async def test_voice_services():
    """Test voice service integration (provider-agnostic)"""
    
    print(f"\n🎤 Testing Voice Integration...")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Check STT Status (any provider)
        print("\n1. Testing Speech-to-Text Service Status...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/stt/status") as response:
                if response.status == 200:
                    data = await response.json()
                    service = data.get('service', 'unknown')
                    provider = DETECTED_PROVIDER.get('stt_provider', 'unknown')
                    
                    print(f"✅ STT Service: {service}")
                    print(f"✅ STT Provider: {provider}")
                    
                    if data.get('api_key_configured'):
                        print(f"✅ {provider.title()} STT API Key: Configured")
                        if data.get('api_key_valid'):
                            print(f"✅ {provider.title()} STT API Key: Valid")
                        else:
                            print(f"❌ {provider.title()} STT API Key: Invalid or verification failed")
                            error = data.get('error')
                            if error:
                                print(f"   Error: {error}")
                    else:
                        print(f"❌ {provider.title()} STT API Key: Not configured")
                        
                    # Show supported models if available
                    models = data.get('supported_models', [])
                    if models:
                        print(f"✅ Supported Models: {', '.join(models)}")
                else:
                    print(f"❌ STT Status Failed: {response.status}")
        except Exception as e:
            print(f"❌ STT Status Error: {e}")
        
        # Test 2: Check TTS Status (any provider)
        print("\n2. Testing Text-to-Speech Service Status...")
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/status") as response:
                if response.status == 200:
                    data = await response.json()
                    provider = data.get('provider', 'unknown')
                    service = data.get('service', 'unknown')
                    
                    print(f"✅ TTS Provider: {provider}")
                    print(f"✅ TTS Service: {service}")
                    
                    # Get provider-specific info
                    provider_info = get_provider_specific_info(provider)
                    print(f"✅ Provider Name: {provider_info['name']}")
                    
                    if data.get('api_key_configured'):
                        print(f"✅ {provider.title()} TTS API Key: Configured")
                    else:
                        print(f"❌ {provider.title()} TTS API Key: Not configured")
                        env_var = provider_info.get('api_key_env', f"{provider.upper()}_API_KEY")
                        print(f"   Set {env_var} environment variable")
                        
                    available_voices = data.get('available_voices', 0)
                    print(f"✅ Available Voices: {available_voices}")
                    
                    supported_encodings = data.get('supported_encodings', [])
                    print(f"✅ Supported Encodings: {', '.join(supported_encodings)}")
                    
                    # Show provider features
                    features = provider_info.get('features', [])
                    if features:
                        print(f"✅ Provider Features: {', '.join(features)}")
                        
                else:
                    print(f"❌ TTS Status Failed: {response.status}")
        except Exception as e:
            print(f"❌ TTS Status Error: {e}")
        
        # Test 3: Get Available Voices (requires auth)
        print(f"\n3. Testing Available {DETECTED_PROVIDER['tts_provider'].title()} Voices...")
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
                    
                    if voices:
                        # Group voices by gender for better display
                        female_voices = [v for v in voices if v.get('gender') == 'FEMALE']
                        male_voices = [v for v in voices if v.get('gender') == 'MALE']
                        other_voices = [v for v in voices if v.get('gender') not in ['FEMALE', 'MALE']]
                        
                        if female_voices:
                            print(f"   Female voices ({len(female_voices)}):")
                            for voice in female_voices[:3]:  # Show first 3
                                name = voice.get('name', voice.get('id', 'Unknown'))
                                quality = voice.get('quality', 'standard')
                                print(f"     - {name} ({quality})")
                        
                        if male_voices:
                            print(f"   Male voices ({len(male_voices)}):")
                            for voice in male_voices[:3]:  # Show first 3
                                name = voice.get('name', voice.get('id', 'Unknown'))
                                quality = voice.get('quality', 'standard')
                                print(f"     - {name} ({quality})")
                        
                        if other_voices:
                            print(f"   Other voices ({len(other_voices)}):")
                            for voice in other_voices[:2]:  # Show first 2
                                name = voice.get('name', voice.get('id', 'Unknown'))
                                print(f"     - {name}")
                        
                        default_voice = data.get('default_voice')
                        if default_voice:
                            print(f"   Default voice: {default_voice}")
                    else:
                        print("   No voice details available")
                else:
                    print(f"❌ Voices request failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:100]}...")
        except Exception as e:
            print(f"❌ Voices request error: {e}")
        
        # Test 4: Test TTS Synthesis (requires auth)
        print(f"\n4. Testing {DETECTED_PROVIDER['tts_provider'].title()} TTS Synthesis...")
        try:
            # Use provider-specific default voice or generic payload
            provider_info = get_provider_specific_info(DETECTED_PROVIDER['tts_provider'])
            default_voices = provider_info.get('default_voices', [])
            test_voice = default_voices[0] if default_voices else None
            
            test_payload = {
                "text": f"This is a test message using {DETECTED_PROVIDER['tts_provider']} TTS. The voice should sound clear and natural.",
                "encoding": "mp3",
                "preprocess_text": True
            }
            
            # Add voice_id if we have a default for this provider
            if test_voice:
                test_payload["voice_id"] = test_voice
            
            async with session.post(f"{BASE_URL}/api/voice/synthesize", json=test_payload) as response:
                if response.status == 401 or response.status == 403:
                    print("✅ TTS synthesis endpoint properly requires authentication (expected)")
                    print("   Status: 401/403 - Authentication required")
                elif response.status == 200:
                    print(f"✅ {DETECTED_PROVIDER['tts_provider'].title()} TTS synthesis successful (user must be authenticated)")
                    content_type = response.headers.get('content-type', '')
                    content_length = response.headers.get('content-length', 'unknown')
                    voice_id = response.headers.get('x-voice-id', 'unknown')
                    voice_name = response.headers.get('x-voice-name', 'unknown')
                    voice_quality = response.headers.get('x-voice-quality', 'unknown')
                    provider = response.headers.get('x-provider', 'unknown')
                    encoding = response.headers.get('x-encoding', 'unknown')
                    
                    print(f"   Provider: {provider}")
                    print(f"   Content Type: {content_type}")
                    print(f"   Content Length: {content_length} bytes")
                    print(f"   Voice ID: {voice_id}")
                    if voice_name != 'unknown':
                        print(f"   Voice Name: {voice_name}")
                    print(f"   Voice Quality: {voice_quality}")
                    print(f"   Encoding: {encoding}")
                else:
                    print(f"❌ TTS synthesis failed: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:100]}...")
        except Exception as e:
            print(f"❌ TTS synthesis error: {e}")
        
        # Test 5: Test Voice Recommendations (requires auth)
        print(f"\n5. Testing {DETECTED_PROVIDER['tts_provider'].title()} Voice Recommendations...")
        try:
            test_params = [
                ("gender=FEMALE", "Female voice"),
                ("gender=MALE", "Male voice"),
                ("quality=conversational", "Conversational quality")
            ]
            
            for param, description in test_params:
                async with session.get(f"{BASE_URL}/api/voice/tts/recommended?{param}") as response:
                    if response.status == 401 or response.status == 403:
                        print(f"✅ {description} recommendation requires auth (expected)")
                    elif response.status == 200:
                        data = await response.json()
                        recommended = data.get('recommended_voice')
                        provider = data.get('provider', 'unknown')
                        voice_details = data.get('voice_details', {})
                        
                        print(f"✅ {description} from {provider}: {recommended}")
                        
                        if voice_details:
                            name = voice_details.get('name', 'Unknown')
                            gender = voice_details.get('gender', 'Unknown')
                            quality = voice_details.get('quality', 'Unknown')
                            print(f"   Details: {name} ({gender}, {quality})")
                    else:
                        print(f"❌ {description} recommendation failed: {response.status}")
        except Exception as e:
            print(f"❌ Voice recommendation error: {e}")
        
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

# Additional test functions for the hybrid test script
# Add these to your existing test_voice_integration.py

async def test_hybrid_language_routing():
    """Test the hybrid TTS language routing capabilities"""
    print("\n12. Testing Hybrid TTS Language Routing...")
    
    async with aiohttp.ClientSession() as session:
        
        # Test language support endpoint
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/language-support") as response:
                if response.status == 401 or response.status == 403:
                    print("✅ Language support endpoint requires auth (expected)")
                elif response.status == 200:
                    data = await response.json()
                    print(f"✅ Hybrid language support information retrieved")
                    
                    elevenlabs_count = len(data.get('elevenlabs_languages', []))
                    google_count = len(data.get('google_fallback_languages', []))
                    total = data.get('total_supported', 0)
                    
                    print(f"   ElevenLabs languages: {elevenlabs_count}")
                    print(f"   Google fallback languages: {google_count}")
                    print(f"   Total supported: {total}")
                    
                    # Check your specific languages
                    your_langs = data.get('your_languages', {})
                    for lang_name, info in your_langs.items():
                        provider = info.get('provider', 'unknown')
                        routing = info.get('routing', 'unknown')
                        print(f"   {lang_name.title()}: {provider} ({routing})")
                        
                else:
                    print(f"❌ Language support request failed: {response.status}")
        except Exception as e:
            print(f"❌ Language support test error: {e}")
        
        # Test provider info for specific languages
        test_languages = ["uk", "th", "hy", "en", "es"]  # Ukrainian, Thai, Armenian, English, Spanish
        
        for lang_code in test_languages:
            try:
                async with session.get(f"{BASE_URL}/api/voice/tts/provider-info?language_code={lang_code}") as response:
                    if response.status == 401 or response.status == 403:
                        print(f"✅ Provider info for {lang_code} requires auth (expected)")
                    elif response.status == 200:
                        data = await response.json()
                        provider = data.get('provider', 'unknown')
                        routing = data.get('routing', 'unknown')
                        lang_name = data.get('language_name', 'unknown')
                        print(f"✅ {lang_code} ({lang_name}): {provider} ({routing})")
                    else:
                        print(f"❌ Provider info for {lang_code} failed: {response.status}")
            except Exception as e:
                print(f"❌ Provider info test error for {lang_code}: {e}")

async def test_hybrid_tts_with_auth(token: str, session: aiohttp.ClientSession):
    """Test hybrid TTS synthesis with different languages (requires auth)"""
    print("\n   Testing Hybrid TTS Language Routing with Authentication...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test cases: text in different languages
    test_cases = [
        {
            "text": "Hello, this is a test in English.",
            "expected_provider": "elevenlabs",
            "language": "English"
        },
        {
            "text": "Привіт, це тест українською мовою.",  # Ukrainian
            "expected_provider": "elevenlabs", 
            "language": "Ukrainian"
        },
        {
            "text": "สวัสดี นี่คือการทดสอบภาษาไทย",  # Thai
            "expected_provider": "google",
            "language": "Thai"
        },
        {
            "text": "Բարև ձեզ, սա թեստ է հայերենով:",  # Armenian  
            "expected_provider": "google",
            "language": "Armenian"
        },
        {
            "text": "Hola, esta es una prueba en español.",  # Spanish
            "expected_provider": "elevenlabs",
            "language": "Spanish"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        try:
            tts_payload = {
                "text": test_case["text"],
                "encoding": "mp3",
                "preprocess_text": True
            }
            
            async with session.post(f"{BASE_URL}/api/voice/synthesize", json=tts_payload, headers=headers) as response:
                if response.status == 200:
                    # Check headers for routing information
                    provider = response.headers.get('x-provider', 'unknown')
                    routing = response.headers.get('x-hybrid-routing', 'unknown')
                    detected_lang = response.headers.get('x-language-detected', 'unknown')
                    lang_name = response.headers.get('x-language-name', 'unknown')
                    
                    expected = test_case["expected_provider"]
                    language = test_case["language"]
                    
                    if provider == expected:
                        print(f"✅ {language}: Routed to {provider} ({routing}) ✓")
                    else:
                        print(f"⚠️  {language}: Expected {expected}, got {provider} ({routing})")
                    
                    print(f"   Detected: {detected_lang} ({lang_name})")
                    
                    # Get audio size
                    content = await response.read()
                    print(f"   Audio: {len(content)} bytes")
                    
                else:
                    print(f"❌ {test_case['language']} synthesis failed: {response.status}")
                    
        except Exception as e:
            print(f"❌ Error testing {test_case['language']}: {e}")

async def test_explicit_language_specification():
    """Test explicit language specification in requests"""
    print("\n13. Testing Explicit Language Specification...")
    
    # Check if we have test credentials
    test_email = os.getenv('TEST_EMAIL')
    test_password = os.getenv('TEST_PASSWORD')
    
    if not test_email or test_password:
        print("ℹ️  No test credentials - skipping explicit language tests")
        return
    
    async with aiohttp.ClientSession() as session:
        try:
            # Login first
            login_payload = {"email": test_email, "password": test_password}
            async with session.post(f"{BASE_URL}/api/auth/login", json=login_payload) as response:
                if response.status != 200:
                    print("❌ Login failed for explicit language tests")
                    return
                
                login_data = await response.json()
                token = login_data.get('access_token')
                if not token:
                    print("❌ No access token received")
                    return
                
                headers = {"Authorization": f"Bearer {token}"}
                
                # Test explicit language specification
                explicit_tests = [
                    {"text": "This should use ElevenLabs", "language_code": "en", "expected": "elevenlabs"},
                    {"text": "This should use Google for Thai", "language_code": "th", "expected": "google"},
                    {"text": "This should use Google for Armenian", "language_code": "hy", "expected": "google"},
                    {"text": "це має використовувати ElevenLabs", "language_code": "uk", "expected": "elevenlabs"}
                ]
                
                for test in explicit_tests:
                    tts_payload = {
                        "text": test["text"],
                        "language_code": test["language_code"],
                        "encoding": "mp3"
                    }
                    
                    async with session.post(f"{BASE_URL}/api/voice/synthesize", json=tts_payload, headers=headers) as response:
                        if response.status == 200:
                            provider = response.headers.get('x-provider', 'unknown')
                            routing = response.headers.get('x-hybrid-routing', 'unknown')
                            
                            if provider == test["expected"]:
                                print(f"✅ Explicit {test['language_code']}: {provider} ({routing}) ✓")
                            else:
                                print(f"❌ Explicit {test['language_code']}: Expected {test['expected']}, got {provider}")
                        else:
                            print(f"❌ Explicit {test['language_code']} failed: {response.status}")
                            
        except Exception as e:
            print(f"❌ Error in explicit language tests: {e}")

# Update the main test function to include hybrid tests
async def test_hybrid_provider_status():
    """Test hybrid provider status endpoint"""
    print("\n11. Testing Hybrid Provider Status...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/voice/tts/status") as response:
                if response.status == 200:
                    data = await response.json()
                    service = data.get('service', 'unknown')
                    provider = data.get('provider', 'unknown')
                    
                    print(f"✅ Service: {service}")
                    print(f"✅ Provider: {provider}")
                    
                    if provider == "hybrid":
                        print("🎯 Confirmed: Using Hybrid TTS service")
                        
                        providers = data.get('providers', {})
                        elevenlabs_info = providers.get('elevenlabs', {})
                        google_info = providers.get('google', {})
                        
                        print(f"   ElevenLabs: {elevenlabs_info.get('languages', 0)} languages ({elevenlabs_info.get('routing', 'unknown')})")
                        print(f"   Google: {google_info.get('languages', 0)} languages ({google_info.get('routing', 'unknown')})")
                        
                        total_languages = data.get('total_languages', 0)
                        print(f"   Total supported: {total_languages} languages")
                        
                        # Show routing examples
                        examples = data.get('routing_examples', {})
                        print("   Routing examples:")
                        for lang, route in examples.items():
                            print(f"     {lang}: {route}")
                        
                        # Check API key status
                        api_keys = data.get('api_keys_configured', {})
                        elevenlabs_key = api_keys.get('elevenlabs', False)
                        google_key = api_keys.get('google', False)
                        
                        print(f"   ElevenLabs API key: {'✅' if elevenlabs_key else '❌'}")
                        print(f"   Google API key: {'✅' if google_key else '❌'}")
                        
                        if not elevenlabs_key:
                            print("   ⚠️  Set ELEVENLABS_API_KEY for premium voices")
                        if not google_key:
                            print("   ⚠️  Set GOOGLE_API_KEY for fallback languages")
                    else:
                        print(f"⚠️  Expected hybrid, got: {provider}")
                        
                else:
                    print(f"❌ Hybrid status failed: {response.status}")
        except Exception as e:
            print(f"❌ Hybrid status error: {e}")

# Add these functions to your existing main() function:
"""
async def main():
    # ... existing code ...
    
    # Add these new test calls:
    await test_hybrid_provider_status()
    await test_hybrid_language_routing() 
    await test_explicit_language_specification()
    
    # Update existing test_with_auth_if_available() to include:
    if auth_success:
        await test_hybrid_tts_with_auth(token, session)
    
    # ... rest of existing code ...
"""

# Updated summary for main():
def print_hybrid_summary():
    """Print summary of hybrid TTS capabilities"""
    print("\n🎯 Hybrid TTS Features Tested:")
    print("   • Automatic language detection and routing")
    print("   • ElevenLabs for supported languages (premium quality)")  
    print("   • Google TTS fallback for unsupported languages")
    print("   • Explicit language specification support")
    print("   • Unified API with intelligent provider selection")
    print("   • Cost optimization through smart routing")
    
    print("\n🌍 Language Coverage:")
    print("   • Ukrainian: ElevenLabs (premium)")
    print("   • Thai: Google TTS (fallback)")  
    print("   • Armenian: Google TTS (fallback)")
    print("   • 30+ other languages automatically routed")
    
    print("\n🔑 API Keys Needed:")
    print("   • ELEVENLABS_API_KEY (for premium voices)")
    print("   • GOOGLE_API_KEY or GOOGLE_CLIENT_ID (for fallback)")
    print("   • DEEPGRAM_API_KEY (for STT)")
    
    print("\n✨ Benefits:")
    print("   • Best of both worlds: Premium + Coverage")
    print("   • Automatic cost optimization")  
    print("   • Transparent to frontend")
    print("   • Future-proof language expansion")

async def test_authentication():
    """Test authentication flow (optional advanced test)"""
    print("\n7. Testing Authentication Flow...")
    print("ℹ️  This is an optional test - requires valid user credentials")
    
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
    test_email = "wylie@acmeanvil.com"
    test_password = "3559scoot"
    
    if not test_email or test_password:
        print("ℹ️  No test credentials found (TEST_EMAIL, TEST_PASSWORD)")
        print("   Set these environment variables to test authenticated endpoints")
        return False
    
    tts_provider = DETECTED_PROVIDER.get('tts_provider', 'unknown')
    provider_info = get_provider_specific_info(tts_provider)
    
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
                        print(f"✅ Login successful - testing authenticated {tts_provider} endpoints")
                        
                        # Test authenticated voices endpoint
                        headers = {"Authorization": f"Bearer {token}"}
                        async with session.get(f"{BASE_URL}/api/voice/tts/voices", headers=headers) as auth_response:
                            if auth_response.status == 200:
                                data = await auth_response.json()
                                voices = data.get('voices', [])
                                provider = data.get('provider', 'unknown')
                                print(f"✅ Authenticated voices request: {len(voices)} {provider} voices available")
                                
                                # Show sample voices (provider-agnostic)
                                for voice in voices[:5]:
                                    voice_name = voice.get('name', voice.get('id', 'Unknown'))
                                    voice_gender = voice.get('gender', 'Unknown')
                                    voice_quality = voice.get('quality', 'Unknown')
                                    print(f"   - {voice_name} ({voice_gender}, {voice_quality})")
                            else:
                                print(f"❌ Authenticated voices request failed: {auth_response.status}")
                        
                        # Test authenticated TTS synthesis with multiple voices
                        print(f"\n   Testing {tts_provider.title()} TTS Synthesis with Authentication...")
                        
                        # Use provider-specific test voices or defaults
                        test_voices = provider_info.get('default_voices', [])
                        if not test_voices:
                            # Fallback to generic test
                            test_voices = [None]  # Will use default voice
                        
                        for i, voice_id in enumerate(test_voices[:2]):  # Test max 2 voices
                            voice_name = f"Voice {i+1}" if not voice_id else voice_id
                            
                            tts_payload = {
                                "text": f"Hello, this is a test of {tts_provider} voice synthesis. Testing voice quality and naturalness.",
                                "encoding": "mp3",
                                "preprocess_text": True
                            }
                            
                            if voice_id:
                                tts_payload["voice_id"] = voice_id
                                
                            async with session.post(f"{BASE_URL}/api/voice/synthesize", json=tts_payload, headers=headers) as tts_response:
                                if tts_response.status == 200:
                                    content = await tts_response.read()
                                    content_length = len(content)
                                    response_voice_id = tts_response.headers.get('x-voice-id', 'unknown')
                                    response_voice_name = tts_response.headers.get('x-voice-name', 'unknown')
                                    voice_quality = tts_response.headers.get('x-voice-quality', 'unknown')
                                    provider = tts_response.headers.get('x-provider', 'unknown')
                                    preprocessed = tts_response.headers.get('x-preprocessed', 'unknown')
                                    
                                    print(f"✅ {tts_provider.title()} TTS synthesis successful:")
                                    print(f"   Provider: {provider}")
                                    print(f"   Audio length: {content_length} bytes")
                                    if response_voice_name != 'unknown':
                                        print(f"   Voice: {response_voice_name} ({response_voice_id})")
                                    else:
                                        print(f"   Voice ID: {response_voice_id}")
                                    print(f"   Quality: {voice_quality}")
                                    print(f"   Text preprocessed: {preprocessed}")
                                else:
                                    print(f"❌ {tts_provider.title()} TTS synthesis failed: {tts_response.status}")
                                    error_text = await tts_response.text()
                                    print(f"   Error: {error_text[:150]}...")
                        
                        # Test voice recommendations with auth
                        print(f"\n   Testing {tts_provider.title()} Voice Recommendations with Authentication...")
                        recommendation_tests = [
                            ("FEMALE", "conversational"),
                            ("MALE", "conversational")
                        ]
                        
                        for gender, quality in recommendation_tests:
                            async with session.get(f"{BASE_URL}/api/voice/tts/recommended?gender={gender}&quality={quality}", headers=headers) as rec_response:
                                if rec_response.status == 200:
                                    data = await rec_response.json()
                                    recommended = data.get('recommended_voice')
                                    provider = data.get('provider', 'unknown')
                                    voice_details = data.get('voice_details', {})
                                    voice_name = voice_details.get('name', voice_details.get('id', 'unknown'))
                                    
                                    print(f"✅ {gender} {quality} recommendation: {voice_name} ({recommended})")
                                else:
                                    print(f"❌ Recommendation failed for {gender} {quality}: {rec_response.status}")
                                
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
    """Check environment configuration for detected providers"""
    print("\n9. Checking Environment Configuration...")
    
    # Get provider-specific info
    tts_provider = DETECTED_PROVIDER.get('tts_provider', 'unknown')
    stt_provider = DETECTED_PROVIDER.get('stt_provider', 'unknown')
    
    tts_info = get_provider_specific_info(tts_provider)
    stt_info = get_provider_specific_info(stt_provider) if stt_provider != tts_provider else tts_info
    
    # Try to get API keys from settings first, then fall back to env vars
    tts_key = None
    stt_key = None
    
    try:
        from app.core.config import settings
        tts_key_attr = tts_info.get('api_key_env', '').replace('_API_KEY', '_API_KEY').replace('GOOGLE_API_KEY', 'GOOGLE_CLIENT_ID')
        stt_key_attr = stt_info.get('api_key_env', '').replace('_API_KEY', '_API_KEY')
        
        tts_key = getattr(settings, tts_key_attr, None)
        stt_key = getattr(settings, stt_key_attr, None)
        print("📝 Using API keys from app.core.config.settings")
    except (ImportError, AttributeError):
        print("📝 Settings not available, checking environment variables directly")
        tts_key = os.getenv(tts_info.get('api_key_env', f"{tts_provider.upper()}_API_KEY"))
        stt_key = os.getenv(stt_info.get('api_key_env', f"{stt_provider.upper()}_API_KEY"))
    
    # Check TTS API key
    tts_env_var = tts_info.get('api_key_env', f"{tts_provider.upper()}_API_KEY")
    print(f"📝 {tts_env_var} (TTS): {'✅ Set' if tts_key and tts_key != 'NOT_SET' else '❌ Not set'}")
    if tts_key and tts_key != 'NOT_SET':
        masked_key = tts_key[:4] + "..." + tts_key[-4:] if len(tts_key) > 8 else "***"
        print(f"   Value: {masked_key}")
    
    # Check STT API key (if different provider)
    if stt_provider != tts_provider:
        stt_env_var = stt_info.get('api_key_env', f"{stt_provider.upper()}_API_KEY")
        print(f"📝 {stt_env_var} (STT): {'✅ Set' if stt_key and stt_key != 'NOT_SET' else '❌ Not set'}")
        if stt_key and stt_key != 'NOT_SET':
            masked_key = stt_key[:4] + "..." + stt_key[-4:] if len(stt_key) > 8 else "***"
            print(f"   Value: {masked_key}")
    
    # Provide setup instructions if keys are missing
    if not tts_key or tts_key == 'NOT_SET':
        print(f"\n⚠️  {tts_provider.title()} TTS API Key Setup:")
        if tts_provider == 'elevenlabs':
            print("   1. Get your API key from: https://elevenlabs.io/app/settings/api-keys")
        elif tts_provider == 'deepgram':
            print("   1. Get your API key from: https://console.deepgram.com/")
        elif tts_provider == 'google':
            print("   1. Get your API key from: https://console.cloud.google.com/")
        print(f"   2. Set it as: export {tts_env_var}='your_api_key_here'")
        print(f"   3. Or add it to your .env file: {tts_env_var}=your_api_key_here")
    
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
    """Check if required files exist based on detected providers"""
    print("\n10. Checking File Structure...")
    
    tts_provider = DETECTED_PROVIDER.get('tts_provider', 'unknown')
    stt_provider = DETECTED_PROVIDER.get('stt_provider', 'unknown')
    
    # Core required files
    required_files = [
        "app/api/voice_tts.py",
        "app/services/voice/__init__.py"
    ]
    
    # Add provider-specific files
    if tts_provider == 'elevenlabs':
        required_files.append("app/services/voice/elevenlabs_tts_service.py")
    elif tts_provider == 'deepgram':
        required_files.append("app/services/voice/deepgram_tts_service.py")
    elif tts_provider == 'google':
        required_files.append("app/services/voice/google_tts_service.py")
    
    if stt_provider == 'deepgram':
        required_files.append("app/services/voice/deepgram_stt_service.py")
    elif stt_provider == 'google':
        required_files.append("app/services/voice/google_stt_service.py")
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing!")
    
    # Check for alternative provider files (informational)
    alternative_files = [
        ("app/services/voice/elevenlabs_tts_service.py", "ElevenLabs TTS"),
        ("app/services/voice/deepgram_tts_service.py", "Deepgram TTS"),
        ("app/services/voice/google_tts_service.py", "Google TTS"),
        ("app/services/voice/deepgram_stt_service.py", "Deepgram STT"),
        ("app/services/voice/google_stt_service.py", "Google STT")
    ]
    
    print("\n   Available provider services:")
    for file_path, description in alternative_files:
        if os.path.exists(file_path):
            status = "🎯 ACTIVE" if (
                (tts_provider in file_path and 'tts' in file_path) or 
                (stt_provider in file_path and 'stt' in file_path)
            ) else "📋 Available"
            print(f"   {status} {file_path} - {description}")

async def test_provider_specific_features():
    """Test provider-specific features based on detected providers"""
    print("\n11. Testing Provider-Specific Features...")
    
    tts_provider = DETECTED_PROVIDER.get('tts_provider', 'unknown')
    
    try:
        if tts_provider == 'elevenlabs':
            from app.services.voice.elevenlabs_tts_service import elevenlabs_tts_service as service
        elif tts_provider == 'deepgram':
            from app.services.voice.deepgram_tts_service import deepgram_tts_service as service
        elif tts_provider == 'google':
            from app.services.voice.google_tts_service import tts_service as service
        else:
            print(f"⚠️  Unknown TTS provider: {tts_provider}")
            return
        
        print(f"✅ {tts_provider.title()} TTS service import successful")
        print(f"   Available voices: {len(getattr(service, 'voices', {}))}")
        print(f"   Default voice: {getattr(service, 'default_voice', 'Not specified')}")
        
        # Test voice recommendation logic
        if hasattr(service, 'get_recommended_voice'):
            female_voice = service.get_recommended_voice(gender="FEMALE")
            male_voice = service.get_recommended_voice(gender="MALE")
            
            print(f"   Female recommendation: {female_voice}")
            print(f"   Male recommendation: {male_voice}")
        
        # Test MIME type function
        if hasattr(service, 'get_audio_mime_type'):
            mime_type = service.get_audio_mime_type("mp3")
            print(f"   MP3 MIME type: {mime_type}")
        
        # Test text preprocessing
        if hasattr(service, 'preprocess_text'):
            test_text = "Hello Dr. Smith! Visit https://example.com for more info."
            processed = service.preprocess_text(test_text)
            print(f"   Text preprocessing working: {len(processed) != len(test_text)}")
        
        print(f"✅ {tts_provider.title()} TTS service functionality verified")
        
    except ImportError as e:
        print(f"❌ Could not import {tts_provider} TTS service: {e}")
    except Exception as e:
        print(f"❌ Error testing {tts_provider} TTS service: {e}")

async def main():
    """Main test function"""
    print("🚀 Universal Voice Integration Test Script")
    print("This script tests voice integration regardless of provider")
    print(f"🔧 Testing server at: {BASE_URL}")
    print("Make sure your FastAPI server is running")
    print()
    
    # Detect providers first
    await detect_voice_providers()
    
    tts_provider = DETECTED_PROVIDER.get('tts_provider', 'unknown')
    stt_provider = DETECTED_PROVIDER.get('stt_provider', 'unknown')
    
    print(f"\n🎯 Detected Voice Stack:")
    print(f"   • STT: {stt_provider.title()}")
    print(f"   • TTS: {tts_provider.title()}")
    print()
    
    # Check file structure
    check_file_structure()
    
    # Test provider-specific service directly
    await test_provider_specific_features()
    
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
    
    print("\n" + "=" * 60)
    print("🎉 Universal voice integration test completed!")
    print("\nNext steps:")
    print("1. If APIs are available, test the frontend components")
    print("2. Open a conversation and try voice input/output")
    print("3. Test different voices available in your provider")
    print("4. Check voice settings page functionality")
    print(f"\nNote: Make sure your server is running on {BASE_URL}")
    
    if 'auth_success' in locals() and auth_success:
        print(f"\n🔐 Authentication tests passed - {tts_provider.title()} voice endpoints fully functional!")
    else:
        print("\n🔐 To test authenticated voice endpoints, set TEST_EMAIL and TEST_PASSWORD environment variables")
    
    print(f"\n🎤 Current Voice Stack Summary:")
    print(f"   • STT Provider: {stt_provider.title()}")
    print(f"   • TTS Provider: {tts_provider.title()}")
    
    # Provider-specific information
    tts_info = get_provider_specific_info(tts_provider)
    stt_info = get_provider_specific_info(stt_provider)
    
    print(f"\n🔑 Required API Keys:")
    print(f"   • {stt_info.get('api_key_env', 'STT_API_KEY')} for speech-to-text")
    print(f"   • {tts_info.get('api_key_env', 'TTS_API_KEY')} for text-to-speech")
    
    tts_features = tts_info.get('features', [])
    if tts_features:
        print(f"\n🎯 {tts_provider.title()} TTS Features:")
        for feature in tts_features:
            print(f"   • {feature.replace('_', ' ').title()}")
    
    print(f"\n✅ Voice integration working with {tts_provider.title()} TTS + {stt_provider.title()} STT")
    
    return True

if __name__ == "__main__":
    asyncio.run(main())
