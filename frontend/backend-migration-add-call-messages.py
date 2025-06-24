"""Add call messages table for message-based call structure

Revision ID: add_call_messages_table
Revises: previous_revision
Create Date: 2024-12-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'add_call_messages_table'
down_revision = 'previous_revision'  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Add call_messages table and modify phone_calls table for message-based structure."""
    
    # Create call_messages table
    op.create_table(
        'call_messages',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('call_id', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sender', postgresql.JSONB(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('message_type', sa.String(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Foreign key constraint
        sa.ForeignKeyConstraint(['call_id'], ['phone_calls.id'], ondelete='CASCADE'),
        
        # Check constraint for message_type
        sa.CheckConstraint(
            "message_type IN ('transcript', 'system', 'summary', 'note')",
            name='check_message_type'
        ),
        
        # Indexes for performance
        sa.Index('idx_call_messages_call_id', 'call_id'),
        sa.Index('idx_call_messages_timestamp', 'timestamp'),
        sa.Index('idx_call_messages_type', 'message_type'),
        sa.Index('idx_call_messages_call_timestamp', 'call_id', 'timestamp'),
    )
    
    # Add indexes on sender type for filtering by speaker
    op.execute("""
        CREATE INDEX idx_call_messages_sender_type 
        ON call_messages USING GIN ((sender->>'type'))
    """)
    
    # Add index on message metadata for audio segments
    op.execute("""
        CREATE INDEX idx_call_messages_has_audio 
        ON call_messages USING GIN (metadata) 
        WHERE metadata ? 'recording_segment_url' OR metadata ? 'audio_start_time'
    """)
    
    # Remove transcript and summary columns from phone_calls (they'll be messages now)
    # Note: In production, you might want to migrate existing data first
    op.drop_column('phone_calls', 'transcript')
    # Keep summary column for backward compatibility during transition
    # op.drop_column('phone_calls', 'summary')
    
    # Add trigger to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_call_messages_updated_at 
        BEFORE UPDATE ON call_messages 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    """Revert call_messages table and restore phone_calls columns."""
    
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS update_call_messages_updated_at ON call_messages")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Add back the transcript column to phone_calls
    op.add_column('phone_calls', sa.Column('transcript', sa.Text(), nullable=True))
    
    # Migrate data back from call_messages to phone_calls (if needed)
    # This is a simplified version - you might want more sophisticated data migration
    op.execute("""
        UPDATE phone_calls 
        SET transcript = (
            SELECT string_agg(
                CASE 
                    WHEN (sender->>'type') = 'customer' THEN 
                        COALESCE(sender->>'name', sender->>'phone_number', 'Customer') || ': ' || content
                    WHEN (sender->>'type') = 'agent' THEN 
                        'Agent: ' || content
                    WHEN (sender->>'type') = 'system' THEN 
                        'System: ' || content
                    ELSE 
                        (sender->>'identifier') || ': ' || content
                END, 
                E'\n' ORDER BY timestamp
            )
            FROM call_messages 
            WHERE call_messages.call_id = phone_calls.id 
            AND message_type = 'transcript'
        )
        WHERE EXISTS (
            SELECT 1 FROM call_messages 
            WHERE call_messages.call_id = phone_calls.id 
            AND message_type = 'transcript'
        )
    """)
    
    # Drop the call_messages table
    op.drop_table('call_messages')


def migrate_existing_call_data():
    """
    Helper function to migrate existing call transcript and summary data to messages.
    This should be called after the upgrade() if you have existing data.
    """
    
    # Migrate existing transcripts to transcript messages
    op.execute("""
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
        WHERE transcript IS NOT NULL 
        AND transcript != ''
    """)
    
    # Migrate existing summaries to summary messages  
    op.execute("""
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
        WHERE summary IS NOT NULL 
        AND summary != ''
    """)


# Example of how to create system messages for call events
def create_call_event_messages():
    """
    Create system messages for important call events.
    This demonstrates how to populate system messages from existing call data.
    """
    
    # Call started messages
    op.execute("""
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
        WHERE start_time IS NOT NULL
    """)
    
    # Call answered messages
    op.execute("""
        INSERT INTO call_messages (id, call_id, content, sender, timestamp, message_type, metadata, created_at)
        SELECT 
            gen_random_uuid()::text,
            id as call_id,
            'Call answered' as content,
            jsonb_build_object(
                'identifier', 'call_system',
                'type', 'system',
                'name', 'Call System'
            ) as sender,
            answer_time as timestamp,
            'system' as message_type,
            jsonb_build_object(
                'system_event_type', 'call_answered'
            ) as metadata,
            created_at
        FROM phone_calls 
        WHERE answer_time IS NOT NULL
    """)
    
    # Call ended messages
    op.execute("""
        INSERT INTO call_messages (id, call_id, content, sender, timestamp, message_type, metadata, created_at)
        SELECT 
            gen_random_uuid()::text,
            id as call_id,
            'Call ended - ' || status || 
            CASE 
                WHEN duration_seconds IS NOT NULL THEN ' (Duration: ' || duration_seconds || 's)'
                ELSE ''
            END as content,
            jsonb_build_object(
                'identifier', 'call_system',
                'type', 'system',
                'name', 'Call System'
            ) as sender,
            end_time as timestamp,
            'system' as message_type,
            jsonb_build_object(
                'system_event_type', 'call_ended',
                'final_status', status,
                'duration_seconds', duration_seconds
            ) as metadata,
            created_at
        FROM phone_calls 
        WHERE end_time IS NOT NULL
    """)