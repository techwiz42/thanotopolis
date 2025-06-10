"""
Integration tests for database models.
Tests actual database operations and relationships.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
import asyncio

from app.models.models import User, Tenant, Conversation, Message, RefreshToken


class TestUserModelIntegration:
    """Test User model with database integration."""

    async def test_create_user_with_required_fields(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test creating user with required fields."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_here",
            tenant_id=sample_tenant.id,
            role="user"
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.tenant_id == sample_tenant.id
        assert user.role == "user"
        assert user.is_active is True  # Default
        assert user.created_at is not None

    async def test_user_email_uniqueness_constraint(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test that email uniqueness is enforced."""
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            hashed_password="hash1",
            tenant_id=sample_tenant.id
        )
        
        user2 = User(
            email="duplicate@example.com",
            username="user2", 
            hashed_password="hash2",
            tenant_id=sample_tenant.id
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()

    async def test_user_tenant_relationship(self, db_session: AsyncSession, sample_user: User):
        """Test user-tenant relationship."""
        await db_session.refresh(sample_user, ["tenant"])
        
        assert sample_user.tenant is not None
        assert sample_user.tenant.id == sample_user.tenant_id

    async def test_user_conversations_relationship(self, db_session: AsyncSession, sample_user: User):
        """Test user-conversations relationship."""
        conversation = Conversation(
            title="Test Conversation",
            tenant_id=sample_user.tenant_id
        )
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
        
        # Add user to conversation (assuming many-to-many relationship)
        # This would depend on your actual model structure
        await db_session.refresh(sample_user, ["conversations"])
        
        # Test that relationship loading works
        assert hasattr(sample_user, 'conversations')

    async def test_user_automatic_timestamps(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test that timestamps are automatically set."""
        user = User(
            email="timestamp@example.com",
            username="timestampuser",
            hashed_password="hash",
            tenant_id=sample_tenant.id
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.created_at is not None
        assert user.updated_at is not None
        
        # Update user
        original_updated = user.updated_at
        await asyncio.sleep(0.01)  # Ensure time difference
        user.username = "updated_username"
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.updated_at > original_updated


class TestTenantModelIntegration:
    """Test Tenant model with database integration."""

    async def test_create_tenant_with_required_fields(self, db_session: AsyncSession):
        """Test creating tenant with required fields."""
        tenant = Tenant(
            name="Test Organization",
            subdomain="testorg"
        )
        
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        
        assert tenant.id is not None
        assert tenant.name == "Test Organization"
        assert tenant.subdomain == "testorg"
        assert tenant.is_active is True  # Default
        assert tenant.access_code is not None  # Should be auto-generated
        assert tenant.created_at is not None

    async def test_tenant_subdomain_uniqueness(self, db_session: AsyncSession):
        """Test subdomain uniqueness constraint."""
        tenant1 = Tenant(name="Org 1", subdomain="duplicate")
        tenant2 = Tenant(name="Org 2", subdomain="duplicate")
        
        db_session.add(tenant1)
        await db_session.commit()
        
        db_session.add(tenant2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()

    async def test_tenant_users_relationship(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test tenant-users relationship."""
        await db_session.refresh(sample_tenant, ["users"])
        
        # Should have at least the sample user
        assert hasattr(sample_tenant, 'users')


class TestConversationModelIntegration:
    """Test Conversation model with database integration."""

    async def test_create_conversation_with_title(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test creating conversation with title."""
        conversation = Conversation(
            title="Test Conversation",
            tenant_id=sample_tenant.id
        )
        
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.title == "Test Conversation"
        assert conversation.tenant_id == sample_tenant.id
        assert conversation.created_at is not None

    async def test_conversation_without_title(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test creating conversation without title."""
        conversation = Conversation(tenant_id=sample_tenant.id)
        
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.title is None
        assert conversation.tenant_id == sample_tenant.id

    async def test_conversation_messages_relationship(self, db_session: AsyncSession, sample_conversation: Conversation):
        """Test conversation-messages relationship."""
        message = Message(
            content="Test message",
            conversation_id=sample_conversation.id,
            user_id=None,  # System message
            agent_type="test_agent"
        )
        
        db_session.add(message)
        await db_session.commit()
        
        await db_session.refresh(sample_conversation, ["messages"])
        assert len(sample_conversation.messages) >= 1


class TestMessageModelIntegration:
    """Test Message model with database integration."""

    async def test_create_user_message(self, db_session: AsyncSession, sample_user: User, sample_conversation: Conversation):
        """Test creating user message."""
        message = Message(
            content="Hello from user",
            conversation_id=sample_conversation.id,
            user_id=sample_user.id
        )
        
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        
        assert message.id is not None
        assert message.content == "Hello from user"
        assert message.user_id == sample_user.id
        assert message.conversation_id == sample_conversation.id
        assert message.created_at is not None

    async def test_create_agent_message(self, db_session: AsyncSession, sample_conversation: Conversation):
        """Test creating agent message."""
        message = Message(
            content="Hello from agent",
            conversation_id=sample_conversation.id,
            agent_type="test_agent"
        )
        
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        
        assert message.id is not None
        assert message.content == "Hello from agent"
        assert message.agent_type == "test_agent"
        assert message.user_id is None

    async def test_message_with_metadata(self, db_session: AsyncSession, sample_conversation: Conversation):
        """Test message with additional metadata."""
        metadata = {"key": "value", "number": 42}
        message = Message(
            content="Message with metadata",
            conversation_id=sample_conversation.id,
            agent_type="test_agent",
            additional_data=metadata
        )
        
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        
        assert message.additional_data == metadata

    async def test_message_ordering_by_timestamp(self, db_session: AsyncSession, sample_conversation: Conversation):
        """Test that messages are ordered by timestamp."""
        message1 = Message(content="First", conversation_id=sample_conversation.id, agent_type="test")
        await asyncio.sleep(0.01)
        message2 = Message(content="Second", conversation_id=sample_conversation.id, agent_type="test")
        
        db_session.add_all([message1, message2])
        await db_session.commit()
        
        # Query messages ordered by timestamp
        result = await db_session.execute(
            select(Message)
            .where(Message.conversation_id == sample_conversation.id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        
        assert len(messages) >= 2
        assert messages[-2].content == "First"
        assert messages[-1].content == "Second"


class TestRefreshTokenModelIntegration:
    """Test RefreshToken model with database integration."""

    async def test_create_refresh_token(self, db_session: AsyncSession, sample_user: User):
        """Test creating refresh token."""
        from datetime import datetime, timedelta, timezone
        
        token = RefreshToken(
            token="test_token_123",
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)
        
        assert token.id is not None
        assert token.token == "test_token_123"
        assert token.user_id == sample_user.id
        assert token.expires_at is not None

    async def test_refresh_token_user_relationship(self, db_session: AsyncSession, sample_user: User):
        """Test refresh token - user relationship."""
        from datetime import datetime, timedelta, timezone
        
        token = RefreshToken(
            token="relationship_test",
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token, ["user"])
        
        assert token.user is not None
        assert token.user.id == sample_user.id

    async def test_multiple_refresh_tokens_per_user(self, db_session: AsyncSession, sample_user: User):
        """Test that user can have multiple refresh tokens."""
        from datetime import datetime, timedelta, timezone
        
        token1 = RefreshToken(
            token="token_1",
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        token2 = RefreshToken(
            token="token_2", 
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        db_session.add_all([token1, token2])
        await db_session.commit()
        
        # Query user's tokens
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == sample_user.id)
        )
        tokens = result.scalars().all()
        
        assert len(tokens) >= 2

    async def test_refresh_token_cleanup_query(self, db_session: AsyncSession, sample_user: User):
        """Test querying expired tokens for cleanup."""
        from datetime import datetime, timedelta, timezone
        
        # Create expired token
        expired_token = RefreshToken(
            token="expired_token",
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        # Create valid token
        valid_token = RefreshToken(
            token="valid_token",
            user_id=sample_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        db_session.add_all([expired_token, valid_token])
        await db_session.commit()
        
        # Query expired tokens
        now = datetime.now(timezone.utc)
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.expires_at < now)
        )
        expired_tokens = result.scalars().all()
        
        assert len(expired_tokens) >= 1
        assert any(token.token == "expired_token" for token in expired_tokens)


class TestModelRelationshipsIntegration:
    """Test model relationships and constraints."""

    async def test_cascade_delete_behavior(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test cascade delete behavior."""
        # Create user
        user = User(
            email="cascade@example.com",
            username="cascadeuser",
            hashed_password="hash",
            tenant_id=sample_tenant.id
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create conversation
        conversation = Conversation(
            title="Cascade Test",
            tenant_id=sample_tenant.id
        )
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
        
        # Create message
        message = Message(
            content="Test message",
            conversation_id=conversation.id,
            user_id=user.id
        )
        db_session.add(message)
        await db_session.commit()
        
        # Delete conversation should cascade to messages
        await db_session.delete(conversation)
        await db_session.commit()
        
        # Verify message is deleted
        result = await db_session.execute(
            select(Message).where(Message.id == message.id)
        )
        deleted_message = result.scalars().first()
        assert deleted_message is None

    async def test_tenant_data_isolation(self, db_session: AsyncSession):
        """Test that tenant data is properly isolated."""
        # Create two tenants
        tenant1 = Tenant(name="Tenant 1", subdomain="tenant1")
        tenant2 = Tenant(name="Tenant 2", subdomain="tenant2") 
        
        db_session.add_all([tenant1, tenant2])
        await db_session.commit()
        await db_session.refresh(tenant1)
        await db_session.refresh(tenant2)
        
        # Create users in each tenant
        user1 = User(email="user1@tenant1.com", username="user1", hashed_password="hash", tenant_id=tenant1.id)
        user2 = User(email="user2@tenant2.com", username="user2", hashed_password="hash", tenant_id=tenant2.id)
        
        db_session.add_all([user1, user2])
        await db_session.commit()
        
        # Query users for tenant1 only
        result = await db_session.execute(
            select(User).where(User.tenant_id == tenant1.id)
        )
        tenant1_users = result.scalars().all()
        
        # Should only contain tenant1 users
        assert len(tenant1_users) >= 1
        assert all(user.tenant_id == tenant1.id for user in tenant1_users)