# backend/app/models/models.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Text, Enum as SQLEnum, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, text
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from sqlalchemy import JSON
from datetime import datetime
import uuid
import secrets
import enum
import json

Base = declarative_base()

# Existing enums
class ParticipantType(str, enum.Enum):
    PHONE = "phone"
    EMAIL = "email"

class MessageType(str, enum.Enum):
    TEXT = "text"
    SYSTEM = "system"
    AGENT_HANDOFF = "agent_handoff"
    PARTICIPANT_JOIN = "participant_join"
    PARTICIPANT_LEAVE = "participant_leave"

class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"

# New telephony enums
class PhoneVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"

class CallStatus(str, enum.Enum):
    INCOMING = "incoming"
    RINGING = "ringing"
    ANSWERED = "answered"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"

class CallMessageType(str, enum.Enum):
    TRANSCRIPT = "transcript"
    SYSTEM = "system"
    SUMMARY = "summary"
    NOTE = "note"

class CallMessageSenderType(str, enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"
    OPERATOR = "operator"

class CallDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=False)
    access_code = Column(String, nullable=False, default=lambda: secrets.token_urlsafe(8))
    
    # Organization fields
    description = Column(String, nullable=True)  # Organization description
    full_name = Column(String, nullable=True)  # Full organization name
    address = Column(JSON, nullable=True)  # JSON for flexible international addresses
    phone = Column(String, nullable=True)
    organization_email = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_demo = Column(Boolean, default=False)  # Demo accounts exempt from billing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="owner_tenant", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="tenant", cascade="all, delete-orphan")
    # NEW: Telephony relationship
    telephony_config = relationship("TelephonyConfiguration", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    # Stripe billing relationship  
    # Note: StripeCustomer is defined in stripe_models.py
    stripe_customer = relationship("StripeCustomer", back_populates="tenant", uselist=False)
    
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False)
    username = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String, default="member")  # member, org_admin, admin
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Unique constraint for email within tenant
    __table_args__ = (UniqueConstraint('email', 'tenant_id', name='unique_email_per_tenant'),)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    conversations_created = relationship("Conversation", back_populates="created_by", foreign_keys="Conversation.created_by_user_id")
    conversation_users = relationship("ConversationUser", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # Agent identification
    agent_type = Column(String, nullable=False, unique=True)  # e.g., "WEB_SEARCH", "MODERATOR"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Agent configuration
    is_enabled = Column(Boolean, default=True)
    is_free_agent = Column(Boolean, default=True)  # Available to all tenants
    owner_domain = Column(String, nullable=True)  # For proprietary agents
    
    # Agent capabilities
    capabilities = Column(JSON, default=[])  # List of capabilities/features
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner_tenant = relationship("Tenant", back_populates="agents")
    # NEW: Telephony relationship
    call_usages = relationship("CallAgent", back_populates="agent", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, default=ConversationStatus.ACTIVE.value)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="conversations")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="conversations_created")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    users = relationship("ConversationUser", back_populates="conversation", cascade="all, delete-orphan")
    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    # No relationship to phone_calls - they are separate entities

class ConversationUser(Base):
    __tablename__ = "conversation_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('conversation_id', 'user_id', name='unique_conversation_user'),)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="users")
    user = relationship("User", back_populates="conversation_users")


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    participant_type = Column(String, nullable=False)  # phone, email
    identifier = Column(String, nullable=False)  # phone number or email
    display_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('conversation_id', 'participant_type', 'identifier', name='unique_conversation_participant'),)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="participants")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("conversation_participants.id"), nullable=True)
    
    # Message content
    message_type = Column(String, default=MessageType.TEXT.value)
    content = Column(Text, nullable=False)
    
    # Agent information
    agent_type = Column(String, nullable=True)  # Which agent responded
    
    # Metadata
    message_metadata = Column(JSON, nullable=True)
    additional_data = Column(Text, nullable=True)  # JSON string for backward compatibility
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")
    participant = relationship("ConversationParticipant", foreign_keys=[participant_id])

class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    
    # Usage tracking
    usage_type = Column(String, nullable=False)  # e.g., "tokens", "api_calls", "telephony_minutes"
    amount = Column(Numeric(precision=10, scale=4), nullable=False)
    cost_per_unit = Column(Numeric(precision=10, scale=6), nullable=True)
    cost_cents = Column(Integer, nullable=True)
    cost_currency = Column(String, default="USD")
    
    # Service context
    service_provider = Column(String, nullable=True)  # e.g., "openai", "elevenlabs", "deepgram"
    model_name = Column(String, nullable=True)  # e.g., "gpt-4", "gpt-3.5-turbo"
    
    # Context
    resource_type = Column(String, nullable=True)  # e.g., "conversation", "phone_call"
    resource_id = Column(String, nullable=True)
    usage_metadata = Column(JSON, nullable=True)  # RENAMED: was "metadata"
    additional_data = Column(JSON, nullable=True)  # Additional metadata
    
    # Timestamps
    usage_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="usage_records")
    user = relationship("User")
    conversation = relationship("Conversation")

class SystemMetrics(Base):
    __tablename__ = "system_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_type = Column(String, nullable=False)
    value = Column(Integer, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    additional_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant")

class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    
    # Content and embedding
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # Use smaller dimension size for testing compatibility
    
    # Metadata
    source_type = Column(String, nullable=False, default="document")  # document, message, url
    source = Column(String, nullable=False)  # filename, message_id, url
    chunk_index = Column(Integer, default=0)
    total_chunks = Column(Integer, default=1)
    
    # Additional metadata as JSON
    additional_data = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    conversation = relationship("Conversation", foreign_keys=[conversation_id])

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

# ============================================================================
# TELEPHONY MODELS
# ============================================================================

class TelephonyConfiguration(Base):
    __tablename__ = "telephony_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    
    # Organization's existing phone number
    organization_phone_number = Column(String, nullable=False)  # E.164 format
    formatted_phone_number = Column(String, nullable=True)  # Display format
    country_code = Column(String, nullable=False)
    verification_status = Column(String, default=PhoneVerificationStatus.PENDING.value)
    
    # Our platform's Twilio number (for forwarding)
    platform_phone_number = Column(String, nullable=True)  # Assigned platform number
    call_forwarding_enabled = Column(Boolean, default=False)
    
    # Configuration settings
    welcome_message = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    business_hours = Column(JSON, nullable=True)  # {"monday": {"start": "09:00", "end": "17:00"}, ...}
    timezone = Column(String, default="UTC")
    
    # Call routing settings
    max_concurrent_calls = Column(Integer, default=5)
    call_timeout_seconds = Column(Integer, default=300)  # 5 minutes
    
    # Voice settings
    voice_id = Column(String, nullable=True)  # ElevenLabs voice ID
    voice_settings = Column(JSON, nullable=True)  # Voice configuration
    
    # Integration settings
    forwarding_instructions = Column(Text, nullable=True)  # Instructions for org to set up forwarding
    integration_method = Column(String, default="call_forwarding")  # call_forwarding, sip_trunk, etc.
    
    # Analytics settings
    record_calls = Column(Boolean, default=True)
    transcript_calls = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="telephony_config")
    verification_attempts = relationship("PhoneVerificationAttempt", back_populates="telephony_config", cascade="all, delete-orphan")
    calls = relationship("PhoneCall", back_populates="telephony_config", cascade="all, delete-orphan")

class PhoneVerificationAttempt(Base):
    __tablename__ = "phone_verification_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telephony_config_id = Column(UUID(as_uuid=True), ForeignKey("telephony_configurations.id", ondelete="CASCADE"), nullable=False)
    
    # Verification details for organization's phone number
    verification_code = Column(String, nullable=False)
    verification_method = Column(String, default="sms")  # sms, call
    organization_phone_number = Column(String, nullable=False)  # The number being verified
    
    # Status tracking
    status = Column(String, default=PhoneVerificationStatus.PENDING.value)
    attempts_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    telephony_config = relationship("TelephonyConfiguration", back_populates="verification_attempts")

class PhoneCall(Base):
    __tablename__ = "phone_calls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telephony_config_id = Column(UUID(as_uuid=True), ForeignKey("telephony_configurations.id", ondelete="CASCADE"), nullable=False)
    # No relationship to conversations - they are separate entities
    
    # Call identification
    call_sid = Column(String, unique=True, nullable=False)  # External telephony provider ID
    session_id = Column(String, nullable=True)  # Internal session ID
    
    # Call details - now with organization vs platform numbers
    customer_phone_number = Column(String, nullable=False)  # The actual caller
    organization_phone_number = Column(String, nullable=False)  # Organization's business number
    platform_phone_number = Column(String, nullable=False)  # Our Twilio number that received the call
    direction = Column(String, nullable=False)
    status = Column(String, default=CallStatus.INCOMING.value)
    
    # Call metrics
    start_time = Column(DateTime(timezone=True), nullable=True)
    answer_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Cost tracking
    cost_cents = Column(Integer, default=0)
    cost_currency = Column(String, default="USD")
    
    # Content
    recording_url = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    
    # Metadata
    call_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    telephony_config = relationship("TelephonyConfiguration", back_populates="calls")
    # No relationship to conversations - they are separate entities
    call_agents = relationship("CallAgent", back_populates="call", cascade="all, delete-orphan")
    messages = relationship("CallMessage", back_populates="call", cascade="all, delete-orphan", order_by="CallMessage.timestamp")
    
    @property
    def transcript_messages(self):
        """Get all transcript messages for this call."""
        return [msg for msg in self.messages if msg.message_type == CallMessageType.TRANSCRIPT.value]
    
    @property
    def system_messages(self):
        """Get all system messages for this call."""
        return [msg for msg in self.messages if msg.message_type == CallMessageType.SYSTEM.value]
    
    @property
    def summary_message(self):
        """Get the summary message for this call."""
        summary_messages = [msg for msg in self.messages if msg.message_type == CallMessageType.SUMMARY.value]
        return summary_messages[0] if summary_messages else None
    
    @property
    def note_messages(self):
        """Get all note messages for this call."""
        return [msg for msg in self.messages if msg.message_type == CallMessageType.NOTE.value]
    
    @property
    def formatted_transcript(self):
        """Get formatted transcript from messages."""
        transcript_messages = sorted(self.transcript_messages, key=lambda x: x.timestamp)
        
        lines = []
        for msg in transcript_messages:
            sender_name = msg.get_sender_name()
            lines.append(f"{sender_name}: {msg.content}")
        
        return '\n'.join(lines)
    
    @property
    def summary_content(self):
        """Get summary content."""
        summary_msg = self.summary_message
        return summary_msg.content if summary_msg else None

class CallMessage(Base):
    """
    Individual messages within a phone call.
    Replaces the monolithic transcript field with granular message-based structure.
    """
    __tablename__ = "call_messages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to phone call
    call_id = Column(UUID(as_uuid=True), ForeignKey("phone_calls.id", ondelete="CASCADE"), nullable=False)
    
    # Message content and metadata
    content = Column(Text, nullable=False)
    sender = Column(JSON, nullable=False)  # CallMessageSender structure
    timestamp = Column(DateTime(timezone=True), nullable=False)
    message_type = Column(String, nullable=False)
    message_metadata = Column(JSONB, nullable=True)  # CallMessageMetadata structure
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    call = relationship("PhoneCall", back_populates="messages")
    
    def get_sender_name(self):
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
    def sender_type(self):
        """Get sender type."""
        return self.sender.get('type', 'unknown') if self.sender else 'unknown'
    
    @property
    def has_audio_segment(self):
        """Check if message has associated audio segment."""
        if not self.message_metadata:
            return False
        return bool(
            self.message_metadata.get('recording_segment_url') or 
            self.message_metadata.get('audio_start_time') is not None
        )
    
    @property
    def confidence_score(self):
        """Get speech-to-text confidence score."""
        return self.message_metadata.get('confidence_score') if self.message_metadata else None
    
    @property
    def language(self):
        """Get detected language."""
        return self.message_metadata.get('language') if self.message_metadata else None
    
    @property
    def audio_duration(self):
        """Calculate audio segment duration in seconds."""
        if not self.message_metadata:
            return None
        
        start_time = self.message_metadata.get('audio_start_time')
        end_time = self.message_metadata.get('audio_end_time')
        
        if start_time is not None and end_time is not None:
            return end_time - start_time
        
        return None
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'call_id': str(self.call_id),
            'content': self.content,
            'sender': self.sender,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'message_type': self.message_type,
            'metadata': self.message_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sender_name': self.get_sender_name(),
            'sender_type': self.sender_type,
            'has_audio_segment': self.has_audio_segment,
            'confidence_score': self.confidence_score,
            'language': self.language,
            'audio_duration': self.audio_duration,
        }
    
    @staticmethod
    def _format_phone_number(phone_number):
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
        call_id,
        content,
        sender_type='customer',
        sender_name=None,
        sender_phone=None,
        timestamp=None,
        confidence_score=None,
        language=None,
        audio_start_time=None,
        audio_end_time=None,
        recording_segment_url=None,
    ):
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
            message_type=CallMessageType.TRANSCRIPT.value,
            message_metadata=metadata if metadata else None,
        )
    
    @classmethod
    def create_system_message(
        cls,
        call_id,
        content,
        timestamp=None,
        system_event_type=None,
        **metadata_kwargs
    ):
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
            message_type=CallMessageType.SYSTEM.value,
            message_metadata=metadata if metadata else None,
        )
    
    @classmethod
    def create_summary_message(
        cls,
        call_id,
        content,
        timestamp=None,
        is_automated=True,
    ):
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
            message_type=CallMessageType.SUMMARY.value,
            message_metadata=metadata,
        )
    
    @classmethod
    def create_note_message(
        cls,
        call_id,
        content,
        user_id,
        user_name=None,
        timestamp=None,
    ):
        """Create a manual note message."""
        
        sender = {
            'identifier': str(user_id),
            'type': 'operator',
            'name': user_name or 'Operator',
        }
        
        return cls(
            call_id=call_id,
            content=content,
            sender=sender,
            timestamp=timestamp or datetime.utcnow(),
            message_type=CallMessageType.NOTE.value,
        )

class CallAgent(Base):
    __tablename__ = "call_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("phone_calls.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    # Agent usage in call
    activated_at = Column(DateTime(timezone=True), server_default=func.now())
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    usage_duration_seconds = Column(Integer, nullable=True)
    tokens_used = Column(Integer, default=0)
    
    # Agent response metrics
    response_count = Column(Integer, default=0)
    average_response_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    call = relationship("PhoneCall", back_populates="call_agents")
    agent = relationship("Agent", back_populates="call_usages")

# ============================================================================
# INDEXES FOR PERFORMANCE
# ============================================================================

# User indexes
Index('idx_users_email_tenant', User.email, User.tenant_id)
Index('idx_users_tenant_id', User.tenant_id)

# Conversation indexes
Index('idx_conversations_tenant_id', Conversation.tenant_id)
Index('idx_conversations_created_by', Conversation.created_by_user_id)
Index('idx_conversations_status', Conversation.status)

# Message indexes
Index('idx_messages_conversation_id', Message.conversation_id)
Index('idx_messages_created_at', Message.created_at)
Index('idx_messages_user_id', Message.user_id)

# Usage record indexes
Index('idx_usage_records_tenant_id', UsageRecord.tenant_id)
Index('idx_usage_records_usage_date', UsageRecord.usage_date)
Index('idx_usage_records_usage_type', UsageRecord.usage_type)

# Document embedding indexes
Index('idx_embeddings_owner_id', DocumentEmbedding.owner_id)
Index('idx_embeddings_conversation_id', DocumentEmbedding.conversation_id)

# Telephony indexes
Index('idx_telephony_config_tenant_id', TelephonyConfiguration.tenant_id)
Index('idx_telephony_config_platform_number', TelephonyConfiguration.platform_phone_number)
Index('idx_phone_calls_telephony_config_id', PhoneCall.telephony_config_id)
Index('idx_phone_calls_call_sid', PhoneCall.call_sid)
Index('idx_phone_calls_customer_number', PhoneCall.customer_phone_number)
Index('idx_phone_calls_created_at', PhoneCall.created_at)
Index('idx_phone_calls_status', PhoneCall.status)
Index('idx_phone_verification_config_id', PhoneVerificationAttempt.telephony_config_id)
Index('idx_call_agents_call_id', CallAgent.call_id)
Index('idx_call_agents_agent_id', CallAgent.agent_id)
