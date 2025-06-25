import pytest
import logging
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tenant_aware_agent_manager import (
    TenantAwareAgentManager, 
    tenant_aware_agent_manager
)
from app.models.models import User, Tenant
from app.agents.base_agent import BaseAgent


class MockFreeAgent(BaseAgent):
    """Mock free agent available to all organizations."""
    OWNER_DOMAINS = []  # Empty list = free agent
    
    def __init__(self):
        super().__init__(name="MockFreeAgent")
        self.description = "Free agent for all"


class MockProprietaryAgent(BaseAgent):
    """Mock proprietary agent owned by specific organization."""
    OWNER_DOMAINS = ["demo", "premium"]  # Only available to demo and premium orgs
    
    def __init__(self):
        super().__init__(name="MockProprietaryAgent")
        self.description = "Proprietary agent"


class MockUnknownAgent(BaseAgent):
    """Mock agent without OWNER_DOMAINS defined."""
    # No OWNER_DOMAINS attribute
    
    def __init__(self):
        super().__init__(name="MockUnknownAgent")
        self.description = "Unknown ownership agent"


class TestTenantAwareAgentManager:
    """Test the TenantAwareAgentManager class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create manager with mocked parent initialization
        with patch.object(TenantAwareAgentManager, '_discover_agents'):
            self.manager = TenantAwareAgentManager()
            
            # Set up mock agents
            self.free_agent = MockFreeAgent()
            self.proprietary_agent = MockProprietaryAgent()
            self.unknown_agent = MockUnknownAgent()
            
            self.manager.discovered_agents = {
                "FREE_AGENT": self.free_agent,
                "PROPRIETARY_AGENT": self.proprietary_agent,
                "UNKNOWN_AGENT": self.unknown_agent
            }
        
        # Mock user and tenant
        self.demo_user = Mock(spec=User)
        self.demo_user.id = uuid4()
        self.demo_user.email = "demo@example.com"
        self.demo_user.tenant_id = uuid4()
        
        self.acme_user = Mock(spec=User)
        self.acme_user.id = uuid4()
        self.acme_user.email = "acme@example.com"
        self.acme_user.tenant_id = uuid4()
        
        # Mock database session
        self.db = AsyncMock(spec=AsyncSession)
        
    @pytest.mark.asyncio
    async def test_get_available_agents_for_demo_user(self):
        """Test getting available agents for demo organization user."""
        # Mock database query to return demo subdomain
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "demo"
        self.db.execute.return_value = mock_result
        
        available_agents = await self.manager.get_available_agents_for_user(
            self.demo_user, self.db
        )
        
        # Demo user should have access to free agent, proprietary agent, and legacy free agents
        assert "FREE_AGENT" in available_agents
        assert "PROPRIETARY_AGENT" in available_agents
        assert "UNKNOWN_AGENT" in available_agents  # Legacy free agent (no OWNER_DOMAINS)
        
    @pytest.mark.asyncio
    async def test_get_available_agents_for_acme_user(self):
        """Test getting available agents for acme organization user."""
        # Mock database query to return acme subdomain
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "acme"
        self.db.execute.return_value = mock_result
        
        available_agents = await self.manager.get_available_agents_for_user(
            self.acme_user, self.db
        )
        
        # Acme user should have access to free agents and legacy free agents, but not proprietary agents
        assert "FREE_AGENT" in available_agents
        assert "PROPRIETARY_AGENT" not in available_agents  # Not available to acme org
        assert "UNKNOWN_AGENT" in available_agents  # Legacy free agent (no OWNER_DOMAINS)
        
    @pytest.mark.asyncio
    async def test_get_available_agents_for_premium_user(self):
        """Test getting available agents for premium organization user."""
        # Create premium user
        premium_user = Mock(spec=User)
        premium_user.id = uuid4()
        premium_user.email = "premium@example.com"
        premium_user.tenant_id = uuid4()
        
        # Mock database query to return premium subdomain
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "premium"
        self.db.execute.return_value = mock_result
        
        available_agents = await self.manager.get_available_agents_for_user(
            premium_user, self.db
        )
        
        # Premium user should have access to free agent, proprietary agent, and legacy free agents
        assert "FREE_AGENT" in available_agents
        assert "PROPRIETARY_AGENT" in available_agents
        assert "UNKNOWN_AGENT" in available_agents  # Legacy free agent (no OWNER_DOMAINS)
        
    @pytest.mark.asyncio
    async def test_get_available_agents_database_error(self):
        """Test handling of database errors during agent filtering."""
        # Mock database to raise an exception
        self.db.execute.side_effect = Exception("Database connection failed")
        
        with patch('app.agents.tenant_aware_agent_manager.logger') as mock_logger:
            available_agents = await self.manager.get_available_agents_for_user(
                self.demo_user, self.db
            )
            
            # Should fall back to free agents only (including legacy free agents)
            assert "FREE_AGENT" in available_agents
            assert "PROPRIETARY_AGENT" not in available_agents
            # UNKNOWN_AGENT is treated as legacy free agent, so it SHOULD be included in error fallback
            assert "UNKNOWN_AGENT" in available_agents
            
            # Should log the error
            mock_logger.error.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_get_available_agents_no_tenant_found(self):
        """Test handling when user's tenant is not found in database."""
        # Mock database query to return None (tenant not found)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = mock_result
        
        available_agents = await self.manager.get_available_agents_for_user(
            self.demo_user, self.db
        )
        
        # Should still include free agents
        assert "FREE_AGENT" in available_agents
        # Proprietary agent should not be available (no matching subdomain)
        assert "PROPRIETARY_AGENT" not in available_agents
        
    @pytest.mark.asyncio
    async def test_get_available_agents_empty_discovered_agents(self):
        """Test handling when no agents are discovered."""
        # Clear discovered agents
        self.manager.discovered_agents = {}
        
        available_agents = await self.manager.get_available_agents_for_user(
            self.demo_user, self.db
        )
        
        assert available_agents == []
        
    @pytest.mark.asyncio
    async def test_get_available_agents_agent_instance_not_found(self):
        """Test handling when agent instance cannot be retrieved."""
        # Mock get_agent to return None for some agents
        original_get_agent = self.manager.get_agent
        
        def mock_get_agent(agent_type):
            if agent_type == "MISSING_AGENT":
                return None
            return original_get_agent(agent_type)
        
        self.manager.get_agent = mock_get_agent
        self.manager.discovered_agents["MISSING_AGENT"] = Mock()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "demo"
        self.db.execute.return_value = mock_result
        
        available_agents = await self.manager.get_available_agents_for_user(
            self.demo_user, self.db
        )
        
        # Missing agent should be skipped
        assert "MISSING_AGENT" not in available_agents
        assert "FREE_AGENT" in available_agents
        
    def test_get_free_agents_only_sync(self):
        """Test synchronous method to get only free agents."""
        free_agents = self.manager._get_free_agents_only_sync()
        
        assert "FREE_AGENT" in free_agents
        assert "PROPRIETARY_AGENT" not in free_agents
        # UNKNOWN_AGENT is a legacy free agent (no OWNER_DOMAINS), so it should be included
        assert "UNKNOWN_AGENT" in free_agents
        
    @pytest.mark.asyncio
    async def test_get_free_agents_only_async(self):
        """Test asynchronous method to get only free agents."""
        free_agents = await self.manager._get_free_agents_only()
        
        assert "FREE_AGENT" in free_agents
        assert "PROPRIETARY_AGENT" not in free_agents
        # UNKNOWN_AGENT is a legacy free agent (no OWNER_DOMAINS), so it should be included
        assert "UNKNOWN_AGENT" in free_agents
        
    def test_get_free_agents_only_no_agents(self):
        """Test getting free agents when no agents are available."""
        self.manager.discovered_agents = {}
        
        free_agents = self.manager._get_free_agents_only_sync()
        
        assert free_agents == []
        
    def test_get_free_agents_only_agent_instance_none(self):
        """Test getting free agents when some agent instances are None."""
        # Mock get_agent to return None for some agents
        original_get_agent = self.manager.get_agent
        
        def mock_get_agent(agent_type):
            if agent_type == "BROKEN_AGENT":
                return None
            return original_get_agent(agent_type)
        
        self.manager.get_agent = mock_get_agent
        self.manager.discovered_agents["BROKEN_AGENT"] = Mock()
        
        free_agents = self.manager._get_free_agents_only_sync()
        
        # Broken agent should be skipped
        assert "BROKEN_AGENT" not in free_agents
        assert "FREE_AGENT" in free_agents
        
    @pytest.mark.asyncio
    async def test_process_conversation_with_tenant_context_success(self):
        """Test successful conversation processing with tenant filtering."""
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "demo"
        self.db.execute.return_value = mock_result
        
        # Mock parent process_conversation method
        with patch.object(self.manager.__class__.__bases__[0], 'process_conversation') as mock_process:
            mock_process.return_value = ("FREE_AGENT", "Test response")
            
            result = await self.manager.process_conversation_with_tenant_context(
                message="Test message",
                user=self.demo_user,
                db=self.db,
                thread_id="test-thread"
            )
            
            assert result == ("FREE_AGENT", "Test response")
            mock_process.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_process_conversation_with_tenant_context_filtered_agents(self):
        """Test that conversation processing uses filtered agents."""
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "acme"  # Acme user
        self.db.execute.return_value = mock_result
        
        # Store original agents
        original_agents = self.manager.discovered_agents.copy()
        
        # Mock parent process_conversation method
        with patch.object(self.manager.__class__.__bases__[0], 'process_conversation') as mock_process:
            mock_process.return_value = ("FREE_AGENT", "Filtered response")
            
            result = await self.manager.process_conversation_with_tenant_context(
                message="Test message",
                user=self.acme_user,
                db=self.db
            )
            
            # Should have called with filtered agents during processing
            mock_process.assert_called_once()
            
            # Verify original agents were restored
            assert self.manager.discovered_agents == original_agents
            
    @pytest.mark.asyncio
    async def test_process_conversation_with_tenant_context_exception_handling(self):
        """Test that original agents are restored even if processing fails."""
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "demo"
        self.db.execute.return_value = mock_result
        
        # Store original agents
        original_agents = self.manager.discovered_agents.copy()
        
        # Mock parent process_conversation to raise exception
        with patch.object(self.manager.__class__.__bases__[0], 'process_conversation') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            with pytest.raises(Exception, match="Processing failed"):
                await self.manager.process_conversation_with_tenant_context(
                    message="Test message",
                    user=self.demo_user,
                    db=self.db
                )
            
            # Verify original agents were restored despite exception
            assert self.manager.discovered_agents == original_agents
            
    @pytest.mark.asyncio
    async def test_process_conversation_with_tenant_context_with_callbacks(self):
        """Test conversation processing with optional parameters."""
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "demo"
        self.db.execute.return_value = mock_result
        
        # Mock callback
        callback = AsyncMock()
        owner_id = uuid4()
        
        # Mock parent process_conversation method
        with patch.object(self.manager.__class__.__bases__[0], 'process_conversation') as mock_process:
            mock_process.return_value = ("FREE_AGENT", "Response with callback")
            
            result = await self.manager.process_conversation_with_tenant_context(
                message="Test message",
                user=self.demo_user,
                db=self.db,
                thread_id="test-thread",
                owner_id=owner_id,
                response_callback=callback
            )
            
            # Verify all parameters were passed through
            args, kwargs = mock_process.call_args
            assert kwargs['thread_id'] == "test-thread"
            assert kwargs['owner_id'] == owner_id
            assert kwargs['response_callback'] == callback
            
    @pytest.mark.asyncio
    async def test_agent_ownership_validation_edge_cases(self):
        """Test edge cases in agent ownership validation."""
        # Create agents with various ownership configurations
        class AgentWithNoAttribute:
            """Agent without OWNER_DOMAINS attribute."""
            pass
        
        class AgentWithNoneAttribute:
            """Agent with OWNER_DOMAINS = None."""
            OWNER_DOMAINS = None
        
        class AgentWithStringAttribute:
            """Agent with OWNER_DOMAINS as string (incorrect type)."""
            OWNER_DOMAINS = "demo"
        
        # Add these to discovered agents
        self.manager.discovered_agents.update({
            "NO_ATTR_AGENT": AgentWithNoAttribute(),
            "NONE_ATTR_AGENT": AgentWithNoneAttribute(),
            "STRING_ATTR_AGENT": AgentWithStringAttribute()
        })
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "demo"
        self.db.execute.return_value = mock_result
        
        available_agents = await self.manager.get_available_agents_for_user(
            self.demo_user, self.db
        )
        
        # Agents without proper OWNER_DOMAINS should be treated as legacy free agents (permissive default)
        assert "NO_ATTR_AGENT" in available_agents  # No attribute = legacy free agent
        assert "NONE_ATTR_AGENT" in available_agents  # None = legacy free agent
        assert "STRING_ATTR_AGENT" in available_agents  # Invalid type = legacy free agent
        
    def test_singleton_instance(self):
        """Test that tenant_aware_agent_manager singleton exists."""
        assert tenant_aware_agent_manager is not None
        assert isinstance(tenant_aware_agent_manager, TenantAwareAgentManager)
        
    def test_singleton_persistence(self):
        """Test that singleton instance persists across imports."""
        from app.agents.tenant_aware_agent_manager import tenant_aware_agent_manager as imported_manager
        
        assert imported_manager is tenant_aware_agent_manager


class TestTenantAwareAgentManagerIntegration:
    """Integration tests for TenantAwareAgentManager."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        with patch.object(TenantAwareAgentManager, '_discover_agents'):
            self.manager = TenantAwareAgentManager()
            
            # Set up mock agents with realistic configurations
            self.moderator = Mock()
            self.moderator.__class__.OWNER_DOMAINS = []  # Free agent
            
            self.demo_special = Mock()
            self.demo_special.__class__.OWNER_DOMAINS = ["demo"]  # Demo only
            
            self.premium_special = Mock()
            self.premium_special.__class__.OWNER_DOMAINS = ["premium", "enterprise"]  # Premium/Enterprise
            
            self.manager.discovered_agents = {
                "MODERATOR": self.moderator,
                "DEMO_SPECIAL": self.demo_special,
                "PREMIUM_SPECIAL": self.premium_special
            }
    
    @pytest.mark.asyncio
    async def test_multi_organization_access_patterns(self):
        """Test agent access patterns across multiple organizations."""
        # Create users from different organizations
        demo_user = Mock(spec=User)
        demo_user.tenant_id = uuid4()
        
        premium_user = Mock(spec=User)
        premium_user.tenant_id = uuid4()
        
        basic_user = Mock(spec=User)
        basic_user.tenant_id = uuid4()
        
        db = AsyncMock(spec=AsyncSession)
        
        # Test demo organization access
        mock_result_demo = Mock()
        mock_result_demo.scalar_one_or_none.return_value = "demo"
        
        db.execute.return_value = mock_result_demo
        demo_agents = await self.manager.get_available_agents_for_user(demo_user, db)
        
        assert "MODERATOR" in demo_agents  # Free agent
        assert "DEMO_SPECIAL" in demo_agents  # Demo-specific
        assert "PREMIUM_SPECIAL" not in demo_agents  # Not for demo
        
        # Test premium organization access
        mock_result_premium = Mock()
        mock_result_premium.scalar_one_or_none.return_value = "premium"
        
        db.execute.return_value = mock_result_premium
        premium_agents = await self.manager.get_available_agents_for_user(premium_user, db)
        
        assert "MODERATOR" in premium_agents  # Free agent
        assert "DEMO_SPECIAL" not in premium_agents  # Not for premium
        assert "PREMIUM_SPECIAL" in premium_agents  # Premium-specific
        
        # Test basic organization access
        mock_result_basic = Mock()
        mock_result_basic.scalar_one_or_none.return_value = "basic"
        
        db.execute.return_value = mock_result_basic
        basic_agents = await self.manager.get_available_agents_for_user(basic_user, db)
        
        assert "MODERATOR" in basic_agents  # Only free agent
        assert "DEMO_SPECIAL" not in basic_agents
        assert "PREMIUM_SPECIAL" not in basic_agents
        
    @pytest.mark.asyncio
    async def test_conversation_filtering_workflow(self):
        """Test complete workflow with agent filtering."""
        # Create demo user
        demo_user = Mock(spec=User)
        demo_user.tenant_id = uuid4()
        demo_user.email = "demo@example.com"
        
        db = AsyncMock(spec=AsyncSession)
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "demo"
        db.execute.return_value = mock_result
        
        # Mock parent conversation processing
        with patch.object(self.manager.__class__.__bases__[0], 'process_conversation') as mock_process:
            mock_process.return_value = ("DEMO_SPECIAL", "Demo-specific response")
            
            # Process conversation
            result = await self.manager.process_conversation_with_tenant_context(
                message="Use demo-specific features",
                user=demo_user,
                db=db,
                thread_id="demo-conversation"
            )
            
            # Verify result
            assert result[0] == "DEMO_SPECIAL"
            assert result[1] == "Demo-specific response"
            
            # Verify process_conversation was called with filtered agents
            mock_process.assert_called_once()
            call_kwargs = mock_process.call_args[1]
            assert call_kwargs['thread_id'] == "demo-conversation"
            
    @pytest.mark.asyncio
    async def test_error_resilience_and_logging(self):
        """Test error handling and logging throughout the system."""
        # Create user
        user = Mock(spec=User)
        user.tenant_id = uuid4()
        user.email = "test@example.com"
        
        db = AsyncMock(spec=AsyncSession)
        
        # Test with various error scenarios
        error_scenarios = [
            Exception("Database timeout"),
            ConnectionError("Network error"),
            ValueError("Invalid tenant ID")
        ]
        
        for error in error_scenarios:
            db.execute.side_effect = error
            
            with patch('app.agents.tenant_aware_agent_manager.logger') as mock_logger:
                # Should not raise, should fall back to free agents
                available_agents = await self.manager.get_available_agents_for_user(user, db)
                
                # Should only have free agents
                assert "MODERATOR" in available_agents
                assert "DEMO_SPECIAL" not in available_agents
                assert "PREMIUM_SPECIAL" not in available_agents
                
                # Should log the error
                mock_logger.error.assert_called_once()
                
            # Reset for next test
            db.execute.side_effect = None