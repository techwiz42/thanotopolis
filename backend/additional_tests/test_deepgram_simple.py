#!/usr/bin/env python3
"""
Test Deepgram API key with basic client
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
from app.core.config import settings

async def test_simple_live():
    """Test live transcription with basic Deepgram client."""
    print("🎤 Testing Simple Deepgram Live Connection")
    print("=" * 40)
    
    try:
        # Create simple client without extra options
        client = DeepgramClient(settings.DEEPGRAM_API_KEY)
        print("✅ Deepgram client created")
        
        # Create connection
        connection = client.listen.asynclive.v("1")
        print("✅ Live connection created")
        
        def on_message(*args, **kwargs):
            print(f"📝 Message: {args}")
        
        def on_error(*args, **kwargs):
            print(f"❌ Error: {args}")
        
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Error, on_error)
        
        # Simple options
        options = LiveOptions(
            model="nova-2",
            language="en-US",
            encoding="linear16",
            sample_rate=16000,
            channels=1
        )
        
        print("🔄 Starting connection...")
        started = await connection.start(options)
        
        if started:
            print("✅ Live connection started successfully!")
            
            # Quick finish
            await connection.finish()
            print("✅ Connection finished")
            return True
        else:
            print("❌ Failed to start live connection")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_simple_live())
    if result:
        print("🎉 Simple live test passed!")
    else:
        print("💥 Simple live test failed!")
        sys.exit(1)