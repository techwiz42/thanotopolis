# STT Utterance Accumulation Fix

## Problem Summary
Phone call speech-to-text (STT) creates separate messages for each utterance instead of accumulating them into coherent messages. Additionally, only some utterances are being transcribed, and there's high latency (15+ seconds) before agent responses.

## Root Cause Analysis

### Frontend Issues (Already Fixed)
- ✅ **Frontend accumulation logic added** to `TelephonyCallManager.ts` and `useActiveCall.ts`
- ❌ **WebSocket streaming endpoint failing**: `wss://thanotopolis.com/api/ws/telephony/stream` returns connection failed
- ❌ **Frontend accumulation never executes** because WebSocket connection fails

### Backend Issues (Need to Fix)
- 🔍 **Real STT processing happens in backend** during live calls
- 🔍 **Backend creates separate messages** for each utterance directly to database
- 🔍 **No accumulation logic in backend** STT processing pipeline

## Evidence from Logs
```
WebSocket connection to 'wss://thanotopolis.com/api/ws/telephony/stream?...' failed
📞 Telephony WebSocket error: {isTrusted: true, type: 'error', eventPhase: 2}
📞 Failed to connect to telephony streaming service
```

- Frontend WebSocket streaming completely fails
- No `📞 CallManager: Received transcript` logs (frontend handler never called)
- Messages exist in database with 5 separate entries for one conversation
- Suggests backend STT pipeline creates messages directly

## Required Backend Fixes

### 1. Fix WebSocket Streaming Endpoint
**File**: `backend/app/api/telephony_websocket.py` (likely location)

**Issue**: `/api/ws/telephony/stream` endpoint failing
**Action**: 
- Verify endpoint exists and is properly configured
- Check authentication/token validation
- Ensure WebSocket connection handling works
- Test connection manually

### 2. Backend STT Accumulation Logic
**Primary Location**: Backend STT processing pipeline

**Current Behavior**: Each utterance → separate database message
**Required Behavior**: Accumulate utterances → single coherent message

**Implementation Strategy**:
```python
# Pseudo-code for backend accumulation logic
class CallTranscriptAccumulator:
    def __init__(self):
        self.active_calls = {}  # call_id -> accumulation_state
    
    def handle_utterance(self, call_id, utterance, is_final, speaker):
        if call_id not in self.active_calls:
            self.active_calls[call_id] = {
                'accumulated_text': '',
                'last_speaker': None,
                'timeout_handle': None,
                'speaker': speaker
            }
        
        state = self.active_calls[call_id]
        
        # Speaker change - finalize previous
        if state['last_speaker'] and state['last_speaker'] != speaker:
            self.finalize_message(call_id)
        
        # Accumulate if final utterance
        if is_final and utterance.strip():
            if state['accumulated_text']:
                # Add smart punctuation
                needs_punct = not state['accumulated_text'].rstrip().endswith(('.', '!', '?'))
                state['accumulated_text'] += ('. ' if needs_punct else ' ') + utterance.strip()
            else:
                state['accumulated_text'] = utterance.strip()
            
            state['last_speaker'] = speaker
            
            # Reset timeout - finalize after 2 seconds of silence
            if state['timeout_handle']:
                cancel_timeout(state['timeout_handle'])
            
            state['timeout_handle'] = set_timeout(
                lambda: self.finalize_message(call_id), 
                2000  # 2 seconds
            )
    
    def finalize_message(self, call_id):
        if call_id in self.active_calls:
            state = self.active_calls[call_id]
            if state['accumulated_text'] and state['last_speaker']:
                # Create single database message with accumulated text
                create_call_message(
                    call_id=call_id,
                    content=state['accumulated_text'],
                    sender=state['last_speaker'],
                    message_type='transcript'
                )
                
                # Reset accumulation
                state['accumulated_text'] = ''
                state['last_speaker'] = None
```

### 3. Backend Files to Investigate/Modify

**Primary Files**:
- `backend/app/api/telephony.py` - Main telephony API endpoints
- `backend/app/api/telephony_websocket.py` - WebSocket handling (if exists)
- Backend STT processing files (search for speech-to-text handling)
- Files that create `call_messages` database records

**Search Commands**:
```bash
cd ../backend
grep -r "call_messages" . --include="*.py"
grep -r "transcript" . --include="*.py" 
grep -r "utterance" . --include="*.py"
grep -r "speech.*text\|stt" . --include="*.py"
grep -r "/api/ws/telephony/stream" . --include="*.py"
```

### 4. Database Investigation
**Check current message pattern**:
```sql
SELECT call_id, content, sender, timestamp, message_type 
FROM call_messages 
WHERE call_id = '37952ae8-98b9-49d8-810f-2c1218db10ac' 
ORDER BY timestamp;
```

**Expected**: Multiple short messages from same speaker at close timestamps
**Goal**: Single longer messages per speaker turn

## Frontend Changes Already Made

### Files Modified:
1. **`src/services/telephony/TelephonyCallManager.ts`**
   - Added accumulation fields to `CallState` interface
   - Modified `handleTranscript()` to accumulate instead of immediately creating messages
   - Added `finalizeAccumulatedTranscript()` method
   - Added timeout cleanup in `endCall()` and cleanup methods

2. **`src/hooks/useActiveCall.ts`**
   - Added accumulation logic for live streaming (when WebSocket works)
   - Added timeout management and cleanup

3. **Enhanced logging** throughout telephony streaming services

### Frontend Status:
- ✅ Accumulation logic implemented
- ✅ Smart punctuation between utterances  
- ✅ 2-second timeout for finalization
- ✅ Speaker change detection
- ✅ Proper cleanup on call end
- ❌ **Cannot test because backend WebSocket fails**

## Testing Strategy

### After Backend Fixes:
1. **Fix WebSocket endpoint** first
2. **Test live streaming connection**:
   ```javascript
   // Should see in browser console:
   // ✅ 📞 Telephony WebSocket opened successfully
   // ✅ 📞 Connecting to telephony WebSocket: wss://...
   // ✅ 📞 Telephony streaming connected
   ```

3. **Test accumulation**:
   - Make call while viewing call details page
   - Speak multiple short phrases with pauses
   - Should see accumulated transcript logs
   - Should create single coherent message

4. **Verify backend accumulation**:
   - Even without frontend, backend should accumulate
   - Check database after calls for single vs. multiple messages

## Priority Order
1. **HIGH**: Fix backend WebSocket endpoint `/api/ws/telephony/stream`
2. **HIGH**: Implement backend STT accumulation logic  
3. **MEDIUM**: Test frontend streaming once WebSocket works
4. **LOW**: Fine-tune accumulation timeouts and punctuation

## Success Criteria
- ✅ Single coherent messages instead of multiple fragments
- ✅ WebSocket streaming connection works
- ✅ Sub-3 second latency for agent responses  
- ✅ All utterances captured (not just fragments)
- ✅ Smart punctuation between accumulated utterances

## Notes
- Frontend changes are ready but can't be tested until backend WebSocket works
- The real fix needs to happen in backend STT pipeline
- Current separate messages suggest backend creates them directly during live calls
- May need to identify and modify existing backend STT handling code