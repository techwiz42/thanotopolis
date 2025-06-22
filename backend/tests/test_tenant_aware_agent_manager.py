import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4, UUID

from app.agents.tenant_aware_agent_manager import TenantAwareAgentManager
from app.models.models import User, Tenant
from app.agents.base_agent import BaseAgent


class MockFreeAgent(BaseAgent):
    """Mock free agent available to all organizations."""
    OWNER_DOMAINS = []  # Empty list means free agent


class MockProprietaryAgent(BaseAgent):
    """Mock proprietary agent owned by 'demo' organization."""
    OWNER_DOMAINS = ["demo"]  # Only available to demo org


class MockProprietaryAgentAcme(BaseAgent):
    """Mock proprietary agent owned by 'acme' organization."""
    OWNER_DOMAINS = ["acme"]  # Only available to acme org


class MockMultiOrgAgent(BaseAgent):
    """Mock proprietary agent available to multiple organizations."""
    OWNER_DOMAINS = ["demo", "acme", "testorg"]  # Available to multiple orgs


class TestTenantAwareAgentManager:
    """Test suite for TenantAwareAgentManager."""

    @pytest.fixture
    def manager(self):
        """Create a TenantAwareAgentManager instance."""
        return TenantAwareAgentManager()

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "demo"
        db.execute.return_value = mock_result
        return db

    @pytest.fixture
    def demo_user(self):
        """Create a mock user from demo organization."""
        user = User()
        user.id = uuid4()
        user.email = "test@demo.com"
        user.tenant_id = uuid4()
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        return user

    @pytest.fixture
    def acme_user(self):
        """Create a mock user from acme organization."""
        user = User()
        user.id = uuid4()
        user.email = "test@acme.com"
        user.tenant_id = uuid4()
        user.username = "acmeuser"
        user.first_name = "Acme"
        user.last_name = "User"
        return user

    @pytest.mark.asyncio
    async def test_get_available_agents_for_user_free_agents_only(self, manager, mock_db, demo_user):
        """Test that free agents are available to all users."""
        # Mock available agents
        with patch.object(manager, 'get_available_agents', return_value=['free_agent_1', 'free_agent_2']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                # Mock free agent instances
                mock_free_agent_1 = MockFreeAgent()
                mock_free_agent_2 = MockFreeAgent()
                
                mock_get_agent.side_effect = lambda agent_type: {
                    'free_agent_1': mock_free_agent_1,
                    'free_agent_2': mock_free_agent_2
                }.get(agent_type)
                
                # Get available agents
                available = await manager.get_available_agents_for_user(demo_user, mock_db)
                
                # Should include all free agents
                assert 'free_agent_1' in available
                assert 'free_agent_2' in available
                assert len(available) == 2

    @pytest.mark.asyncio
    async def test_get_available_agents_for_user_proprietary_access_granted(self, manager, mock_db, demo_user):
        """Test that proprietary agents are available to users from owner organization."""
        # Mock available agents including proprietary ones
        with patch.object(manager, 'get_available_agents', return_value=['free_agent', 'demo_proprietary']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                # Mock agent instances
                mock_free_agent = MockFreeAgent()
                mock_proprietary_agent = MockProprietaryAgent()
                
                mock_get_agent.side_effect = lambda agent_type: {
                    'free_agent': mock_free_agent,
                    'demo_proprietary': mock_proprietary_agent
                }.get(agent_type)
                
                # Get available agents
                available = await manager.get_available_agents_for_user(demo_user, mock_db)
                
                # Should include both free and proprietary agents
                assert 'free_agent' in available
                assert 'demo_proprietary' in available
                assert len(available) == 2

    @pytest.mark.asyncio
    async def test_get_available_agents_for_user_proprietary_access_denied(self, manager, mock_db, acme_user):
        """Test that proprietary agents are not available to users from different organizations."""
        # Mock tenant query to return 'acme' for the user
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "acme"
        mock_db.execute.return_value = mock_result
        
        # Mock available agents including proprietary ones
        with patch.object(manager, 'get_available_agents', return_value=['free_agent', 'demo_proprietary']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                # Mock agent instances
                mock_free_agent = MockFreeAgent()
                mock_proprietary_agent = MockProprietaryAgent()  # Owned by 'demo'
                
                mock_get_agent.side_effect = lambda agent_type: {
                    'free_agent': mock_free_agent,
                    'demo_proprietary': mock_proprietary_agent
                }.get(agent_type)
                
                # Get available agents
                available = await manager.get_available_agents_for_user(acme_user, mock_db)
                
                # Should include only free agents
                assert 'free_agent' in available
                assert 'demo_proprietary' not in available
                assert len(available) == 1

    @pytest.mark.asyncio
    async def test_get_available_agents_for_user_multiple_proprietary_agents(self, manager, mock_db, demo_user):
        """Test filtering with multiple proprietary agents from different organizations."""
        # Mock available agents with multiple proprietary ones
        agent_types = ['free_agent', 'demo_proprietary', 'acme_proprietary']
        
        with patch.object(manager, 'get_available_agents', return_value=agent_types):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                # Mock agent instances
                mock_free_agent = MockFreeAgent()
                mock_demo_proprietary = MockProprietaryAgent()  # Owned by 'demo'
                mock_acme_proprietary = MockProprietaryAgentAcme()  # Owned by 'acme'
                
                mock_get_agent.side_effect = lambda agent_type: {
                    'free_agent': mock_free_agent,
                    'demo_proprietary': mock_demo_proprietary,
                    'acme_proprietary': mock_acme_proprietary
                }.get(agent_type)
                
                # Get available agents for demo user
                available = await manager.get_available_agents_for_user(demo_user, mock_db)
                
                # Should include free agent and demo proprietary, but not acme proprietary
                assert 'free_agent' in available
                assert 'demo_proprietary' in available
                assert 'acme_proprietary' not in available
                assert len(available) == 2

    @pytest.mark.asyncio
    async def test_get_available_agents_for_user_no_owner_domains(self, manager, mock_db, demo_user):
        """Test agents without OWNER_DOMAINS attribute default to free agents."""
        # Create mock agent with no OWNER_DOMAINS attribute
        class MockNoOwnerDomainsAgent(BaseAgent):
            # No OWNER_DOMAINS attribute - should default to []
            pass
        
        with patch.object(manager, 'get_available_agents', return_value=['no_owner_domains_agent']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                mock_agent = MockNoOwnerDomainsAgent()
                mock_get_agent.return_value = mock_agent
                
                # Get available agents
                available = await manager.get_available_agents_for_user(demo_user, mock_db)
                
                # Should include the agent (defaults to free agent)
                assert 'no_owner_domains_agent' in available
                assert len(available) == 1

    @pytest.mark.asyncio
    async def test_get_available_agents_for_user_agent_not_found(self, manager, mock_db, demo_user):
        """Test handling when agent instance cannot be retrieved."""
        with patch.object(manager, 'get_available_agents', return_value=['missing_agent']):
            with patch.object(manager, 'get_agent', return_value=None):
                # Get available agents
                available = await manager.get_available_agents_for_user(demo_user, mock_db)
                
                # Should not include missing agent
                assert 'missing_agent' not in available
                assert len(available) == 0

    @pytest.mark.asyncio
    async def test_get_available_agents_for_user_database_error(self, manager, demo_user):
        """Test fallback behavior when database query fails."""
        # Mock database session that raises an exception
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")
        
        # Mock available agents including a proprietary one to ensure DB query is attempted
        with patch.object(manager, 'get_available_agents', return_value=['free_agent', 'proprietary_agent']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                # Mock agent instances - need at least one proprietary agent to trigger DB query
                mock_free_agent = MockFreeAgent()
                mock_proprietary_agent = MockProprietaryAgent()  # This will trigger the DB query
                
                mock_get_agent.side_effect = lambda agent_type: {
                    'free_agent': mock_free_agent,
                    'proprietary_agent': mock_proprietary_agent
                }.get(agent_type)
                
                with patch.object(manager, '_get_free_agents_only_sync', return_value=['free_agent']) as mock_fallback:
                    # Get available agents
                    available = await manager.get_available_agents_for_user(demo_user, mock_db)
                    
                    # Should fall back to free agents only
                    mock_fallback.assert_called_once()
                    assert available == ['free_agent']

    def test_get_free_agents_only_sync(self, manager):
        """Test synchronous fallback method for getting free agents."""
        with patch.object(manager, 'get_available_agents', return_value=['free_agent', 'proprietary_agent']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                # Mock agent instances
                mock_free_agent = MockFreeAgent()
                mock_proprietary_agent = MockProprietaryAgent()
                
                mock_get_agent.side_effect = lambda agent_type: {
                    'free_agent': mock_free_agent,
                    'proprietary_agent': mock_proprietary_agent
                }.get(agent_type)
                
                # Get free agents only
                free_agents = manager._get_free_agents_only_sync()
                
                # Should include only free agents
                assert 'free_agent' in free_agents
                assert 'proprietary_agent' not in free_agents
                assert len(free_agents) == 1

    @pytest.mark.asyncio
    async def test_get_free_agents_only_async(self, manager):
        """Test async method for getting free agents."""
        with patch.object(manager, 'get_available_agents', return_value=['free_agent', 'proprietary_agent']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                # Mock agent instances
                mock_free_agent = MockFreeAgent()
                mock_proprietary_agent = MockProprietaryAgent()
                
                mock_get_agent.side_effect = lambda agent_type: {
                    'free_agent': mock_free_agent,
                    'proprietary_agent': mock_proprietary_agent
                }.get(agent_type)
                
                # Get free agents only
                free_agents = await manager._get_free_agents_only()
                
                # Should include only free agents
                assert 'free_agent' in free_agents
                assert 'proprietary_agent' not in free_agents
                assert len(free_agents) == 1

    @pytest.mark.asyncio
    async def test_process_conversation_with_tenant_context(self, manager, mock_db, demo_user):
        """Test conversation processing with tenant context."""
        # Mock available agents
        with patch.object(manager, 'get_available_agents_for_user', return_value=['free_agent']) as mock_get_available:
            with patch.object(manager, 'process_conversation', return_value=('free_agent', 'response')) as mock_process:
                # Mock discovered agents
                manager.discovered_agents = {
                    'free_agent': Mock(),
                    'proprietary_agent': Mock()
                }
                
                # Process conversation
                result = await manager.process_conversation_with_tenant_context(
                    message="test message",
                    user=demo_user,
                    db=mock_db,
                    thread_id="test-thread",
                    owner_id=uuid4()
                )
                
                # Verify filtering was applied
                mock_get_available.assert_called_once_with(demo_user, mock_db)
                mock_process.assert_called_once()
                
                # Check that discovered agents were filtered
                call_args = mock_process.call_args
                assert call_args[1]['message'] == "test message"
                assert call_args[1]['thread_id'] == "test-thread"
                
                # Verify result
                assert result == ('free_agent', 'response')

    @pytest.mark.asyncio
    async def test_process_conversation_with_tenant_context_restores_agents(self, manager, mock_db, demo_user):
        """Test that original discovered agents are restored after filtering."""
        # Set up original discovered agents
        original_agents = {
            'free_agent': Mock(),
            'proprietary_agent': Mock()
        }
        manager.discovered_agents = original_agents.copy()
        
        with patch.object(manager, 'get_available_agents_for_user', return_value=['free_agent']):
            with patch.object(manager, 'process_conversation', return_value=('free_agent', 'response')):
                # Process conversation
                await manager.process_conversation_with_tenant_context(
                    message="test message",
                    user=demo_user,
                    db=mock_db
                )
                
                # Verify original agents were restored
                assert manager.discovered_agents == original_agents

    @pytest.mark.asyncio
    async def test_process_conversation_with_tenant_context_exception_handling(self, manager, mock_db, demo_user):
        """Test that original agents are restored even if an exception occurs."""
        # Set up original discovered agents
        original_agents = {
            'free_agent': Mock(),
            'proprietary_agent': Mock()
        }
        manager.discovered_agents = original_agents.copy()
        
        with patch.object(manager, 'get_available_agents_for_user', return_value=['free_agent']):
            with patch.object(manager, 'process_conversation', side_effect=Exception("Test error")):
                # Process conversation (should raise exception)
                with pytest.raises(Exception, match="Test error"):
                    await manager.process_conversation_with_tenant_context(
                        message="test message",
                        user=demo_user,
                        db=mock_db
                    )
                
                # Verify original agents were restored despite exception
                assert manager.discovered_agents == original_agents

    @pytest.mark.asyncio
    async def test_edge_case_no_available_agents(self, manager, mock_db, demo_user):
        """Test behavior when no agents are available to user."""
        with patch.object(manager, 'get_available_agents', return_value=[]):
            # Get available agents
            available = await manager.get_available_agents_for_user(demo_user, mock_db)
            
            # Should return empty list
            assert available == []

    @pytest.mark.asyncio
    async def test_get_available_agents_for_user_multi_org_access(self, manager, mock_db, demo_user):
        """Test proprietary agents with multiple organization access."""
        # Mock available agents including multi-org agent
        with patch.object(manager, 'get_available_agents', return_value=['multi_org_agent', 'single_org_agent']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                # Mock agent instances
                mock_multi_org = MockMultiOrgAgent()  # Available to demo, acme, testorg
                mock_single_org = MockProprietaryAgentAcme()  # Only available to acme
                
                mock_get_agent.side_effect = lambda agent_type: {
                    'multi_org_agent': mock_multi_org,
                    'single_org_agent': mock_single_org
                }.get(agent_type)
                
                # Get available agents for demo user
                available = await manager.get_available_agents_for_user(demo_user, mock_db)
                
                # Should include multi-org agent but not single-org agent
                assert 'multi_org_agent' in available
                assert 'single_org_agent' not in available
                assert len(available) == 1

    @pytest.mark.asyncio
    async def test_edge_case_none_user_tenant_id(self, manager, mock_db):
        """Test behavior when user has no tenant_id."""
        user = User()
        user.id = uuid4()
        user.email = "test@example.com"
        user.tenant_id = None  # No tenant
        
        # Mock database to return None for tenant query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch.object(manager, 'get_available_agents', return_value=['proprietary_agent']):
            with patch.object(manager, 'get_agent') as mock_get_agent:
                mock_proprietary_agent = MockProprietaryAgent()
                mock_get_agent.return_value = mock_proprietary_agent
                
                # Get available agents
                available = await manager.get_available_agents_for_user(user, mock_db)
                
                # Should not include proprietary agents
                assert 'proprietary_agent' not in available
                assert len(available) == 0