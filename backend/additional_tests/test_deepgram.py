#!/usr/bin/env python3
"""
Deepgram API Key Test Fixture
Tests if the Deepgram API key is operational and can connect to their services.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from deepgram.clients.listen import AsyncListenWebSocketClient
import httpx
import json
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

def test_api_key_format():
    """Test if API key is properly formatted"""
    print("=== Testing API Key Format ===")
    if not DEEPGRAM_API_KEY:
        print("❌ DEEPGRAM_API_KEY not found in environment")
        return False
    
    if len(DEEPGRAM_API_KEY) < 20:
        print("❌ API key appears too short")
        return False
    
    print(f"✅ API key found: {DEEPGRAM_API_KEY[:8]}...{DEEPGRAM_API_KEY[-4:]}")
    return True

async def test_api_connectivity():
    """Test basic API connectivity with HTTP request"""
    print("\n=== Testing API Connectivity ===")
    
    url = "https://api.deepgram.com/v1/projects"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API connectivity successful")
            print(f"   Projects found: {len(data.get('projects', []))}")
            return True
        elif response.status_code == 401:
            print(f"❌ Authentication failed (401)")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        return False

async def test_prerecorded_transcription():
    """Test prerecorded transcription with a simple audio URL"""
    print("\n=== Testing Prerecorded Transcription ===")
    
    try:
        # Initialize the Deepgram client
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Use a sample audio URL from Deepgram's examples
        audio_url = {"url": "https://static.deepgram.com/examples/Bueller-Life-moves-pretty-fast.wav"}
        
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            language="en-US"
        )
        
        print(f"   Testing with sample audio: {audio_url['url']}")
        
        # Make the request using the current SDK
        response = await deepgram.listen.asyncrest.v("1").transcribe_url(
            audio_url, options
        )
        
        # Check the response
        if response.results and response.results.channels:
            transcript = response.results.channels[0].alternatives[0].transcript
            print(f"✅ Prerecorded transcription successful")
            print(f"   Transcript: '{transcript[:100]}...'")
            return True
        else:
            print(f"❌ No transcription results returned")
            return False
            
    except Exception as e:
        print(f"❌ Prerecorded transcription test failed: {e}")
        return False

async def test_live_transcription():
    """Test live transcription WebSocket connection"""
    print("\n=== Testing Live Transcription WebSocket ===")
    
    try:
        # Initialize the Deepgram client
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Create a WebSocket connection using current SDK
        dg_connection = deepgram.listen.asyncwebsocket.v("1")
        
        # Connection event handlers
        connection_established = False
        connection_error = None
        
        async def on_open(self, open, **kwargs):
            nonlocal connection_established
            connection_established = True
            print("   ✅ WebSocket connection opened successfully")
        
        async def on_message(self, result, **kwargs):
            try:
                if hasattr(result, 'channel') and result.channel and result.channel.alternatives:
                    transcript = result.channel.alternatives[0].transcript
                    if transcript.strip():
                        print(f"   📝 Received transcript: '{transcript}'")
            except:
                pass
        
        async def on_error(self, error, **kwargs):
            nonlocal connection_error
            connection_error = error
            print(f"   ❌ WebSocket error: {error}")
        
        async def on_close(self, close, **kwargs):
            print("   🔒 WebSocket connection closed")
        
        # Register event handlers - simplified for current SDK
        try:
            dg_connection.on("open", on_open)
            dg_connection.on("message", on_message)  
            dg_connection.on("error", on_error)
            dg_connection.on("close", on_close)
        except:
            # If event registration fails, continue without handlers
            pass
        
        # Connection options
        options = {
            "model": "nova-2",
            "encoding": "linear16",
            "channels": 1,
            "sample_rate": 16000,
            "language": "en-US"
        }
        
        print(f"   Attempting WebSocket connection...")
        
        # Start the connection
        result = await dg_connection.start(options)
        if result:
            # Wait a moment for connection to establish
            await asyncio.sleep(2)
            
            print("✅ Live transcription WebSocket connection test successful")
            
            # Send a test message to close cleanly
            try:
                await dg_connection.send(json.dumps({"type": "CloseStream"}).encode())
                await asyncio.sleep(1)
            except:
                pass
                
            return True
        else:
            print("❌ Failed to start WebSocket connection")
            return False
            
    except Exception as e:
        print(f"❌ Live transcription test failed: {e}")
        return False
    finally:
        try:
            if 'dg_connection' in locals():
                await dg_connection.finish()
        except:
            pass

async def test_account_usage():
    """Test account usage and credits"""
    print("\n=== Testing Account Usage ===")
    
    url = "https://api.deepgram.com/v1/projects"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Get projects
            response = await client.get(url, headers=headers, timeout=10.0)
            
            if response.status_code != 200:
                print(f"❌ Could not retrieve account info")
                return False
                
            projects = response.json().get('projects', [])
            if not projects:
                print(f"❌ No projects found in account")
                return False
                
            project_id = projects[0]['project_id']
            print(f"   Using project: {project_id}")
            
            # Get usage for the project
            usage_url = f"https://api.deepgram.com/v1/projects/{project_id}/usage"
            usage_response = await client.get(usage_url, headers=headers, timeout=10.0)
            
            if usage_response.status_code == 200:
                usage_data = usage_response.json()
                print(f"✅ Account usage retrieved successfully")
                
                # Show some usage stats if available
                if 'requests' in usage_data:
                    total_requests = sum(usage_data['requests'].values()) if usage_data['requests'] else 0
                    print(f"   Total requests this period: {total_requests}")
                
                return True
            else:
                print(f"❌ Could not retrieve usage data: {usage_response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Account usage test failed: {e}")
        return False

async def main():
    """Run all Deepgram tests"""
    print(f"🧪 Deepgram API Key Test Suite")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    tests = [
        ("API Key Format", test_api_key_format),
        ("API Connectivity", test_api_connectivity),
        ("Account Usage", test_account_usage),
        ("Prerecorded Transcription", test_prerecorded_transcription),
        ("Live Transcription WebSocket", test_live_transcription),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Deepgram API key is operational.")
        return 0
    else:
        print("⚠️  Some tests failed. Check Deepgram API key and account status.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)