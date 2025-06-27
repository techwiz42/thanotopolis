#!/usr/bin/env python3
"""
Debug script to test the call messages API endpoint and identify issues
"""

import requests
import json
import sys
import os

# Add the backend directory to the path
sys.path.append('/home/peter/thanotopolis/backend')

def test_call_messages_api():
    """Test the call messages API endpoint"""
    
    base_url = "http://localhost:8000"
    
    # Test data
    test_call_id = "test-call-id"
    
    # Headers (you'll need to provide a valid token)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_TEST_TOKEN_HERE"
    }
    
    print("🔍 Testing Call Messages API Endpoint")
    print("=" * 50)
    
    # Test 1: Get call messages endpoint
    print("\n1. Testing GET /telephony/calls/{call_id}/messages")
    url = f"{base_url}/api/telephony/calls/{test_call_id}/messages"
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Messages found: {len(data.get('messages', []))}")
            print(f"Total: {data.get('total', 0)}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Backend server is not running")
        print("Please start the backend server with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def check_database_directly():
    """Check the database directly for call messages"""
    
    print("\n🗄️ Checking Database Directly")
    print("=" * 50)
    
    try:
        # Import database modules
        from app.db.database import engine
        from app.models.models import CallMessage, PhoneCall
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import text
        
        # Create session
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Check if call_messages table exists
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'call_messages'
            );
        """))
        
        table_exists = result.scalar()
        print(f"call_messages table exists: {table_exists}")
        
        if table_exists:
            # Check table structure
            result = session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'call_messages'
                ORDER BY ordinal_position;
            """))
            
            print("\nTable structure:")
            for row in result:
                print(f"  {row.column_name}: {row.data_type} (nullable: {row.is_nullable})")
            
            # Check if there are any call messages
            result = session.execute(text("SELECT COUNT(*) FROM call_messages"))
            count = result.scalar()
            print(f"\nTotal call messages in database: {count}")
            
            # Check if there are any phone calls
            result = session.execute(text("SELECT COUNT(*) FROM phone_calls"))
            call_count = result.scalar()
            print(f"Total phone calls in database: {call_count}")
            
            if call_count > 0:
                # Get a sample call ID
                result = session.execute(text("SELECT id FROM phone_calls LIMIT 1"))
                sample_call_id = result.scalar()
                print(f"Sample call ID: {sample_call_id}")
                
                # Check messages for this call
                result = session.execute(text("""
                    SELECT COUNT(*) FROM call_messages 
                    WHERE call_id = :call_id
                """), {"call_id": sample_call_id})
                
                messages_for_call = result.scalar()
                print(f"Messages for sample call: {messages_for_call}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False

def check_frontend_service():
    """Check the frontend telephony service"""
    
    print("\n🌐 Checking Frontend Service")
    print("=" * 50)
    
    # Check if the telephony service is correctly configured
    service_file = "/home/peter/thanotopolis/frontend/src/services/telephony.ts"
    
    try:
        with open(service_file, 'r') as f:
            content = f.read()
            
        # Check for the getCallMessages method
        if "getCallMessages" in content:
            print("✅ getCallMessages method found in telephony service")
            
            # Extract the method
            lines = content.split('\n')
            in_method = False
            method_lines = []
            
            for line in lines:
                if 'async getCallMessages(' in line:
                    in_method = True
                    method_lines.append(line.strip())
                elif in_method:
                    method_lines.append(line.strip())
                    if line.strip().startswith('}') and not line.strip().startswith('} else'):
                        break
            
            print("\ngetCallMessages method:")
            for line in method_lines[:10]:  # Show first 10 lines
                print(f"  {line}")
            
        else:
            print("❌ getCallMessages method not found in telephony service")
            
    except FileNotFoundError:
        print(f"❌ Service file not found: {service_file}")
    except Exception as e:
        print(f"❌ Error reading service file: {e}")

def main():
    """Main debug function"""
    
    print("🔧 Debug: Phone Call Messages Not Displaying")
    print("=" * 60)
    
    # Check components
    check_database_directly()
    check_frontend_service()
    # test_call_messages_api()  # Commented out as it needs valid auth token
    
    print("\n📋 Summary of Findings:")
    print("=" * 30)
    
    print("\n🔍 Potential Issues to Check:")
    print("1. User role permissions - API requires 'org_admin', 'admin', or 'super_admin'")
    print("2. Call messages table might be empty (no messages saved)")
    print("3. Call ID might not exist or not belong to user's tenant")
    print("4. Database migration might not have run successfully")
    print("5. Frontend token might be invalid or expired")
    
    print("\n🛠️ Next Steps:")
    print("1. Check user role in the database")
    print("2. Verify call messages are being saved during phone calls")
    print("3. Test the API endpoint directly with curl or Postman")
    print("4. Check browser network tab for API call errors")
    print("5. Check backend logs for any error messages")

if __name__ == "__main__":
    main()