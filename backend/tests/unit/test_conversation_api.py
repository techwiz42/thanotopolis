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