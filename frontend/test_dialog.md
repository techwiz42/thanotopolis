# Telephony Dialog Test Plan

## Changes Made to Fix Two-Way Dialog:

### 1. Reduced Audio Buffer Size
- **Before**: 8000 bytes (500ms) minimum
- **After**: 3200 bytes (200ms) minimum
- **Result**: Audio processed more frequently

### 2. Added Timeout-Based Processing
- **Before**: Only processed on buffer size
- **After**: Also processes after 300ms timeout
- **Result**: No more waiting for "enough" audio

### 3. Improved Utterance Detection
- **Before**: Required 100+ characters or punctuation
- **After**: 
  - Reduced to 30 characters (~5-6 words)
  - Added common endings: "please", "thanks", "yes", "no", etc.
  - Question words need only 10 characters
- **Result**: Much more responsive to natural speech

### 4. Better Logging
- Added transcript buffer logging to see what's being accumulated
- Changed "no transcript" warnings to debug level

## Expected Behavior Now:

1. **You call** → Hear greeting
2. **You speak** (e.g., "Hello" or "I need help") → 
   - Audio buffered for 200-300ms
   - Sent to Deepgram for STT
   - Transcript processed when complete utterance detected
   - Agent responds with TTS
3. **Continuous dialog** should now work

## Test Dialog Examples:

Try these short phrases that should trigger responses:
- "Hello" (common ending)
- "Yes please" (common ending)
- "I need help" (>10 chars)
- "What can you do" (question word)
- "How does this work" (question word)

The system should now be much more responsive to natural conversation!