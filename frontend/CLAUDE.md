# Thanotopolis Frontend - WebSocket Connection Issues

## IMPORTANT: Git Commit Policy
**NEVER COMMIT CODE TO GIT ON BEHALF OF THE USER**
- User explicitly forbids automated git commits
- Always let the user handle their own git operations
- Only suggest what changes could be committed, never execute git commit commands

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

## Issue 3: TTS Auto-Play for Streaming Messages (June 7, 2025)

### Problem
When TTS (Text-to-Speech) was enabled on the conversation page, text output was not automatically rendered as speech when agent messages arrived. The speaker icons on individual messages worked for manual replay, but new streaming messages were not automatically spoken.

### Root Cause
**Stale Closure Issue**: The `handleMessage` callback in the WebSocket was created with an outdated `isTTSEnabled` value. Even when TTS was enabled in the UI, the callback still had `isTTSEnabled: false` from when it was initially created, preventing auto-play from working.

### Investigation Process
1. **Timing Issue Discovered**: Logs showed that when agent messages arrived, `isTTSEnabled` was `false`, but later became `true`
2. **Attempted Retroactive TTS**: Initially tried to speak recent messages when TTS was enabled, but this caused unwanted behavior
3. **Identified Stale Closure**: The WebSocket callback wasn't seeing the current TTS state due to closure capture

### Solution Implemented

#### 1. Fixed Stale Closure with Refs (`/frontend/src/app/conversations/[id]/page.tsx`)
```typescript
// Use refs to avoid stale closure issues
const currentTTSEnabledRef = useRef(isTTSEnabled);
const currentSpeakTextRef = useRef(speakText);

// Update refs when values change
useEffect(() => {
  currentTTSEnabledRef.current = isTTSEnabled;
  currentSpeakTextRef.current = speakText;
}, [isTTSEnabled, speakText]);

// In handleMessage callback - use refs instead of closure values
const currentTTSEnabled = currentTTSEnabledRef.current;
const currentSpeakTextFn = currentSpeakTextRef.current;

if (currentTTSEnabled && message.content.trim() && message.id && !completedMessagesRef.current.has(message.id)) {
  // TTS logic using current values
}
```

#### 2. Removed Unwanted Retroactive TTS
- Initially implemented retroactive TTS to speak recent messages when TTS was enabled
- This caused unwanted behavior (speaking old messages when toggling TTS)
- Removed retroactive feature entirely - only auto-play NEW messages

#### 3. Differentiated Streaming vs Non-Streaming Messages
```typescript
if (hasStreamingContent) {
  // Wait for streaming to complete
  setTimeout(() => {
    if (!isStillStreaming) {
      currentSpeakTextFn(message.content);
    }
  }, 1500);
} else {
  // Non-streaming message, speak immediately
  currentSpeakTextFn(message.content);
}
```

### Final Behavior
1. **✅ Auto-play for new messages**: When TTS is enabled, new agent responses automatically play as speech
2. **✅ Manual replay preserved**: Speaker icons on individual messages still work for replaying any message  
3. **✅ No unwanted retroactive speech**: Enabling TTS doesn't speak existing messages

### Key Learning
**React Closure Gotcha**: `useCallback` dependencies ensure the callback is recreated when values change, but external services (like WebSocket handlers) may cache the old callback. Using refs ensures access to current values regardless of when the callback was created.

### Testing
1. Enable TTS → Should NOT speak any existing message
2. Send message to get agent response → Should auto-play the new response
3. Click speaker icons → Should still work for manual replay

## Issue 4: Admin Dashboard Security and Organization Management (June 11, 2025)

### Problems Identified
1. **Admin Data Visibility Bug**: Regular admins could see data from all organizations in the admin dashboard
2. **Missing Organization Registration Flow**: Organization creation lacked comprehensive information capture
3. **No Organization Edit Page**: Admins had no way to update organization information after creation

### Root Causes
1. **Data Filtering Issue**: Admin dashboard showed usage statistics and tenant data from all organizations without filtering by user's organization
2. **Incomplete Registration**: Organization creation only captured basic name and subdomain
3. **Missing Management Interface**: No UI for editing organization details post-creation

### Solutions Implemented

#### 1. Fixed Admin Data Visibility (`/frontend/src/app/admin/page.tsx`)
```typescript
// Filter organization usage data by admin role
{dashboard.usage_by_organization
  .filter(org => user?.role === 'super_admin' || org.tenant_id === user?.tenant_id)
  .map((org) => (
    // Display org data
  ))}

// Filter tenant statistics by admin role  
{dashboard.tenant_stats
  .filter(tenant => user?.role === 'super_admin' || tenant.tenant_id === user?.tenant_id)
  .map((tenant) => (
    // Display tenant data
  ))}
```

**Security Fix**: Regular admins now only see their own organization's data, while super_admins see all organizations.

#### 2. Enhanced Organization Registration (`/frontend/src/app/organizations/new/page.tsx`)
Extended the organization creation form with comprehensive fields:

**Basic Information**:
- Organization name (required)
- Subdomain (required) 
- Description

**Organization Details**:
- Industry selection (Technology, Healthcare, Finance, etc.)
- Organization size (1-10, 11-50, 51-200, etc.)

**Contact Information**:
- Contact email
- Contact phone

**Address Information** (Optional):
- Street address
- City, State/Province, Postal Code
- Country selection

**Form Improvements**:
- Multi-section layout with clear headings
- Proper form validation
- Responsive grid layouts
- Enhanced UX with dropdowns and proper field types

#### 3. Created Organization Edit Page (`/frontend/src/app/organizations/edit/page.tsx`)
New comprehensive organization management interface:

**Features**:
- Load current organization data via API
- Edit all organization fields except subdomain (read-only after creation)
- Role-based access control (admin/super_admin only)
- Success/error feedback
- Automatic redirect for unauthorized users

**API Integration**:
- Fetches current org data from `/api/organizations/current`
- Updates via PATCH to `/api/organizations/current`
- Proper authentication headers with tenant ID

**UI/UX**:
- Form sections matching registration page
- Disabled subdomain field with explanation
- Creation/update timestamps display
- Navigation back to admin dashboard

#### 4. Admin Dashboard Integration
Added "Edit Organization" button to admin dashboard header for easy access to organization management.

### Security Improvements
1. **Data Isolation**: Regular admins can only view their own organization's data
2. **Role-Based Access**: Organization edit page restricted to admin/super_admin roles
3. **Tenant Filtering**: All admin API calls include proper tenant headers

### Related Files
- `/frontend/src/app/admin/page.tsx` - Admin dashboard with data filtering
- `/frontend/src/app/organizations/new/page.tsx` - Enhanced registration form
- `/frontend/src/app/organizations/edit/page.tsx` - New organization edit interface

### Testing
1. **Admin Data Visibility**: 
   - Regular admin should only see their org's data
   - Super admin should see all organizations
2. **Organization Registration**:
   - Form should capture all additional fields
   - All fields should be optional except name/subdomain
3. **Organization Edit**:
   - Only admins can access edit page
   - All fields editable except subdomain
   - Changes save successfully with feedback

## Issue 5: Database Schema Mismatch and Token Management (June 12, 2025)

### Problems Identified
1. **Login Failure**: Admin users couldn't log in due to missing database columns
2. **Schema Mismatch**: SQLAlchemy Tenant model expected columns that didn't exist in database
3. **Missing Token Management**: No way for admins to regenerate organization access tokens
4. **Navigation Issue**: Organization edit page didn't redirect back to admin dashboard after updates

### Root Causes
1. **Incomplete Migration**: The Alembic migration `87b8d0316915` was missing the `description` column that the model expected
2. **No Token Regeneration API**: Backend lacked endpoint for regenerating organization access codes
3. **Poor UX Flow**: Users stayed on edit page after successful updates instead of returning to main dashboard

### Solutions Implemented

#### 1. Fixed Database Schema Mismatch
**Problem**: SQLAlchemy was trying to query `tenants.description` column that didn't exist
```sql
column tenants.description does not exist
[SQL: SELECT tenants.id, tenants.name, tenants.subdomain, tenants.access_code, 
tenants.description, tenants.full_name, tenants.address, tenants.phone, 
tenants.organization_email, tenants.is_active, tenants.created_at, tenants.updated_at
FROM tenants WHERE tenants.id = $1::UUID]
```

**Solution**: Created and executed new Alembic migration `add_description_new`
- Added missing `description` column to tenants table
- Preserved Alembic migration tracking (no direct SQL alterations)
- Verified all required columns exist: `description`, `full_name`, `address`, `phone`, `organization_email`

#### 2. Implemented Organization Access Token Management

**Backend Enhancement** (`/backend/app/api/organizations.py`):
```python
@router.post("/current/regenerate-access-code", response_model=OrganizationResponse)
async def regenerate_organization_access_code(
    current_user: User = Depends(is_org_admin),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate organization access code (org_admin or higher required)"""
    # Generate new access code using secrets.token_urlsafe(8)
    # Invalidates old token immediately
    # Returns updated organization with new access_code
```

**Frontend Implementation** (`/frontend/src/app/admin/page.tsx`):
- Added "Generate Token" button in admin dashboard header
- Secure token display (auto-hides after 30 seconds)
- One-click copy functionality for easy sharing
- Clear success/error feedback
- Loading states during API calls

**Security Features**:
- Only org_admin, admin, or super_admin can regenerate tokens
- Generated tokens are never stored in localStorage or displayed permanently
- Old tokens become invalid immediately upon regeneration
- Current tokens are never displayed in UI (only newly generated ones)

#### 3. Improved Organization Edit Navigation
**Problem**: After updating organization details, users remained on edit page
**Solution**: Added automatic redirect to admin dashboard after successful update
```typescript
// Redirect to admin page after 2 seconds
setTimeout(() => {
  router.push('/admin')
}, 2000)
```

### Key Features Added

#### 1. Database Schema Resolution
- ✅ Proper Alembic migration without breaking tracking
- ✅ All organization fields now supported
- ✅ Login functionality restored for all user types

#### 2. Token Management System
- ✅ **Generate Token Button**: Easily accessible in admin dashboard
- ✅ **Secure Display**: Tokens auto-hide after 30 seconds
- ✅ **Copy Functionality**: One-click clipboard copying
- ✅ **Old Token Invalidation**: Previous access codes stop working immediately
- ✅ **Role-Based Security**: Only organization administrators can regenerate
- ✅ **No Current Token Display**: Existing tokens remain secret

#### 3. Enhanced User Experience
- ✅ **Auto-redirect**: Organization edit page returns to admin dashboard
- ✅ **Clear Feedback**: Success messages before navigation
- ✅ **Loading States**: Visual feedback during API operations

### Migration Details
**File**: `/backend/alembic/versions/add_description_to_tenants_new.py`
```python
def upgrade() -> None:
    # Add description column to tenants table if it doesn't exist
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'tenants' 
            AND column_name = 'description'
        );
    """))
    if not result.scalar():
        op.add_column('tenants', sa.Column('description', sa.Text(), nullable=True))
```

### Related Files
- `/backend/alembic/versions/add_description_to_tenants_new.py` - New migration for missing column
- `/backend/app/api/organizations.py` - Token regeneration endpoint
- `/frontend/src/app/admin/page.tsx` - Enhanced admin dashboard with token management
- `/frontend/src/app/organizations/edit/page.tsx` - Improved navigation flow

### Testing
1. **Database Schema**:
   - Admin login should work without column errors
   - All organization CRUD operations should function properly
2. **Token Generation**:
   - Only admins can access "Generate Token" button
   - New tokens display for 30 seconds then auto-hide
   - Old tokens become invalid immediately
   - Copy functionality works correctly
3. **Navigation Flow**:
   - Organization edit page redirects to admin dashboard after successful update
   - Success message displays before redirect

## Future Improvements
1. Consider implementing a message cache to avoid reloading messages
2. Add reconnection status indicator for users
3. Implement message pagination for conversations with many messages
4. Consider using a state management library (Redux/Zustand) for complex WebSocket state
5. Add organization logo upload functionality
6. Implement organization user management interface
7. Add audit logs for organization changes