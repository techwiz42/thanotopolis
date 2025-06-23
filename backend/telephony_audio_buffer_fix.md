# Telephony Audio Buffer Fix

## Problem
The telephony system was sending 20ms audio chunks (160 bytes mulaw) individually to Deepgram, causing:
- Empty transcripts due to insufficient speech context
- Excessive API calls (~50 per second)
- Poor transcription quality
- Resource waste

## Solution Implemented
Added audio buffering to accumulate speech before sending to Deepgram.

### Changes Made

#### 1. Enhanced Session State
```python
# Added buffering parameters to call sessions
"audio_buffer": bytearray(),
"last_audio_time": time.time(),
"silence_threshold": 0.5,  # 500ms of silence before processing buffer
"min_buffer_size": 8000,   # ~500ms at 8000 Hz, 16-bit = 8000 bytes per 500ms
"max_buffer_size": 32000   # ~2 seconds max buffer
```

#### 2. Modified Audio Processing
- **Before**: Each 20ms chunk → Deepgram API call
- **After**: Buffer chunks until 500ms+ accumulated → Single API call

#### 3. Buffer Management
- Accumulate PCM audio data in memory buffer
- Process when buffer reaches minimum size (500ms)
- Prevent memory issues with maximum buffer size (2 seconds)
- Flush remaining audio when call ends

#### 4. Improved Audio Conversion
- Convert mulaw → PCM → WAV pipeline
- Use proper WAV headers for better Deepgram compatibility
- Maintain 8kHz/16-bit/mono format

### Expected Results
- **Reduced API calls**: From ~50/sec to ~2-4/sec
- **Better transcription**: 500ms chunks contain complete words/phrases
- **Improved accuracy**: Sufficient audio context for speech recognition
- **Lower costs**: Fewer API requests to Deepgram
- **Better latency**: Processing meaningful chunks vs fragments

### Technical Details
- **Buffer size**: 8000 bytes = 500ms of 16-bit PCM at 8kHz
- **Max buffer**: 32000 bytes = 2 seconds (prevents memory buildup)
- **Audio format**: mulaw → 16-bit PCM → WAV with proper headers
- **Cleanup**: Flush remaining buffer when call ends

## Files Modified
- `app/api/telephony_websocket.py`: Core buffering implementation

## Testing
- Syntax check: ✅ Passed
- Import test: ✅ Passed
- Ready for live testing with actual phone calls

This fix addresses the core issue identified in the logs where Deepgram consistently returned empty transcripts due to audio chunks being too small for meaningful speech recognition.