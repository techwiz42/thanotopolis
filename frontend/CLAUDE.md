# Thanotopolis Frontend - WebSocket Connection Issues

## Issue 1: Message Streaming on Login
When a user logs in and resumes a conversation, messages would stream into the conversation page repeatedly. After refreshing the browser (forcing re-login), messages would stream correctly only once. This unstable behavior only occurred on the first login.

## Issue 2: Conversation Reopen Issue (Jan 6, 2025)
When reopening a conversation, the frontend would create multiple WebSocket connections, causing:
- Duplicate `user_joined` events being sent repeatedly
- Repeated message history streaming from backend
- Input component being disabled due to unstable connection state
- WebSocket repeatedly attempting to connect to the same conversation

## Root Causes
1. **Initial Issue**: Multiple WebSocket connections during authentication state changes, with each connection receiving full message history from backend
2. **Reopen Issue**: 
   - `useWebSocket` hook had `connect` function in its useEffect dependencies, causing reconnection loops
   - WebSocket service didn't check for `CONNECTING` state before attempting new connections
   - Event listeners weren't properly cleaned up on disconnect
   - Auto-reconnect was triggered even on normal closures

### Specific Problems:
1. The `useWebSocket` hook would call `connect()` multiple times during re-renders
2. No protection against simultaneous connection attempts
3. WebSocket service didn't check if already connected to the same conversation
4. Message handlers weren't cleaned up properly between connections
5. Historical messages from WebSocket were being added even when already loaded via API

## Solution Implemented

### 1. WebSocket Service (`/frontend/src/services/websocket.ts`)
- Added check to prevent reconnecting to the same conversation
- Clear message handlers when connecting to prevent duplicates
- Track conversation ID to avoid duplicate connections
- Improved disconnect method to reset state properly

### 2. useWebSocket Hook (`/frontend/src/app/conversations/[id]/hooks/useWebSocket.ts`)
- Added `connectingRef` to prevent simultaneous connection attempts
- Added `connectedConversationRef` to track which conversation is connected
- Check if already connected before attempting new connection
- Proper cleanup on unmount including WebSocket disconnection
- Reset connection state in cleanup function

### 3. useMessageLoader Hook (`/frontend/src/app/conversations/[id]/hooks/useMessageLoader.ts`)
- Added `hasLoadedInitialMessages` flag to track initial load state
- Skip historical messages from WebSocket if initial load hasn't completed
- Enhanced duplicate detection with content matching
- Reset flag when conversation changes

### 4. Message Type (`/frontend/src/app/conversations/[id]/types/message.types.ts`)
- Added `is_history?: boolean` field to distinguish historical messages

## Key Changes Made

### websocket.ts
```typescript
// Check if already connected to same conversation
if (this.ws?.readyState === WebSocket.OPEN && this.conversationId === conversationId) {
  console.log('WebSocket already connected to this conversation');
  return;
}

// Clear handlers to prevent duplicates
this.messageHandlers.clear();
```

### useWebSocket.ts
```typescript
// Prevent multiple simultaneous connections
const connectingRef = useRef(false);
const connectedConversationRef = useRef<string | null>(null);

// In connect function
if (connectingRef.current) {
  console.log('Connection already in progress, skipping...');
  return;
}

// Track connected conversation
connectedConversationRef.current = conversationId;
```

### useMessageLoader.ts
```typescript
// Track initial load state
const hasLoadedInitialMessages = useRef(false);

// Skip historical messages during initial load
if (!hasLoadedInitialMessages.current && 'is_history' in message && message.is_history) {
  console.log('Skipping historical message during initial load');
  return;
}
```

## Testing the Fix

### Initial Login Issue
1. Log in as a user
2. Navigate to a conversation with existing messages
3. Messages should load once without duplication
4. Send new messages - they should appear immediately
5. Refresh the page - messages should load once again

### Conversation Reopen Issue
1. Open a conversation and send messages
2. Navigate away to another page
3. Return to the same conversation
4. Check that:
   - No duplicate messages appear
   - Only one `user_joined` event in console
   - Input component remains enabled
   - Can send messages immediately
5. Switch between multiple conversations - no duplicates

## Latest Fixes (Jan 6, 2025):

### websocket.ts
```typescript
// Added CONNECTING state check
if (this.ws?.readyState === WebSocket.CONNECTING) {
  console.log('WebSocket connection already in progress');
  return;
}

// Properly clean up event listeners
disconnect(): void {
  if (this.ws) {
    this.ws.onopen = null;
    this.ws.onmessage = null;
    this.ws.onerror = null;
    this.ws.onclose = null;
    // ...
  }
}

// Only reconnect on abnormal closures
if (event.code !== 1000 && event.code !== 1001) {
  this.handleReconnect();
}
```

### useWebSocket.ts  
```typescript
// Removed connect from dependencies to prevent loops
useEffect(() => {
  // Only connect if credentials available
  if (conversationId && (token || participantStorage.getSession(conversationId))) {
    connect();
  }
  // ...
}, [conversationId]); // No more [connect] dependency

// Check service connection state
if (websocketService.isConnected && connectedConversationRef.current === conversationId) {
  console.log('Already connected to this conversation via service');
  setWsConnected(true);
  return;
}
```

### Types
- Added `is_history?: boolean` field to `Message` and `MessageWebSocketMessage` interfaces

## Related Files
- `/frontend/src/services/websocket.ts` - WebSocket service singleton
- `/frontend/src/app/conversations/[id]/hooks/useWebSocket.ts` - WebSocket React hook
- `/frontend/src/app/conversations/[id]/hooks/useMessageLoader.ts` - Message loading hook
- `/frontend/src/app/conversations/[id]/page.tsx` - Main conversation page
- `/backend/app/api/websockets.py` - Backend WebSocket handler (sends historical messages)

## Future Improvements
1. Consider implementing a message cache to avoid reloading messages
2. Add reconnection status indicator for users
3. Implement message pagination for conversations with many messages
4. Consider using a state management library (Redux/Zustand) for complex WebSocket state