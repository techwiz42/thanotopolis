# backend/app/models/models.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
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

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=False)
    access_code = Column(String, nullable=False, default=lambda: secrets.token_urlsafe(8))
    
    # New organization fields
    description = Column(String, nullable=True)  # Organization description
    full_name = Column(String, nullable=True)  # Full organization name
    address = Column(JSON, nullable=True)  # JSON for flexible international addresses
    phone = Column(String, nullable=True)
    organization_email = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="owner_tenant", cascade="all, delete-orphan")
    
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
    role = Column(String, default="user")  # user, org_admin, admin, super_admin
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("ConversationUser", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    
    # Unique constraint for email within a tenant
    __table_args__ = (
        UniqueConstraint('email', 'tenant_id', name='_email_tenant_uc'),
        UniqueConstraint('username', 'tenant_id', name='_username_tenant_uc'),
    )

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

class Agent(Base):
    """Agent configurations - both free agents and proprietary agents"""
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(String, unique=True, nullable=False)  # e.g., "MODERATOR", "FINANCIAL_SERVICES"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Ownership model
    is_free_agent = Column(Boolean, default=True)  # True = available to all, False = proprietary
    owner_tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # Configuration
    configuration_template = Column(JSON, default={})  # Default configuration for this agent
    capabilities = Column(JSON, default=[])  # List of capabilities/features
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner_tenant = relationship("Tenant", back_populates="agents")
    conversation_agents = relationship("ConversationAgent", back_populates="agent", cascade="all, delete-orphan")

# Enum for participant types
class ParticipantType(str, enum.Enum):
    PHONE = "phone"
    EMAIL = "email"

# Enum for message types
class MessageType(str, enum.Enum):
    TEXT = "text"
    SYSTEM = "system"
    AGENT_HANDOFF = "agent_handoff"
    PARTICIPANT_JOIN = "participant_join"
    PARTICIPANT_LEAVE = "participant_leave"

# Enum for conversation status
class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, default=ConversationStatus.ACTIVE.value)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="conversations")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    users = relationship("ConversationUser", back_populates="conversation", cascade="all, delete-orphan")
    agents = relationship("ConversationAgent", back_populates="conversation", cascade="all, delete-orphan")
    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")

class Participant(Base):
    """Non-registered users who participate via phone or email"""
    __tablename__ = "participants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    participant_type = Column(String, nullable=False)
    identifier = Column(String, nullable=False)  # phone number or email
    name = Column(String, nullable=True)
    additional_data = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    conversations = relationship("ConversationParticipant", back_populates="participant", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="participant", cascade="all, delete-orphan")
    
    # Unique constraint for identifier within a tenant
    __table_args__ = (
        UniqueConstraint('identifier', 'tenant_id', name='_identifier_tenant_uc'),
    )

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    message_type = Column(String, default=MessageType.TEXT.value)
    content = Column(Text, nullable=False)
    
    # Sender can be user, agent, or participant (only one should be set)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    agent_type = Column(String, nullable=True)  # e.g., "MODERATOR", "DATA_AGENT"
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=True)
    
    # Metadata for additional info (JSON string)
    additional_data = Column(Text, nullable=True)
    
    # Alias for compatibility
    @property
    def message_metadata(self):
        if self.additional_data:
            if isinstance(self.additional_data, str):
                try:
                    return json.loads(self.additional_data)
                except:
                    return None
            return self.additional_data
        return None
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")
    participant = relationship("Participant", back_populates="messages")

# Junction tables for many-to-many relationships
class ConversationUser(Base):
    """Junction table for users in conversations"""
    __tablename__ = "conversation_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="users")
    user = relationship("User", back_populates="conversations")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('conversation_id', 'user_id', name='_conversation_user_uc'),
    )

class ConversationAgent(Base):
    """Junction table for agents in conversations"""
    __tablename__ = "conversation_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    agent_type = Column(String, nullable=True)  # Kept for backward compatibility
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    configuration = Column(Text, nullable=True)  # JSON string for agent-specific config
    
    # Relationships
    conversation = relationship("Conversation", back_populates="agents")
    agent = relationship("Agent", back_populates="conversation_agents")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('conversation_id', 'agent_id', name='_conversation_agent_uc'),
    )

class ConversationParticipant(Base):
    """Junction table for participants in conversations"""
    __tablename__ = "conversation_participants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    participant = relationship("Participant", back_populates="conversations")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('conversation_id', 'participant_id', name='_conversation_participant_uc'),
    )

class UsageRecord(Base):
    """Track usage metrics for users and organizations"""
    __tablename__ = "usage_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Usage type and metrics
    usage_type = Column(String, nullable=False)  # 'tokens', 'tts_minutes', 'stt_minutes'
    amount = Column(Integer, nullable=False)  # tokens count or minutes in seconds
    
    # Metadata for tracking context
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    service_provider = Column(String, nullable=True)  # 'openai', 'elevenlabs', 'deepgram'
    model_name = Column(String, nullable=True)  # 'gpt-4', 'eleven_turbo_v2', etc.
    
    # Cost tracking (in cents)
    cost_cents = Column(Integer, nullable=True, default=0)
    
    # Additional metadata
    additional_data = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User")
    conversation = relationship("Conversation")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_usage_tenant_date', 'tenant_id', 'created_at'),
        Index('idx_usage_user_date', 'user_id', 'created_at'),
        Index('idx_usage_type', 'usage_type'),
    )

class SystemMetrics(Base):
    """Track system-level metrics like DB connections, WebSocket connections"""
    __tablename__ = "system_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_type = Column(String, nullable=False)  # 'db_connections', 'ws_connections', 'active_users'
    value = Column(Integer, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # Additional context
    additional_data = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    
    # Indexes
    __table_args__ = (
        Index('idx_metrics_type_date', 'metric_type', 'created_at'),
        Index('idx_metrics_tenant_date', 'tenant_id', 'created_at'),
    )

class StripeCustomer(Base):
    """Stripe customer information for tenants"""
    __tablename__ = "stripe_customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    stripe_customer_id = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    
    # Customer details
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
    subscriptions = relationship("StripeSubscription", back_populates="customer", cascade="all, delete-orphan")
    invoices = relationship("StripeInvoice", back_populates="customer", cascade="all, delete-orphan")

class StripeSubscription(Base):
    """Stripe subscription for monthly billing"""
    __tablename__ = "stripe_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("stripe_customers.id"), nullable=False)
    stripe_subscription_id = Column(String, nullable=False, unique=True)
    stripe_price_id = Column(String, nullable=False)
    
    # Subscription details
    status = Column(String, nullable=False)  # active, canceled, past_due, etc.
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, default=False)
    
    # Pricing
    amount_cents = Column(Integer, nullable=False)  # Monthly subscription cost in cents
    currency = Column(String, default="usd")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("StripeCustomer", back_populates="subscriptions")

class StripeInvoice(Base):
    """Stripe invoices for both subscription and usage billing"""
    __tablename__ = "stripe_invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("stripe_customers.id"), nullable=False)
    stripe_invoice_id = Column(String, nullable=False, unique=True)
    
    # Invoice details
    status = Column(String, nullable=False)  # draft, open, paid, uncollectible, void
    amount_due_cents = Column(Integer, nullable=False)
    amount_paid_cents = Column(Integer, default=0)
    currency = Column(String, default="usd")
    
    # Billing period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Usage billing details
    voice_words_count = Column(Integer, default=0)  # Combined STT + TTS words
    voice_usage_cents = Column(Integer, default=0)  # $1.00 per 1000 words
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer = relationship("StripeCustomer", back_populates="invoices")

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
    
    # Indexes for performance (skip vector index for testing)
    __table_args__ = (
        Index('idx_embeddings_owner_id', 'owner_id'),
        Index('idx_embeddings_conversation_id', 'conversation_id'),
        Index('idx_embeddings_source_type', 'source_type'),
    )
