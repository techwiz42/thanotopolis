import pytest
import asyncio
import time
import logging
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import UUID

from app.agents.collaboration_manager import (
    CollaborationManager, 
    CollaborationSession, 
    CollaborationStatus
)


class TestCollaborationStatus:
    """Test the CollaborationStatus constants."""
    
    def test_status_constants(self):
        """Test that status constants have expected values."""
        assert CollaborationStatus.PENDING == "pending"
        assert CollaborationStatus.IN_PROGRESS == "in_progress"
        assert CollaborationStatus.COMPLETED == "completed"
        assert CollaborationStatus.FAILED == "failed"
        assert CollaborationStatus.TIMEOUT == "timeout"


class TestCollaborationSession:
    """Test the CollaborationSession class."""
    
    def test_init_with_all_params(self):
        """Test session initialization with all parameters."""
        session = CollaborationSession(
            collab_id="test-123",
            query="Test query",
            primary_agent_name="MODERATOR",
            collaborating_agents=["AGENT1", "AGENT2"],
            thread_id="thread-456"
        )
        
        assert session.collab_id == "test-123"
        assert session.query == "Test query"
        assert session.primary_agent_name == "MODERATOR"
        assert session.collaborating_agents == ["AGENT1", "AGENT2"]
        assert session.thread_id == "thread-456"
        assert session.status == CollaborationStatus.PENDING
        assert session.end_time is None
        assert session.result is None
        assert session.response_parts == {}
        assert session.error is None
        assert session.future is None
        assert isinstance(session.start_time, float)
        
    def test_init_with_minimal_params(self):
        """Test session initialization with minimal parameters."""
        session = CollaborationSession(
            collab_id="test-123",
            query="Test query",
            primary_agent_name="MODERATOR",
            collaborating_agents=[]
        )
        
        assert session.thread_id is None
        assert session.collaborating_agents == []
        
    def test_start_time_is_current(self):
        """Test that start_time is set to current time."""
        before = time.time()
        session = CollaborationSession(
            collab_id="test",
            query="test",
            primary_agent_name="test",
            collaborating_agents=[]
        )
        after = time.time()
        
        assert before <= session.start_time <= after


class TestCollaborationManager:
    """Test the CollaborationManager class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.manager = CollaborationManager()
        
    def test_init(self):
        """Test CollaborationManager initialization."""
        assert self.manager.active_collaborations == {}
        assert self.manager.collaboration_history == []
        assert self.manager.INDIVIDUAL_AGENT_TIMEOUT == 30.0
        assert self.manager.TOTAL_COLLABORATION_TIMEOUT == 90.0
        assert self.manager.SYNTHESIS_TIMEOUT == 30.0
        assert self.manager.MAX_COLLABORATORS == 3
        assert self.manager._client is None
        
    @patch('app.agents.collaboration_manager.AsyncOpenAI')
    def test_get_client_creates_new_client(self, mock_openai):
        """Test that get_client creates a new OpenAI client when needed."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        client = self.manager.get_client()
        
        assert client == mock_client
        assert self.manager._client == mock_client
        mock_openai.assert_called_once()
        
    @patch('app.agents.collaboration_manager.AsyncOpenAI')
    def test_get_client_reuses_existing_client(self, mock_openai):
        """Test that get_client reuses existing client."""
        mock_client = Mock()
        self.manager._client = mock_client
        
        client = self.manager.get_client()
        
        assert client == mock_client
        mock_openai.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_check_collaboration_needed_explicit_keywords(self):
        """Test collaboration detection with explicit collaboration keywords."""
        test_cases = [
            ("Can you collaborate with multiple experts?", True),
            ("I need different perspectives on this", True),
            ("Compare and contrast these options", True),
            ("Let's work together on this", True),
            ("What are your thoughts?", False),
            ("Simple question here", False),
        ]
        
        available_agents = ["MODERATOR", "AGENT1", "AGENT2"]
        
        for message, expected in test_cases:
            result = await self.manager.check_collaboration_needed(
                message=message,
                primary_agent_type="MODERATOR",
                available_agents=available_agents
            )
            assert result == expected, f"Failed for message: {message}"
            
    @pytest.mark.asyncio
    async def test_check_collaboration_needed_no_collaborators(self):
        """Test collaboration detection when no collaborators available."""
        # Only one agent available (same as primary)
        available_agents = ["MODERATOR"]
        
        result = await self.manager.check_collaboration_needed(
            message="Can you collaborate with multiple experts?",
            primary_agent_type="MODERATOR",
            available_agents=available_agents
        )
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_check_collaboration_needed_case_insensitive(self):
        """Test that collaboration detection is case insensitive."""
        available_agents = ["MODERATOR", "AGENT1"]
        
        result = await self.manager.check_collaboration_needed(
            message="Can you COLLABORATE with MULTIPLE experts?",
            primary_agent_type="MODERATOR",
            available_agents=available_agents
        )
        
        assert result is True
        
    @pytest.mark.asyncio
    async def test_initiate_collaboration_basic(self):
        """Test basic collaboration initiation."""
        query = "Test collaboration query"
        primary_agent = "MODERATOR"
        available_agents = ["MODERATOR", "AGENT1", "AGENT2"]
        collaborating_agents = ["AGENT1", "AGENT2"]
        
        with patch.object(self.manager, '_run_collaboration') as mock_run:
            mock_run.return_value = None
            
            collab_id = await self.manager.initiate_collaboration(
                query=query,
                primary_agent_name=primary_agent,
                available_agents=available_agents,
                collaborating_agents=collaborating_agents
            )
            
        # Verify collaboration ID is UUID format
        assert isinstance(collab_id, str)
        UUID(collab_id)  # Should not raise if valid UUID
        
        # Verify session was created
        assert collab_id in self.manager.active_collaborations
        session = self.manager.active_collaborations[collab_id]
        assert session.query == query
        assert session.primary_agent_name == primary_agent
        assert session.collaborating_agents == collaborating_agents
        assert session.status == CollaborationStatus.PENDING
        
    @pytest.mark.asyncio
    async def test_initiate_collaboration_with_thread_id(self):
        """Test collaboration initiation with thread ID."""
        thread_id = "test-thread-123"
        
        with patch.object(self.manager, '_run_collaboration') as mock_run:
            mock_run.return_value = None
            
            collab_id = await self.manager.initiate_collaboration(
                query="test",
                primary_agent_name="MODERATOR",
                available_agents=["MODERATOR"],
                collaborating_agents=[],
                thread_id=thread_id
            )
            
        session = self.manager.active_collaborations[collab_id]
        assert session.thread_id == thread_id
        
    @pytest.mark.asyncio
    async def test_initiate_collaboration_limits_collaborators(self):
        """Test that initiate_collaboration limits number of collaborators."""
        # Provide more collaborators than the limit
        many_collaborators = ["AGENT1", "AGENT2", "AGENT3", "AGENT4", "AGENT5"]
        
        with patch.object(self.manager, '_run_collaboration') as mock_run:
            mock_run.return_value = None
            
            collab_id = await self.manager.initiate_collaboration(
                query="test",
                primary_agent_name="MODERATOR",
                available_agents=["MODERATOR"] + many_collaborators,
                collaborating_agents=many_collaborators
            )
            
        session = self.manager.active_collaborations[collab_id]
        # Should be limited to MAX_COLLABORATORS (3)
        assert len(session.collaborating_agents) == self.manager.MAX_COLLABORATORS
        assert session.collaborating_agents == many_collaborators[:3]
        
    @pytest.mark.asyncio
    async def test_initiate_collaboration_with_streaming_callback(self):
        """Test collaboration initiation with streaming callback."""
        callback = AsyncMock()
        
        with patch.object(self.manager, '_run_collaboration') as mock_run:
            mock_run.return_value = None
            
            await self.manager.initiate_collaboration(
                query="test",
                primary_agent_name="MODERATOR",
                available_agents=["MODERATOR"],
                collaborating_agents=[],
                streaming_callback=callback
            )
            
        # Verify callback was passed to _run_collaboration
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert 'streaming_callback' in kwargs
        assert kwargs['streaming_callback'] == callback
        
    def test_handle_task_done_with_exception(self):
        """Test task done callback handling with exception."""
        collab_id = "test-collab-123"
        
        # Create a session
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="MODERATOR",
            collaborating_agents=[]
        )
        session.future = asyncio.Future()
        self.manager.active_collaborations[collab_id] = session
        
        # Create a mock task that failed
        mock_task = Mock()
        mock_task.done.return_value = True
        mock_task.cancelled.return_value = False
        test_exception = Exception("Test error")
        mock_task.exception.return_value = test_exception
        
        with patch('app.agents.collaboration_manager.logger') as mock_logger:
            self.manager._handle_task_done(mock_task, collab_id)
            
        # Verify error was logged
        mock_logger.error.assert_called_once()
        
        # Verify session was updated
        assert session.status == CollaborationStatus.FAILED
        assert session.error == "Test error"
        assert session.future.done()
        assert session.future.exception() == test_exception
        
    def test_handle_task_done_successful_task(self):
        """Test task done callback with successful task."""
        collab_id = "test-collab-123"
        
        # Create a mock task that completed successfully
        mock_task = Mock()
        mock_task.done.return_value = True
        mock_task.cancelled.return_value = False
        mock_task.exception.return_value = None
        
        with patch('app.agents.collaboration_manager.logger') as mock_logger:
            self.manager._handle_task_done(mock_task, collab_id)
            
        # Should not log errors for successful tasks
        mock_logger.error.assert_not_called()
        
    def test_handle_task_done_cancelled_task(self):
        """Test task done callback with cancelled task."""
        collab_id = "test-collab-123"
        
        # Create a mock task that was cancelled
        mock_task = Mock()
        mock_task.done.return_value = True
        mock_task.cancelled.return_value = True
        
        with patch('app.agents.collaboration_manager.logger') as mock_logger:
            self.manager._handle_task_done(mock_task, collab_id)
            
        # Should not process cancelled tasks
        mock_logger.error.assert_not_called()
        
    def test_handle_task_done_nonexistent_session(self):
        """Test task done callback when session doesn't exist."""
        collab_id = "nonexistent-collab"
        
        mock_task = Mock()
        mock_task.done.return_value = True
        mock_task.cancelled.return_value = False
        mock_task.exception.return_value = Exception("Test error")
        
        # Should not raise exception even if session doesn't exist
        with patch('app.agents.collaboration_manager.logger'):
            self.manager._handle_task_done(mock_task, collab_id)
            
    @pytest.mark.asyncio
    async def test_get_collaboration_result_completed(self):
        """Test getting result from completed collaboration."""
        collab_id = "test-collab-123"
        expected_result = "Collaboration result"
        
        # Create a completed session
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="MODERATOR",
            collaborating_agents=[]
        )
        session.status = CollaborationStatus.COMPLETED
        session.result = expected_result
        session.end_time = time.time()
        
        # Create a completed future
        future = asyncio.Future()
        future.set_result(expected_result)
        session.future = future
        
        self.manager.active_collaborations[collab_id] = session
        
        result = await self.manager.get_collaboration_result(collab_id)
        
        assert result == expected_result
        # Session should be moved to history and removed from active
        assert collab_id not in self.manager.active_collaborations
        assert session in self.manager.collaboration_history
        
    @pytest.mark.asyncio
    async def test_get_collaboration_result_failed(self):
        """Test getting result from failed collaboration."""
        collab_id = "test-collab-123"
        error_message = "Collaboration failed"
        
        # Create a failed session
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="MODERATOR",
            collaborating_agents=[]
        )
        session.status = CollaborationStatus.FAILED
        session.error = error_message
        session.end_time = time.time()
        
        # Create a failed future
        future = asyncio.Future()
        future.set_exception(Exception(error_message))
        session.future = future
        
        self.manager.active_collaborations[collab_id] = session
        
        with pytest.raises(Exception) as exc_info:
            await self.manager.get_collaboration_result(collab_id)
            
        assert str(exc_info.value) == error_message
        # Session should still be cleaned up
        assert collab_id not in self.manager.active_collaborations
        assert session in self.manager.collaboration_history
        
    @pytest.mark.asyncio
    async def test_get_collaboration_result_timeout(self):
        """Test getting result from collaboration that times out."""
        collab_id = "test-collab-123"
        
        # Create a session with future that won't complete
        session = CollaborationSession(
            collab_id=collab_id,
            query="test",
            primary_agent_name="MODERATOR",
            collaborating_agents=[]
        )
        session.future = asyncio.Future()  # Never completes
        
        self.manager.active_collaborations[collab_id] = session
        
        # Mock a very short timeout for testing
        original_timeout = self.manager.TOTAL_COLLABORATION_TIMEOUT
        self.manager.TOTAL_COLLABORATION_TIMEOUT = 0.1
        
        try:
            with pytest.raises(asyncio.TimeoutError):
                await self.manager.get_collaboration_result(collab_id)
                
            # Session should be cleaned up and marked as timed out
            assert session.status == CollaborationStatus.TIMEOUT
            assert collab_id not in self.manager.active_collaborations
            assert session in self.manager.collaboration_history
        finally:
            # Restore original timeout
            self.manager.TOTAL_COLLABORATION_TIMEOUT = original_timeout
            
    @pytest.mark.asyncio
    async def test_get_collaboration_result_nonexistent(self):
        """Test getting result for nonexistent collaboration."""
        with pytest.raises(KeyError):
            await self.manager.get_collaboration_result("nonexistent-id")
            
    def test_get_collaboration_stats_empty(self):
        """Test getting stats when no collaborations have occurred."""
        stats = self.manager.get_collaboration_stats()
        
        expected = {
            "total_collaborations": 0,
            "active_collaborations": 0,
            "completed_collaborations": 0,
            "failed_collaborations": 0,
            "timeout_collaborations": 0,
            "average_duration": 0.0,
            "agent_participation": {}
        }
        
        assert stats == expected
        
    def test_get_collaboration_stats_with_history(self):
        """Test getting stats with collaboration history."""
        # Create some mock history
        session1 = CollaborationSession("1", "query1", "MODERATOR", ["AGENT1"])
        session1.status = CollaborationStatus.COMPLETED
        session1.start_time = 100.0
        session1.end_time = 105.0  # 5 second duration
        
        session2 = CollaborationSession("2", "query2", "AGENT1", ["MODERATOR", "AGENT2"])
        session2.status = CollaborationStatus.FAILED
        session2.start_time = 200.0
        session2.end_time = 210.0  # 10 second duration
        
        session3 = CollaborationSession("3", "query3", "AGENT2", [])
        session3.status = CollaborationStatus.TIMEOUT
        session3.start_time = 300.0
        session3.end_time = 330.0  # 30 second duration
        
        # Add active collaboration
        session4 = CollaborationSession("4", "query4", "MODERATOR", ["AGENT1"])
        session4.status = CollaborationStatus.IN_PROGRESS
        
        self.manager.collaboration_history = [session1, session2, session3]
        self.manager.active_collaborations = {"4": session4}
        
        stats = self.manager.get_collaboration_stats()
        
        assert stats["total_collaborations"] == 3  # Only completed ones
        assert stats["active_collaborations"] == 1
        assert stats["completed_collaborations"] == 1
        assert stats["failed_collaborations"] == 1
        assert stats["timeout_collaborations"] == 1
        assert stats["average_duration"] == 15.0  # (5+10+30)/3
        
        # Check agent participation
        expected_participation = {
            "MODERATOR": 2,  # primary in session1 and session4, collaborator in session2
            "AGENT1": 2,     # primary in session2, collaborator in session1 and session4
            "AGENT2": 2      # primary in session3, collaborator in session2
        }
        assert stats["agent_participation"] == expected_participation
        
    def test_get_collaboration_stats_no_duration_data(self):
        """Test stats calculation when sessions have no duration data."""
        session = CollaborationSession("1", "query1", "MODERATOR", [])
        session.status = CollaborationStatus.COMPLETED
        # No end_time set
        
        self.manager.collaboration_history = [session]
        
        stats = self.manager.get_collaboration_stats()
        
        assert stats["average_duration"] == 0.0


class TestCollaborationManagerIntegration:
    """Integration tests for CollaborationManager with mocked dependencies."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = CollaborationManager()
        
    @pytest.mark.asyncio
    async def test_full_collaboration_workflow_success(self):
        """Test complete successful collaboration workflow."""
        # Mock agent manager and agents
        mock_agent_manager = Mock()
        mock_primary_agent = AsyncMock()
        mock_collaborator = AsyncMock()
        
        # Set up agent responses
        mock_primary_agent.process_conversation.return_value = "Primary response"
        mock_collaborator.process_conversation.return_value = "Collaborator response"
        
        mock_agent_manager.get_agent.side_effect = lambda thread_id, agent_type: {
            "MODERATOR": mock_primary_agent,
            "AGENT1": mock_collaborator
        }.get(agent_type)
        
        # Mock OpenAI client for synthesis
        mock_openai_client = AsyncMock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="Synthesized response"))]
        mock_openai_client.chat.completions.create.return_value = mock_completion
        
        with patch('app.agents.collaboration_manager.importlib.import_module') as mock_import:
            mock_import.return_value.agent_manager = mock_agent_manager
            
            with patch.object(self.manager, 'get_client', return_value=mock_openai_client):
                # Initiate collaboration
                collab_id = await self.manager.initiate_collaboration(
                    query="Test collaboration query",
                    primary_agent_name="MODERATOR",
                    available_agents=["MODERATOR", "AGENT1"],
                    collaborating_agents=["AGENT1"]
                )
                
                # Give some time for the background task to complete
                await asyncio.sleep(0.1)
                
                # Get result
                result = await self.manager.get_collaboration_result(collab_id)
                
        assert result == "Synthesized response"
        
        # Verify session was moved to history
        assert collab_id not in self.manager.active_collaborations
        assert len(self.manager.collaboration_history) == 1
        assert self.manager.collaboration_history[0].status == CollaborationStatus.COMPLETED
        
    @pytest.mark.asyncio 
    async def test_collaboration_with_agent_timeout(self):
        """Test collaboration when some agents timeout."""
        # Mock agent manager
        mock_agent_manager = Mock()
        mock_primary_agent = AsyncMock()
        mock_slow_agent = AsyncMock()
        
        # Primary agent responds quickly
        mock_primary_agent.process_conversation.return_value = "Primary response"
        
        # Slow agent times out
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(100)  # Longer than timeout
            return "Slow response"
        mock_slow_agent.process_conversation = slow_response
        
        mock_agent_manager.get_agent.side_effect = lambda thread_id, agent_type: {
            "MODERATOR": mock_primary_agent,
            "SLOW_AGENT": mock_slow_agent
        }.get(agent_type)
        
        # Mock OpenAI client
        mock_openai_client = AsyncMock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="Primary response only"))]
        mock_openai_client.chat.completions.create.return_value = mock_completion
        
        # Reduce timeout for testing
        original_timeout = self.manager.INDIVIDUAL_AGENT_TIMEOUT
        self.manager.INDIVIDUAL_AGENT_TIMEOUT = 0.1
        
        try:
            with patch('app.agents.collaboration_manager.importlib.import_module') as mock_import:
                mock_import.return_value.agent_manager = mock_agent_manager
                
                with patch.object(self.manager, 'get_client', return_value=mock_openai_client):
                    collab_id = await self.manager.initiate_collaboration(
                        query="Test timeout query",
                        primary_agent_name="MODERATOR",
                        available_agents=["MODERATOR", "SLOW_AGENT"],
                        collaborating_agents=["SLOW_AGENT"]
                    )
                    
                    # Give time for processing
                    await asyncio.sleep(0.2)
                    
                    result = await self.manager.get_collaboration_result(collab_id)
                    
            # Should still get a result (primary agent's response)
            assert result == "Primary response only"
            
        finally:
            # Restore original timeout
            self.manager.INDIVIDUAL_AGENT_TIMEOUT = original_timeout
            
    @pytest.mark.asyncio
    async def test_collaboration_synthesis_fallback(self):
        """Test collaboration falls back when synthesis fails."""
        # Mock agent manager
        mock_agent_manager = Mock()
        mock_primary_agent = AsyncMock()
        mock_primary_agent.process_conversation.return_value = "Primary response"
        mock_agent_manager.get_agent.return_value = mock_primary_agent
        
        # Mock OpenAI client that fails
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        
        with patch('app.agents.collaboration_manager.importlib.import_module') as mock_import:
            mock_import.return_value.agent_manager = mock_agent_manager
            
            with patch.object(self.manager, 'get_client', return_value=mock_openai_client):
                collab_id = await self.manager.initiate_collaboration(
                    query="Test fallback query",
                    primary_agent_name="MODERATOR",
                    available_agents=["MODERATOR"],
                    collaborating_agents=[]
                )
                
                await asyncio.sleep(0.1)
                result = await self.manager.get_collaboration_result(collab_id)
                
        # Should fall back to primary agent response
        assert result == "Primary response"
        
    @pytest.mark.asyncio
    async def test_collaboration_with_streaming_callback(self):
        """Test collaboration with streaming callback integration."""
        callback_calls = []
        
        async def mock_callback(token):
            callback_calls.append(token)
            
        # Mock agent manager
        mock_agent_manager = Mock()
        mock_agent = AsyncMock()
        
        # Mock agent that supports streaming
        async def streaming_response(*args, **kwargs):
            streaming_callback = kwargs.get('streaming_callback')
            if streaming_callback:
                await streaming_callback("Token 1")
                await streaming_callback("Token 2")
            return "Complete response"
            
        mock_agent.process_conversation = streaming_response
        mock_agent_manager.get_agent.return_value = mock_agent
        
        # Mock synthesis
        mock_openai_client = AsyncMock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="Synthesized"))]
        mock_openai_client.chat.completions.create.return_value = mock_completion
        
        with patch('app.agents.collaboration_manager.importlib.import_module') as mock_import:
            mock_import.return_value.agent_manager = mock_agent_manager
            
            with patch.object(self.manager, 'get_client', return_value=mock_openai_client):
                collab_id = await self.manager.initiate_collaboration(
                    query="Test streaming",
                    primary_agent_name="MODERATOR",
                    available_agents=["MODERATOR"],
                    collaborating_agents=[],
                    streaming_callback=mock_callback
                )
                
                await asyncio.sleep(0.1)
                result = await self.manager.get_collaboration_result(collab_id)
                
        # Verify streaming tokens were received
        assert "Token 1" in callback_calls
        assert "Token 2" in callback_calls
        assert result == "Synthesized"