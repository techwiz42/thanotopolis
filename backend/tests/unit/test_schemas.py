"""
Comprehensive unit tests for Pydantic schemas.
Tests all request/response models for validation, serialization, and data integrity.
"""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from uuid import uuid4, UUID
from decimal import Decimal
from typing import Dict, Any

from app.schemas.schemas import (
    # Enums
    ParticipantType, MessageType, ConversationStatus,
    PhoneVerificationStatus, CallStatus, CallDirection,
    
    # Organization schemas
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationRegisterRequest, OrganizationRegisterResponse,
    
    # User schemas
    UserCreate, UserLogin, UserRegister, UserResponse, UserUpdate,
    
    # Token schemas
    TokenResponse, RefreshTokenRequest, TokenPayload,
    
    # Participant schemas
    ParticipantCreate, ParticipantUpdate, ParticipantResponse,
    
    # Conversation schemas
    ConversationCreate, ConversationUpdate, ConversationUserAdd,
    ConversationParticipantAdd,
    MessageCreate, MessageResponse, ConversationResponse,
    ConversationListResponse,
    
    # Pagination schemas
    PaginationParams, PaginatedResponse,
    
    # Agent schemas
    AgentCreate, AgentUpdate, AgentResponse, AgentInfo,
    AvailableAgentsResponse,
    
    # Usage tracking schemas
    UsageRecordCreate, UsageRecordResponse, UsageStats,
    SystemMetricsResponse, AdminDashboardResponse,
    AdminUserUpdate, UsageBillingCreate,
    
    # Telephony schemas
    TelephonyConfigurationCreate, TelephonyConfigurationUpdate,
    TelephonyConfigurationResponse, PhoneVerificationAttemptCreate,
    PhoneVerificationAttemptResponse, PhoneVerificationSubmit,
    PhoneCallCreate, PhoneCallUpdate, PhoneCallResponse,
    CallAgentCreate, CallAgentUpdate, CallAgentResponse,
    TelephonyDashboardResponse, CallAnalytics
)


class TestEnumSchemas:
    """Test enum validation and values."""

    def test_participant_type_enum(self):
        """Test ParticipantType enum values."""
        assert ParticipantType.PHONE == "phone"
        assert ParticipantType.EMAIL == "email"
        
        # Test validation
        assert ParticipantType("phone") == ParticipantType.PHONE
        assert ParticipantType("email") == ParticipantType.EMAIL
        
        with pytest.raises(ValueError):
            ParticipantType("invalid")

    def test_message_type_enum(self):
        """Test MessageType enum values."""
        assert MessageType.TEXT == "text"
        assert MessageType.SYSTEM == "system"
        assert MessageType.AGENT_HANDOFF == "agent_handoff"
        assert MessageType.PARTICIPANT_JOIN == "participant_join"
        assert MessageType.PARTICIPANT_LEAVE == "participant_leave"

    def test_conversation_status_enum(self):
        """Test ConversationStatus enum values."""
        assert ConversationStatus.ACTIVE == "active"
        assert ConversationStatus.ARCHIVED == "archived"
        assert ConversationStatus.CLOSED == "closed"

    def test_phone_verification_status_enum(self):
        """Test PhoneVerificationStatus enum values."""
        assert PhoneVerificationStatus.PENDING == "pending"
        assert PhoneVerificationStatus.VERIFIED == "verified"
        assert PhoneVerificationStatus.FAILED == "failed"
        assert PhoneVerificationStatus.EXPIRED == "expired"

    def test_call_status_enum(self):
        """Test CallStatus enum values."""
        assert CallStatus.INCOMING == "incoming"
        assert CallStatus.RINGING == "ringing"
        assert CallStatus.ANSWERED == "answered"
        assert CallStatus.IN_PROGRESS == "in_progress"
        assert CallStatus.COMPLETED == "completed"
        assert CallStatus.FAILED == "failed"
        assert CallStatus.NO_ANSWER == "no_answer"
        assert CallStatus.BUSY == "busy"

    def test_call_direction_enum(self):
        """Test CallDirection enum values."""
        assert CallDirection.INBOUND == "inbound"
        assert CallDirection.OUTBOUND == "outbound"


class TestOrganizationSchemas:
    """Test organization-related schemas."""

    def test_organization_create_valid(self):
        """Test valid OrganizationCreate schema."""
        data = {
            "name": "Test Organization",
            "subdomain": "testorg",
            "description": "A test organization",
            "full_name": "Test Organization Ltd",
            "address": {"street": "123 Main St", "city": "Test City"},
            "phone": "+1234567890",
            "organization_email": "contact@testorg.com"
        }
        
        org = OrganizationCreate(**data)
        assert org.name == "Test Organization"
        assert org.subdomain == "testorg"
        assert org.organization_email == "contact@testorg.com"
        assert org.address["street"] == "123 Main St"

    def test_organization_create_minimal(self):
        """Test OrganizationCreate with minimal required fields."""
        data = {
            "name": "Test Org",
            "subdomain": "testorg"
        }
        
        org = OrganizationCreate(**data)
        assert org.name == "Test Org"
        assert org.subdomain == "testorg"
        assert org.description is None
        assert org.full_name is None
        assert org.address is None

    def test_organization_create_invalid_email(self):
        """Test OrganizationCreate with invalid email."""
        data = {
            "name": "Test Org",
            "subdomain": "testorg",
            "organization_email": "invalid-email"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(**data)
        
        assert "value is not a valid email address" in str(exc_info.value)

    def test_organization_update_partial(self):
        """Test OrganizationUpdate with partial data."""
        data = {
            "full_name": "Updated Organization Name",
            "phone": "+9876543210"
        }
        
        update = OrganizationUpdate(**data)
        assert update.full_name == "Updated Organization Name"
        assert update.phone == "+9876543210"
        assert update.name is None  # Not provided

    def test_organization_register_request_valid(self):
        """Test valid OrganizationRegisterRequest."""
        data = {
            "name": "Test Org",
            "subdomain": "testorg",
            "full_name": "Test Organization Ltd",
            "address": {"street": "123 Main St", "city": "Test City"},
            "phone": "+1234567890",
            "organization_email": "contact@testorg.com",
            "admin_email": "admin@testorg.com",
            "admin_username": "admin",
            "admin_password": "securepassword123",
            "admin_first_name": "Admin",
            "admin_last_name": "User"
        }
        
        request = OrganizationRegisterRequest(**data)
        assert request.name == "Test Org"
        assert request.admin_email == "admin@testorg.com"
        assert request.admin_password == "securepassword123"

    def test_organization_register_request_password_too_short(self):
        """Test OrganizationRegisterRequest with password too short."""
        data = {
            "name": "Test Org",
            "subdomain": "testorg",
            "full_name": "Test Organization Ltd",
            "address": {},
            "phone": "+1234567890",
            "organization_email": "contact@testorg.com",
            "admin_email": "admin@testorg.com",
            "admin_username": "admin",
            "admin_password": "short",  # Too short
            "admin_first_name": "Admin",
            "admin_last_name": "User"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OrganizationRegisterRequest(**data)
        
        # Pydantic v2 error message
        assert "String should have at least 8 characters" in str(exc_info.value)

    def test_organization_response_model_config(self):
        """Test OrganizationResponse model configuration."""
        # Verify from_attributes is enabled for SQLAlchemy compatibility
        assert OrganizationResponse.model_config.get("from_attributes") is True


class TestUserSchemas:
    """Test user-related schemas."""

    def test_user_create_valid(self):
        """Test valid UserCreate schema."""
        data = {
            "email": "user@example.com",
            "username": "testuser",
            "password": "securepassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        user = UserCreate(**data)
        assert user.email == "user@example.com"
        assert user.username == "testuser"
        assert user.password == "securepassword123"

    def test_user_create_password_validation(self):
        """Test UserCreate password length validation."""
        data = {
            "email": "user@example.com",
            "username": "testuser",
            "password": "short"  # Too short
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        
        # Pydantic v2 error message
        assert "String should have at least 8 characters" in str(exc_info.value)

    def test_user_login_schema(self):
        """Test UserLogin schema."""
        data = {
            "email": "user@example.com",
            "password": "password123"
        }
        
        login = UserLogin(**data)
        assert login.email == "user@example.com"
        assert login.password == "password123"

    def test_user_register_schema(self):
        """Test UserRegister schema."""
        data = {
            "email": "user@example.com",
            "username": "testuser",
            "password": "securepassword123",
            "first_name": "Test",
            "last_name": "User",
            "organization_subdomain": "testorg",
            "access_code": "access123"
        }
        
        register = UserRegister(**data)
        assert register.organization_subdomain == "testorg"
        assert register.access_code == "access123"

    def test_user_response_model_config(self):
        """Test UserResponse model configuration."""
        assert UserResponse.model_config.get("from_attributes") is True

    def test_user_update_partial(self):
        """Test UserUpdate with partial data."""
        data = {
            "first_name": "Updated",
            "is_active": False
        }
        
        update = UserUpdate(**data)
        assert update.first_name == "Updated"
        assert update.is_active is False
        assert update.email is None  # Not provided


class TestTokenSchemas:
    """Test token-related schemas."""

    def test_token_response_schema(self):
        """Test TokenResponse schema."""
        data = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_456",
            "organization_subdomain": "testorg"
        }
        
        token = TokenResponse(**data)
        assert token.access_token == "access_token_123"
        assert token.refresh_token == "refresh_token_456"
        assert token.token_type == "bearer"  # Default value
        assert token.organization_subdomain == "testorg"

    def test_refresh_token_request_schema(self):
        """Test RefreshTokenRequest schema."""
        data = {"refresh_token": "refresh_token_123"}
        
        request = RefreshTokenRequest(**data)
        assert request.refresh_token == "refresh_token_123"

    def test_token_payload_schema(self):
        """Test TokenPayload schema."""
        data = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "email": "user@example.com",
            "role": "user",
            "exp": datetime.now(timezone.utc)
        }
        
        payload = TokenPayload(**data)
        assert payload.email == "user@example.com"
        assert payload.role == "user"


class TestConversationSchemas:
    """Test conversation-related schemas."""

    def test_conversation_create_schema(self):
        """Test ConversationCreate schema."""
        data = {
            "title": "Test Conversation",
            "description": "A test conversation",
            "user_ids": [uuid4(), uuid4()],
            "agent_types": ["moderator", "web_search"],
            "participant_emails": ["user1@example.com", "user2@example.com"]
        }
        
        conv = ConversationCreate(**data)
        assert conv.title == "Test Conversation"
        assert len(conv.user_ids) == 2
        assert len(conv.agent_types) == 2
        assert len(conv.participant_emails) == 2

    def test_conversation_create_defaults(self):
        """Test ConversationCreate default values."""
        conv = ConversationCreate()
        assert conv.title is None
        assert conv.user_ids == []
        assert conv.agent_types == []
        assert conv.participant_emails == []

    def test_message_create_schema(self):
        """Test MessageCreate schema."""
        data = {
            "content": "Hello, world!",
            "message_type": MessageType.TEXT,
            "metadata": {"key": "value"},
            "mention": "@moderator"
        }
        
        message = MessageCreate(**data)
        assert message.content == "Hello, world!"
        assert message.message_type == MessageType.TEXT
        assert message.metadata == {"key": "value"}
        assert message.mention == "@moderator"

    def test_message_create_defaults(self):
        """Test MessageCreate default values."""
        message = MessageCreate(content="Test message")
        assert message.content == "Test message"
        assert message.message_type == MessageType.TEXT  # Default
        assert message.metadata is None
        assert message.mention is None

    def test_conversation_response_model_config(self):
        """Test ConversationResponse model configuration."""
        assert ConversationResponse.model_config.get("from_attributes") is True


class TestPaginationSchemas:
    """Test pagination schemas."""

    def test_pagination_params_defaults(self):
        """Test PaginationParams default values."""
        pagination = PaginationParams()
        assert pagination.page == 1
        assert pagination.page_size == 20

    def test_pagination_params_validation(self):
        """Test PaginationParams validation."""
        # Valid params
        pagination = PaginationParams(page=2, page_size=50)
        assert pagination.page == 2
        assert pagination.page_size == 50

    def test_pagination_params_invalid_page(self):
        """Test PaginationParams with invalid page number."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page=0)  # Must be >= 1
        
        # Pydantic v2 error message
        assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_pagination_params_invalid_page_size(self):
        """Test PaginationParams with invalid page size."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page_size=0)  # Must be >= 1
        
        # Pydantic v2 error message
        assert "Input should be greater than or equal to 1" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page_size=101)  # Must be <= 100
        
        # Pydantic v2 error message  
        assert "Input should be less than or equal to 100" in str(exc_info.value)

    def test_paginated_response_schema(self):
        """Test PaginatedResponse schema."""
        data = {
            "items": [{"id": 1}, {"id": 2}],
            "total": 2,
            "page": 1,
            "page_size": 20,
            "total_pages": 1
        }
        
        response = PaginatedResponse(**data)
        assert len(response.items) == 2
        assert response.total == 2
        assert response.total_pages == 1


class TestAgentSchemas:
    """Test agent-related schemas."""

    def test_agent_create_schema(self):
        """Test AgentCreate schema."""
        data = {
            "agent_type": "custom_agent",
            "name": "Custom Agent",
            "description": "A custom agent for testing",
            "is_free_agent": True,
            "configuration_template": {"key": "value"},
            "capabilities": ["search", "analysis"]
        }
        
        agent = AgentCreate(**data)
        assert agent.agent_type == "custom_agent"
        assert agent.name == "Custom Agent"
        assert agent.is_free_agent is True
        assert agent.configuration_template == {"key": "value"}
        assert agent.capabilities == ["search", "analysis"]

    def test_agent_create_defaults(self):
        """Test AgentCreate default values."""
        data = {
            "agent_type": "test_agent",
            "name": "Test Agent"
        }
        
        agent = AgentCreate(**data)
        assert agent.is_free_agent is False  # Default to proprietary
        assert agent.configuration_template == {}
        assert agent.capabilities == []

    def test_agent_update_partial(self):
        """Test AgentUpdate with partial data."""
        data = {
            "name": "Updated Agent Name",
            "is_enabled": False
        }
        
        update = AgentUpdate(**data)
        assert update.name == "Updated Agent Name"
        assert update.is_enabled is False
        assert update.description is None  # Not provided

    def test_agent_response_model_config(self):
        """Test AgentResponse model configuration."""
        assert AgentResponse.model_config.get("from_attributes") is True

    def test_agent_info_schema(self):
        """Test AgentInfo schema."""
        data = {
            "agent_type": "test_agent",
            "name": "Test Agent",
            "description": "A test agent",
            "capabilities": ["search", "analysis"],
            "configuration_schema": {"param1": "string"},
            "is_available": True
        }
        
        info = AgentInfo(**data)
        assert info.agent_type == "test_agent"
        assert info.is_available is True
        assert len(info.capabilities) == 2


class TestUsageTrackingSchemas:
    """Test usage tracking and billing schemas."""

    def test_usage_record_create_schema(self):
        """Test UsageRecordCreate schema."""
        data = {
            "usage_type": "tokens",
            "amount": Decimal("1000.50"),
            "cost_per_unit": Decimal("0.001"),
            "cost_cents": 100,
            "cost_currency": "USD",
            "resource_type": "conversation",
            "resource_id": str(uuid4()),
            "usage_metadata": {"model": "gpt-4"}
        }
        
        record = UsageRecordCreate(**data)
        assert record.usage_type == "tokens"
        assert record.amount == Decimal("1000.50")
        assert record.cost_cents == 100
        assert record.cost_currency == "USD"
        assert record.usage_metadata == {"model": "gpt-4"}

    def test_usage_record_create_defaults(self):
        """Test UsageRecordCreate default values."""
        data = {
            "usage_type": "api_calls",
            "amount": Decimal("10")
        }
        
        record = UsageRecordCreate(**data)
        assert record.cost_currency == "USD"  # Default
        assert record.usage_metadata == {}  # Default

    def test_usage_stats_schema(self):
        """Test UsageStats schema."""
        data = {
            "period": "month",
            "start_date": datetime.now(timezone.utc),
            "end_date": datetime.now(timezone.utc),
            "total_tokens": 50000,
            "total_tts_words": 10000,
            "total_stt_words": 8000,
            "total_cost_cents": 500,
            "breakdown_by_user": {"user1": {"tokens": 25000}},
            "breakdown_by_service": {"gpt-4": {"tokens": 30000}}
        }
        
        stats = UsageStats(**data)
        assert stats.period == "month"
        assert stats.total_tokens == 50000
        assert stats.total_cost_cents == 500

    def test_admin_dashboard_response_schema(self):
        """Test AdminDashboardResponse schema."""
        data = {
            "total_users": 100,
            "total_conversations": 250,
            "active_ws_connections": 15,
            "db_connection_pool_size": 10,
            "recent_usage": [],
            "system_metrics": [],
            "tenant_stats": [],
            "overall_usage_stats": {
                "period": "month",
                "start_date": datetime.now(timezone.utc),
                "end_date": datetime.now(timezone.utc),
                "total_tokens": 0,
                "total_tts_words": 0,
                "total_stt_words": 0,
                "total_cost_cents": 0
            },
            "usage_by_organization": []
        }
        
        dashboard = AdminDashboardResponse(**data)
        assert dashboard.total_users == 100
        assert dashboard.total_conversations == 250
        assert dashboard.active_ws_connections == 15

    def test_admin_user_update_schema(self):
        """Test AdminUserUpdate schema."""
        data = {
            "role": "admin",
            "is_active": True,
            "is_verified": True
        }
        
        update = AdminUserUpdate(**data)
        assert update.role == "admin"
        assert update.is_active is True
        assert update.is_verified is True


class TestTelephonySchemas:
    """Test telephony-related schemas."""

    def test_telephony_configuration_create_schema(self):
        """Test TelephonyConfigurationCreate schema."""
        data = {
            "organization_phone_number": "+1234567890",
            "formatted_phone_number": "(123) 456-7890",
            "country_code": "US",
            "welcome_message": "Welcome to our service",
            "business_hours": {"monday": "9-17"},
            "timezone": "America/New_York",
            "max_concurrent_calls": 10,
            "call_timeout_seconds": 600,
            "voice_id": "voice123",
            "voice_settings": {"speed": 1.0},
            "integration_method": "sip_trunking",
            "record_calls": True,
            "transcript_calls": True
        }
        
        config = TelephonyConfigurationCreate(**data)
        assert config.organization_phone_number == "+1234567890"
        assert config.country_code == "US"
        assert config.max_concurrent_calls == 10
        assert config.integration_method == "sip_trunking"

    def test_telephony_configuration_create_defaults(self):
        """Test TelephonyConfigurationCreate default values."""
        data = {
            "organization_phone_number": "+1234567890",
            "country_code": "US"
        }
        
        config = TelephonyConfigurationCreate(**data)
        assert config.timezone == "UTC"  # Default
        assert config.max_concurrent_calls == 5  # Default
        assert config.call_timeout_seconds == 300  # Default
        assert config.integration_method == "call_forwarding"  # Default
        assert config.record_calls is True  # Default
        assert config.transcript_calls is True  # Default

    def test_phone_call_create_schema(self):
        """Test PhoneCallCreate schema."""
        data = {
            "call_sid": "call123",
            "session_id": "session456",
            "customer_phone_number": "+1234567890",
            "organization_phone_number": "+0987654321",
            "platform_phone_number": "+1122334455",
            "direction": CallDirection.INBOUND,
            "call_metadata": {"source": "twilio"}
        }
        
        call = PhoneCallCreate(**data)
        assert call.call_sid == "call123"
        assert call.direction == CallDirection.INBOUND
        assert call.call_metadata == {"source": "twilio"}

    def test_phone_call_update_schema(self):
        """Test PhoneCallUpdate schema."""
        data = {
            "status": CallStatus.COMPLETED,
            "duration_seconds": 300,
            "cost_cents": 50,
            "recording_url": "https://example.com/recording.mp3",
            "transcript": "Hello, how can I help you?",
            "summary": "Customer inquiry about services"
        }
        
        update = PhoneCallUpdate(**data)
        assert update.status == CallStatus.COMPLETED
        assert update.duration_seconds == 300
        assert update.cost_cents == 50

    def test_call_analytics_schema(self):
        """Test CallAnalytics schema."""
        data = {
            "period": "week",
            "start_date": datetime.now(timezone.utc),
            "end_date": datetime.now(timezone.utc),
            "total_calls": 50,
            "total_duration_seconds": 15000,
            "total_cost_cents": 750,
            "average_call_duration": 300,
            "call_status_breakdown": {"completed": 45, "failed": 5},
            "calls_by_hour": {"09": 10, "10": 15},
            "top_agents_used": [{"agent": "customer_service", "count": 30}]
        }
        
        analytics = CallAnalytics(**data)
        assert analytics.period == "week"
        assert analytics.total_calls == 50
        assert analytics.average_call_duration == 300


class TestSchemaValidationEdgeCases:
    """Test edge cases and validation scenarios."""

    def test_uuid_field_validation(self):
        """Test UUID field validation."""
        # Valid UUID
        valid_uuid = uuid4()
        data = {"user_id": valid_uuid}
        request = ConversationUserAdd(**data)
        assert request.user_id == valid_uuid

        # Invalid UUID string
        with pytest.raises(ValidationError):
            ConversationUserAdd(user_id="not-a-uuid")

    def test_email_field_validation(self):
        """Test email field validation across schemas."""
        # Valid email
        valid_data = {
            "email": "user@example.com",
            "username": "testuser",
            "password": "password123"
        }
        user = UserCreate(**valid_data)
        assert user.email == "user@example.com"

        # Invalid email formats
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user@.com"
        ]

        for invalid_email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(
                    email=invalid_email,
                    username="testuser", 
                    password="password123"
                )

    def test_decimal_field_validation(self):
        """Test Decimal field validation in usage records."""
        # Valid decimal
        data = {
            "usage_type": "tokens",
            "amount": Decimal("1000.50")
        }
        record = UsageRecordCreate(**data)
        assert record.amount == Decimal("1000.50")

        # String that can be converted to decimal
        data = {
            "usage_type": "tokens",
            "amount": "1000.50"
        }
        record = UsageRecordCreate(**data)
        assert record.amount == Decimal("1000.50")

    def test_datetime_field_handling(self):
        """Test datetime field handling."""
        now = datetime.now(timezone.utc)
        
        # Valid datetime
        data = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "email": "user@example.com",
            "role": "user",
            "exp": now
        }
        payload = TokenPayload(**data)
        assert payload.exp == now

    def test_optional_field_handling(self):
        """Test optional field handling across schemas."""
        # Test with minimal required fields
        minimal_org = OrganizationCreate(
            name="Test Org",
            subdomain="testorg"
        )
        assert minimal_org.description is None
        assert minimal_org.full_name is None

        # Test with all optional fields provided
        full_org = OrganizationCreate(
            name="Test Org",
            subdomain="testorg",
            description="Description",
            full_name="Full Name",
            address={"street": "123 Main St"},
            phone="+1234567890",
            organization_email="contact@example.com"
        )
        assert full_org.description == "Description"
        assert full_org.full_name == "Full Name"

    def test_json_field_validation(self):
        """Test JSON/Dict field validation."""
        # Valid JSON data
        valid_address = {
            "street": "123 Main St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345",
            "country": "US"
        }
        
        org = OrganizationCreate(
            name="Test Org",
            subdomain="testorg",
            address=valid_address
        )
        assert org.address == valid_address

        # Empty dict should be valid
        org_empty = OrganizationCreate(
            name="Test Org",
            subdomain="testorg",
            address={}
        )
        assert org_empty.address == {}

    def test_list_field_validation(self):
        """Test List field validation."""
        # Valid list of UUIDs
        user_ids = [uuid4(), uuid4()]
        conv = ConversationCreate(user_ids=user_ids)
        assert conv.user_ids == user_ids

        # Valid list of strings
        agent_types = ["moderator", "web_search"]
        conv = ConversationCreate(agent_types=agent_types)
        assert conv.agent_types == agent_types

        # Empty list should be valid
        conv_empty = ConversationCreate()
        assert conv_empty.user_ids == []
        assert conv_empty.agent_types == []

    def test_model_serialization(self):
        """Test model serialization with model_dump."""
        org_data = {
            "name": "Test Org",
            "subdomain": "testorg",
            "full_name": "Test Organization Ltd"
        }
        
        org = OrganizationCreate(**org_data)
        serialized = org.model_dump()
        
        assert serialized["name"] == "Test Org"
        assert serialized["subdomain"] == "testorg"
        assert serialized["full_name"] == "Test Organization Ltd"

    def test_model_dump_exclude_unset(self):
        """Test model_dump with exclude_unset=True."""
        update_data = {
            "full_name": "Updated Name"
        }
        
        update = OrganizationUpdate(**update_data)
        serialized = update.model_dump(exclude_unset=True)
        
        # Only provided fields should be in the output
        assert "full_name" in serialized
        assert "name" not in serialized
        assert "description" not in serialized