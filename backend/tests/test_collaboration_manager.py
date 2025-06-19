import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

from app.agents.collaboration_manager import (
    CollaborationManager, 
    CollaborationSession,
    CollaborationStatus
)


class TestCollaborationStatus:
    """Test CollaborationStatus constants."""
    
    def test_status_constants(self):
        """Test that all expected status constants exist."""
        assert CollaborationStatus.PENDING == "pending"
        assert CollaborationStatus.IN_PROGRESS == "in_progress"
        assert CollaborationStatus.COMPLETED == "completed"
        assert CollaborationStatus.FAILED == "failed"
        assert CollaborationStatus.TIMEOUT == "timeout"


class TestCollaborationSession:
    """Test CollaborationSession class."""
    
    def test_session_initialization(self):
        """Test CollaborationSession initialization."""
        collab_id = "test-collab-id"
        query = "test query"
        primary_agent = "primary_agent"
        collaborators = ["agent1", "agent2"]
        thread_id = "test-thread-id"
        
        session = CollaborationSession(
            collab_id=collab_id,
            query=query,
            primary_agent_name=primary_agent,
            collaborating_agents=collaborators,
            thread_id=thread_id
        )
        
        assert session.collab_id == collab_id
        assert session.query == query
        assert session.primary_agent_name == primary_agent
        assert session.collaborating_agents == collaborators
        assert session.thread_id == thread_id
        assert session.status == CollaborationStatus.PENDING
        assert session.result is None
        assert session.response_parts == {}
        assert session.error is None
        assert session.future is None
        assert isinstance(session.start_time, float)
        assert session.end_time is None

    def test_session_optional_thread_id(self):
        """Test CollaborationSession with optional thread_id."""
        session = CollaborationSession(
            collab_id="test-id",
            query="test query",
            primary_agent_name="agent",
            collaborating_agents=[]
        )
        
        assert session.thread_id is None


class TestCollaborationManager:
    """Test CollaborationManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a CollaborationManager instance."""
        return CollaborationManager()
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = AsyncMock()
        return client

    def test_manager_initialization(self, manager):
        """Test CollaborationManager initialization."""
        assert manager.active_collaborations == {}
        assert manager.collaboration_history == []
        assert manager.INDIVIDUAL_AGENT_TIMEOUT == 30.0
        assert manager.TOTAL_COLLABORATION_TIMEOUT == 90.0
        assert manager.SYNTHESIS_TIMEOUT == 30.0
        assert manager.MAX_COLLABORATORS == 3
        assert manager._client is None

    def test_get_client(self, manager):
        """Test OpenAI client creation."""
        with patch('app.agents.collaboration_manager.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            client = manager.get_client()
            
            assert client == mock_client
            assert manager._client == mock_client
            mock_openai.assert_called_once()

    def test_get_client_reuses_existing(self, manager):
        """Test that get_client reuses existing client."""
        existing_client = Mock()
        manager._client = existing_client
        
        client = manager.get_client()
        
        assert client == existing_client

    @pytest.mark.asyncio
    async def test_check_collaboration_needed_explicit_keywords(self, manager):
        """Test collaboration detection with explicit keywords."""
        messages_with_keywords = [
            "I need multiple perspectives on this",
            "Can we collaborate on this?",
            "I want different views from experts",
            "Let's compare and contrast approaches",
            "Get experts together on this"
        ]
        
        for message in messages_with_keywords:
            result = await manager.check_collaboration_needed(
                message=message,
                primary_agent_type="primary_agent",
                available_agents=["primary_agent", "other_agent"]
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_check_collaboration_needed_no_keywords(self, manager):
        """Test collaboration detection without keywords."""
        message = "What is the weather today?"
        
        result = await manager.check_collaboration_needed(
            message=message,
            primary_agent_type="primary_agent",
            available_agents=["primary_agent", "other_agent"]
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_check_collaboration_needed_no_collaborators(self, manager):
        """Test collaboration when no other agents available."""
        message = "I need multiple perspectives"
        
        result = await manager.check_collaboration_needed(
            message=message,
            primary_agent_type="only_agent",
            available_agents=["only_agent"]  # Only primary agent available
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_initiate_collaboration(self, manager):
        """Test collaboration initiation."""
        query = "test query"
        primary_agent = "primary_agent"
        available_agents = ["primary_agent", "agent1", "agent2"]
        collaborators = ["agent1", "agent2"]
        thread_id = "test-thread"
        
        with patch.object(manager, '_run_collaboration') as mock_run:
            # Mock future task
            mock_task = AsyncMock()
            mock_task.add_done_callback = Mock()
            
            with patch('asyncio.create_task', return_value=mock_task):
                collab_id = await manager.initiate_collaboration(
                    query=query,
                    primary_agent_name=primary_agent,
                    available_agents=available_agents,
                    collaborating_agents=collaborators,
                    thread_id=thread_id
                )
                
                # Verify collaboration was created
                assert collab_id in manager.active_collaborations
                session = manager.active_collaborations[collab_id]
                
                assert session.query == query
                assert session.primary_agent_name == primary_agent
                assert session.collaborating_agents == collaborators
                assert session.thread_id == thread_id
                assert session.status == CollaborationStatus.PENDING

    @pytest.mark.asyncio
    async def test_initiate_collaboration_limits_collaborators(self, manager):
        """Test that collaboration limits number of collaborators."""
        query = "test query"
        primary_agent = "primary_agent"
        available_agents = ["primary_agent"] + [f"agent{i}" for i in range(10)]
        collaborators = [f"agent{i}" for i in range(10)]  # More than MAX_COLLABORATORS
        
        with patch.object(manager, '_run_collaboration'):
            with patch('asyncio.create_task'):
                collab_id = await manager.initiate_collaboration(
                    query=query,
                    primary_agent_name=primary_agent,
                    available_agents=available_agents,
                    collaborating_agents=collaborators
                )
                
                session = manager.active_collaborations[collab_id]
                
                # Should be limited to MAX_COLLABORATORS
                assert len(session.collaborating_agents) == manager.MAX_COLLABORATORS

    @pytest.mark.asyncio
    async def test_get_collaboration_result_completed(self, manager):
        """Test getting result from completed collaboration."""
        collab_id = "test-collab"
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="agent",
            collaborating_agents=[]
        )
        session.status = CollaborationStatus.COMPLETED
        session.result = "test result"
        
        manager.active_collaborations[collab_id] = session
        
        result = await manager.get_collaboration_result(collab_id)
        
        assert result == "test result"

    @pytest.mark.asyncio
    async def test_get_collaboration_result_not_found(self, manager):
        """Test getting result from non-existent collaboration."""
        result = await manager.get_collaboration_result("non-existent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_collaboration_result_with_future(self, manager):
        """Test getting result that requires waiting for future."""
        collab_id = "test-collab"
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="agent",
            collaborating_agents=[]
        )
        
        # Create a future that resolves immediately
        future = asyncio.Future()
        future.set_result("future result")
        session.future = future
        
        manager.active_collaborations[collab_id] = session
        
        result = await manager.get_collaboration_result(collab_id, timeout=1.0)
        
        assert result == "future result"

    @pytest.mark.asyncio
    async def test_get_collaboration_result_timeout(self, manager):
        """Test timeout when waiting for collaboration result."""
        collab_id = "test-collab"
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="agent",
            collaborating_agents=[]
        )
        
        # Create a future that never resolves
        session.future = asyncio.Future()
        
        manager.active_collaborations[collab_id] = session
        
        result = await manager.get_collaboration_result(collab_id, timeout=0.1)
        
        assert result is None
        assert session.status == CollaborationStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_run_collaboration_no_thread_id(self, manager):
        """Test collaboration run failure when no thread_id."""
        session = CollaborationSession(
            collab_id="test-collab",
            query="test",
            primary_agent_name="agent",
            collaborating_agents=[],
            thread_id=None  # No thread ID
        )
        session.future = asyncio.Future()
        
        await manager._run_collaboration(session, [])
        
        assert session.status == CollaborationStatus.FAILED
        assert "Thread ID is required" in session.error
        assert session.future.done()

    @pytest.mark.asyncio
    async def test_run_collaboration_primary_agent_not_found(self, manager):
        """Test collaboration run failure when primary agent not found."""
        session = CollaborationSession(
            collab_id="test-collab",
            query="test",
            primary_agent_name="missing_agent",
            collaborating_agents=[],
            thread_id="test-thread"
        )
        session.future = asyncio.Future()
        
        with patch('app.agents.agent_manager.agent_manager') as mock_agent_manager:
            mock_agent_manager.get_agent.return_value = None
            
            await manager._run_collaboration(session, ["missing_agent"])
            
            assert session.status == CollaborationStatus.FAILED
            assert "Primary agent missing_agent not found" in session.error
            assert session.future.done()

    @pytest.mark.asyncio
    async def test_get_agent_response(self, manager):
        """Test getting response from a single agent."""
        agent_name = "test_agent"
        query = "test query"
        thread_id = "test-thread"
        
        # Mock agent and runner
        mock_agent = Mock()
        mock_streamed_result = Mock()
        mock_streamed_result.final_output = "agent response"
        
        # Mock stream events
        async def mock_stream_events():
            # Yield some mock events
            mock_event = Mock()
            mock_event.type = "raw_response_event"
            mock_event.data = Mock()
            mock_event.data.type = "response.output_text.delta"
            mock_event.data.delta = "test"
            yield mock_event
        
        mock_streamed_result.stream_events = mock_stream_events
        
        with patch('app.agents.collaboration_manager.Runner') as mock_runner:
            with patch('app.agents.collaboration_manager.RunConfig'):
                with patch('app.agents.collaboration_manager.ModelSettings'):
                    mock_runner.run_streamed.return_value = mock_streamed_result
                    
                    result = await manager._get_agent_response(
                        agent_name=agent_name,
                        agent=mock_agent,
                        query=query,
                        is_primary=True,
                        thread_id=thread_id
                    )
                    
                    assert result == (agent_name, "agent response")

    @pytest.mark.asyncio
    async def test_get_agent_response_with_streaming(self, manager):
        """Test getting agent response with streaming callback."""
        agent_name = "test_agent"
        query = "test query"
        thread_id = "test-thread"
        
        # Mock streaming callback
        streaming_callback = AsyncMock()
        
        # Mock agent and runner
        mock_agent = Mock()
        mock_streamed_result = Mock()
        mock_streamed_result.final_output = "agent response"
        
        # Mock stream events with tokens
        async def mock_stream_events():
            mock_event = Mock()
            mock_event.type = "raw_response_event"
            mock_event.data = Mock()
            mock_event.data.type = "response.output_text.delta"
            mock_event.data.delta = "token"
            yield mock_event
        
        mock_streamed_result.stream_events = mock_stream_events
        
        with patch('app.agents.collaboration_manager.Runner') as mock_runner:
            with patch('app.agents.collaboration_manager.RunConfig'):
                with patch('app.agents.collaboration_manager.ModelSettings'):
                    mock_runner.run_streamed.return_value = mock_streamed_result
                    
                    result = await manager._get_agent_response(
                        agent_name=agent_name,
                        agent=mock_agent,
                        query=query,
                        is_primary=True,
                        thread_id=thread_id,
                        streaming_callback=streaming_callback
                    )
                    
                    assert result == (agent_name, "agent response")
                    
                    # Verify streaming was called
                    assert streaming_callback.call_count >= 3  # Start, token, end messages

    @pytest.mark.asyncio
    async def test_get_agent_response_error(self, manager):
        """Test error handling in agent response."""
        agent_name = "test_agent"
        query = "test query"
        
        # Mock agent that raises an error
        mock_agent = Mock()
        
        with patch('app.agents.collaboration_manager.Runner') as mock_runner:
            mock_runner.run_streamed.side_effect = Exception("Agent error")
            
            result = await manager._get_agent_response(
                agent_name=agent_name,
                agent=mock_agent,
                query=query,
                is_primary=True
            )
            
            assert result == (agent_name, "Error: Agent test_agent could not provide a response.")

    @pytest.mark.asyncio
    async def test_synthesize_responses_no_supporting(self, manager, mock_openai_client):
        """Test synthesis with only primary response."""
        session = CollaborationSession(
            collab_id="test-collab",
            query="test query",
            primary_agent_name="primary_agent",
            collaborating_agents=[]
        )
        session.response_parts = {"primary_agent": "primary response"}
        
        await manager._synthesize_responses(session)
        
        assert session.result == "primary response"

    @pytest.mark.asyncio
    async def test_synthesize_responses_with_supporting(self, manager):
        """Test synthesis with primary and supporting responses."""
        import uuid
        thread_uuid = str(uuid.uuid4())
        
        session = CollaborationSession(
            collab_id="test-collab",
            query="test query",
            primary_agent_name="primary_agent",
            collaborating_agents=["agent1", "agent2"],
            thread_id=thread_uuid
        )
        session.response_parts = {
            "primary_agent": "primary response",
            "agent1": "supporting response 1",
            "agent2": "supporting response 2"
        }
        
        # Mock OpenAI client
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta = Mock()
        mock_chunk.choices[0].delta.content = "synthesized"
        
        async def mock_stream():
            yield mock_chunk
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream()
        
        with patch.object(manager, 'get_client', return_value=mock_client):
            with patch('app.core.websocket_queue.connection_health'):
                await manager._synthesize_responses(session)
                
                assert session.result == "synthesized"
                mock_client.chat.completions.create.assert_called_once()

    def test_get_collaboration_stats_empty(self, manager):
        """Test collaboration statistics with no history."""
        stats = manager.get_collaboration_stats()
        
        assert stats == {"total_collaborations": 0}

    def test_get_collaboration_stats_with_history(self, manager):
        """Test collaboration statistics with history."""
        # Create mock collaboration sessions
        session1 = CollaborationSession(
            collab_id="collab1",
            query="query1",
            primary_agent_name="agent1",
            collaborating_agents=["agent2"]
        )
        session1.status = CollaborationStatus.COMPLETED
        session1.start_time = time.time()
        session1.end_time = session1.start_time + 10.0
        
        session2 = CollaborationSession(
            collab_id="collab2",
            query="query2",
            primary_agent_name="agent2",
            collaborating_agents=["agent1", "agent3"]
        )
        session2.status = CollaborationStatus.FAILED
        session2.start_time = time.time()
        session2.end_time = session2.start_time + 5.0
        
        manager.collaboration_history = [session1, session2]
        
        stats = manager.get_collaboration_stats()
        
        assert stats["total_collaborations"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["completion_rate"] == 0.5
        assert stats["avg_duration_seconds"] == 7.5
        assert "agent_participation" in stats
        
        # Check agent participation
        participation = stats["agent_participation"]
        assert participation["agent1"]["primary"] == 1
        assert participation["agent1"]["supporting"] == 1
        assert participation["agent2"]["primary"] == 1
        assert participation["agent2"]["supporting"] == 1
        assert participation["agent3"]["supporting"] == 1

    def test_handle_task_done_with_exception(self, manager):
        """Test task done callback with exception."""
        collab_id = "test-collab"
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="agent",
            collaborating_agents=[]
        )
        session.future = asyncio.Future()
        
        manager.active_collaborations[collab_id] = session
        
        # Create mock task with exception
        mock_task = Mock()
        mock_task.done.return_value = True
        mock_task.cancelled.return_value = False
        mock_task.exception.return_value = Exception("Task failed")
        
        manager._handle_task_done(mock_task, collab_id)
        
        assert session.status == CollaborationStatus.FAILED
        assert session.error == "Task failed"
        assert collab_id not in manager.active_collaborations

    def test_handle_task_done_no_exception(self, manager):
        """Test task done callback without exception."""
        collab_id = "test-collab"
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="agent",
            collaborating_agents=[]
        )
        
        manager.active_collaborations[collab_id] = session
        
        # Create mock task without exception
        mock_task = Mock()
        mock_task.done.return_value = True
        mock_task.cancelled.return_value = False
        mock_task.exception.return_value = None
        
        manager._handle_task_done(mock_task, collab_id)
        
        # Session should remain unchanged
        assert session.status == CollaborationStatus.PENDING
        assert collab_id in manager.active_collaborations