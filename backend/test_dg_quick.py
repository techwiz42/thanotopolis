#!/usr/bin/env python3
# quick_fix_test.py - Test the parameter None value fix

import asyncio
import os
import sys

async def test_none_value_fix():
    """Test that we properly handle None values in parameters"""
    print("🔧 Testing None Value Fix")
    print("=" * 40)
    
    try:
        # Import the fixed service
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        sys.path.insert(0, os.path.dirname(__file__))
        
        from app.services.voice.deepgram_tts_service import deepgram_tts_service
        
        print(f"✅ Service imported")
        
        if not deepgram_tts_service.api_key:
            print("❌ No API key found")
            return False
        
        # Test 1: MP3 with explicit None values (should work now)
        print(f"\n🎵 Test 1: MP3 with None values")
        result1 = await deepgram_tts_service.synthesize_speech(
            text="Testing MP3 with None values fixed",
            voice_id="aura-asteria-en",
            encoding="mp3",
            sample_rate=None,  # Explicit None
            container=None,    # Explicit None
            preprocess_text=True
        )
        
        if result1["success"]:
            print(f"✅ MP3 with None test: {len(result1['audio'])} bytes")
            print(f"   Actual params used: {result1.get('actual_params', {})}")
            
            with open("none_fix_mp3.mp3", "wb") as f:
                f.write(result1["audio"])
            print(f"💾 Saved: none_fix_mp3.mp3")
        else:
            print(f"❌ MP3 test failed: {result1.get('error')}")
            print(f"   Details: {result1.get('details', 'No details')}")
            return False
        
        # Test 2: WAV with proper values
        print(f"\n🎵 Test 2: WAV with proper values")
        result2 = await deepgram_tts_service.synthesize_speech(
            text="Testing WAV with proper parameter values",
            voice_id="aura-orion-en",
            encoding="linear16",
            sample_rate=24000,
            container="wav",
            preprocess_text=True
        )
        
        if result2["success"]:
            print(f"✅ WAV test: {len(result2['audio'])} bytes")
            print(f"   Actual params used: {result2.get('actual_params', {})}")
            
            with open("none_fix_wav.wav", "wb") as f:
                f.write(result2["audio"])
            print(f"💾 Saved: none_fix_wav.wav")
        else:
            print(f"❌ WAV test failed: {result2.get('error')}")
            return False
        
        # Test 3: Minimal parameters (defaults)
        print(f"\n🎵 Test 3: Minimal parameters")
        result3 = await deepgram_tts_service.synthesize_speech(
            text="Testing with minimal parameters",
            voice_id="aura-luna-en"
            # All other parameters will be defaults/None
        )
        
        if result3["success"]:
            print(f"✅ Minimal test: {len(result3['audio'])} bytes")
            print(f"   Actual params used: {result3.get('actual_params', {})}")
            
            with open("none_fix_minimal.mp3", "wb") as f:
                f.write(result3["audio"])
            print(f"💾 Saved: none_fix_minimal.mp3")
        else:
            print(f"❌ Minimal test failed: {result3.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Test the None value fix"""
    print("🔧 Quick Fix Test: None Value Parameter Handling")
    print("This tests that None values are properly filtered from URL parameters")
    print()
    
    success = await test_none_value_fix()
    
    print(f"\n" + "=" * 50)
    if success:
        print(f"🎉 SUCCESS! None value fix is working!")
        print(f"\n📁 Generated files:")
        print(f"   - none_fix_mp3.mp3")
        print(f"   - none_fix_wav.wav") 
        print(f"   - none_fix_minimal.mp3")
        print(f"\n✅ The service now properly handles None parameters")
    else:
        print(f"❌ Fix still not working - check error details above")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
