# backend/app/models/models.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import secrets
import enum

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=False)
    access_code = Column(String, nullable=False, default=lambda: secrets.token_urlsafe(8))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="tenant", cascade="all, delete-orphan")
    
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
    role = Column(String, default="user")  # user, admin, super_admin
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
    agent_type = Column(String, nullable=False)  # e.g., "MODERATOR", "DATA_AGENT"
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    configuration = Column(Text, nullable=True)  # JSON string for agent-specific config
    
    # Relationships
    conversation = relationship("Conversation", back_populates="agents")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('conversation_id', 'agent_type', name='_conversation_agent_uc'),
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
