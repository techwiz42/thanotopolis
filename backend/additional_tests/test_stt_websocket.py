#!/usr/bin/env python3
"""
Test STT WebSocket connectivity
"""

import asyncio
import websockets
import json
import requests
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from dotenv import load_dotenv
load_dotenv()

# Test credentials - you might need to adjust these
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "testpass123"
BACKEND_URL = "http://localhost:8000"

async def get_auth_token():
    """Get authentication token for testing."""
    try:
        # Try to login with test credentials
        login_data = {
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/auth/token",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting auth token: {e}")
        return None

async def test_stt_websocket():
    """Test STT WebSocket connection."""
    print("🎤 Testing STT WebSocket Connection")
    print("=" * 40)
    
    # Get auth token
    print("1. Getting authentication token...")
    token = await get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return False
    
    print(f"✅ Authentication token obtained: {token[:20]}...")
    
    # Test WebSocket connection
    print("\n2. Testing WebSocket connection...")
    
    try:
        # Construct WebSocket URL
        ws_url = f"ws://localhost:8000/api/ws/voice/streaming-stt?token={token}"
        print(f"   Connecting to: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully")
            
            # Wait for welcome message
            try:
                welcome_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(welcome_message)
                print(f"✅ Received welcome: {welcome_data.get('type')} - {welcome_data.get('message')}")
                
                # Send a ping
                ping_message = json.dumps({"type": "ping"})
                await websocket.send(ping_message)
                print("📤 Sent ping message")
                
                # Wait for pong
                pong_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pong_data = json.loads(pong_message)
                if pong_data.get("type") == "pong":
                    print("✅ Received pong response")
                else:
                    print(f"⚠️  Unexpected response: {pong_data}")
                
                # Send start transcription message
                start_message = json.dumps({"type": "start_transcription"})
                await websocket.send(start_message)
                print("📤 Sent start transcription message")
                
                # Wait for ready response
                ready_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                ready_data = json.loads(ready_message)
                if ready_data.get("type") == "transcription_ready":
                    print("✅ Transcription service ready")
                else:
                    print(f"⚠️  Unexpected response: {ready_data}")
                
                print("🎉 STT WebSocket test successful!")
                return True
                
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for WebSocket messages")
                return False
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing WebSocket message: {e}")
                return False
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
        return False
    except websockets.exceptions.InvalidURI as e:
        print(f"❌ Invalid WebSocket URI: {e}")
        return False
    except Exception as e:
        print(f"❌ WebSocket connection error: {e}")
        return False

async def test_stt_status():
    """Test STT status endpoint."""
    print("\n3. Testing STT status endpoint...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/voice/stt/status")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ STT Status:")
            print(f"   Service: {data.get('service')}")
            print(f"   Available: {data.get('available')}")
            print(f"   Model: {data.get('model')}")
            print(f"   Language: {data.get('language')}")
            return True
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking STT status: {e}")
        return False

async def main():
    """Run all STT tests."""
    print("🧪 STT WebSocket Test Suite")
    print("⏰ Testing real-time speech-to-text functionality")
    print("=" * 50)
    
    tests = [
        ("STT Status Check", test_stt_status),
        ("STT WebSocket Connection", test_stt_websocket),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Running: {test_name}")
            result = await test_func()
            results[test_name] = result
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 STT Test Results Summary:")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All STT tests passed! Speech-to-text should work.")
        return 0
    else:
        print("⚠️  Some STT tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)