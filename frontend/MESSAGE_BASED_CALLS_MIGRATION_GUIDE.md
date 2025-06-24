# Message-Based Call Structure Migration Guide

This guide outlines the complete migration from monolithic call transcripts to a message-based structure that treats phone calls like chat conversations.

## Overview

The new structure replaces the single `transcript` and `summary` fields in the `phone_calls` table with individual `call_messages` that provide:

- **Granular Control**: Each part of the conversation is a separate message
- **Rich Metadata**: Audio timestamps, confidence scores, language detection
- **Chat-Like Interface**: Familiar UI similar to conversations
- **Extensible**: Easy to add new message types and metadata
- **Audio Segments**: Support for individual audio clips per message

## Database Changes

### 1. New `call_messages` Table

```sql
CREATE TABLE call_messages (
    id VARCHAR PRIMARY KEY,
    call_id VARCHAR NOT NULL REFERENCES phone_calls(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    sender JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    message_type VARCHAR NOT NULL CHECK (message_type IN ('transcript', 'system', 'summary', 'note')),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Message Types

- **transcript**: Individual speech segments from call participants
- **system**: Automated system events (call started, ended, transferred)
- **summary**: AI-generated or manual call summaries
- **note**: Manual notes added by operators

### 3. Sender Structure (JSONB)

```json
{
    "identifier": "unique_id_or_phone",
    "name": "Display Name",
    "type": "customer|agent|system|operator",
    "phone_number": "+1234567890"
}
```

### 4. Metadata Structure (JSONB)

```json
{
    "audio_start_time": 12.5,
    "audio_end_time": 18.3,
    "confidence_score": 0.95,
    "language": "en-US",
    "recording_segment_url": "https://...",
    "is_automated": true,
    "system_event_type": "call_started"
}
```

## Migration Steps

### 1. Backend Migration

#### A. Run Alembic Migration

```bash
# In your backend repository
alembic upgrade head
```

Use the migration script: `backend-migration-add-call-messages.py`

#### B. Update Models

Add the SQLAlchemy models from: `backend-models-call-messages.py`

#### C. Add API Endpoints

Implement the FastAPI endpoints from: `backend-api-call-messages.py`

### 2. Data Migration

#### A. Migrate Existing Transcripts

```sql
-- Convert existing transcripts to transcript messages
INSERT INTO call_messages (id, call_id, content, sender, timestamp, message_type, created_at)
SELECT 
    gen_random_uuid()::text,
    id as call_id,
    transcript as content,
    jsonb_build_object(
        'identifier', 'legacy_system',
        'type', 'system',
        'name', 'Legacy Import'
    ) as sender,
    COALESCE(answer_time, start_time, created_at) as timestamp,
    'transcript' as message_type,
    created_at
FROM phone_calls 
WHERE transcript IS NOT NULL AND transcript != '';
```

#### B. Migrate Existing Summaries

```sql
-- Convert existing summaries to summary messages
INSERT INTO call_messages (id, call_id, content, sender, timestamp, message_type, created_at)
SELECT 
    gen_random_uuid()::text,
    id as call_id,
    summary as content,
    jsonb_build_object(
        'identifier', 'ai_summarizer',
        'type', 'system',
        'name', 'AI Summarizer'
    ) as sender,
    COALESCE(end_time, answer_time, start_time, created_at) as timestamp,
    'summary' as message_type,
    created_at
FROM phone_calls 
WHERE summary IS NOT NULL AND summary != '';
```

#### C. Create System Event Messages

```sql
-- Add call event messages for better timeline
INSERT INTO call_messages (id, call_id, content, sender, timestamp, message_type, metadata, created_at)
SELECT 
    gen_random_uuid()::text,
    id as call_id,
    'Call started - ' || direction || ' call from ' || customer_phone_number as content,
    jsonb_build_object(
        'identifier', 'call_system',
        'type', 'system',
        'name', 'Call System'
    ) as sender,
    start_time as timestamp,
    'system' as message_type,
    jsonb_build_object(
        'system_event_type', 'call_started',
        'direction', direction,
        'customer_phone', customer_phone_number
    ) as metadata,
    created_at
FROM phone_calls 
WHERE start_time IS NOT NULL;
```

### 3. Frontend Updates

The frontend has already been updated with:

- **New TypeScript interfaces** in `src/services/telephony.ts`
- **Message management hook** in `src/app/organizations/telephony/calls/hooks/useCallMessages.ts`
- **Reusable components** in `src/app/organizations/telephony/calls/components/`
- **Updated call details page** with tabbed message interface

## API Endpoints

### Call Messages CRUD

- `GET /api/telephony/calls/{call_id}/messages` - List messages
- `POST /api/telephony/calls/{call_id}/messages` - Create message
- `PATCH /api/telephony/calls/{call_id}/messages/{message_id}` - Update message
- `DELETE /api/telephony/calls/{call_id}/messages/{message_id}` - Delete message

### Specialized Endpoints

- `GET /api/telephony/calls/{call_id}/messages/transcript` - Formatted transcript
- `GET /api/telephony/calls/{call_id}/messages/summary` - Call summary
- `POST /api/telephony/calls/{call_id}/messages/bulk` - Bulk message creation
- `GET /api/telephony/calls/{call_id}/messages/analytics` - Message analytics

## Integration Points

### 1. STT (Speech-to-Text) Processing

When processing audio in real-time:

```python
# Create transcript message for each speech segment
message = CallMessage.create_transcript_message(
    call_id=call.id,
    content=transcribed_text,
    sender_type='customer',  # or 'agent'
    sender_phone=caller_phone,
    timestamp=segment_timestamp,
    confidence_score=stt_confidence,
    language=detected_language,
    audio_start_time=segment_start,
    audio_end_time=segment_end,
    recording_segment_url=audio_url
)
```

### 2. Call Event Tracking

System events during calls:

```python
# Call answered
CallMessage.create_system_message(
    call_id=call.id,
    content="Call answered",
    timestamp=datetime.utcnow(),
    system_event_type="call_answered"
)

# Call transferred
CallMessage.create_system_message(
    call_id=call.id,
    content="Call transferred to agent",
    timestamp=datetime.utcnow(),
    system_event_type="call_transferred",
    agent_id=agent.id,
    agent_name=agent.name
)
```

### 3. AI Summary Generation

After call completion:

```python
# Generate and store AI summary
summary_content = await ai_service.generate_summary(call_messages)
CallMessage.create_summary_message(
    call_id=call.id,
    content=summary_content,
    timestamp=datetime.utcnow(),
    is_automated=True
)
```

## Performance Considerations

### 1. Database Indexes

The migration includes optimized indexes:

```sql
-- Core indexes
CREATE INDEX idx_call_messages_call_id ON call_messages (call_id);
CREATE INDEX idx_call_messages_timestamp ON call_messages (timestamp);
CREATE INDEX idx_call_messages_type ON call_messages (message_type);

-- Composite indexes
CREATE INDEX idx_call_messages_call_timestamp ON call_messages (call_id, timestamp);
CREATE INDEX idx_call_messages_call_type_timestamp ON call_messages (call_id, message_type, timestamp);

-- JSON indexes
CREATE INDEX idx_call_messages_sender_type ON call_messages USING GIN ((sender->>'type'));
CREATE INDEX idx_call_messages_has_audio ON call_messages USING GIN (metadata) 
WHERE metadata ? 'recording_segment_url' OR metadata ? 'audio_start_time';
```

### 2. Query Optimization

- Use `selectinload` for eager loading messages with calls
- Implement pagination for large message lists
- Use filtering to reduce data transfer
- Cache formatted transcripts for frequently accessed calls

### 3. Storage Considerations

- Message content is typically small (< 1KB per message)
- Metadata JSON is lightweight (< 500 bytes)
- Audio URLs reference external storage
- Estimate ~10-50 messages per call

## Testing Strategy

### 1. Data Integrity Tests

```python
def test_message_migration():
    # Verify all transcripts migrated
    assert CallMessage.objects.filter(message_type='transcript').count() > 0
    
    # Verify no data loss
    original_calls = PhoneCall.objects.filter(transcript__isnull=False).count()
    migrated_messages = CallMessage.objects.filter(message_type='transcript').count()
    assert migrated_messages >= original_calls

def test_message_relationships():
    # Verify foreign key constraints
    call = PhoneCall.objects.first()
    messages = call.messages.all()
    assert all(msg.call_id == call.id for msg in messages)
```

### 2. API Tests

```python
def test_message_crud():
    # Test creating messages
    response = client.post(f"/api/telephony/calls/{call_id}/messages", json=message_data)
    assert response.status_code == 201
    
    # Test filtering
    response = client.get(f"/api/telephony/calls/{call_id}/messages?message_type=transcript")
    assert len(response.json()['messages']) > 0

def test_transcript_formatting():
    response = client.get(f"/api/telephony/calls/{call_id}/messages/transcript")
    assert 'transcript' in response.json()
    assert len(response.json()['transcript']) > 0
```

### 3. Performance Tests

```python
def test_message_query_performance():
    # Test large message sets
    with assert_max_queries(5):
        messages = CallMessage.objects.filter(call_id=call_id).order_by('timestamp')[:100]
        list(messages)  # Force evaluation

def test_bulk_message_creation():
    # Test STT bulk processing
    messages_data = [create_message_data() for _ in range(100)]
    response = client.post(f"/api/telephony/calls/{call_id}/messages/bulk", json=messages_data)
    assert response.status_code == 201
```

## Rollback Plan

If issues arise during migration:

### 1. Database Rollback

```bash
# Revert to previous migration
alembic downgrade -1
```

### 2. Data Recovery

The migration preserves original data:

```sql
-- Restore transcript column if needed
UPDATE phone_calls 
SET transcript = (
    SELECT string_agg(content, E'\n' ORDER BY timestamp)
    FROM call_messages 
    WHERE call_messages.call_id = phone_calls.id 
    AND message_type = 'transcript'
)
WHERE EXISTS (
    SELECT 1 FROM call_messages 
    WHERE call_messages.call_id = phone_calls.id 
    AND message_type = 'transcript'
);
```

### 3. Frontend Fallback

The frontend gracefully handles missing API endpoints:

- Falls back to legacy transcript display
- Shows error messages for unavailable features
- Maintains basic call viewing functionality

## Monitoring and Maintenance

### 1. Message Volume Monitoring

```sql
-- Daily message creation rate
SELECT 
    DATE(created_at) as date,
    COUNT(*) as messages_created,
    COUNT(DISTINCT call_id) as calls_with_messages
FROM call_messages 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### 2. Data Quality Checks

```sql
-- Messages without valid calls
SELECT COUNT(*) FROM call_messages cm
LEFT JOIN phone_calls pc ON cm.call_id = pc.id
WHERE pc.id IS NULL;

-- Calls with message count anomalies
SELECT 
    call_id,
    COUNT(*) as message_count,
    COUNT(CASE WHEN message_type = 'transcript' THEN 1 END) as transcript_count
FROM call_messages 
GROUP BY call_id
HAVING COUNT(*) > 1000 OR COUNT(*) = 0;
```

### 3. Performance Monitoring

Monitor query performance for:
- Message list retrieval by call
- Transcript formatting
- Message filtering and searching
- Bulk message creation

## Benefits Achieved

✅ **Granular Control**: Individual message management  
✅ **Rich Metadata**: Audio segments, confidence scores, language detection  
✅ **Chat-Like Interface**: Familiar message-based UI  
✅ **Extensible**: Easy to add new message types  
✅ **Better Analytics**: Message-level insights  
✅ **Improved Performance**: Optimized queries and indexes  
✅ **Scalable**: Handles high-volume call centers  
✅ **Audio Integration**: Per-message audio playback  

This migration transforms phone calls from monolithic records into rich, interactive conversations that provide much better user experience and analytical capabilities.