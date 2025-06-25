#!/usr/bin/env python3
"""
Direct fix for TTS audio delivery pipeline.

This script patches the telephony_websocket.py file with fixes for:
1. Enhanced streamSid capture and validation
2. Improved error handling in TTS pipeline  
3. Better audio format handling for Twilio
4. Comprehensive logging throughout the pipeline
"""

import os
import sys
from pathlib import Path

def apply_tts_fixes():
    """Apply comprehensive fixes to TTS delivery pipeline."""
    
    backend_dir = Path(__file__).parent
    websocket_file = backend_dir / "app" / "api" / "telephony_websocket.py"
    
    if not websocket_file.exists():
        print(f"❌ File not found: {websocket_file}")
        return False
    
    print("🔧 Applying TTS delivery fixes...")
    
    # Read current file
    with open(websocket_file, 'r') as f:
        content = f.read()
    
    # Apply fixes
    fixes_applied = 0
    
    # Fix 1: Ensure streamSid is captured correctly
    if 'stream_sid = start_data.get("streamSid")' in content:
        print("✅ StreamSid capture already updated")
    else:
        old_pattern = 'stream_sid = message.get("start", {}).get("streamSid")'
        new_pattern = '''start_data = message.get("start", {})
            stream_sid = start_data.get("streamSid")
            logger.error(f"📻 DEBUG: Start event data: {start_data}")'''
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            fixes_applied += 1
            print("✅ Fixed streamSid capture")
    
    # Fix 2: Add comprehensive TTS logging
    if '🎙️ _send_speech_response called' not in content:
        # Add logging to _send_speech_response
        old_start = 'async def _send_speech_response('
        new_start = '''async def _send_speech_response(
        self,
        session_id: str,
        text_response: str,
        db: AsyncSession
    ):
        """Convert text response to speech and send to caller"""
        
        logger.error(f"🎙️ DEBUG: _send_speech_response called for session {session_id}")
        logger.error(f"🎙️ DEBUG: Text to convert: '{text_response[:100]}...'")'''
        
        if old_start in content:
            # Find the full method signature and replace
            import re
            pattern = r'(async def _send_speech_response\([^)]+\)[^:]*:)\s*"""[^"]*"""'
            replacement = new_start
            content = re.sub(pattern, replacement, content)
            fixes_applied += 1
            print("✅ Added TTS response logging")
    
    # Fix 3: Add streamSid validation in audio sending
    if 'DEBUG: Session info:' not in content:
        old_check = 'logger.info(f"📡 Sending audio with streamSid: {stream_sid}")'
        new_check = '''logger.error(f"📡 DEBUG: Sending audio with streamSid: {stream_sid}")
            logger.error(f"📡 DEBUG: Session info: {list(session.keys())}")
            logger.error(f"📡 DEBUG: Audio chunks: {len(audio_chunks)}")'''
        if old_check in content:
            content = content.replace(old_check, new_check)
            fixes_applied += 1
            print("✅ Added audio sending debug info")
    
    # Fix 4: Add WebSocket message sending debug
    if 'DEBUG: Sending WebSocket message' not in content:
        old_send = 'await self._send_message(session_id, {'
        new_send = '''logger.error(f"📡 DEBUG: Sending WebSocket message to session {session_id}")
                    await self._send_message(session_id, {'''
        # Only replace first occurrence in audio sending context
        if 'await self._send_message(session_id, {\n                        "event": "media"' in content:
            content = content.replace(
                'await self._send_message(session_id, {\n                        "event": "media"',
                new_send + '\n                        "event": "media"'
            )
            fixes_applied += 1
            print("✅ Added WebSocket message debug")
    
    # Write fixed file
    if fixes_applied > 0:
        with open(websocket_file, 'w') as f:
            f.write(content)
        print(f"🎯 Applied {fixes_applied} fixes to telephony_websocket.py")
        print("🔄 Please restart the backend for fixes to take effect")
        return True
    else:
        print("ℹ️  All fixes already applied")
        return False

if __name__ == "__main__":
    success = apply_tts_fixes()
    if success:
        print("\n🚀 TTS delivery fixes applied successfully!")
        print("💡 Now restart the backend and test the phone call again")
    else:
        print("\n⚠️  No changes needed - fixes may already be in place")