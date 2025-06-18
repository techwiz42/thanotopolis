# backend/app/schemas/schemas.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum
from decimal import Decimal

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

# Telephony Enums
class PhoneVerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"

class CallStatus(str, Enum):
    INCOMING = "incoming"
    RINGING = "ringing"
    ANSWERED = "answered"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"

class CallDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

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
    conversation_id: UUID
    participant_type: str
    identifier: str
    display_name: Optional[str]
    is_active: bool
    joined_at: datetime
    left_at: Optional[datetime]
    
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
    mention: Optional[str] = None  # Agent mention for routing

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
    is_enabled: Optional[bool] = None
    is_active: Optional[bool] = None

class AgentResponse(BaseModel):
    id: UUID
    agent_type: str
    name: str
    description: Optional[str]
    is_free_agent: bool
    owner_tenant_id: Optional[UUID]
    owner_domain: Optional[str]
    is_enabled: bool
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
    usage_type: str  # 'tokens', 'api_calls', 'telephony_minutes'
    amount: Decimal
    cost_per_unit: Optional[Decimal] = None
    cost_cents: Optional[int] = None
    cost_currency: str = "USD"
    resource_type: Optional[str] = None  # 'conversation', 'phone_call'
    resource_id: Optional[str] = None
    usage_metadata: Optional[Dict[str, Any]] = {}

class UsageRecordResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    usage_type: str
    amount: Decimal
    cost_per_unit: Optional[Decimal]
    cost_cents: Optional[int]
    cost_currency: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    usage_metadata: Optional[Dict[str, Any]]
    usage_date: datetime
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

# Stripe billing schemas removed

class UsageBillingCreate(BaseModel):
    """Schema for creating usage-based billing charges"""
    period_start: datetime
    period_end: datetime
    voice_words_count: int
    voice_usage_cents: int

# ============================================================================
# TELEPHONY SCHEMAS
# ============================================================================

# Telephony Configuration Schemas
class TelephonyConfigurationCreate(BaseModel):
    organization_phone_number: str  # E.164 format
    formatted_phone_number: Optional[str] = None
    country_code: str
    welcome_message: Optional[str] = None
    business_hours: Optional[Dict[str, Any]] = None
    timezone: str = "UTC"
    max_concurrent_calls: int = 5
    call_timeout_seconds: int = 300
    voice_id: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    integration_method: str = "call_forwarding"
    record_calls: bool = True
    transcript_calls: bool = True

class TelephonyConfigurationUpdate(BaseModel):
    organization_phone_number: Optional[str] = None
    formatted_phone_number: Optional[str] = None
    country_code: Optional[str] = None
    welcome_message: Optional[str] = None
    call_forwarding_enabled: Optional[bool] = None
    is_enabled: Optional[bool] = None
    business_hours: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None
    max_concurrent_calls: Optional[int] = None
    call_timeout_seconds: Optional[int] = None
    voice_id: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    forwarding_instructions: Optional[str] = None
    integration_method: Optional[str] = None
    record_calls: Optional[bool] = None
    transcript_calls: Optional[bool] = None

class TelephonyConfigurationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    organization_phone_number: str
    formatted_phone_number: Optional[str]
    country_code: str
    verification_status: PhoneVerificationStatus
    platform_phone_number: Optional[str]
    call_forwarding_enabled: bool
    welcome_message: Optional[str]
    is_enabled: bool
    business_hours: Optional[Dict[str, Any]]
    timezone: str
    max_concurrent_calls: int
    call_timeout_seconds: int
    voice_id: Optional[str]
    voice_settings: Optional[Dict[str, Any]]
    forwarding_instructions: Optional[str]
    integration_method: str
    record_calls: bool
    transcript_calls: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

# Phone Verification Schemas
class PhoneVerificationAttemptCreate(BaseModel):
    verification_method: str = "sms"  # sms, call
    organization_phone_number: str

class PhoneVerificationAttemptResponse(BaseModel):
    id: UUID
    telephony_config_id: UUID
    verification_code: str
    verification_method: str
    organization_phone_number: str
    status: PhoneVerificationStatus
    attempts_count: int
    max_attempts: int
    created_at: datetime
    expires_at: datetime
    verified_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class PhoneVerificationSubmit(BaseModel):
    verification_code: str

# Phone Call Schemas
class PhoneCallCreate(BaseModel):
    call_sid: str
    session_id: Optional[str] = None
    customer_phone_number: str
    organization_phone_number: str
    platform_phone_number: str
    direction: CallDirection
    call_metadata: Optional[Dict[str, Any]] = None

class PhoneCallUpdate(BaseModel):
    status: Optional[CallStatus] = None
    start_time: Optional[datetime] = None
    answer_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    cost_cents: Optional[int] = None
    cost_currency: Optional[str] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    call_metadata: Optional[Dict[str, Any]] = None

class PhoneCallResponse(BaseModel):
    id: UUID
    telephony_config_id: UUID
    conversation_id: Optional[UUID]
    call_sid: str
    session_id: Optional[str]
    customer_phone_number: str
    organization_phone_number: str
    platform_phone_number: str
    direction: CallDirection
    status: CallStatus
    start_time: Optional[datetime]
    answer_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    cost_cents: int
    cost_currency: str
    recording_url: Optional[str]
    transcript: Optional[str]
    summary: Optional[str]
    call_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

# Call Agent Schemas
class CallAgentCreate(BaseModel):
    call_id: UUID
    agent_id: UUID

class CallAgentUpdate(BaseModel):
    deactivated_at: Optional[datetime] = None
    usage_duration_seconds: Optional[int] = None
    tokens_used: Optional[int] = None
    response_count: Optional[int] = None
    average_response_time_ms: Optional[int] = None

class CallAgentResponse(BaseModel):
    id: UUID
    call_id: UUID
    agent_id: UUID
    activated_at: datetime
    deactivated_at: Optional[datetime]
    usage_duration_seconds: Optional[int]
    tokens_used: int
    response_count: int
    average_response_time_ms: Optional[int]
    
    model_config = ConfigDict(from_attributes=True)

# Telephony Dashboard Schemas
class TelephonyDashboardResponse(BaseModel):
    configuration: TelephonyConfigurationResponse
    recent_calls: List[PhoneCallResponse]
    call_stats: Dict[str, Any]  # call volume, duration stats, etc.
    verification_status: PhoneVerificationStatus
    total_calls_today: int
    total_call_duration_today: int
    active_calls: int

# Telephony Analytics Schemas
class CallAnalytics(BaseModel):
    period: str  # 'day', 'week', 'month'
    start_date: datetime
    end_date: datetime
    total_calls: int
    total_duration_seconds: int
    total_cost_cents: int
    average_call_duration: int
    call_status_breakdown: Dict[str, int]
    calls_by_hour: Dict[str, int]
    top_agents_used: List[Dict[str, Any]]
