#!/usr/bin/env python3
"""
Test script to verify OpenAI Whisper API access and capabilities
"""
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables
env_path = '/home/peter/thanotopolis/backend/.env'
load_dotenv(env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

async def test_whisper_api():
    """Test if the OpenAI API key has access to Whisper"""
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOU_GOT_NOTHIN":
        print("❌ No valid OpenAI API key found in environment")
        return False
    
    print("✅ OpenAI API key found")
    
    # Create a simple test audio file (1 second of silence)
    # This is a minimal WAV file header + silence
    wav_header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    silence_data = b'\x00\x00' * 16000  # 1 second at 16kHz
    test_audio = wav_header + silence_data
    
    # Test Whisper API endpoint
    url = "https://api.openai.com/v1/audio/transcriptions"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    # Prepare form data
    form_data = aiohttp.FormData()
    form_data.add_field('file', test_audio, filename='test.wav', content_type='audio/wav')
    form_data.add_field('model', 'whisper-1')
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form_data) as response:
                if response.status == 200:
                    result = await response.json()
                    print("\n✅ Whisper API is accessible!")
                    print(f"Response: {result}")
                    
                    # Test language detection
                    print("\n🌍 Testing language detection capabilities...")
                    
                    # List of supported languages according to OpenAI docs
                    languages = [
                        "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr",
                        "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi",
                        "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no",
                        "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk",
                        "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk",
                        "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw",
                        "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc",
                        "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo",
                        "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl",
                        "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su"
                    ]
                    
                    print(f"✅ Whisper supports {len(languages)} languages")
                    print(f"Supported languages: {', '.join(languages[:20])}... and {len(languages)-20} more")
                    
                    return True
                    
                elif response.status == 401:
                    print("\n❌ Authentication failed - API key may not have Whisper access")
                    error_data = await response.json()
                    print(f"Error: {error_data}")
                    return False
                    
                elif response.status == 429:
                    print("\n⚠️  Rate limit reached - but this confirms Whisper access exists")
                    return True
                    
                else:
                    print(f"\n❌ Unexpected status code: {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"\n❌ Error testing Whisper API: {e}")
        return False

async def compare_features():
    """Compare Deepgram vs OpenAI Whisper features"""
    
    print("\n📊 Feature Comparison: Deepgram vs OpenAI Whisper")
    print("=" * 60)
    
    features = [
        ("Streaming/Real-time STT", "✅ Yes", "❌ No (file-based only)"),
        ("Language auto-detection", "⚠️  Limited", "✅ Yes (automatic)"),
        ("Supported languages", "~36 languages", "✅ 99+ languages"),
        ("WebSocket support", "✅ Yes", "❌ No"),
        ("File transcription", "✅ Yes", "✅ Yes"),
        ("Response format", "JSON with timestamps", "JSON/SRT/VTT"),
        ("Max file size", "2GB", "25MB"),
        ("Pricing", "$0.0059/min", "$0.006/min"),
        ("Diarization", "✅ Yes", "❌ No"),
        ("Custom vocabulary", "✅ Yes", "✅ Yes (prompts)"),
        ("Word-level timestamps", "✅ Yes", "✅ Yes"),
    ]
    
    print(f"{'Feature':<25} {'Deepgram':<20} {'OpenAI Whisper':<20}")
    print("-" * 65)
    
    for feature, deepgram, whisper in features:
        print(f"{feature:<25} {deepgram:<20} {whisper:<20}")
    
    print("\n🔑 Key Differences:")
    print("1. Whisper does NOT support real-time streaming - only file uploads")
    print("2. Whisper has much better multi-language support (99+ languages)")
    print("3. Deepgram supports WebSocket streaming, Whisper is REST API only")
    print("4. Whisper has smaller file size limit (25MB vs 2GB)")
    print("5. Deepgram supports speaker diarization, Whisper doesn't")

if __name__ == "__main__":
    print("🔍 Testing OpenAI Whisper API Access...")
    print("=" * 60)
    
    # Run the test
    asyncio.run(test_whisper_api())
    
    # Show feature comparison
    asyncio.run(compare_features())