#!/usr/bin/env python3
"""Test Deepgram with a file to ensure it's working."""

import asyncio
from app.services.voice.deepgram_service import deepgram_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a simple test audio file with speech
# This creates a WAV file with a sine wave (not speech, but should trigger something)
import wave
import array
import math

def create_test_wav():
    """Create a test WAV file with a tone."""
    sample_rate = 16000
    duration = 2  # seconds
    frequency = 440  # A4 note
    
    # Generate samples
    samples = []
    for i in range(int(sample_rate * duration)):
        sample = 32767 * math.sin(2 * math.pi * frequency * i / sample_rate)
        samples.append(int(sample))
    
    # Save as WAV
    with wave.open('test.wav', 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(array.array('h', samples).tobytes())
    
    logger.info("Created test.wav")
    
    # Read it back
    with open('test.wav', 'rb') as f:
        return f.read()

async def test_file_transcription():
    """Test file transcription."""
    
    audio_data = create_test_wav()
    
    logger.info(f"Testing file transcription with {len(audio_data)} bytes")
    
    result = await deepgram_service.transcribe_file(
        audio_data=audio_data,
        content_type="audio/wav",
        language="en-US",
        punctuate=True
    )
    
    logger.info(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_file_transcription())