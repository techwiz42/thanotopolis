# Thanotopolis Backend Project Status

## Overview
This is a multi-tenant backend system with authentication, conversations, and RAG (Retrieval Augmented Generation) capabilities. The code uses FastAPI, SQLAlchemy with asyncpg for PostgreSQL, and includes voice service integrations.

## Fixed Issues
- Database model integrity issues (nullable tenant_id)
- Field name inconsistencies (thread_id vs conversation_id)
- Foreign key constraint violations
- JSON serialization problems
- API endpoint URL mismatches in tests

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