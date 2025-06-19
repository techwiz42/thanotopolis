#!/usr/bin/env python3
"""
Test Deepgram live transcription directly
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.voice.deepgram_service import deepgram_service

async def test_live_transcription():
    """Test creating a live transcription session."""
    print("🎤 Testing Deepgram Live Transcription")
    print("=" * 40)
    
    if not deepgram_service.is_available():
        print("❌ Deepgram service not available")
        return False
    
    print("✅ Deepgram service is available")
    
    def on_message(data):
        print(f"📝 Transcript: {data}")
    
    def on_error(error):
        print(f"❌ Error: {error}")
    
    try:
        print("🔄 Creating live transcription session...")
        session = await deepgram_service.start_live_transcription(
            on_message=on_message,
            on_error=on_error,
            interim_results=True
        )
        
        print("✅ Live transcription session created")
        
        print("🔄 Starting session...")
        await session.start()
        
        print("✅ Live transcription session started successfully")
        
        print("🔄 Finishing session...")
        await session.finish()
        
        print("✅ Live transcription session finished")
        return True
        
    except Exception as e:
        print(f"❌ Error in live transcription: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_live_transcription())
    if result:
        print("🎉 Live transcription test passed!")
    else:
        print("💥 Live transcription test failed!")
        sys.exit(1)