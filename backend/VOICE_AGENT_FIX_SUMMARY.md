# Voice Agent User Message Fix Summary

## Problem Identified
The telephony system was only saving AI agent messages to the database, but not user/caller messages. All call messages showed `sender.type = "agent"` with no `sender.type = "customer"` entries.

## Root Cause Analysis
1. **Field Name Mismatch**: Handler expected `content` field but Voice Agent might use `text` field
2. **Role Value Mismatch**: Handler expected `role = "human"` but Voice Agent likely uses `role = "user"`
3. **Missing Event Types**: User speech might come through different event types than expected
4. **Insufficient Logging**: No visibility into what events were actually being received

## Fixes Applied

### 1. Enhanced Field Name Handling
**Files Modified**: 
- `app/api/telephony_voice_agent.py:278`
- `app/services/voice/deepgram_voice_agent.py:299,306,313,319,323`

**Change**: Now tries both `content` and `text` fields:
```python
text = event.get("content", "") or event.get("text", "")
```

### 2. Expanded Role Mapping
**File Modified**: `app/api/telephony_voice_agent.py:298-306`

**Change**: Maps multiple possible role values:
```python
# User roles: "user", "human", "customer", "caller"  
# Agent roles: "assistant", "agent", "bot", "ai"
is_user = role.lower() in ["user", "human", "customer", "caller"]
```

### 3. Additional Event Type Handlers
**File Modified**: `app/api/telephony_voice_agent.py:345-348`

**Change**: Registered handlers for more event types:
- `UserTranscript`
- `SpeechTranscript` 
- `RecognitionResult`

### 4. Comprehensive Logging
**Files Modified**:
- `app/services/voice/deepgram_voice_agent.py:268-269` - Full event data logging
- `app/services/voice/deepgram_voice_agent.py:344-362` - Unhandled event detection
- `app/api/telephony_voice_agent.py:301` - Role mapping logging

**Change**: All Voice Agent events are now logged with full data to identify user speech patterns.

### 5. Unhandled Event Detection
**File Modified**: `app/services/voice/deepgram_voice_agent.py:347-354`

**Change**: Detects unhandled events containing text that might be user speech:
```python
if text_content and text_content.strip():
    logger.warning(f"🚨 UNHANDLED EVENT WITH TEXT: {event_type}")
    logger.warning(f"🚨 This might be user speech that we're missing!")
```

## Testing Instructions

### 1. Deploy Changes
Restart the backend application to apply the logging and handler changes.

### 2. Monitor Logs During Test Call
Watch application logs for these key indicators:
- `📥 Voice Agent event:` - All events being received
- `🔍 FULL EVENT DATA:` - Complete event structure
- `🔍 Role mapping` - How roles are being interpreted
- `🚨 UNHANDLED EVENT WITH TEXT:` - Potential user speech in unexpected events
- `💾 Queued user message:` - Successful user message capture

### 3. Check Database After Call
Run the debug script to verify user messages are being saved:
```bash
python debug_voice_agent_events.py
```

Expected result: Both `sender.type = "customer"` and `sender.type = "agent"` messages.

### 4. Use Debug Script
The `debug_voice_agent_events.py` script provides:
- Database message analysis
- Real-time log monitoring
- Summary of user vs agent message counts

## Expected Outcomes

### ✅ Success Indicators
- Log shows `ConversationText` events with `role = "user"` (or similar)
- Database contains messages with `sender.type = "customer"`
- Call details page displays both caller and AI agent messages distinctly
- Debug script shows: "✅ SUCCESS: Both user and agent messages found!"

### ⚠️ Troubleshooting Indicators
- Log shows only `role = "assistant"` events → User speech not being transcribed
- Log shows unhandled events with text → User speech in unexpected format
- Log shows audio format errors → Twilio/Deepgram audio compatibility issue

## Next Steps If Issue Persists

1. **Audio Format Investigation**: Check if Twilio's mulaw format is compatible with Voice Agent
2. **Alternative STT Route**: Consider parallel STT processing for user speech
3. **Deepgram Support**: Contact Deepgram about expected event structure for user speech
4. **Event Type Discovery**: Use comprehensive logging to identify actual user speech events

## Files Modified
- `app/api/telephony_voice_agent.py` - Enhanced message handler and role mapping
- `app/services/voice/deepgram_voice_agent.py` - Comprehensive event logging
- `debug_voice_agent_events.py` - Created debugging tool

## Monitoring Commands
```bash
# Check recent messages
python debug_voice_agent_events.py

# Monitor logs in real-time
tail -f /var/log/thanotopolis.log | grep -E "Voice Agent|ConversationText|📥|💬|🔍"

# Check database directly
psql -h localhost -U postgres -d thanotopolis -c "
SELECT sender->>'type' as sender_type, COUNT(*) 
FROM call_messages 
WHERE timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY sender->>'type';"
```