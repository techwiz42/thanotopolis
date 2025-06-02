#!/usr/bin/env python3
# final_tts_test.py - Test the corrected Deepgram TTS service

import asyncio
import os
import sys

async def test_corrected_service():
    """Test the corrected TTS service implementation"""
    print("🧪 Testing Corrected Deepgram TTS Service")
    print("=" * 50)
    
    try:
        # Import the corrected service
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        sys.path.insert(0, os.path.dirname(__file__))
        
        from app.services.voice.deepgram_tts_service import deepgram_tts_service
        
        print(f"✅ Service imported successfully")
        print(f"📋 API key configured: {bool(deepgram_tts_service.api_key)}")
        
        if not deepgram_tts_service.api_key:
            print("❌ No API key found")
            return False
        
        # Test 1: MP3 format (working combination)
        print(f"\n🎵 Test 1: MP3 Format (working combination)")
        result1 = await deepgram_tts_service.synthesize_speech(
            text="Testing MP3 format with corrected parameters",
            voice_id="aura-asteria-en",
            encoding="mp3",
            # Note: No container or sample_rate for MP3
            preprocess_text=True
        )
        
        if result1["success"]:
            print(f"✅ MP3 test successful: {len(result1['audio'])} bytes")
            print(f"   Voice: {result1.get('voice_id')}")
            print(f"   Actual params: {result1.get('actual_params', {})}")
            
            with open("corrected_mp3_test.mp3", "wb") as f:
                f.write(result1["audio"])
            print(f"💾 Saved: corrected_mp3_test.mp3")
        else:
            print(f"❌ MP3 test failed: {result1.get('error')}")
            return False
        
        # Test 2: WAV format (working combination)
        print(f"\n🎵 Test 2: WAV Format (working combination)")
        result2 = await deepgram_tts_service.synthesize_speech(
            text="Testing WAV format with linear16 encoding",
            voice_id="aura-orion-en",  # Try male voice
            encoding="linear16",
            container="wav",
            sample_rate=24000,
            preprocess_text=True
        )
        
        if result2["success"]:
            print(f"✅ WAV test successful: {len(result2['audio'])} bytes")
            print(f"   Voice: {result2.get('voice_id')}")
            print(f"   Actual params: {result2.get('actual_params', {})}")
            
            with open("corrected_wav_test.wav", "wb") as f:
                f.write(result2["audio"])
            print(f"💾 Saved: corrected_wav_test.wav")
        else:
            print(f"❌ WAV test failed: {result2.get('error')}")
            return False
        
        # Test 3: Default format (minimal parameters)
        print(f"\n🎵 Test 3: Default Format (minimal parameters)")
        result3 = await deepgram_tts_service.synthesize_speech(
            text="Testing default format with minimal parameters",
            voice_id="aura-luna-en",  # Try different female voice
            # Use all defaults for other parameters
        )
        
        if result3["success"]:
            print(f"✅ Default test successful: {len(result3['audio'])} bytes")
            print(f"   Voice: {result3.get('voice_id')}")
            print(f"   Actual params: {result3.get('actual_params', {})}")
            
            with open("corrected_default_test.mp3", "wb") as f:
                f.write(result3["audio"])
            print(f"💾 Saved: corrected_default_test.mp3")
        else:
            print(f"❌ Default test failed: {result3.get('error')}")
            return False
        
        # Test 4: Voice selection
        print(f"\n🎭 Test 4: Voice Selection")
        voices = deepgram_tts_service.get_available_voices()
        print(f"✅ Available voices: {len(voices)}")
        
        # Test recommended voice function
        recommended_female = deepgram_tts_service.get_recommended_voice(gender="FEMALE")
        recommended_male = deepgram_tts_service.get_recommended_voice(gender="MALE")
        
        print(f"📋 Recommended female voice: {recommended_female}")
        print(f"📋 Recommended male voice: {recommended_male}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing service: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_endpoint_simulation():
    """Simulate API endpoint calls"""
    print(f"\n" + "=" * 50)
    print(f"🌐 Simulating API Endpoint Calls")
    
    try:
        from app.services.voice.deepgram_tts_service import deepgram_tts_service
        
        # Simulate the API request format
        class MockRequest:
            def __init__(self, text, voice_id=None, encoding="mp3", sample_rate=None, container=None, preprocess_text=True):
                self.text = text
                self.voice_id = voice_id
                self.encoding = encoding
                self.sample_rate = sample_rate
                self.container = container
                self.preprocess_text = preprocess_text
        
        # Test case 1: Standard MP3 request (like from frontend)
        print(f"\n📡 API Test 1: Standard MP3 Request")
        request1 = MockRequest(
            text="Hello, this is a test from the API endpoint",
            voice_id="aura-asteria-en",
            encoding="mp3"
        )
        
        result = await deepgram_tts_service.synthesize_speech(
            text=request1.text,
            voice_id=request1.voice_id,
            encoding=request1.encoding,
            sample_rate=request1.sample_rate,
            container=request1.container,
            preprocess_text=request1.preprocess_text
        )
        
        if result["success"]:
            print(f"✅ API MP3 test successful: {len(result['audio'])} bytes")
            mime_type = deepgram_tts_service.get_audio_mime_type(request1.encoding)
            print(f"📋 MIME type: {mime_type}")
        else:
            print(f"❌ API MP3 test failed: {result}")
            return False
        
        # Test case 2: WAV request
        print(f"\n📡 API Test 2: WAV Request")
        request2 = MockRequest(
            text="Testing WAV output from API endpoint",
            voice_id="aura-orion-en",
            encoding="linear16",
            container="wav",
            sample_rate=24000
        )
        
        result = await deepgram_tts_service.synthesize_speech(
            text=request2.text,
            voice_id=request2.voice_id,
            encoding=request2.encoding,
            sample_rate=request2.sample_rate,
            container=request2.container,
            preprocess_text=request2.preprocess_text
        )
        
        if result["success"]:
            print(f"✅ API WAV test successful: {len(result['audio'])} bytes")
            mime_type = deepgram_tts_service.get_audio_mime_type(request2.encoding)
            print(f"📋 MIME type: {mime_type}")
        else:
            print(f"❌ API WAV test failed: {result}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error in API simulation: {e}")
        return False

async def main():
    """Main test function"""
    print("🔧 Final Test: Corrected Deepgram TTS Service")
    print("This tests the service with the corrected parameter handling")
    print()
    
    # Test the service implementation
    service_success = await test_corrected_service()
    
    # Test API endpoint simulation
    api_success = await test_api_endpoint_simulation()
    
    # Summary
    print(f"\n" + "=" * 50)
    print(f"📊 Final Test Results:")
    print(f"   Service implementation: {'✅ PASSED' if service_success else '❌ FAILED'}")
    print(f"   API endpoint simulation: {'✅ PASSED' if api_success else '❌ FAILED'}")
    
    if service_success and api_success:
        print(f"\n🎉 SUCCESS! Deepgram TTS service is now working correctly!")
        print(f"\n📁 Generated test files:")
        print(f"   - corrected_mp3_test.mp3 (MP3 format)")
        print(f"   - corrected_wav_test.wav (WAV format)")
        print(f"   - corrected_default_test.mp3 (Default format)")
        print(f"\n🎵 Play these files to verify audio quality")
        print(f"\n✅ The service is ready for production use!")
        
        print(f"\n📋 Working Parameter Combinations:")
        print(f"   MP3: encoding='mp3' (no container/sample_rate)")
        print(f"   WAV: encoding='linear16', container='wav', sample_rate=24000")
        print(f"   Default: Just model name (uses Deepgram defaults)")
        
    else:
        print(f"\n❌ Some tests still failing - check logs above")
    
    return service_success and api_success

if __name__ == "__main__":
    asyncio.run(main())
