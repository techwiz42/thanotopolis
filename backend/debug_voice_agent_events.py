#!/usr/bin/env python3
"""
Debug script to monitor Voice Agent events in real-time
"""

import asyncio
import json
import logging
from datetime import datetime
import psycopg2

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('voice_agent_debug.log')
    ]
)

logger = logging.getLogger(__name__)

def check_recent_call_messages():
    """Check recent call messages to see what's being saved"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='thanotopolis',
            user='postgres',
            password='postgres'
        )
        
        cur = conn.cursor()
        
        # Get messages from the last 10 minutes
        cur.execute('''
            SELECT 
                cm.id,
                cm.call_id,
                cm.message_type,
                cm.sender,
                cm.content,
                cm.timestamp,
                pc.customer_phone_number,
                pc.organization_phone_number
            FROM call_messages cm
            JOIN phone_calls pc ON cm.call_id = pc.id
            WHERE cm.timestamp >= NOW() - INTERVAL '10 minutes'
            ORDER BY cm.timestamp DESC
            LIMIT 20
        ''')
        
        rows = cur.fetchall()
        
        print("\n" + "="*80)
        print("RECENT CALL MESSAGES (Last 10 minutes)")
        print("="*80)
        
        if not rows:
            print("❌ No call messages found in last 10 minutes")
        else:
            user_messages = 0
            agent_messages = 0
            
            for row in rows:
                msg_id, call_id, msg_type, sender_json, content, timestamp, customer, org = row
                
                # Parse sender JSON
                sender = json.loads(sender_json) if isinstance(sender_json, str) else sender_json
                sender_type = sender.get('type', 'unknown')
                sender_name = sender.get('name', 'unknown')
                
                if sender_type == 'customer':
                    user_messages += 1
                    print(f"👤 USER: {content[:60]}...")
                elif sender_type == 'agent':
                    agent_messages += 1
                    print(f"🤖 AGENT: {content[:60]}...")
                else:
                    print(f"❓ UNKNOWN({sender_type}): {content[:60]}...")
                    
                print(f"   ID: {msg_id}")
                print(f"   Call: {call_id}")
                print(f"   Time: {timestamp}")
                print(f"   From: {customer} → {org}")
                print("-" * 60)
            
            print(f"\n📊 SUMMARY:")
            print(f"   User messages: {user_messages}")
            print(f"   Agent messages: {agent_messages}")
            print(f"   Total messages: {len(rows)}")
            
            if user_messages == 0 and agent_messages > 0:
                print("🚨 PROBLEM: Only agent messages found - user messages missing!")
            elif user_messages > 0 and agent_messages > 0:
                print("✅ SUCCESS: Both user and agent messages found!")
            else:
                print("⚠️ UNCLEAR: Unexpected message distribution")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def monitor_voice_agent_logs():
    """Monitor the application logs for Voice Agent events"""
    print("\n" + "="*80)
    print("MONITORING VOICE AGENT LOGS")
    print("="*80)
    print("Watching logs for Voice Agent events...")
    print("Make a test call now to see real-time events!")
    print("Press Ctrl+C to stop monitoring")
    print("-" * 80)
    
    try:
        import subprocess
        import sys
        
        # Follow the application logs
        cmd = ["tail", "-f", "/var/log/thanotopolis.log"]
        
        # If that doesn't exist, try watching journalctl or docker logs
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            # Try docker logs if running in container
            cmd = ["docker", "logs", "-f", "thanotopolis-backend"]
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            except FileNotFoundError:
                print("❌ Cannot find logs. Try running this from the backend directory:")
                print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info")
                return
        
        print("📡 Monitoring logs...")
        
        for line in process.stdout:
            if any(keyword in line for keyword in [
                "Voice Agent", "ConversationText", "📥", "💬", "🔍", 
                "handle_conversation_text", "FULL EVENT DATA"
            ]):
                print(f"🔍 {datetime.now().strftime('%H:%M:%S')} | {line.strip()}")
                
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped")
    except Exception as e:
        print(f"❌ Log monitoring error: {e}")

if __name__ == "__main__":
    print("🔧 VOICE AGENT DEBUG TOOL")
    print("This tool helps debug why user messages aren't being saved")
    
    # Check recent messages first
    check_recent_call_messages()
    
    # Ask if user wants to monitor logs
    response = input("\nDo you want to monitor logs in real-time? (y/n): ").lower().strip()
    
    if response.startswith('y'):
        monitor_voice_agent_logs()
    else:
        print("\n💡 To debug further:")
        print("1. Make a test call")
        print("2. Run this script again to check for new messages")
        print("3. Check application logs for Voice Agent events")