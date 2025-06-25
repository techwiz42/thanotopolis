# Backend Telephony Requirements

## Issue Analysis
The frontend telephony system is complete and functional, but the backend lacks the necessary WebSocket endpoints and message handling. When you call the organization's number:

1. ✅ Call is received and logged by backend
2. ❌ Backend doesn't send call events to frontend via WebSocket
3. ❌ Backend doesn't implement telephony WebSocket endpoints
4. ❌ Backend doesn't route TTS audio to actual phone calls
5. ❌ Backend doesn't store call messages in database

## Required Backend Implementation

### 1. WebSocket Endpoint
**Endpoint:** `/api/ws/telephony/stream`
**Protocol:** WebSocket upgrade from HTTP

#### Connection Parameters (Query String)
```
?token=<auth_token>&call_id=<call_id>&language=<language>&model=<model>&client_type=telephony
```

#### Initial Handshake
Frontend sends on connection:
```json
{
  "type": "init_telephony_stream",
  "call_id": "string",
  "language": "auto|en|es|fr|de",
  "model": "nova-2",
  "client_type": "telephony"
}
```

### 2. WebSocket Message Types

#### From Frontend to Backend

**Agent Message (TTS Request)**
```json
{
  "type": "agent_message",
  "call_id": "string",
  "message": "Hello! Thank you for calling. How can I help you today?",
  "language": "auto",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Call Status Update**
```json
{
  "type": "update_call_status",
  "call_id": "string",
  "status": "answered|in_progress|ended",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Audio Data (STT)**
```json
{
  "type": "audio_data",
  "call_id": "string",
  "audio_data": "base64_encoded_audio",
  "sample_rate": 8000,
  "encoding": "MULAW",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Heartbeat**
```json
{
  "type": "ping"
}
```

#### From Backend to Frontend

**Call Status Update**
```json
{
  "type": "call_status_update",
  "call_id": "string",
  "status": "incoming|answered|in_progress|ended",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Customer Transcript (STT Result)**
```json
{
  "type": "customer_transcript",
  "call_id": "string",
  "transcript": "Hello, I need help with my account",
  "is_final": true,
  "confidence": 0.95,
  "detected_language": "en",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Agent TTS Audio**
```json
{
  "type": "agent_tts_audio",
  "call_id": "string",
  "audio_data": "base64_encoded_audio",
  "message": "Original text that was synthesized",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Telephony Connected**
```json
{
  "type": "telephony_connected",
  "call_id": "string",
  "status": "ready"
}
```

**Heartbeat Response**
```json
{
  "type": "pong"
}
```

### 3. Call Event Flow

#### When Phone Call Arrives
1. Backend receives call via Twilio webhook
2. Backend creates call record in database
3. Backend sends WebSocket message to connected frontend clients:
   ```json
   {
     "type": "call_status_update",
     "call_id": "generated_call_id",
     "status": "incoming",
     "customer_number": "+1234567890",
     "organization_number": "+0987654321",
     "timestamp": "2024-01-01T12:00:00Z"
   }
   ```

#### When Call is Answered
1. Backend receives call answered event from Twilio
2. Backend sends WebSocket message:
   ```json
   {
     "type": "call_status_update",
     "call_id": "call_id",
     "status": "answered",
     "timestamp": "2024-01-01T12:00:00Z"
   }
   ```

#### When Frontend Sends Agent Message
1. Frontend sends `agent_message` via WebSocket
2. Backend receives message and:
   - Stores message in database as agent message
   - Converts text to speech using TTS service
   - Sends TTS audio to phone call via Twilio
   - Confirms delivery back to frontend

#### When Customer Speaks
1. Backend receives audio from Twilio
2. Backend processes with STT service
3. Backend sends transcript to frontend:
   ```json
   {
     "type": "customer_transcript",
     "call_id": "call_id",
     "transcript": "Customer's words",
     "is_final": true,
     "confidence": 0.95,
     "timestamp": "2024-01-01T12:00:00Z"
   }
   ```
4. Backend stores transcript in database as customer message

### 4. Database Schema Requirements

#### phone_call_messages Table
```sql
CREATE TABLE phone_call_messages (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(255) NOT NULL,
    message_type VARCHAR(50) NOT NULL, -- 'transcript', 'tts_audio'
    content TEXT NOT NULL,
    sender_type VARCHAR(50) NOT NULL, -- 'customer', 'agent'
    sender_name VARCHAR(255),
    confidence FLOAT,
    detected_language VARCHAR(10),
    is_final BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### phone_calls Table (if not exists)
```sql
CREATE TABLE phone_calls (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(255) UNIQUE NOT NULL,
    call_sid VARCHAR(255) UNIQUE NOT NULL,
    customer_number VARCHAR(20) NOT NULL,
    organization_number VARCHAR(20) NOT NULL,
    status VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration INTEGER,
    tenant_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Integration Points

#### Twilio Integration
- **Incoming Call Webhook:** Receive call events, create call records, notify frontend
- **Media Streams:** Route TTS audio to phone calls, receive STT audio from calls
- **Call Control:** Handle call status updates (answered, ended, etc.)

#### TTS/STT Services
- **TTS:** Convert agent messages to speech, send to phone calls
- **STT:** Convert customer speech to text, send to frontend
- **Language Detection:** Determine customer language for better processing

### 6. Error Handling

#### WebSocket Errors
```json
{
  "type": "telephony_error",
  "call_id": "string",
  "error_code": "CONNECTION_FAILED|TTS_ERROR|STT_ERROR|TWILIO_ERROR",
  "message": "Detailed error message",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 7. Security Considerations

- **Authentication:** Validate JWT tokens on WebSocket connections
- **Authorization:** Ensure users can only access calls for their organization
- **Rate Limiting:** Prevent abuse of WebSocket connections
- **Call Privacy:** Ensure call data is properly isolated by tenant

### 8. Performance Requirements

- **Low Latency:** TTS and STT processing should complete within 1-2 seconds
- **Real-time:** WebSocket messages should be delivered immediately
- **Scalability:** Support multiple concurrent calls per organization
- **Reliability:** Implement reconnection logic and error recovery

## Current Frontend Capabilities

The frontend telephony system is already implemented and includes:

✅ **TelephonyWebSocketManager** - Manages WebSocket connections  
✅ **TelephonyCallManager** - Handles call state and routing  
✅ **TelephonyTTSSTTProcessor** - Processes TTS/STT requests  
✅ **TwilioAudioService** - Audio format conversion and streaming  
✅ **IncomingCallHandler** - Automatically handles incoming calls  
✅ **Error Handling** - Comprehensive error logging and recovery  
✅ **UI Components** - Call details, active calls, test panel  
✅ **Auto-initialization** - Starts when user enters organization section  

## Testing the Integration

Once backend is implemented, you can test with:

1. **Test Panel:** `/organizations/telephony/test` - Run validation tests
2. **Simulate Call:** Use the "Simulate Incoming Call" button
3. **Real Call:** Call the organization's phone number
4. **Check Database:** Verify messages are stored correctly
5. **Check Logs:** Monitor WebSocket messages and call flow

## Expected Behavior After Implementation

1. **Call Arrives:** Phone rings, call appears in Active Calls dashboard
2. **Call Answered:** Welcome message plays automatically to caller
3. **Customer Speaks:** Transcript appears in real-time on call detail page
4. **Agent Responds:** Agent can type message, TTS plays to caller
5. **Messages Stored:** All transcripts and agent messages saved to database
6. **Call History:** Complete call records with full message history

The frontend is ready and waiting for these backend implementations.