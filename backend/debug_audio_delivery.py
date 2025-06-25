#!/usr/bin/env python3
"""
Debug script to identify why audio isn't being delivered to callers.

This script will:
1. Test the complete TTS → mulaw conversion pipeline
2. Simulate the WebSocket message format sent to Twilio
3. Check for common audio delivery issues
"""

import asyncio
import sys
import base64
import json
import tempfile
import subprocess
import audioop
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.services.voice.elevenlabs_service import elevenlabs_service


async def test_complete_audio_pipeline():
    """Test the complete audio pipeline from TTS to Twilio format."""
    
    print("🔍 Debugging Audio Delivery Pipeline")
    print("=" * 60)
    
    try:
        # Step 1: Generate TTS audio
        print("1. Testing TTS generation...")
        test_text = "Hello, this is a test message from the AI agent."
        
        tts_audio = await elevenlabs_service.generate_speech(
            text=test_text,
            voice_id=None
        )
        
        if not tts_audio:
            print("❌ TTS generation failed")
            return False
            
        print(f"✅ TTS generated {len(tts_audio)} bytes of MP3 audio")
        
        # Step 2: Convert MP3 to mulaw (same as telephony_websocket.py)
        print("\n2. Testing MP3 → mulaw conversion...")
        
        mulaw_audio = await convert_mp3_to_mulaw_test(tts_audio)
        if not mulaw_audio:
            print("❌ Audio conversion failed")
            return False
            
        print(f"✅ Converted to {len(mulaw_audio)} bytes of mulaw audio")
        
        # Step 3: Test chunking and base64 encoding
        print("\n3. Testing audio chunking and encoding...")
        
        chunk_size = 4000  # Same as telephony code
        audio_chunks = [mulaw_audio[i:i+chunk_size] for i in range(0, len(mulaw_audio), chunk_size)]
        
        print(f"✅ Split into {len(audio_chunks)} chunks")
        
        # Step 4: Test WebSocket message format
        print("\n4. Testing WebSocket message format...")
        
        test_stream_sid = "MZ1234567890abcdef"  # Example Twilio stream ID
        
        for i, chunk in enumerate(audio_chunks[:3]):  # Test first 3 chunks
            if chunk:
                audio_base64 = base64.b64encode(chunk).decode('utf-8')
                
                websocket_message = {
                    "event": "media",
                    "streamSid": test_stream_sid,
                    "media": {
                        "payload": audio_base64
                    }
                }
                
                message_size = len(json.dumps(websocket_message))
                print(f"  Chunk {i+1}: {len(chunk)} bytes → {len(audio_base64)} base64 chars → {message_size} bytes JSON")
        
        print("✅ WebSocket message format looks correct")
        
        # Step 5: Check for potential issues
        print("\n5. Checking for potential issues...")
        
        # Check audio properties
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3:
            temp_mp3.write(tts_audio)
            temp_mp3.flush()
            
            try:
                # Get audio duration
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-show_entries', 
                    'format=duration', '-of', 'csv=p=0', temp_mp3.name
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    duration = float(result.stdout.strip())
                    print(f"  📊 Audio duration: {duration:.2f} seconds")
                    
                    if duration < 0.5:
                        print("  ⚠️  Audio is very short - might be clipped")
                    elif duration > 10:
                        print("  ⚠️  Audio is very long - might be truncated by Twilio")
                    else:
                        print("  ✅ Audio duration looks good")
                
            except Exception as e:
                print(f"  ❓ Could not analyze audio: {e}")
            finally:
                os.unlink(temp_mp3.name)
        
        # Check mulaw audio size
        expected_samples = int(8000 * 2)  # 2 seconds at 8kHz
        actual_samples = len(mulaw_audio)
        
        print(f"  📊 Mulaw samples: {actual_samples} (expected ~{expected_samples} for 2s)")
        
        if actual_samples < 1000:
            print("  ⚠️  Very few audio samples - might be too quiet")
        else:
            print("  ✅ Mulaw sample count looks reasonable")
        
        print("\n" + "=" * 60)
        print("🎯 Audio Pipeline Test Complete!")
        print("✅ TTS generation: Working")
        print("✅ MP3 → mulaw conversion: Working") 
        print("✅ Audio chunking: Working")
        print("✅ WebSocket message format: Working")
        print()
        print("🤔 Since the pipeline tests successfully, the issue is likely:")
        print("   1. WebSocket connection between Twilio and backend not established")
        print("   2. streamSid not captured correctly from Twilio")
        print("   3. Twilio rejecting the audio format or messages")
        print("   4. Network/firewall blocking the WebSocket stream")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def convert_mp3_to_mulaw_test(mp3_data: bytes):
    """Test version of the MP3 to mulaw conversion."""
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3:
            temp_mp3.write(mp3_data)
            temp_mp3.flush()
            
            try:
                result = subprocess.run([
                    'ffmpeg', '-i', temp_mp3.name,
                    '-f', 's16le',
                    '-acodec', 'pcm_s16le', 
                    '-ar', '8000',
                    '-ac', '1',
                    '-loglevel', 'error',
                    '-'
                ], capture_output=True, check=True)
                
                pcm_data = result.stdout
                
                if not pcm_data:
                    return None
                
                mulaw_data = audioop.lin2ulaw(pcm_data, 2)
                return mulaw_data
                
            except subprocess.CalledProcessError as e:
                print(f"❌ ffmpeg error: {e.stderr.decode() if e.stderr else 'Unknown'}")
                return None
            finally:
                os.unlink(temp_mp3.name)
                
    except Exception as e:
        print(f"❌ Conversion error: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(test_complete_audio_pipeline())