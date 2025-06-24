# Thanotopolis Frontend - Critical Issues & Solutions

## IMPORTANT: Git Commit Policy
**NEVER COMMIT CODE TO GIT** - User handles all git operations

## Key Issues & Solutions

### 1. WebSocket Connection Issues
**Problem**: Multiple WebSocket connections causing duplicate messages and events
**Solution**: 
- Check connection state before connecting (`websocket.ts`)
- Use refs to prevent simultaneous connections (`useWebSocket.ts`)
- Track loaded messages to skip duplicates (`useMessageLoader.ts`)
- Added `is_history?: boolean` to message types

### 2. TTS Auto-Play Issues
**Problem**: Stale closure prevented TTS from seeing current state
**Solution**: Use refs for current values in callbacks:
```typescript
const currentTTSEnabledRef = useRef(isTTSEnabled);
const currentSpeakTextRef = useRef(speakText);
```

### 3. Admin Dashboard Security
**Problem**: Regular admins could see all organizations' data
**Solution**: Filter by user role/tenant:
```typescript
.filter(org => user?.role === 'super_admin' || org.tenant_id === user?.tenant_id)
```

### 4. Organization Management
- Enhanced registration form with full details
- Created edit page at `/organizations/edit`
- Token regeneration endpoint with 30-second display
- Member management at `/organizations/members`

### 5. Database Schema Issues
**Problem**: Missing `description` column in tenants table
**Solution**: Created migration `add_description_to_tenants_new.py`

### 6. Voice Detection System
**Current**: Voice-optimized detection for Spanish, French, German, English
**Key Points**:
- Only detects phonetic patterns (no accent marks in STT)
- Conservative detection thresholds
- English only when no other language detected

### 7. STT Input Clearing
**Problem**: Voice transcript persisted after sending
**Solution**: Call `onVoiceTranscriptFinal('')` when sending messages

### 8. Speech Reliability Improvements
- Lower audio thresholds for initial syllables
- Accumulate utterances instead of replacing
- Smart punctuation between utterances

## Critical Patterns

### WebSocket Connection
- Always check `readyState` and `conversationId` before connecting
- Clear message handlers on new connections
- Use refs to prevent race conditions

### Voice/TTS Integration
- Use refs in callbacks to avoid stale closures
- Clear voice transcript explicitly after sending
- Memoize options in STT service to prevent re-renders

### Role-Based Access
- Filter data by `user?.role` and `user?.tenant_id`
- Restrict admin features to appropriate roles
- Prevent self-modification in member management

## Known Issues
- Agent system expects database records but should use dynamic discovery
- `conversation_agents` table constraint prevents new conversations

## Testing Checklist
1. WebSocket: No duplicate messages on reconnect
2. TTS: Auto-plays new messages when enabled
3. Admin: Data filtered by organization
4. Voice: Detects languages correctly (Spanish ~95%, French ~94%)
5. STT: Input clears completely after sending