#!/usr/bin/env python3
"""
Test the call messages API endpoint directly
"""

import requests
import json

def test_api():
    """Test the API endpoint"""
    
    # Test call ID that has messages
    call_id = "d6c909b9-4a8e-4bfd-8e51-6e0a357ba3f9"
    
    # You would need to provide a valid JWT token here
    # For now, let's test if the endpoint is reachable
    
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/telephony/calls/{call_id}/messages"
    
    print(f"🔍 Testing API endpoint: {url}")
    
    try:
        # Test without auth first to see if we get a 401 or other error
        response = requests.get(url)
        print(f"Status Code (no auth): {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 401:
            print("✅ API endpoint is working (401 means auth is required, which is expected)")
        elif response.status_code == 404:
            print("❌ API endpoint not found - check if backend is running")
        else:
            print(f"🤔 Unexpected response: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Backend server is not running")
        print("Please start the backend server with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def check_network_details():
    """Provide details about the API call that should be made"""
    
    print("\n🌐 Expected API Call Details")
    print("=" * 40)
    
    print("URL Pattern: GET /api/telephony/calls/{call_id}/messages")
    print("Headers required:")
    print("  - Authorization: Bearer <JWT_TOKEN>")
    print("  - Content-Type: application/json")
    
    print("\nExpected Response (success):")
    print("""
    {
        "messages": [
            {
                "id": "uuid",
                "call_id": "uuid", 
                "content": "message text",
                "sender": {
                    "identifier": "string",
                    "name": "string",
                    "type": "customer|agent|system|operator",
                    "phone_number": "string"
                },
                "timestamp": "datetime",
                "message_type": "transcript|system|summary|note",
                "metadata": {},
                "created_at": "datetime"
            }
        ],
        "total": 0,
        "call_id": "uuid"
    }
    """)
    
    print("\nFrontend should check:")
    print("1. Network tab in browser dev tools")
    print("2. Look for the API call to /api/telephony/calls/{id}/messages")
    print("3. Check if the call returns 200 OK")
    print("4. Check if the response has messages array")
    print("5. Check if messages array is empty or populated")

def main():
    test_api()
    check_network_details()

if __name__ == "__main__":
    main()