# Telephony Greeting & WebSocket Route Fix

## Problem Identified
**No initial greeting from Barney** because the WebSocket connection was failing due to **route mismatch**.

## Root Cause
The WebSocket routes didn't match between what Twilio was told to connect to and what the backend was serving:

- **Twilio was told to connect to**: `/api/telephony/ws/{call_id}` (from webhook)
- **Backend route was**: `/api/ws/telephony/stream/{call_id}` (expected by config)

This mismatch meant:
1. Twilio couldn't establish the WebSocket connection
2. No greeting method was called
3. Only HTTP webhook calls worked (for call status)

## Fixes Applied

### 1. Fixed WebSocket Route Definition
**File**: `app/api/telephony_websocket.py`

**Before**:
```python
router = APIRouter(
    prefix="/telephony/ws",
    tags=["telephony-websocket"],
    responses={404: {"description": "Not found"}},
)

@router.websocket("/{call_id}")
```
**Actual route**: `/api/telephony/ws/{call_id}`

**After**:
```python
router = APIRouter(
    prefix="/ws/telephony",
    tags=["telephony-websocket"],
    responses={404: {"description": "Not found"}},
)

@router.websocket("/stream/{call_id}")
```
**Actual route**: `/api/ws/telephony/stream/{call_id}` ✅

### 2. Fixed Webhook WebSocket URL Generation
**File**: `app/api/telephony.py`

**Before**:
```python
websocket_url = f"wss://{host}/api/telephony/ws/{phone_call.id}"
```

**After**:
```python
websocket_url = f"wss://{host}/api/ws/telephony/stream/{phone_call.id}"
```

## Expected Results

After these fixes, when you call the Twilio number:

1. **Twilio receives the call** → Calls webhook at `/api/telephony/webhook/incoming-call`
2. **Webhook returns TwiML** with correct WebSocket URL: `wss://thanotopolis.com/api/ws/telephony/stream/{call_id}`
3. **Twilio connects to WebSocket** → Backend accepts connection
4. **Greeting method runs** → Calls OpenAI agent to generate greeting
5. **TTS conversion** → Converts text to speech via ElevenLabs
6. **Audio streaming** → Plays Barney's greeting to caller

## Logs to Expect

You should now see logs like:
```
📞 Sending TwiML response with WebSocket URL: wss://thanotopolis.com/api/ws/telephony/stream/[call_id]
📞 Telephony WebSocket connected for call [call_sid]
🎙️ About to send initial greeting for session [session_id]
🎙️ Starting initial greeting for session [session_id]
📞 Initial greeting from DEMO_ANSWERING_SERVICE: [greeting_text]
🎙️ Converting greeting to speech and sending to caller
```

## Next Steps

1. **Restart the server** to apply the route changes
2. **Call the Twilio number**: `+18884374952`
3. **Check logs** for the greeting flow
4. **You should hear Barney's greeting first** before needing to speak

This should resolve both the greeting issue and ensure proper WebSocket connectivity for the telephony system.