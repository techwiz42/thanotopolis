import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4, UUID

from app.agents.enhanced_agent_manager import EnhancedAgentManager
from app.models.models import Agent


class TestEnhancedAgentManager:
    """Test suite for EnhancedAgentManager."""

    @pytest.fixture
    def manager(self):
        """Create an EnhancedAgentManager instance."""
        return EnhancedAgentManager()

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def sample_agents(self):
        """Sample discovered agents."""
        return ['agent_1', 'agent_2', 'agent_3']

    @pytest.fixture
    def sample_agent_descriptions(self):
        """Sample agent descriptions."""
        return {
            'agent_1': 'First test agent',
            'agent_2': 'Second test agent',
            'agent_3': 'Third test agent'
        }

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager._db_synced is False
        assert hasattr(manager, 'get_available_agents')
        assert hasattr(manager, 'get_agent_descriptions')

    @pytest.mark.asyncio
    async def test_ensure_agents_synced_to_db_first_time(self, manager, mock_db, sample_agents, sample_agent_descriptions):
        """Test initial database synchronization with no existing agents."""
        # Mock discovered agents
        with patch.object(manager, 'get_available_agents', return_value=sample_agents):
            with patch.object(manager, 'get_agent_descriptions', return_value=sample_agent_descriptions):
                # Mock database query returning no existing agents
                mock_result = Mock()
                mock_result.fetchall.return_value = []
                mock_db.execute.return_value = mock_result
                
                # Run sync
                result = await manager.ensure_agents_synced_to_db(mock_db)
                
                # Verify success
                assert result is True
                assert manager._db_synced is True
                
                # Verify database operations
                assert mock_db.add.call_count == 3  # Should add all 3 agents
                mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_agents_synced_to_db_partial_existing(self, manager, mock_db, sample_agents, sample_agent_descriptions):
        """Test synchronization when some agents already exist in database."""
        # Mock discovered agents
        with patch.object(manager, 'get_available_agents', return_value=sample_agents):
            with patch.object(manager, 'get_agent_descriptions', return_value=sample_agent_descriptions):
                # Mock database query returning one existing agent
                mock_result = Mock()
                mock_result.fetchall.return_value = [('agent_1',)]  # agent_1 already exists
                mock_db.execute.return_value = mock_result
                
                # Run sync
                result = await manager.ensure_agents_synced_to_db(mock_db)
                
                # Verify success
                assert result is True
                assert manager._db_synced is True
                
                # Verify only 2 new agents were added (agent_2 and agent_3)
                assert mock_db.add.call_count == 2
                mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_agents_synced_to_db_all_existing(self, manager, mock_db, sample_agents, sample_agent_descriptions):
        """Test synchronization when all agents already exist."""
        # Mock discovered agents
        with patch.object(manager, 'get_available_agents', return_value=sample_agents):
            with patch.object(manager, 'get_agent_descriptions', return_value=sample_agent_descriptions):
                # Mock database query returning all existing agents
                mock_result = Mock()
                mock_result.fetchall.return_value = [('agent_1',), ('agent_2',), ('agent_3',)]
                mock_db.execute.return_value = mock_result
                
                # Run sync
                result = await manager.ensure_agents_synced_to_db(mock_db)
                
                # Verify success
                assert result is True
                assert manager._db_synced is True
                
                # Verify no agents were added
                mock_db.add.assert_not_called()
                mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_agents_synced_to_db_already_synced(self, manager, mock_db):
        """Test that sync is skipped when already synced."""
        # Set as already synced
        manager._db_synced = True
        
        # Run sync
        result = await manager.ensure_agents_synced_to_db(mock_db)
        
        # Verify early return
        assert result is True
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_agents_synced_to_db_database_error(self, manager, mock_db, sample_agents):
        """Test error handling during database synchronization."""
        # Mock discovered agents
        with patch.object(manager, 'get_available_agents', return_value=sample_agents):
            # Mock database error
            mock_db.execute.side_effect = Exception("Database connection failed")
            
            # Run sync
            result = await manager.ensure_agents_synced_to_db(mock_db)
            
            # Verify failure
            assert result is False
            assert manager._db_synced is False
            mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_agents_synced_to_db_commit_error(self, manager, mock_db, sample_agents, sample_agent_descriptions):
        """Test error handling when commit fails."""
        # Mock discovered agents
        with patch.object(manager, 'get_available_agents', return_value=sample_agents):
            with patch.object(manager, 'get_agent_descriptions', return_value=sample_agent_descriptions):
                # Mock database query returning no existing agents
                mock_result = Mock()
                mock_result.fetchall.return_value = []
                mock_db.execute.return_value = mock_result
                
                # Mock commit error
                mock_db.commit.side_effect = Exception("Commit failed")
                
                # Run sync
                result = await manager.ensure_agents_synced_to_db(mock_db)
                
                # Verify failure
                assert result is False
                assert manager._db_synced is False
                mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_agent_record_existing_agent(self, manager, mock_db):
        """Test getting an existing agent record."""
        agent_type = "test_agent"
        existing_agent = Agent(
            id=uuid4(),
            agent_type=agent_type,
            name="Test Agent",
            description="Test description"
        )
        
        # Mock sync
        with patch.object(manager, 'ensure_agents_synced_to_db', return_value=True):
            # Mock database query returning existing agent
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = existing_agent
            mock_db.execute.return_value = mock_result
            
            # Get agent record
            result = await manager.get_or_create_agent_record(agent_type, mock_db)
            
            # Verify existing agent returned
            assert result == existing_agent
            mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_agent_record_create_new(self, manager, mock_db):
        """Test creating a new agent record."""
        agent_type = "new_agent"
        
        # Mock sync
        with patch.object(manager, 'ensure_agents_synced_to_db', return_value=True):
            # Mock available agents
            with patch.object(manager, 'get_available_agents', return_value=[agent_type]):
                # Mock agent descriptions
                manager.agent_descriptions = {agent_type: "New agent description"}
                
                # Mock database query returning no existing agent
                mock_result = Mock()
                mock_result.scalar_one_or_none.return_value = None
                mock_db.execute.return_value = mock_result
                
                # Get/create agent record
                result = await manager.get_or_create_agent_record(agent_type, mock_db)
                
                # Verify new agent was created
                assert result is not None
                mock_db.add.assert_called_once()
                mock_db.flush.assert_called_once()
                
                # Verify agent properties
                added_agent = mock_db.add.call_args[0][0]
                assert added_agent.agent_type == agent_type
                assert added_agent.name == "New Agent"
                assert added_agent.description == "New agent description"
                assert added_agent.is_free_agent is True
                assert added_agent.owner_tenant_id is None

    @pytest.mark.asyncio
    async def test_get_or_create_agent_record_unknown_agent(self, manager, mock_db):
        """Test handling of unknown agent type."""
        agent_type = "unknown_agent"
        
        # Mock sync
        with patch.object(manager, 'ensure_agents_synced_to_db', return_value=True):
            # Mock available agents (doesn't include unknown_agent)
            with patch.object(manager, 'get_available_agents', return_value=['known_agent']):
                # Mock database query returning no existing agent
                mock_result = Mock()
                mock_result.scalar_one_or_none.return_value = None
                mock_db.execute.return_value = mock_result
                
                # Get/create agent record
                result = await manager.get_or_create_agent_record(agent_type, mock_db)
                
                # Verify None returned for unknown agent
                assert result is None
                mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_agent_record_sync_failed(self, manager, mock_db):
        """Test handling when sync fails."""
        agent_type = "test_agent"
        
        # Mock sync failure
        with patch.object(manager, 'ensure_agents_synced_to_db', return_value=False):
            # Get/create agent record
            result = await manager.get_or_create_agent_record(agent_type, mock_db)
            
            # Verify None returned when sync fails
            assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_agent_record_database_error(self, manager, mock_db):
        """Test error handling during agent record operations."""
        agent_type = "test_agent"
        
        # Mock sync
        with patch.object(manager, 'ensure_agents_synced_to_db', return_value=True):
            # Mock database error
            mock_db.execute.side_effect = Exception("Database error")
            
            # Get/create agent record
            result = await manager.get_or_create_agent_record(agent_type, mock_db)
            
            # Verify None returned on error
            assert result is None

    @pytest.mark.asyncio
    async def test_agent_record_creation_details(self, manager, mock_db):
        """Test detailed agent record creation with all properties."""
        agent_type = "detailed_agent"
        description = "Detailed agent for testing"
        
        # Mock sync
        with patch.object(manager, 'ensure_agents_synced_to_db', return_value=True):
            # Mock available agents
            with patch.object(manager, 'get_available_agents', return_value=[agent_type]):
                # Mock agent descriptions
                manager.agent_descriptions = {agent_type: description}
                
                # Mock database query returning no existing agent
                mock_result = Mock()
                mock_result.scalar_one_or_none.return_value = None
                mock_db.execute.return_value = mock_result
                
                # Get/create agent record
                result = await manager.get_or_create_agent_record(agent_type, mock_db)
                
                # Verify agent was created with correct properties
                mock_db.add.assert_called_once()
                added_agent = mock_db.add.call_args[0][0]
                
                assert isinstance(added_agent, Agent)
                assert added_agent.agent_type == agent_type
                assert added_agent.name == "Detailed Agent"
                assert added_agent.description == description
                assert added_agent.is_free_agent is True
                assert added_agent.owner_tenant_id is None
                assert added_agent.capabilities == []
                assert added_agent.is_active is True

    @pytest.mark.asyncio
    async def test_sync_with_missing_descriptions(self, manager, mock_db):
        """Test sync behavior when agent descriptions are missing."""
        sample_agents = ['agent_with_desc', 'agent_without_desc']
        sample_descriptions = {'agent_with_desc': 'Has description'}
        
        # Mock discovered agents
        with patch.object(manager, 'get_available_agents', return_value=sample_agents):
            with patch.object(manager, 'get_agent_descriptions', return_value=sample_descriptions):
                # Mock database query returning no existing agents
                mock_result = Mock()
                mock_result.fetchall.return_value = []
                mock_db.execute.return_value = mock_result
                
                # Run sync
                result = await manager.ensure_agents_synced_to_db(mock_db)
                
                # Verify success
                assert result is True
                
                # Verify both agents were added with appropriate descriptions
                assert mock_db.add.call_count == 2
                
                # Check the agents that were added
                added_agents = [call.args[0] for call in mock_db.add.call_args_list]
                
                # Find the agents by type
                agent_with_desc = next(a for a in added_agents if a.agent_type == 'agent_with_desc')
                agent_without_desc = next(a for a in added_agents if a.agent_type == 'agent_without_desc')
                
                assert agent_with_desc.description == 'Has description'
                assert agent_without_desc.description == 'agent_without_desc agent'  # Default description

    @pytest.mark.asyncio
    async def test_multiple_sync_calls_idempotent(self, manager, mock_db, sample_agents):
        """Test that multiple sync calls are idempotent."""
        # Mock discovered agents
        with patch.object(manager, 'get_available_agents', return_value=sample_agents):
            # First sync
            mock_result = Mock()
            mock_result.fetchall.return_value = []
            mock_db.execute.return_value = mock_result
            
            result1 = await manager.ensure_agents_synced_to_db(mock_db)
            assert result1 is True
            assert manager._db_synced is True
            
            # Reset mocks
            mock_db.reset_mock()
            
            # Second sync should skip
            result2 = await manager.ensure_agents_synced_to_db(mock_db)
            assert result2 is True
            mock_db.execute.assert_not_called()

    def test_manager_inheritance(self, manager):
        """Test that EnhancedAgentManager properly inherits from AgentManager."""
        from app.agents.agent_manager import AgentManager
        assert isinstance(manager, AgentManager)
        
        # Verify it has the enhanced functionality
        assert hasattr(manager, 'ensure_agents_synced_to_db')
        assert hasattr(manager, 'get_or_create_agent_record')
        assert hasattr(manager, '_db_synced')