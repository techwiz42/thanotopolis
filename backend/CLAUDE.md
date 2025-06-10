# Thanotopolis Backend Project Status

## CRITICAL: Mock Values Policy
**DO NOT EVER PUT MOCK VALUES IN PRODUCTION CODE!!! NEVER. NOT EVER.**
- Mock values cause false reporting and hide real system issues
- Always implement real monitoring and stats collection
- If real data isn't available, throw an error or return null - don't fake it
- The admin page showed 0 WebSocket connections because of hardcoded mock values
- This type of issue wastes debugging time and creates false confidence

## 🚨 CRITICAL: ABSOLUTE GIT COMMIT PROHIBITION 🚨
**CLAUDE CODE MUST NEVER, EVER, UNDER ANY CIRCUMSTANCES COMMIT CODE TO GIT**

### STRICT RULES - NO EXCEPTIONS:
1. **NEVER run `git commit` commands** - User explicitly forbids ALL automated git commits
2. **NEVER run `git add` followed by commits** - No staging and committing workflows
3. **NEVER suggest git commit commands** - Don't even recommend commit messages
4. **NEVER create commits** - Even with user approval, let them handle it
5. **NEVER push to remote** - Absolutely forbidden under all circumstances

### ALLOWED GIT OPERATIONS:
- `git status` - To check repository state
- `git diff` - To view changes
- `git log` - To view commit history
- `git branch` - To check/list branches
- READ-ONLY operations only

### VIOLATION CONSEQUENCES:
- Any Claude Code session that commits to git violates user trust
- This has caused problems before and must be prevented
- User must maintain complete control over their git workflow

### IF ASKED ABOUT COMMITS:
- Respond: "I cannot commit code to git. Please handle git operations yourself."
- Suggest what files have been changed, but never commit them
- Let user decide when and how to commit their changes

## Current Project: Language Selection for STT (January 8, 2025)

### Background
- Currently using Deepgram for STT with limited language auto-detection
- Evaluated OpenAI Whisper but it doesn't support streaming (only file-based)
- Decision: Add language selection dropdowns instead of migrating to Whisper

### Implementation Plan
1. **New Conversation Page** - Add language dropdown
2. **Message Input Component** - Add language switcher (visible when STT is enabled)
3. **Backend** - Store language preference in conversation model
4. **STT Service** - Handle dynamic language switching

### Progress Tracking
- [x] Add language dropdown to conversation page (visible when STT enabled)
- [x] Update StreamingSpeechToTextService to accept language parameter
- [x] Handle language changes in useVoice hook
- [x] Store language preference in localStorage
- [x] Update to nova-2 model for better multilingual support (changed from nova-3)
- [x] Fix dropdown opacity for better readability over page content
- [x] Fix language switching to work when STT enabled (not just active)
- [x] Fix focus restoration to message input after language change
- [x] Test non-English language functionality ✅ WORKS!
- [ ] Verify message input returns to voice mode (red) after language change

### Technical Notes
- **Model Choice**: Using Nova-2 model for better multilingual support (nova-3 limited to English/Spanish)
- **Language Support**: 30+ languages supported via Nova-2 model
- Language code format: "en-US", "es-ES", "fr-FR", etc.
- WebSocket automatically reconnects when language changes during STT enabled state
- Language preference stored in localStorage as 'stt-language'
- Language selector only visible when STT is enabled
- Dropdown has opaque white background for readability over page content
- Focus restoration to message input after language change with 150ms delay
- **Audio Processing**: Optimized for 16kHz, enhanced sensitivity, connection stability

### Remaining Tasks
1. ✅ ~~Non-English STT functionality~~ - RESOLVED! Works well now
2. Verify message input returns to voice mode (red highlight) after language switching

### Project Status: ✅ MAJOR SUCCESS
**Language selection for STT is now working reliably across multiple languages including Spanish, German, and French!**

### ✅ Issues Resolved (January 8, 2025)
- ~~**French STT works, but other languages don't work at all**~~ - FIXED!
- ~~User tested: "Was gibt?" (German) - no recognition~~ - NOW WORKS!
- Multiple languages now working reliably

### Language Support Research & Fixes (January 8, 2025)
- **Researched Deepgram Nova-2 language support**: Confirmed German (de) IS supported
- **Updated language mapping**: Added missing mappings for all offered languages
- **Removed unsupported languages**: Removed Arabic and Hebrew from dropdown (not in Nova-2)
- **Enhanced logging**: Added complete options logging to debug exactly what's sent to Deepgram

### ✅ FINAL TEST RESULTS (January 8, 2025) - SUCCESS!
- **Spanish (Spain/Mexico)**: ✅ Works well after fixes
- **German**: ✅ Works reliably, no longer gives up after first phrases
- **French**: ✅ Works (confirmed earlier)
- **Overall**: STT now works pretty well across multiple languages

### Root Cause Analysis & Fixes Applied (January 8, 2025)
- **Primary Issue**: Model mismatch between frontend (nova-3) and backend config (nova-2)
- **Secondary Issues**: Audio processing, connection stability, and silence detection problems

### ✅ COMPREHENSIVE STT FIXES APPLIED (January 8, 2025):

#### 1. Model Consistency Fix
- **Frontend**: Changed default from `nova-3` to `nova-2` in StreamingSpeechToTextService.ts
- **Frontend**: Updated useVoice hook to use `nova-2` instead of `nova-3`
- **Backend**: Already configured for `nova-2` (better multilingual support)
- **Result**: Eliminates model fallback complexity and ensures consistent multilingual support

#### 2. Audio Processing Improvements
- **Enhanced Audio Detection**: Added RMS (Root Mean Square) calculation for better sensitivity
- **Improved Thresholds**: Lowered audio detection thresholds (0.003 RMS, 0.005 peak) for different languages/accents
- **Connection Heartbeat**: Added periodic audio transmission to prevent connection drops during silence
- **Buffer Management**: Increased recent activity threshold (5 frames) and reduced send interval (40ms)

#### 3. Audio Constraints Optimization
- **Sample Rate**: Explicitly request 16kHz to match Deepgram requirements
- **Noise Suppression**: Disabled to preserve speech characteristics for language detection
- **Advanced Constraints**: Added specific browser constraints for consistent audio capture

#### 4. Connection Stability Enhancements
- **Reconnection Logic**: Improved with exponential backoff for abnormal closures (code 1006)
- **Error Handling**: Added language-specific error context and better logging
- **Audio Validation**: Backend validates audio chunk sizes (10 bytes min, 32KB max)

#### 5. Backend Deepgram Options Tuning
- **Utterance Detection**: Increased to 1.5 seconds for better multilingual support
- **Latency Optimization**: Added `no_delay=True` for reduced latency
- **Multichannel**: Disabled to ensure single-channel processing stability
- **Enhanced Logging**: Added detailed connection and audio transmission error context

### Bugs Found & Resolved (January 8, 2025)
- **STT Language Recognition Failure**: Non-English languages not being recognized at all
- **Duplicate Transcriptions**: English STT showing duplicate phrases ("Hello. My name is Anigo Montoya. You killed my uncle Hello. My name is Anigo Montoya...")
- **Name Recognition**: "Inigo" transcribed as "Anigo"
- **✅ RESOLVED: Deepgram WebSocket HTTP 400 Error**: Fixed nova-3 model compatibility issues
  - **Root Cause**: Nova-3 model has limited language support (mainly English, Spanish)
  - **Solution**: Implemented automatic model fallback (nova-3 → nova-2) for unsupported languages
  - **Details**: French, German, and other languages not supported by nova-3 automatically fall back to nova-2

### Fixes Applied (via Agent)
1. **Backend WebSocket Updates**:
   - Modified `/ws/stt/stream` to accept `language` and `model` query parameters
   - Language parameters now properly passed to Deepgram service
   - Added control message support for dynamic language switching

2. **Duplicate Prevention**:
   - Added duplicate detection logic
   - Audio throttling (50ms intervals)
   - Improved buffer management (1024 size)
   - Tracking of last interim/final transcripts

3. **Audio Processing Improvements**:
   - Reduced audio activity threshold
   - Added 1.5x audio boosting for quiet speech
   - Better silence detection with recent activity tracking

4. **Frontend Updates**:
   - `useVoice` hook properly passes language to STT service
   - STT service options recreated on language change using `useMemo`
   - Added language detection feedback logging

5. **✅ FINAL FIX: Deepgram Model Compatibility** (HTTP 400 error completely resolved):
   - **Root Issue**: Nova-3 model doesn't support French and many other languages
   - Added `map_language_code_to_deepgram()` function in deepgram_service.py
   - Maps standard locale codes (fr-FR) to Deepgram format (fr)
   - **Automatic Model Fallback**: Added `get_compatible_model_for_language()` function
   - When nova-3 is requested but language is unsupported → automatically switches to nova-2
   - Comprehensive logging shows model fallback decisions
   - Changed default model from nova-3 to nova-2 for better language support
   - **Result**: French STT now works perfectly with automatic nova-3 → nova-2 fallback

### Implementation Details
**Language Selector Component:**
- 36 supported languages from Deepgram nova-3
- Radix UI Select with proper accessibility
- Always enabled (not disabled during recording)
- Positioned next to voice controls in conversation header

**Language Switching Logic:**
- Triggers STT restart whenever STT is enabled (not just during active recording)
- 500ms delay for clean WebSocket reconnection
- Automatic focus restoration to message input textarea
- Console logging for debugging language change flow

**Voice Integration:**
- Language passed to useVoice hook via languageCode prop
- useStreamingSpeechToText receives language parameter
- Backend uses nova-3 model with specified language code

## Overview
This is a multi-tenant backend system with authentication, conversations, and RAG (Retrieval Augmented Generation) capabilities. The code uses FastAPI, SQLAlchemy with asyncpg for PostgreSQL, and includes voice service integrations.

## Fixed Issues
- Database model integrity issues (nullable tenant_id)
- Field name inconsistencies (thread_id vs conversation_id)
- Foreign key constraint violations
- JSON serialization problems
- API endpoint URL mismatches in tests
- **NEW: Backend STT Implementation Complete**
  - Created dedicated streaming STT API (`/app/api/streaming_stt.py`)
  - Added new WebSocket endpoint `/api/ws/stt/stream` for real-time transcription
  - Added HTTP endpoint `/api/stt/file` for audio file transcription
  - Added status endpoint `/api/stt/status` for service monitoring
  - Integrated with main application router and shutdown handlers
  - Includes usage tracking, error handling, and authentication

## Remaining Issues

### API Endpoint Implementation
- Conversation API endpoints don't match test expectations
- Several endpoints return 403/404 for valid users
- PATCH/DELETE operations return 405 Method Not Allowed
- Some endpoints return incorrect response formats

### Access Control
- Conversation access permissions need review
- Test fixtures need proper user-conversation relationships

### Agent Processing
- Missing implementation for agent processing
- The code references a non-existent `process_conversation` function

### RAG Services
- Vector database integration still failing
- Naming inconsistencies between thread_id and conversation_id
- Document ingestion process needs review

### Voice Services
- TTS/STT preprocessing has formatting issues
- SSML generation tests failing

## Test Status
- 122 passing tests (increased from 115)
- 27 failing tests
- 2 errors

## Recent Fixes (December 2024)

### WebSocket Scaling for 100+ Users
- Added connection limits (500 total, 50 per conversation)
- Implemented automatic cleanup task (runs every 5 minutes)
- Added real-time connection monitoring at `/api/ws/stats`
- Created production Gunicorn configuration
- Fixed admin dashboard to show REAL WebSocket stats instead of mock values

### Admin Dashboard Mock Values Issue FIXED
- Admin page was showing 0 WebSocket connections due to hardcoded mock values
- Now shows real connection counts from actual WebSocket manager
- Added detailed admin WebSocket stats endpoint at `/api/admin/websocket/stats`
- **LESSON LEARNED**: Mock values in production code are absolutely forbidden

### Language Auto-Detection for STT IMPLEMENTED
- Updated `deepgram_service.py` to support automatic language detection
- Added `detect_language` parameter to both live streaming and file transcription
- When `language=None` and `detect_language=True`, Deepgram will automatically detect the input language
- Streaming STT endpoint now uses auto-detection by default (`language=None, detect_language=True`)
- File transcription endpoint enables auto-detection when no language is specified
- Added `detected_language` field to transcript responses to show detected language
- Added comprehensive logging to debug language detection behavior
- Using `nova-2` model which supports multi-language detection
- **STATUS**: Works for English, testing non-English language detection in progress

## Next Steps
1. Review conversation API routes for proper method handling
2. Fix access control for conversation endpoints
3. Create or mock agent processing functionality
4. Update RAG services to use consistent field names
5. Fix voice service preprocessing tests

## Project Structure
- `/app/api/` - API endpoints
- `/app/models/` - SQLAlchemy models
- `/app/services/` - Business logic services
- `/app/auth/` - Authentication
- `/tests/` - Test suite

## Important Command
When resuming work, run tests with:
```
pytest -v
```