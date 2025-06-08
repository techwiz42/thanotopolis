# Thanotopolis Backend Project Status

## CRITICAL: Mock Values Policy
**DO NOT EVER PUT MOCK VALUES IN PRODUCTION CODE!!! NEVER. NOT EVER.**
- Mock values cause false reporting and hide real system issues
- Always implement real monitoring and stats collection
- If real data isn't available, throw an error or return null - don't fake it
- The admin page showed 0 WebSocket connections because of hardcoded mock values
- This type of issue wastes debugging time and creates false confidence

## IMPORTANT: Git Commit Policy
**NEVER COMMIT CODE TO GIT ON BEHALF OF THE USER**
- User explicitly forbids automated git commits
- Always let the user handle their own git operations
- Only suggest what changes could be committed, never execute git commit commands

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