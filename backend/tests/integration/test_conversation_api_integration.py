"""
Integration tests for conversation API endpoints.
Tests the actual HTTP endpoints for creating, managing, and interacting with conversations.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from uuid import uuid4
import json
from datetime import datetime, timezone

from app.models.models import (
    User, Conversation, Message, ConversationUser, ConversationAgent, 
    ConversationParticipant, ConversationStatus, MessageType
)
from app.schemas.schemas import ConversationCreate, MessageCreate


@pytest.mark.asyncio
async def test_create_conversation_success(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test successful conversation creation."""
    conversation_data = {
        "title": "Test Conversation",
        "description": "A test conversation",
        "user_ids": [],
        "agent_types": ["WEBSEARCH"],
        "participant_emails": ["test@example.com"]
    }
    
    response = await async_client.post(
        "/api/conversations/",
        json=conversation_data,
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["title"] == "Test Conversation"
    assert data["description"] == "A test conversation"
    assert data["status"] == "active"
    assert len(data["agents"]) == 1
    assert data["agents"][0]["agent_type"] == "WEBSEARCH"
    assert len(data["participants"]) == 1
    assert data["participants"][0]["identifier"] == "test@example.com"


@pytest.mark.asyncio
async def test_create_conversation_auto_title(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test conversation creation with auto-generated title."""
    conversation_data = {
        "participant_emails": ["john@example.com", "jane@example.com"]
    }
    
    response = await async_client.post(
        "/api/conversations/",
        json=conversation_data,
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Should auto-generate title with participant info
    assert "john@example.com" in data["title"] or "jane@example.com" in data["title"]
    assert "et al." in data["title"]


@pytest.mark.asyncio
async def test_list_conversations_empty(
    async_client: AsyncClient,
    authenticated_user: dict
):
    """Test listing conversations when none exist."""
    response = await async_client.get(
        "/api/conversations/",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_conversations_with_data(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test listing conversations with existing data."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        description="Test description",
        created_by_user_id=user.id,
        status="active"
    )
    db_session.add(conversation)
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    db_session.add(conv_user)
    
    # Add test message
    message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        user_id=user.id,
        content="Test message",
        message_type="text"
    )
    db_session.add(message)
    
    await db_session.commit()
    
    response = await async_client.get(
        "/api/conversations/",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Conversation"
    assert data[0]["message_count"] == 1
    assert data[0]["participant_count"] == 1


@pytest.mark.asyncio
async def test_get_conversation_success(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test getting a specific conversation."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id
    )
    db_session.add(conversation)
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    db_session.add(conv_user)
    
    await db_session.commit()
    
    response = await async_client.get(
        f"/api/conversations/{conversation.id}",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(conversation.id)
    assert data["title"] == "Test Conversation"
    assert len(data["users"]) == 1
    assert data["users"][0]["id"] == str(user.id)


@pytest.mark.asyncio
async def test_get_conversation_not_found(
    async_client: AsyncClient,
    authenticated_user: dict
):
    """Test getting a non-existent conversation."""
    fake_id = uuid4()
    
    response = await async_client.get(
        f"/api/conversations/{fake_id}",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_send_message_success(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test sending a message to a conversation."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id
    )
    db_session.add(conversation)
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    db_session.add(conv_user)
    
    await db_session.commit()
    
    message_data = {
        "content": "Hello, world!",
        "message_type": "text",
        "metadata": {"test": "value"}
    }
    
    response = await async_client.post(
        f"/api/conversations/{conversation.id}/messages",
        json=message_data,
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Should return agent response due to default agent processing
    assert data["content"] == "This is the agent response"
    assert data["sender_type"] == "agent"
    assert data["agent_type"] == "ASSISTANT"


@pytest.mark.asyncio
async def test_unauthorized_access(
    async_client: AsyncClient
):
    """Test that endpoints require authentication."""
    conversation_id = uuid4()
    
    # Test various endpoints without authentication
    endpoints = [
        ("GET", f"/api/conversations/"),
        ("POST", f"/api/conversations/"),
        ("GET", f"/api/conversations/{conversation_id}"),
        ("GET", f"/api/conversations/{conversation_id}/messages"),
        ("POST", f"/api/conversations/{conversation_id}/messages"),
        ("PATCH", f"/api/conversations/{conversation_id}"),
        ("DELETE", f"/api/conversations/{conversation_id}")
    ]
    
    for method, endpoint in endpoints:
        response = await async_client.request(method, endpoint)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.asyncio
async def test_get_messages_with_data(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test getting messages with existing data."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id,
        status="active"
    )
    db_session.add(conversation)
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    db_session.add(conv_user)
    
    # Add test messages
    now = datetime.now(timezone.utc)
    
    user_message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        user_id=user.id,
        content="User message",
        message_type="text",
        created_at=now,
        updated_at=now
    )
    db_session.add(user_message)
    
    agent_message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        agent_type="WEBSEARCH",
        content="Agent response",
        message_type="text",
        created_at=now,
        updated_at=now,
        additional_data=json.dumps({
            "agent_type": "WEBSEARCH",
            "message_type": "agent",
            "sender_type": "agent"
        })
    )
    db_session.add(agent_message)
    
    await db_session.commit()
    
    response = await async_client.get(
        f"/api/conversations/{conversation.id}/messages",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    
    # First message should be user message
    assert data[0]["content"] == "User message"
    assert data[0]["sender_type"] == "user"
    assert data[0]["user_id"] == str(user.id)
    
    # Second message should be agent message
    assert data[1]["content"] == "Agent response"
    assert data[1]["sender_type"] == "agent"
    assert data[1]["agent_type"] == "WEBSEARCH"


@pytest.mark.asyncio
async def test_update_conversation_success(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test updating conversation details."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Original Title",
        description="Original description",
        created_by_user_id=user.id,
        status="active"
    )
    db_session.add(conversation)
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    db_session.add(conv_user)
    
    await db_session.commit()
    
    update_data = {
        "title": "Updated Title",
        "description": "Updated description",
        "status": "closed"
    }
    
    response = await async_client.patch(
        f"/api/conversations/{conversation.id}",
        json=update_data,
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated description"
    assert data["status"] == "closed"


@pytest.mark.asyncio
async def test_export_conversation(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test exporting conversation history."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id,
        status="active"
    )
    db_session.add(conversation)
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    db_session.add(conv_user)
    
    # Add test message
    now = datetime.now(timezone.utc)
    
    message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        user_id=user.id,
        content="Test message",
        message_type="text",
        created_at=now,
        updated_at=now
    )
    db_session.add(message)
    
    await db_session.commit()
    
    response = await async_client.get(
        f"/api/conversations/{conversation.id}/export",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["thread_id"] == str(conversation.id)
    assert data["title"] == "Test Conversation"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "Test message"


@pytest.mark.asyncio
async def test_get_conversation_stats(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test getting conversation statistics."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id,
        status="active"
    )
    db_session.add(conversation)
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    db_session.add(conv_user)
    
    # Add test messages with different agent types
    now = datetime.now(timezone.utc)
    
    messages = [
        Message(
            id=uuid4(),
            conversation_id=conversation.id,
            user_id=user.id,
            content="User message",
            message_type="text",
            created_at=now,
            updated_at=now
        ),
        Message(
            id=uuid4(),
            conversation_id=conversation.id,
            agent_type="WEBSEARCH",
            content="Assistant response",
            message_type="text",
            created_at=now,
            updated_at=now
        ),
        Message(
            id=uuid4(),
            conversation_id=conversation.id,
            agent_type="WEB_SEARCH",
            content="Search results",
            message_type="text",
            created_at=now,
            updated_at=now
        )
    ]
    
    for message in messages:
        db_session.add(message)
    
    await db_session.commit()
    
    response = await async_client.get(
        f"/api/conversations/{conversation.id}/stats",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message_count"] == 3
    assert data["status"] == "active"
    assert data["title"] == "Test Conversation"
    assert set(data["agents_used"]) == {"WEBSEARCH", "WEB_SEARCH"}


@pytest.mark.asyncio
async def test_message_pagination(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession
):
    """Test message pagination with skip and limit."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id,
        status="active"
    )
    db_session.add(conversation)
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    db_session.add(conv_user)
    
    # Add multiple test messages
    now = datetime.now(timezone.utc)
    
    messages = []
    for i in range(10):
        message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            user_id=user.id,
            content=f"Message {i}",
            message_type="text",
            created_at=now,
            updated_at=now
        )
        messages.append(message)
        db_session.add(message)
    
    await db_session.commit()
    
    # Test pagination
    response = await async_client.get(
        f"/api/conversations/{conversation.id}/messages?skip=2&limit=3",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 3
    assert data[0]["content"] == "Message 2"  # Should start from message 2 (0-indexed)
    assert data[2]["content"] == "Message 4"  # Should end at message 4