"""
Integration tests for database models and their relationships.
Tests actual database operations, constraints, and model behavior.
"""
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models import User, Tenant, Conversation, ConversationUser, Message, RefreshToken


class TestUserModel:
    """Test User model functionality."""

    @pytest.mark.asyncio
    async def test_create_user_with_required_fields(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test creating user with all required fields."""
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            hashed_password="hashed_password_here",
            tenant_id=sample_tenant.id
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.role == "member"  # Default value
        assert user.is_active is True  # Default value
        assert user.created_at is not None
        # updated_at is None on creation, only set on updates
        assert user.updated_at is None

    @pytest.mark.asyncio
    async def test_user_email_uniqueness_constraint(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test that email uniqueness is enforced."""
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            first_name="User",
            last_name="One",
            hashed_password="hash1",
            tenant_id=sample_tenant.id
        )
        
        user2 = User(
            email="duplicate@example.com",  # Same email
            username="user2",
            first_name="User",
            last_name="Two",
            hashed_password="hash2",
            tenant_id=sample_tenant.id
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        # Rollback the failed transaction
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_user_tenant_relationship(self, db_session: AsyncSession, sample_user: User):
        """Test that user can access their tenant."""
        # Load user with tenant relationship
        query = select(User).where(User.id == sample_user.id)
        result = await db_session.execute(query)
        user = result.scalar_one()
        
        # Access tenant through relationship
        await db_session.refresh(user, ["tenant"])
        
        assert user.tenant is not None
        assert user.tenant.id == sample_user.tenant_id


class TestTenantModel:
    """Test Tenant model functionality."""

    @pytest.mark.asyncio
    async def test_create_tenant_with_required_fields(self, db_session: AsyncSession):
        """Test creating tenant with required fields."""
        tenant = Tenant(
            name="Test Organization",
            subdomain="testorg",
            access_code="TEST123"
        )
        
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        
        assert tenant.id is not None
        assert tenant.name == "Test Organization"
        assert tenant.subdomain == "testorg"
        assert tenant.access_code == "TEST123"
        assert tenant.is_active is True
        assert tenant.created_at is not None

    @pytest.mark.asyncio
    async def test_tenant_subdomain_uniqueness(self, db_session: AsyncSession):
        """Test that subdomain uniqueness is enforced."""
        tenant1 = Tenant(
            name="Org 1",
            subdomain="duplicate",
            access_code="CODE1"
        )
        
        tenant2 = Tenant(
            name="Org 2",
            subdomain="duplicate",  # Same subdomain
            access_code="CODE2"
        )
        
        db_session.add(tenant1)
        await db_session.commit()
        
        db_session.add(tenant2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        # Rollback the failed transaction
        await db_session.rollback()


class TestConversationModel:
    """Test Conversation model functionality."""

    @pytest.mark.asyncio
    async def test_create_conversation_with_title(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test creating conversation with title."""
        conversation = Conversation(
            title="Test Conversation",
            tenant_id=sample_tenant.id  # Add required tenant_id
        )
        
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.title == "Test Conversation"
        assert conversation.status == "active"  # Default status
        assert conversation.created_at is not None

    @pytest.mark.asyncio
    async def test_conversation_users_relationship(self, db_session: AsyncSession, sample_conversation: Conversation, sample_user: User):
        """Test conversation-user many-to-many relationship."""
        # Add user to conversation
        conversation_user = ConversationUser(
            conversation_id=sample_conversation.id,
            user_id=sample_user.id,
            is_active=True
        )
        db_session.add(conversation_user)
        await db_session.commit()
        
        # Load conversation with users
        await db_session.refresh(sample_conversation, ["users"])
        
        assert len(sample_conversation.users) == 1
        assert sample_conversation.users[0].user_id == sample_user.id


class TestMessageModel:
    """Test Message model functionality."""

    @pytest.mark.asyncio
    async def test_create_user_message(self, db_session: AsyncSession, sample_conversation: Conversation, sample_user: User):
        """Test creating a user message."""
        message = Message(
            conversation_id=sample_conversation.id,
            content="Hello, this is a test message",
            user_id=sample_user.id,
            message_type="text"
        )
        
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        
        assert message.id is not None
        assert message.content == "Hello, this is a test message"
        assert message.user_id == sample_user.id
        assert message.message_type == "text"
        assert message.created_at is not None

    @pytest.mark.asyncio
    async def test_message_with_metadata(self, db_session: AsyncSession, sample_conversation: Conversation, sample_user: User):
        """Test creating message with metadata."""
        metadata = {
            "file_attachment": True,
            "filename": "document.pdf",
            "file_size": 1024000
        }
        
        message = Message(
            conversation_id=sample_conversation.id,
            content="Please review this document",
            user_id=sample_user.id,
            message_type="text",
            message_metadata=metadata
        )
        
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        
        assert message.message_metadata is not None
        assert message.message_metadata["filename"] == "document.pdf"
        assert message.message_metadata["file_size"] == 1024000


class TestRefreshTokenModel:
    """Test RefreshToken model functionality."""

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, db_session: AsyncSession, sample_user: User):
        """Test creating a refresh token."""
        token = RefreshToken(
            token="refresh_token_string_here",
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)
        
        assert token.id is not None
        assert token.token == "refresh_token_string_here"
        assert token.user_id == sample_user.id
        assert token.is_revoked is False
        assert token.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_multiple_refresh_tokens_per_user(self, db_session: AsyncSession, sample_user: User):
        """Test that user can have multiple active refresh tokens."""
        token1 = RefreshToken(
            token="token1",
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        token2 = RefreshToken(
            token="token2",
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        db_session.add_all([token1, token2])
        await db_session.commit()
        
        # Query user's active tokens
        query = select(RefreshToken).where(
            RefreshToken.user_id == sample_user.id,
            RefreshToken.is_revoked == False
        )
        
        result = await db_session.execute(query)
        tokens = result.scalars().all()
        
        assert len(tokens) == 2


class TestModelRelationships:
    """Test complex relationships between models."""

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test that tenant data isolation works properly."""
        # Create second tenant
        other_tenant = Tenant(
            name="Other Org",
            subdomain="other",
            access_code="OTHER123"
        )
        db_session.add(other_tenant)
        await db_session.commit()
        
        # Create users for each tenant
        user1 = User(
            email="user1@tenant1.com",
            username="tenant1user",
            first_name="Tenant1",
            last_name="User",
            hashed_password="hash1",
            tenant_id=sample_tenant.id
        )
        
        user2 = User(
            email="user2@tenant2.com",
            username="tenant2user",
            first_name="Tenant2",
            last_name="User",
            hashed_password="hash2",
            tenant_id=other_tenant.id
        )
        
        db_session.add_all([user1, user2])
        await db_session.commit()
        
        # Query users for specific tenant
        query = select(User).where(User.tenant_id == sample_tenant.id)
        result = await db_session.execute(query)
        tenant1_users = result.scalars().all()
        
        # Should only get users for that tenant
        tenant1_emails = [user.email for user in tenant1_users]
        assert "user1@tenant1.com" in tenant1_emails
        assert "user2@tenant2.com" not in tenant1_emails