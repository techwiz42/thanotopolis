"""
Unit tests for Voice Agent Collaboration Service
Tests the consent-based collaboration system for Deepgram Voice Agent integration
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from app.services.voice.voice_agent_collaboration import (
    VoiceAgentCollaborationService,
    CollaborationState,
    ComplexityAnalysis,
    CollaborationSession,
    voice_agent_collaboration_service
)
from app.services.voice.deepgram_voice_agent import VoiceAgentSession, DeepgramVoiceAgent


class MockVoiceAgentSession:
    """Mock Voice Agent session for testing"""
    def __init__(self, session_id: str = "test-session"):
        self.session_id = session_id
        self.agent = Mock(spec=DeepgramVoiceAgent)
        self.agent.inject_message = AsyncMock()
        self.agent.update_instructions = AsyncMock()


class TestComplexityAnalysis:
    """Test complexity analysis functionality"""
    
    def test_complexity_analysis_dataclass(self):
        """Test ComplexityAnalysis dataclass initialization"""
        analysis = ComplexityAnalysis(
            is_complex=True,
            confidence=0.8,
            reasoning="Multi-domain query requiring specialist knowledge",
            suggested_agents=["LEGAL", "FINANCIAL"],
            estimated_duration=25
        )
        
        assert analysis.is_complex is True
        assert analysis.confidence == 0.8
        assert analysis.reasoning == "Multi-domain query requiring specialist knowledge"
        assert analysis.suggested_agents == ["LEGAL", "FINANCIAL"]
        assert analysis.estimated_duration == 25


class TestCollaborationSession:
    """Test collaboration session management"""
    
    def test_collaboration_session_creation(self):
        """Test collaboration session initialization"""
        voice_session = MockVoiceAgentSession()
        complexity = ComplexityAnalysis(
            is_complex=True,
            confidence=0.9,
            reasoning="Test reasoning",
            suggested_agents=["TEST_AGENT"],
            estimated_duration=20
        )
        
        session = CollaborationSession(
            session_id="test-123",
            voice_session=voice_session,
            state=CollaborationState.IDLE,
            user_query="Test query",
            complexity_analysis=complexity,
            selected_agents=["TEST_AGENT"],
            consent_given=None,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        
        assert session.session_id == "test-123"
        assert session.state == CollaborationState.IDLE
        assert session.user_query == "Test query"
        assert session.complexity_analysis == complexity
        assert session.selected_agents == ["TEST_AGENT"]
        assert session.consent_given is None
        assert session.collaboration_response is None
        assert isinstance(session.start_time, datetime)


class TestVoiceAgentCollaborationService:
    """Test the main collaboration service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = VoiceAgentCollaborationService()
        self.voice_session = MockVoiceAgentSession("test-session-123")
        self.test_message = "I need help with complex legal and financial matters"
    
    @pytest.mark.asyncio
    async def test_analyze_query_complexity_simple(self):
        """Test complexity analysis for simple query"""
        # Mock OpenAI response for simple query
        with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai_class:
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "is_complex": False,
                "confidence": 0.3,
                "reasoning": "Simple query can be handled by basic assistant",
                "suggested_agents": [],
                "estimated_duration": 15
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Mock agent manager
            with patch.object(self.service, 'agent_manager') as mock_agent_mgr:
                mock_agent_mgr.get_agent_descriptions.return_value = {
                    "LEGAL": "Legal expertise agent",
                    "FINANCIAL": "Financial expertise agent"
                }
                mock_agent_mgr.get_agent.return_value = Mock()
                
                result = await self.service._analyze_query_complexity("What time is it?")
                
                assert result.is_complex is False
                assert result.confidence == 0.3
                assert result.reasoning == "Simple query can be handled by basic assistant"
                assert result.suggested_agents == []
                assert result.estimated_duration == 15
    
    @pytest.mark.asyncio
    async def test_analyze_query_complexity_complex(self):
        """Test complexity analysis for complex query"""
        # Mock OpenAI response for complex query
        with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai_class:
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "is_complex": True,
                "confidence": 0.9,
                "reasoning": "Query requires both legal and financial expertise",
                "suggested_agents": ["LEGAL", "FINANCIAL"],
                "estimated_duration": 25
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Mock agent manager
            with patch.object(self.service, 'agent_manager') as mock_agent_mgr:
                mock_agent_mgr.get_agent_descriptions.return_value = {
                    "LEGAL": "Legal expertise agent",
                    "FINANCIAL": "Financial expertise agent",
                    "MODERATOR": "Moderator agent"
                }
                mock_agent_mgr.get_agent.return_value = Mock()
                
                result = await self.service._analyze_query_complexity(
                    "I need advice on tax implications of my divorce settlement"
                )
                
                assert result.is_complex is True
                assert result.confidence == 0.9
                assert result.reasoning == "Query requires both legal and financial expertise"
                assert result.suggested_agents == ["LEGAL", "FINANCIAL"]
                assert result.estimated_duration == 25
    
    @pytest.mark.asyncio
    async def test_analyze_query_complexity_error_handling(self):
        """Test complexity analysis error handling"""
        # Mock agent manager with missing MODERATOR
        with patch.object(self.service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent.return_value = None
            
            result = await self.service._analyze_query_complexity("Test query")
            
            assert result.is_complex is False
            assert result.confidence == 0.0
            assert "MODERATOR agent not available" in result.reasoning
            assert result.suggested_agents == []
            assert result.estimated_duration == 0
    
    @pytest.mark.asyncio
    async def test_process_user_message_simple_query(self):
        """Test processing simple query that doesn't trigger collaboration"""
        with patch.object(self.service, '_analyze_query_complexity') as mock_analyze:
            # Mock simple query analysis
            mock_analyze.return_value = ComplexityAnalysis(
                is_complex=False,
                confidence=0.4,
                reasoning="Simple query",
                suggested_agents=[],
                estimated_duration=15
            )
            
            result = await self.service.process_user_message(
                session_id="test-session",
                voice_session=self.voice_session,
                user_message="What time is it?",
                db_session=None,
                owner_id=None
            )
            
            assert result is False  # No collaboration initiated
            assert "test-session" not in self.service.active_sessions
    
    @pytest.mark.asyncio
    async def test_process_user_message_complex_query(self):
        """Test processing complex query that triggers collaboration"""
        with patch.object(self.service, '_analyze_query_complexity') as mock_analyze, \
             patch.object(self.service, '_request_consent') as mock_request:
            
            # Mock complex query analysis
            mock_analyze.return_value = ComplexityAnalysis(
                is_complex=True,
                confidence=0.9,
                reasoning="Complex multi-domain query",
                suggested_agents=["LEGAL", "FINANCIAL"],
                estimated_duration=25
            )
            
            result = await self.service.process_user_message(
                session_id="test-session",
                voice_session=self.voice_session,
                user_message=self.test_message,
                db_session=None,
                owner_id=None
            )
            
            assert result is True  # Collaboration initiated
            assert "test-session" in self.service.active_sessions
            session = self.service.active_sessions["test-session"]
            assert session.state == CollaborationState.DETECTING_COMPLEXITY
            assert session.user_query == self.test_message
            assert session.selected_agents == ["LEGAL", "FINANCIAL"]
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_user_message_ongoing_collaboration(self):
        """Test handling user message during ongoing collaboration"""
        # Set up existing session
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.AWAITING_CONSENT,
            user_query="Original query",
            complexity_analysis=None,
            selected_agents=[],
            consent_given=None,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        self.service.active_sessions["test-session"] = session
        
        with patch.object(self.service, '_handle_ongoing_collaboration', return_value=True) as mock_handle:
            result = await self.service.process_user_message(
                session_id="test-session",
                voice_session=self.voice_session,
                user_message="Yes, please consult the experts",
                db_session=None,
                owner_id=None
            )
            
            assert result is True
            mock_handle.assert_called_once_with("test-session", "Yes, please consult the experts")
    
    @pytest.mark.asyncio
    async def test_request_consent(self):
        """Test consent request functionality"""
        complexity = ComplexityAnalysis(
            is_complex=True,
            confidence=0.8,
            reasoning="Test reasoning",
            suggested_agents=["LEGAL", "COMPLIANCE"],
            estimated_duration=25
        )
        
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.DETECTING_COMPLEXITY,
            user_query="Test query",
            complexity_analysis=complexity,
            selected_agents=["LEGAL", "COMPLIANCE"],
            consent_given=None,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        
        await self.service._request_consent(session)
        
        assert session.state == CollaborationState.AWAITING_CONSENT
        self.voice_session.agent.inject_message.assert_called_once()
        
        # Check consent message content
        consent_call = self.voice_session.agent.inject_message.call_args[0][0]
        assert "LEGAL, COMPLIANCE" in consent_call
        assert "25 seconds" in consent_call
        assert "Would you like me to check with the experts?" in consent_call
        
        assert session.timeout_task is not None
    
    @pytest.mark.asyncio
    async def test_detect_consent_positive(self):
        """Test positive consent detection"""
        positive_responses = [
            "Yes please",
            "Yeah, go ahead", 
            "Sure, consult with them",
            "Okay, do it",
            "Please check with experts"
        ]
        
        for response in positive_responses:
            result = await self.service._detect_consent(response)
            assert result is True, f"Failed to detect positive consent in: {response}"
    
    @pytest.mark.asyncio
    async def test_detect_consent_negative(self):
        """Test negative consent detection"""
        negative_responses = [
            "No thanks",
            "Nope, just give me a quick answer",
            "Skip it",
            "Not now",
            "No, I need a quick response"
        ]
        
        for response in negative_responses:
            result = await self.service._detect_consent(response)
            assert result is False, f"Failed to detect negative consent in: {response}"
    
    @pytest.mark.asyncio
    async def test_detect_consent_llm_fallback(self):
        """Test LLM fallback for ambiguous consent"""
        # Mock OpenAI response
        with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai_class:
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "consent": True,
                "confidence": 0.8
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await self.service._detect_consent("I suppose that would be helpful")
            
            assert result is True
            mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_ongoing_collaboration_consent_given(self):
        """Test handling ongoing collaboration when consent is given"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.AWAITING_CONSENT,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=None,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        self.service.active_sessions["test-session"] = session
        
        with patch.object(self.service, '_detect_consent', return_value=True), \
             patch.object(self.service, '_start_collaboration') as mock_start:
            
            result = await self.service._handle_ongoing_collaboration(
                "test-session", 
                "Yes, please consult with experts"
            )
            
            assert result is True
            assert session.consent_given is True
            mock_start.assert_called_once_with(session)
    
    @pytest.mark.asyncio
    async def test_handle_ongoing_collaboration_consent_declined(self):
        """Test handling ongoing collaboration when consent is declined"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.AWAITING_CONSENT,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=None,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        self.service.active_sessions["test-session"] = session
        
        with patch.object(self.service, '_detect_consent', return_value=False), \
             patch.object(self.service, '_decline_collaboration') as mock_decline:
            
            result = await self.service._handle_ongoing_collaboration(
                "test-session", 
                "No, just give me a quick answer"
            )
            
            assert result is True
            assert session.consent_given is False
            mock_decline.assert_called_once_with(session)
    
    @pytest.mark.asyncio
    async def test_handle_ongoing_collaboration_unclear_response(self):
        """Test handling unclear consent response"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.AWAITING_CONSENT,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=None,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        self.service.active_sessions["test-session"] = session
        
        with patch.object(self.service, '_detect_consent', return_value=None):
            result = await self.service._handle_ongoing_collaboration(
                "test-session", 
                "Um, what do you mean?"
            )
            
            assert result is True
            assert session.consent_given is None
            # Should ask for clarification
            self.voice_session.agent.inject_message.assert_called_once()
            clarification_call = self.voice_session.agent.inject_message.call_args[0][0]
            assert "didn't catch that" in clarification_call
    
    @pytest.mark.asyncio
    async def test_start_collaboration(self):
        """Test starting collaboration process"""
        mock_timeout_task = Mock()
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.AWAITING_CONSENT,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=True,
            collaboration_response=None,
            start_time=datetime.utcnow(),
            timeout_task=mock_timeout_task
        )
        
        with patch.object(self.service, '_execute_collaboration') as mock_execute, \
             patch('asyncio.create_task') as mock_create_task:
            
            mock_create_task.return_value = Mock()
            
            await self.service._start_collaboration(session)
            
            assert session.state == CollaborationState.COLLABORATING
            mock_timeout_task.cancel.assert_called_once()
            self.voice_session.agent.inject_message.assert_called_once()
            self.voice_session.agent.update_instructions.assert_called_once()
            
            # Check that collaboration message was injected
            collab_call = self.voice_session.agent.inject_message.call_args[0][0]
            assert "consult with the experts" in collab_call
    
    @pytest.mark.asyncio
    async def test_execute_collaboration(self):
        """Test executing collaboration with agents"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.COLLABORATING,
            user_query="Test complex query",
            complexity_analysis=None,
            selected_agents=["LEGAL", "FINANCIAL"],
            consent_given=True,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        
        with patch.object(self.service.agent_manager, 'process_conversation') as mock_process, \
             patch.object(self.service, '_resume_voice_agent') as mock_resume:
            
            mock_process.return_value = ("LEGAL", "Expert legal and financial advice")
            
            await self.service._execute_collaboration(session)
            
            assert session.collaboration_response == "Expert legal and financial advice"
            assert session.state == CollaborationState.RESUMING
            mock_process.assert_called_once()
            mock_resume.assert_called_once_with(session)
            
            # Check process_conversation call arguments
            call_args = mock_process.call_args
            assert call_args[1]['message'] == "Test complex query"
            assert call_args[1]['db'] is None  # No persistent storage for voice
            assert call_args[1]['response_callback'] is None  # No streaming
    
    @pytest.mark.asyncio
    async def test_resume_voice_agent(self):
        """Test resuming Voice Agent with collaboration results"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.RESUMING,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=True,
            collaboration_response="Expert legal advice about your situation",
            start_time=datetime.utcnow()
        )
        
        with patch('asyncio.create_task') as mock_create_task:
            await self.service._resume_voice_agent(session)
            
            assert session.state == CollaborationState.COMPLETED
            self.voice_session.agent.update_instructions.assert_called_once()
            self.voice_session.agent.inject_message.assert_called_once()
            
            # Check enhanced instructions
            instructions_call = self.voice_session.agent.update_instructions.call_args[0][0]
            assert "Expert legal advice about your situation" in instructions_call
            assert "expert consultation" in instructions_call
            
            # Check response injection
            response_call = self.voice_session.agent.inject_message.call_args[0][0]
            assert "expert consultation" in response_call
            assert "Expert legal advice" in response_call
            
            # Check delayed cleanup was scheduled
            mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_decline_collaboration(self):
        """Test declining collaboration"""
        mock_timeout_task = Mock()
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.AWAITING_CONSENT,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=False,
            collaboration_response=None,
            start_time=datetime.utcnow(),
            timeout_task=mock_timeout_task
        )
        self.service.active_sessions["test-session"] = session
        
        with patch.object(self.service, '_cleanup_session') as mock_cleanup:
            await self.service._decline_collaboration(session)
            
            assert session.state == CollaborationState.COMPLETED
            mock_timeout_task.cancel.assert_called_once()
            self.voice_session.agent.inject_message.assert_called_once()
            mock_cleanup.assert_called_once_with("test-session")
            
            # Check decline message
            decline_call = self.voice_session.agent.inject_message.call_args[0][0]
            assert "No problem" in decline_call
            assert "best answer I can provide directly" in decline_call
    
    @pytest.mark.asyncio
    async def test_handle_consent_timeout(self):
        """Test handling consent timeout"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.AWAITING_CONSENT,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=None,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        self.service.active_sessions["test-session"] = session
        
        with patch.object(self.service, '_cleanup_session') as mock_cleanup:
            # Simulate timeout
            await self.service._handle_consent_timeout("test-session")
            
            assert session.consent_given is False
            self.voice_session.agent.inject_message.assert_called_once()
            mock_cleanup.assert_called_once_with("test-session")
            
            # Check timeout message
            timeout_call = self.voice_session.agent.inject_message.call_args[0][0]
            assert "direct answer" in timeout_call
    
    @pytest.mark.asyncio
    async def test_handle_collaboration_timeout(self):
        """Test handling collaboration timeout"""
        collaboration_task = Mock()
        collaboration_task.done.return_value = False
        collaboration_task.cancel = Mock()
        
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.COLLABORATING,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=True,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        self.service.active_sessions["test-session"] = session
        
        with patch.object(self.service, '_cleanup_session') as mock_cleanup:
            await self.service._handle_collaboration_timeout("test-session", collaboration_task)
            
            assert session.state == CollaborationState.FAILED
            collaboration_task.cancel.assert_called_once()
            self.voice_session.agent.inject_message.assert_called_once()
            mock_cleanup.assert_called_once_with("test-session")
            
            # Check timeout message
            timeout_call = self.voice_session.agent.inject_message.call_args[0][0]
            assert "taking longer than expected" in timeout_call
    
    @pytest.mark.asyncio
    async def test_cleanup_session(self):
        """Test session cleanup"""
        mock_timeout_task = Mock()
        mock_timeout_task.done.return_value = False
        mock_timeout_task.cancel = Mock()
        
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.COMPLETED,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=True,
            collaboration_response="Test response",
            start_time=datetime.utcnow(),
            timeout_task=mock_timeout_task
        )
        self.service.active_sessions["test-session"] = session
        
        await self.service._cleanup_session("test-session")
        
        mock_timeout_task.cancel.assert_called_once()
        assert "test-session" not in self.service.active_sessions
    
    def test_get_session_status(self):
        """Test getting session status"""
        complexity = ComplexityAnalysis(
            is_complex=True,
            confidence=0.9,
            reasoning="Test reasoning",
            suggested_agents=["LEGAL"],
            estimated_duration=25
        )
        
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.COLLABORATING,
            user_query="Test query",
            complexity_analysis=complexity,
            selected_agents=["LEGAL"],
            consent_given=True,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        self.service.active_sessions["test-session"] = session
        
        status = self.service.get_session_status("test-session")
        
        assert status is not None
        assert status["session_id"] == "test-session"
        assert status["state"] == "collaborating"
        assert status["consent_given"] is True
        assert status["selected_agents"] == ["LEGAL"]
        assert status["complexity_score"] == 0.9
        assert "start_time" in status
    
    def test_get_session_status_nonexistent(self):
        """Test getting status for nonexistent session"""
        status = self.service.get_session_status("nonexistent-session")
        assert status is None


class TestCollaborationServiceErrorHandling:
    """Test error handling scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = VoiceAgentCollaborationService()
        self.voice_session = MockVoiceAgentSession("test-session")
    
    @pytest.mark.asyncio
    async def test_process_user_message_error_handling(self):
        """Test error handling in process_user_message"""
        with patch.object(self.service, '_analyze_query_complexity', side_effect=Exception("Analysis error")):
            result = await self.service.process_user_message(
                session_id="test-session",
                voice_session=self.voice_session,
                user_message="Test message",
                db_session=None,
                owner_id=None
            )
            
            assert result is False  # Should not initiate collaboration on error
    
    @pytest.mark.asyncio
    async def test_request_consent_error_handling(self):
        """Test error handling in request_consent"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.DETECTING_COMPLEXITY,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=None,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        
        # Mock inject_message to raise an exception
        self.voice_session.agent.inject_message.side_effect = Exception("Injection error")
        
        with patch.object(self.service, '_cleanup_session') as mock_cleanup:
            await self.service._request_consent(session)
            
            assert session.state == CollaborationState.FAILED
            mock_cleanup.assert_called_once_with("test-session")
    
    @pytest.mark.asyncio
    async def test_execute_collaboration_error_handling(self):
        """Test error handling in execute_collaboration"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.COLLABORATING,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=True,
            collaboration_response=None,
            start_time=datetime.utcnow()
        )
        
        with patch.object(self.service.agent_manager, 'process_conversation', side_effect=Exception("Collaboration error")), \
             patch.object(self.service, '_cleanup_session') as mock_cleanup:
            
            await self.service._execute_collaboration(session)
            
            assert session.state == CollaborationState.FAILED
            self.voice_session.agent.inject_message.assert_called_once()
            mock_cleanup.assert_called_once_with("test-session")
            
            # Check error message
            error_call = self.voice_session.agent.inject_message.call_args[0][0]
            assert "encountered an issue" in error_call
    
    @pytest.mark.asyncio
    async def test_resume_voice_agent_error_handling(self):
        """Test error handling in resume_voice_agent"""
        session = CollaborationSession(
            session_id="test-session",
            voice_session=self.voice_session,
            state=CollaborationState.RESUMING,
            user_query="Test query",
            complexity_analysis=None,
            selected_agents=["LEGAL"],
            consent_given=True,
            collaboration_response=None,  # Missing response
            start_time=datetime.utcnow()
        )
        
        with patch.object(self.service, '_cleanup_session') as mock_cleanup:
            await self.service._resume_voice_agent(session)
            
            assert session.state == CollaborationState.FAILED
            mock_cleanup.assert_called_once_with("test-session")
    
    @pytest.mark.asyncio
    async def test_detect_consent_openai_error(self):
        """Test consent detection when OpenAI fails"""
        with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("OpenAI error")
            
            result = await self.service._detect_consent("Maybe that would be good")
            
            assert result is None  # Should return None on error


class TestCollaborationServiceConfiguration:
    """Test collaboration service configuration"""
    
    def test_service_initialization(self):
        """Test service initialization with default configuration"""
        service = VoiceAgentCollaborationService()
        
        assert service.complexity_threshold == 0.7
        assert service.consent_timeout == 10
        assert service.collaboration_timeout == 30
        assert len(service.active_sessions) == 0
        assert service.agent_manager is not None
    
    def test_service_singleton(self):
        """Test that service singleton exists"""
        assert voice_agent_collaboration_service is not None
        assert isinstance(voice_agent_collaboration_service, VoiceAgentCollaborationService)


class TestCollaborationStates:
    """Test collaboration state transitions"""
    
    def test_collaboration_states_enum(self):
        """Test collaboration state enum values"""
        states = [
            CollaborationState.IDLE,
            CollaborationState.DETECTING_COMPLEXITY,
            CollaborationState.REQUESTING_CONSENT,
            CollaborationState.AWAITING_CONSENT,
            CollaborationState.COLLABORATING,
            CollaborationState.RESUMING,
            CollaborationState.COMPLETED,
            CollaborationState.FAILED
        ]
        
        expected_values = [
            "idle", "detecting_complexity", "requesting_consent",
            "awaiting_consent", "collaborating", "resuming",
            "completed", "failed"
        ]
        
        for state, expected in zip(states, expected_values):
            assert state.value == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])