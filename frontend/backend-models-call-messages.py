"""
SQLAlchemy models for message-based call structure.
This file shows the backend models that would be needed to support the new frontend structure.

Place this in your backend at: app/models/call_messages.py
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base  # Adjust import based on your backend structure
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List


class CallMessage(Base):
    """
    Individual messages within a phone call.
    Replaces the monolithic transcript field with granular message-based structure.
    """
    __tablename__ = "call_messages"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to phone call
    call_id = Column(String, ForeignKey("phone_calls.id", ondelete="CASCADE"), nullable=False)
    
    # Message content and metadata
    content = Column(Text, nullable=False)
    sender = Column(JSONB, nullable=False)  # CallMessageSender structure
    timestamp = Column(DateTime(timezone=True), nullable=False)
    message_type = Column(String, nullable=False)
    metadata = Column(JSONB, nullable=True)  # CallMessageMetadata structure
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    call = relationship("PhoneCall", back_populates="messages")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "message_type IN ('transcript', 'system', 'summary', 'note')",
            name='check_message_type'
        ),
        
        # Indexes for performance
        Index('idx_call_messages_call_id', 'call_id'),
        Index('idx_call_messages_timestamp', 'timestamp'),
        Index('idx_call_messages_type', 'message_type'),
        Index('idx_call_messages_call_timestamp', 'call_id', 'timestamp'),
    )
    
    @property
    def sender_name(self) -> str:
        """Get display name for message sender."""
        sender_data = self.sender or {}
        
        if sender_data.get('name'):
            return sender_data['name']
        
        sender_type = sender_data.get('type', 'unknown')
        
        if sender_type == 'customer':
            phone = sender_data.get('phone_number')
            return self._format_phone_number(phone) if phone else 'Customer'
        elif sender_type == 'agent':
            return 'Agent'
        elif sender_type == 'system':
            return 'System'
        elif sender_type == 'operator':
            return 'Operator'
        else:
            return sender_data.get('identifier', 'Unknown')
    
    @property
    def sender_type(self) -> str:
        """Get sender type."""
        return self.sender.get('type', 'unknown') if self.sender else 'unknown'
    
    @property
    def has_audio_segment(self) -> bool:
        """Check if message has associated audio segment."""
        if not self.metadata:
            return False
        return bool(
            self.metadata.get('recording_segment_url') or 
            self.metadata.get('audio_start_time') is not None
        )
    
    @property
    def confidence_score(self) -> Optional[float]:
        """Get speech-to-text confidence score."""
        return self.metadata.get('confidence_score') if self.metadata else None
    
    @property
    def language(self) -> Optional[str]:
        """Get detected language."""
        return self.metadata.get('language') if self.metadata else None
    
    @property
    def audio_duration(self) -> Optional[float]:
        """Calculate audio segment duration in seconds."""
        if not self.metadata:
            return None
        
        start_time = self.metadata.get('audio_start_time')
        end_time = self.metadata.get('audio_end_time')
        
        if start_time is not None and end_time is not None:
            return end_time - start_time
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'call_id': self.call_id,
            'content': self.content,
            'sender': self.sender,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'message_type': self.message_type,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sender_name': self.sender_name,
            'sender_type': self.sender_type,
            'has_audio_segment': self.has_audio_segment,
            'confidence_score': self.confidence_score,
            'language': self.language,
            'audio_duration': self.audio_duration,
        }
    
    @staticmethod
    def _format_phone_number(phone_number: str) -> str:
        """Format phone number for display."""
        if not phone_number:
            return phone_number
        
        # Remove non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Format US numbers
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        
        return phone_number
    
    @classmethod
    def create_transcript_message(
        cls,
        call_id: str,
        content: str,
        sender_type: str = 'customer',
        sender_name: Optional[str] = None,
        sender_phone: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        confidence_score: Optional[float] = None,
        language: Optional[str] = None,
        audio_start_time: Optional[float] = None,
        audio_end_time: Optional[float] = None,
        recording_segment_url: Optional[str] = None,
    ) -> 'CallMessage':
        """Create a transcript message."""
        
        sender = {
            'identifier': sender_phone or f"{sender_type}_speaker",
            'type': sender_type,
        }
        
        if sender_name:
            sender['name'] = sender_name
        if sender_phone:
            sender['phone_number'] = sender_phone
        
        metadata = {}
        if confidence_score is not None:
            metadata['confidence_score'] = confidence_score
        if language:
            metadata['language'] = language
        if audio_start_time is not None:
            metadata['audio_start_time'] = audio_start_time
        if audio_end_time is not None:
            metadata['audio_end_time'] = audio_end_time
        if recording_segment_url:
            metadata['recording_segment_url'] = recording_segment_url
        
        return cls(
            call_id=call_id,
            content=content,
            sender=sender,
            timestamp=timestamp or datetime.utcnow(),
            message_type='transcript',
            metadata=metadata if metadata else None,
        )
    
    @classmethod
    def create_system_message(
        cls,
        call_id: str,
        content: str,
        timestamp: Optional[datetime] = None,
        system_event_type: Optional[str] = None,
        **metadata_kwargs
    ) -> 'CallMessage':
        """Create a system message."""
        
        sender = {
            'identifier': 'call_system',
            'type': 'system',
            'name': 'Call System',
        }
        
        metadata = {'system_event_type': system_event_type} if system_event_type else {}
        metadata.update(metadata_kwargs)
        
        return cls(
            call_id=call_id,
            content=content,
            sender=sender,
            timestamp=timestamp or datetime.utcnow(),
            message_type='system',
            metadata=metadata if metadata else None,
        )
    
    @classmethod
    def create_summary_message(
        cls,
        call_id: str,
        content: str,
        timestamp: Optional[datetime] = None,
        is_automated: bool = True,
    ) -> 'CallMessage':
        """Create a summary message."""
        
        sender = {
            'identifier': 'ai_summarizer',
            'type': 'system',
            'name': 'AI Summarizer',
        }
        
        metadata = {'is_automated': is_automated}
        
        return cls(
            call_id=call_id,
            content=content,
            sender=sender,
            timestamp=timestamp or datetime.utcnow(),
            message_type='summary',
            metadata=metadata,
        )
    
    @classmethod
    def create_note_message(
        cls,
        call_id: str,
        content: str,
        user_id: str,
        user_name: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> 'CallMessage':
        """Create a manual note message."""
        
        sender = {
            'identifier': user_id,
            'type': 'operator',
            'name': user_name or 'Operator',
        }
        
        return cls(
            call_id=call_id,
            content=content,
            sender=sender,
            timestamp=timestamp or datetime.utcnow(),
            message_type='note',
        )


# Update the existing PhoneCall model to include the messages relationship
class PhoneCallUpdate:
    """
    This shows the update needed to the existing PhoneCall model.
    Add this relationship to your existing PhoneCall model.
    """
    
    # Add this relationship to the existing PhoneCall model
    messages = relationship(
        "CallMessage", 
        back_populates="call", 
        cascade="all, delete-orphan",
        order_by="CallMessage.timestamp"
    )
    
    @property
    def transcript_messages(self) -> List[CallMessage]:
        """Get all transcript messages for this call."""
        return [msg for msg in self.messages if msg.message_type == 'transcript']
    
    @property
    def system_messages(self) -> List[CallMessage]:
        """Get all system messages for this call."""
        return [msg for msg in self.messages if msg.message_type == 'system']
    
    @property
    def summary_message(self) -> Optional[CallMessage]:
        """Get the summary message for this call."""
        summary_messages = [msg for msg in self.messages if msg.message_type == 'summary']
        return summary_messages[0] if summary_messages else None
    
    @property
    def note_messages(self) -> List[CallMessage]:
        """Get all note messages for this call."""
        return [msg for msg in self.messages if msg.message_type == 'note']
    
    @property
    def formatted_transcript(self) -> str:
        """Get formatted transcript from messages."""
        transcript_messages = sorted(self.transcript_messages, key=lambda x: x.timestamp)
        
        lines = []
        for msg in transcript_messages:
            lines.append(f"{msg.sender_name}: {msg.content}")
        
        return '\n'.join(lines)
    
    @property
    def summary_content(self) -> Optional[str]:
        """Get summary content."""
        summary_msg = self.summary_message
        return summary_msg.content if summary_msg else None


# Database indexes to add (if not using the migration script above)
additional_indexes = """
-- GIN index for sender type filtering
CREATE INDEX idx_call_messages_sender_type ON call_messages USING GIN ((sender->>'type'));

-- GIN index for messages with audio segments
CREATE INDEX idx_call_messages_has_audio ON call_messages USING GIN (metadata) 
WHERE metadata ? 'recording_segment_url' OR metadata ? 'audio_start_time';

-- Composite index for efficient call message queries
CREATE INDEX idx_call_messages_call_type_timestamp ON call_messages (call_id, message_type, timestamp);

-- Index for language filtering
CREATE INDEX idx_call_messages_language ON call_messages USING GIN ((metadata->>'language'));

-- Index for confidence score filtering
CREATE INDEX idx_call_messages_confidence ON call_messages ((metadata->>'confidence_score')::numeric) 
WHERE metadata ? 'confidence_score';
"""