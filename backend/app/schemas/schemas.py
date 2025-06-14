# backend/app/schemas/schemas.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

# Enums
class ParticipantType(str, Enum):
    PHONE = "phone"
    EMAIL = "email"

class MessageType(str, Enum):
    TEXT = "text"
    SYSTEM = "system"
    AGENT_HANDOFF = "agent_handoff"
    PARTICIPANT_JOIN = "participant_join"
    PARTICIPANT_LEAVE = "participant_leave"

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"

# Organization Schemas (formerly Tenant)
class OrganizationCreate(BaseModel):
    name: str
    subdomain: str
    description: Optional[str] = None
    full_name: Optional[str] = None
    address: Optional[Dict[str, Any]] = None  # JSON for flexible international addresses
    phone: Optional[str] = None
    organization_email: Optional[EmailStr] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    full_name: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    phone: Optional[str] = None
    organization_email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    subdomain: str
    access_code: str
    description: Optional[str]
    full_name: Optional[str]
    address: Optional[Dict[str, Any]]
    phone: Optional[str]
    organization_email: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class OrganizationRegisterRequest(BaseModel):
    # Organization details
    name: str
    subdomain: str
    full_name: str
    address: Dict[str, Any]  # Required for registration
    phone: str
    organization_email: EmailStr
    
    # Admin user details
    admin_email: EmailStr
    admin_username: str
    admin_password: str = Field(..., min_length=8)
    admin_first_name: str
    admin_last_name: str

class OrganizationRegisterResponse(BaseModel):
    organization: OrganizationResponse
    admin_user: 'UserResponse'
    access_token: str
    refresh_token: str

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_subdomain: str
    access_code: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    tenant_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None

# Token Schemas
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    organization_subdomain: str  # Add this to return org info on login

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    email: str
    role: str
    exp: Optional[datetime] = None

# Participant Schemas
class ParticipantCreate(BaseModel):
    participant_type: ParticipantType
    identifier: str  # phone or email
    name: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class ParticipantUpdate(BaseModel):
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ParticipantResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    participant_type: ParticipantType
    identifier: str
    name: Optional[str]
    additional_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

# Conversation Schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    user_ids: Optional[List[UUID]] = []
    agent_types: Optional[List[str]] = []
    participant_ids: Optional[List[UUID]] = []
    participant_emails: Optional[List[str]] = []  # New field for email addresses

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ConversationStatus] = None

class ConversationUserAdd(BaseModel):
    user_id: UUID

class ConversationAgentAdd(BaseModel):
    agent_type: str
    configuration: Optional[Dict[str, Any]] = None

class ConversationParticipantAdd(BaseModel):
    participant_id: UUID

class MessageCreate(BaseModel):
    content: str
    message_type: MessageType = MessageType.TEXT
    metadata: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    message_type: MessageType
    content: str
    user_id: Optional[UUID]
    agent_type: Optional[str]
    participant_id: Optional[UUID]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Include sender info
    sender_name: Optional[str] = None
    sender_type: str  # "user", "agent", or "participant"
    
    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    title: Optional[str]
    description: Optional[str]
    status: ConversationStatus
    created_by_user_id: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Include related entities
    users: Optional[List[UserResponse]] = []
    agents: Optional[List[Dict[str, Any]]] = []  # {agent_type, added_at, is_active, configuration}
    participants: Optional[List[ParticipantResponse]] = []
    recent_messages: Optional[List[MessageResponse]] = []
    
    # For backward compatibility
    owner_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)

class ConversationListResponse(BaseModel):
    id: UUID
    title: Optional[str]
    description: Optional[str]
    status: ConversationStatus
    created_at: datetime
    updated_at: Optional[datetime]
    last_message: Optional[MessageResponse] = None
    participant_count: int
    message_count: int
    
    model_config = ConfigDict(from_attributes=True)

# Pagination
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

# Agent-related schemas
class AgentCreate(BaseModel):
    agent_type: str
    name: str
    description: Optional[str] = None
    is_free_agent: bool = False  # Default to proprietary
    configuration_template: Optional[Dict[str, Any]] = {}
    capabilities: Optional[List[str]] = []

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    configuration_template: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    is_active: Optional[bool] = None

class AgentResponse(BaseModel):
    id: UUID
    agent_type: str
    name: str
    description: Optional[str]
    is_free_agent: bool
    owner_tenant_id: Optional[UUID]
    configuration_template: Optional[Dict[str, Any]]
    capabilities: Optional[List[str]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class AgentInfo(BaseModel):
    agent_type: str
    name: str
    description: str
    capabilities: List[str]
    configuration_schema: Optional[Dict[str, Any]] = None
    is_available: bool  # True if free agent or owned by user's org

class AvailableAgentsResponse(BaseModel):
    agents: List[AgentResponse]

# Usage tracking schemas
class UsageRecordCreate(BaseModel):
    usage_type: str  # 'tokens', 'tts_minutes', 'stt_minutes'
    amount: int
    conversation_id: Optional[UUID] = None
    service_provider: Optional[str] = None
    model_name: Optional[str] = None
    cost_cents: Optional[int] = 0
    additional_data: Optional[Dict[str, Any]] = {}

class UsageRecordResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID]
    usage_type: str
    amount: int
    conversation_id: Optional[UUID]
    service_provider: Optional[str]
    model_name: Optional[str]
    cost_cents: Optional[int]
    additional_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UsageStats(BaseModel):
    period: str  # 'day', 'week', 'month'
    start_date: datetime
    end_date: datetime
    total_tokens: int
    total_tts_words: int
    total_stt_words: int
    total_cost_cents: int
    breakdown_by_user: Optional[Dict[str, Dict[str, int]]] = {}
    breakdown_by_service: Optional[Dict[str, Dict[str, int]]] = {}

class SystemMetricsResponse(BaseModel):
    id: UUID
    metric_type: str
    value: int
    tenant_id: Optional[UUID]
    additional_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AdminDashboardResponse(BaseModel):
    total_users: int
    total_conversations: int
    active_ws_connections: int
    db_connection_pool_size: int
    recent_usage: List[UsageRecordResponse]
    system_metrics: List[SystemMetricsResponse]
    tenant_stats: List[Dict[str, Any]]
    overall_usage_stats: UsageStats
    usage_by_organization: List[Dict[str, Any]]

# Admin user management
class AdminUserUpdate(BaseModel):
    role: Optional[str] = None  # 'user', 'admin', 'super_admin'
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

# Stripe billing schemas
class StripeCustomerCreate(BaseModel):
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None

class StripeCustomerResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    stripe_customer_id: str
    email: str
    name: Optional[str]
    phone: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class StripeSubscriptionCreate(BaseModel):
    stripe_price_id: str
    
class StripeSubscriptionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    stripe_subscription_id: str
    stripe_price_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    amount_cents: int
    currency: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class StripeInvoiceResponse(BaseModel):
    id: UUID
    customer_id: UUID
    stripe_invoice_id: str
    status: str
    amount_due_cents: int
    amount_paid_cents: int
    currency: str
    period_start: datetime
    period_end: datetime
    voice_words_count: int
    voice_usage_cents: int
    created_at: datetime
    due_date: Optional[datetime]
    paid_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class BillingDashboardResponse(BaseModel):
    current_subscription: Optional[StripeSubscriptionResponse]
    recent_invoices: List[StripeInvoiceResponse]
    current_period_usage: UsageStats
    upcoming_charges: Dict[str, int]  # estimated costs for current period

class UsageBillingCreate(BaseModel):
    """Schema for creating usage-based billing charges"""
    period_start: datetime
    period_end: datetime
    voice_words_count: int
    voice_usage_cents: int
