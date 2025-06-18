"""
Unit tests for conversation API endpoint functions.
Tests the core logic of conversation API functions with proper mocking.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from uuid import uuid4, UUID
import json
from datetime import datetime

from app.models.models import (
    User, Conversation, Message, ConversationUser, ConversationAgent, Agent,
    ConversationParticipant, ConversationStatus, MessageType
)
from app.schemas.schemas import ConversationCreate, MessageCreate, ConversationResponse


@pytest.fixture
def mock_auth_and_db(authenticated_user, db_session):
    """Fixture that overrides FastAPI dependencies."""
    from app.main import app
    from app.auth.auth import get_current_active_user, get_tenant_from_request
    from app.db.database import get_db
    
    # Create a mock tenant
    mock_tenant = Mock()
    mock_tenant.id = authenticated_user["user"].tenant_id
    mock_tenant.subdomain = "test-org"
    mock_tenant.name = "Test Organization"
    
    # Override dependencies
    app.dependency_overrides[get_current_active_user] = lambda: authenticated_user["user"]
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_tenant_from_request] = lambda: mock_tenant
    
    yield
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_conversation_success(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test successful conversation creation."""
    conversation_data = {
        "title": "Test Conversation",
        "description": "A test conversation",
        "user_ids": [],
        "agent_types": [],  # Simplified - no agents to avoid complex mocking
        "participant_emails": []  # Simplified - no participants to avoid title generation
    }
    
    # Mock database operations for conversation creation
    added_objects = []
    def mock_add(obj):
        # Simulate setting ID on flush
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = uuid4()
        added_objects.append(obj)
    
    db_session.add = Mock(side_effect=mock_add)
    
    async def mock_flush():
        # Set IDs for all added objects
        for obj in added_objects:
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = uuid4()
    
    db_session.flush = AsyncMock(side_effect=mock_flush)
    db_session.commit = AsyncMock()
    db_session.refresh = AsyncMock()
    
    # Mock get_conversation_with_details
    with patch('app.api.conversations.get_conversation_with_details') as mock_get_details:
        mock_conversation_response = {
            "id": str(uuid4()),
            "tenant_id": str(authenticated_user["user"].tenant_id),
            "title": "Test Conversation",
            "description": "A test conversation",
            "status": ConversationStatus.ACTIVE,
            "created_by_user_id": str(authenticated_user["user"].id),
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "users": [],
            "agents": [],
            "participants": [],
            "recent_messages": [],
            "owner_id": str(authenticated_user["user"].id)
        }
        mock_get_details.return_value = mock_conversation_response
        
        response = await async_client.post(
            "/api/conversations/",
            json=conversation_data,
            headers=authenticated_user["headers"]
        )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_create_conversation_auto_title(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test conversation creation with auto-generated title."""
    conversation_data = {
        "participant_emails": ["john@example.com", "jane@example.com"]
    }
    
    # Mock database operations for conversation creation
    db_session.add = Mock()
    db_session.flush = AsyncMock()
    db_session.commit = AsyncMock()
    db_session.refresh = AsyncMock()
    
    # Mock get_conversation_with_details
    with patch('app.api.conversations.get_conversation_with_details') as mock_get_details:
        mock_conversation_response = {
            "id": str(uuid4()),
            "tenant_id": str(authenticated_user["user"].tenant_id),
            "title": f"{authenticated_user['user'].username or authenticated_user['user'].email} - john@example.com et al. - Dec 06, 2025 12:00 PM",
            "description": None,
            "status": ConversationStatus.ACTIVE,
            "created_by_user_id": str(authenticated_user["user"].id),
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "users": [],
            "agents": [],
            "participants": [],
            "recent_messages": [],
            "owner_id": str(authenticated_user["user"].id)
        }
        mock_get_details.return_value = mock_conversation_response
        
        response = await async_client.post(
            "/api/conversations/",
            json=conversation_data,
            headers=authenticated_user["headers"]
        )
    
    assert response.status_code == status.HTTP_200_OK
    

@pytest.mark.asyncio
async def test_list_conversations_empty(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test listing conversations when none exist."""
    # Mock empty conversation query
    mock_empty_result = Mock()
    mock_empty_scalars = Mock()
    mock_empty_scalars.all.return_value = []
    mock_empty_result.scalars.return_value = mock_empty_scalars
    
    mock_count_result = Mock()
    mock_count_result.scalar.return_value = 0
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Count query
            return mock_count_result
        else:  # Conversations query
            return mock_empty_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
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
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test listing conversations with existing data."""
    user = authenticated_user["user"]
    
    # Create test conversation with proper timestamps
    now = datetime.now()
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        description="Test description",
        created_by_user_id=user.id,
        status=ConversationStatus.ACTIVE,
        created_at=now,
        updated_at=now
    )
    
    # Add test message with proper timestamps
    message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        user_id=user.id,
        content="Test message",
        message_type=MessageType.TEXT,
        created_at=now,
        updated_at=now
    )
    # Don't set relationships directly - they will be handled in mocks
    
    # Mock the database queries
    mock_count_result = Mock()
    mock_count_result.scalar.return_value = 1
    
    mock_conversations_result = Mock()
    mock_conversations_scalars = Mock()
    mock_conversations_scalars.all.return_value = [conversation]
    mock_conversations_result.scalars.return_value = mock_conversations_scalars
    
    mock_last_msg_result = Mock()
    mock_last_msg_result.scalar_one_or_none = Mock(return_value=message)
    
    mock_participant_count = Mock()
    mock_participant_count.scalar.return_value = 1
    
    mock_message_count = Mock()
    mock_message_count.scalar.return_value = 1
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Total count
            return mock_count_result
        elif call_count[0] == 2:  # Conversations query
            return mock_conversations_result
        elif call_count[0] == 3:  # Last message
            return mock_last_msg_result
        elif call_count[0] == 4:  # Participant count
            return mock_participant_count
        else:  # Message count
            return mock_message_count
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
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
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test getting a specific conversation."""
    user = authenticated_user["user"]
    
    # Create test conversation with required fields
    now = datetime.now()
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id,
        status=ConversationStatus.ACTIVE,
        created_at=now,
        updated_at=now
    )
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    # Don't set relationships directly - they will be handled in mocks
    
    # Mock conversation query
    mock_conv_result = Mock()
    mock_conv_result.scalar_one_or_none = Mock(return_value=conversation)
    
    # Mock access check
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=conv_user)
    
    # Mock get_conversation_with_details
    conversation.users = [conv_user]
    conversation.agents = []
    conversation.participants = []
    
    mock_detailed_result = Mock()
    mock_detailed_result.scalar_one_or_none = Mock(return_value=conversation)
    
    mock_messages_result = Mock()
    mock_messages_scalars = Mock()
    mock_messages_scalars.all.return_value = []
    mock_messages_result.scalars.return_value = mock_messages_scalars
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Get conversation
            return mock_conv_result
        elif call_count[0] == 2:  # Access check
            return mock_access_result
        elif call_count[0] == 3:  # Detailed conversation
            return mock_detailed_result
        else:  # Messages
            return mock_messages_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    response = await async_client.get(
        f"/api/conversations/{conversation.id}",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(conversation.id)
    assert data["title"] == "Test Conversation"


@pytest.mark.asyncio
async def test_get_conversation_not_found(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test getting a non-existent conversation."""
    fake_id = uuid4()
    
    # Mock conversation not found
    mock_conv_result = Mock()
    mock_conv_result.scalar_one_or_none = Mock(return_value=None)
    
    db_session.execute = AsyncMock(return_value=mock_conv_result)
    
    response = await async_client.get(
        f"/api/conversations/{fake_id}",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_conversation_access_denied(
    async_client: AsyncClient,
    authenticated_user: dict,
    other_user: User,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test access denied when user not in conversation."""
    # Create conversation for other user
    conversation = Conversation(
        id=uuid4(),
        tenant_id=other_user.tenant_id,
        title="Other User's Conversation",
        created_by_user_id=other_user.id
    )
    
    # Mock conversation exists
    mock_conv_result = Mock()
    mock_conv_result.scalar_one_or_none = Mock(return_value=conversation)
    
    # Mock access denied (no access for current user)
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=None)
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Get conversation
            return mock_conv_result
        else:  # Access check
            return mock_access_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    response = await async_client.get(
        f"/api/conversations/{conversation.id}",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_send_message_success(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
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
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    
    # Mock access verification
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=conv_user)
    
    # Mock conversation query for timestamp update
    mock_conv_result = Mock()
    mock_conv_result.scalar_one = Mock(return_value=conversation)
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Access check
            return mock_access_result
        else:  # Conversation query
            return mock_conv_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    # Mock database operations with proper side effects
    def mock_add(obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = uuid4()
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.now()
        if hasattr(obj, 'updated_at') and obj.updated_at is None:
            obj.updated_at = datetime.now()
    
    db_session.add = Mock(side_effect=mock_add)
    db_session.commit = AsyncMock()
    
    async def mock_refresh(obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = uuid4()
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.now()
        if hasattr(obj, 'updated_at') and obj.updated_at is None:
            obj.updated_at = datetime.now()
    
    db_session.refresh = AsyncMock(side_effect=mock_refresh)
    
    # Mock the updated_at attribute access
    conversation.updated_at = None
    
    message_data = {
        "content": "Hello, world!",
        "message_type": MessageType.TEXT,
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
async def test_send_message_with_mention(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test sending a message with agent mention."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id
    )
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    
    # Mock access verification
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=conv_user)
    
    # Mock conversation query for timestamp update
    mock_conv_result = Mock()
    mock_conv_result.scalar_one = Mock(return_value=conversation)
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Access check
            return mock_access_result
        else:  # Conversation query
            return mock_conv_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    # Mock database operations with proper side effects
    def mock_add(obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = uuid4()
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.now()
        if hasattr(obj, 'updated_at') and obj.updated_at is None:
            obj.updated_at = datetime.now()
    
    db_session.add = Mock(side_effect=mock_add)
    db_session.commit = AsyncMock()
    
    async def mock_refresh(obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = uuid4()
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.now()
        if hasattr(obj, 'updated_at') and obj.updated_at is None:
            obj.updated_at = datetime.now()
    
    db_session.refresh = AsyncMock(side_effect=mock_refresh)
    
    # Mock the updated_at attribute access
    conversation.updated_at = None
    
    message_data = {
        "content": "Search for something",
        "message_type": MessageType.TEXT,
        "mention": "WEB_SEARCH"
    }
    
    response = await async_client.post(
        f"/api/conversations/{conversation.id}/messages",
        json=message_data,
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Should return web search agent response
    assert data["content"] == "Search results..."
    assert data["agent_type"] == "WEB_SEARCH"


@pytest.mark.asyncio
async def test_get_messages_empty(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test getting messages from conversation with no messages."""
    user = authenticated_user["user"]
    
    # Create test conversation
    conversation = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Test Conversation",
        created_by_user_id=user.id
    )
    
    # Add user to conversation
    conv_user = ConversationUser(
        conversation_id=conversation.id,
        user_id=user.id,
        is_active=True
    )
    
    # Mock access verification
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=conv_user)
    
    # Mock empty messages query
    mock_messages_result = Mock()
    mock_messages_scalars = Mock()
    mock_messages_scalars.all = Mock(return_value=[])
    mock_messages_result.scalars = Mock(return_value=mock_messages_scalars)
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Access check
            return mock_access_result
        else:  # Messages query
            return mock_messages_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    response = await async_client.get(
        f"/api/conversations/{conversation.id}/messages",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_delete_conversation_success(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test deleting a conversation."""
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
    
    # Mock the database queries properly
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=conv_user)
    
    mock_conversation_result = Mock()
    mock_conversation_result.scalar_one_or_none = Mock(return_value=conversation)
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Access check
            return mock_access_result
        else:  # Get conversation
            return mock_conversation_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    await db_session.commit()
    
    response = await async_client.delete(
        f"/api/conversations/{conversation.id}",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert "deleted successfully" in data["message"]


@pytest.mark.asyncio
async def test_add_agent_to_conversation(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test adding an agent to a conversation."""
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
    
    # Mock the database queries properly
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=conv_user)
    
    # Mock no existing agent
    mock_no_agent_result = Mock()
    mock_no_agent_result.scalar_one_or_none = Mock(return_value=None)
    
    # Mock agent record creation
    mock_agent_record_result = Mock()
    mock_agent_record_result.scalar_one_or_none = Mock(return_value=None)
    
    # Create a test agent with proper attributes
    test_agent = Agent(
        id=uuid4(),
        agent_type="WEB_SEARCH",
        name="Web Search Agent",
        description="Test web search agent",
        is_free_agent=True,
        capabilities=["web_search", "research"]
    )
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Access check
            return mock_access_result
        elif call_count[0] == 2:  # Get agent record
            return mock_no_agent_result
        else:  # Check existing conversation agent
            return mock_agent_record_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    # Mock db.add and db.flush for agent creation
    db_session.add = Mock()
    db_session.flush = AsyncMock()
    
    await db_session.commit()
    
    agent_data = {
        "agent_type": "WEB_SEARCH",
        "configuration": {"max_results": 10}
    }
    
    response = await async_client.post(
        f"/api/conversations/{conversation.id}/agents",
        json=agent_data,
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["agent_type"] == "WEB_SEARCH"
    assert data["configuration"]["max_results"] == 10


@pytest.mark.asyncio
async def test_get_conversation_agents(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test getting agents in a conversation."""
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
    
    # Add test agent first
    test_agent = Agent(
        id=uuid4(),
        agent_type="ASSISTANT",
        name="Assistant Agent",
        description="Test assistant agent",
        is_free_agent=True,
        capabilities=["assistance", "conversation"]
    )
    db_session.add(test_agent)
    
    # Add conversation agent relationship
    conv_agent = ConversationAgent(
        id=uuid4(),
        conversation_id=conversation.id,
        agent_id=test_agent.id,
        configuration=json.dumps({"temperature": 0.7}),
        is_active=True
    )
    # Set the agent relationship for the test
    conv_agent.agent = test_agent
    db_session.add(conv_agent)
    
    # Mock the database queries properly
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=conv_user)
    
    mock_agents_result = Mock()
    mock_agents_scalars = Mock()
    mock_agents_scalars.all.return_value = [conv_agent]
    mock_agents_result.scalars.return_value = mock_agents_scalars
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Access check
            return mock_access_result
        else:  # Get agents
            return mock_agents_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    await db_session.commit()
    
    response = await async_client.get(
        f"/api/conversations/{conversation.id}/agents",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["configuration"]["temperature"] == 0.7


@pytest.mark.asyncio
async def test_search_conversations(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test searching conversations by query."""
    user = authenticated_user["user"]
    
    # Create test conversations with required fields
    now = datetime.now()
    conv1 = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Project Meeting",
        description="Weekly project sync",
        created_by_user_id=user.id,
        status=ConversationStatus.ACTIVE,
        created_at=now,
        updated_at=now
    )
    db_session.add(conv1)
    
    conv2 = Conversation(
        id=uuid4(),
        tenant_id=user.tenant_id,
        title="Budget Discussion",
        description="Q4 budget planning",
        created_by_user_id=user.id,
        status=ConversationStatus.ACTIVE,
        created_at=now,
        updated_at=now
    )
    db_session.add(conv2)
    
    # Add user to both conversations
    for conv in [conv1, conv2]:
        conv_user = ConversationUser(
            conversation_id=conv.id,
            user_id=user.id,
            is_active=True
        )
        db_session.add(conv_user)
    
    # Mock the search query to return only conv1 (matching "project")
    mock_search_result = Mock()
    mock_search_scalars = Mock()
    mock_search_scalars.all.return_value = [conv1]
    mock_search_result.scalars.return_value = mock_search_scalars
    
    # Mock the count queries
    mock_count_result = Mock()
    mock_count_result.scalar.return_value = 1
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] == 1:  # Search query
            return mock_search_result
        elif call_count[0] == 2:  # Message count
            return mock_count_result
        else:  # Participant count
            return mock_count_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    await db_session.commit()
    
    # Search for "project" - note the endpoint is at the router level
    response = await async_client.get(
        "/api/conversations/search?q=project",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Project Meeting"


@pytest.mark.asyncio
async def test_clear_messages(
    async_client: AsyncClient,
    authenticated_user: dict,
    db_session: AsyncSession,
    mock_auth_and_db
):
    """Test clearing all messages in a conversation."""
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
    
    # Add test messages
    from datetime import datetime
    now = datetime.now()
    
    for i in range(3):
        message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            user_id=user.id,
            content=f"Message {i}",
            message_type=MessageType.TEXT,
            created_at=now,
            updated_at=now
        )
        db_session.add(message)
    
    # Mock the database queries properly
    mock_access_result = Mock()
    mock_access_result.scalar_one_or_none = Mock(return_value=conv_user)
    
    # Mock empty messages after clearing
    mock_empty_messages_result = Mock()
    mock_empty_scalars = Mock()
    mock_empty_scalars.all.return_value = []
    mock_empty_messages_result.scalars.return_value = mock_empty_scalars
    
    call_count = [0]
    async def mock_execute(query):
        call_count[0] += 1
        if call_count[0] <= 2:  # Access checks for both requests
            return mock_access_result
        else:  # Messages query after clearing
            return mock_empty_messages_result
    
    db_session.execute = AsyncMock(side_effect=mock_execute)
    
    await db_session.commit()
    
    # Clear messages
    response = await async_client.delete(
        f"/api/conversations/{conversation.id}/messages",
        headers=authenticated_user["headers"]
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    
    # Verify messages are cleared
    messages_response = await async_client.get(
        f"/api/conversations/{conversation.id}/messages",
        headers=authenticated_user["headers"]
    )
    assert len(messages_response.json()) == 0


@pytest.mark.asyncio
async def test_unauthorized_access(
    async_client: AsyncClient
):
    """Test that endpoints require authentication."""
    # Clear any dependency overrides to ensure we test actual auth
    from app.main import app
    app.dependency_overrides.clear()
    
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
        assert response.status_code == status.HTTP_403_FORBIDDEN