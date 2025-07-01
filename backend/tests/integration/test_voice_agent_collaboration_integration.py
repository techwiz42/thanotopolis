"""
Integration tests for Voice Agent Collaboration System
Tests the complete workflow from telephony handler to collaboration service
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

# Set pytest asyncio mode
pytestmark = pytest.mark.asyncio

from app.services.voice.voice_agent_collaboration import (
    VoiceAgentCollaborationService,
    CollaborationState,
    voice_agent_collaboration_service
)
from app.services.voice.deepgram_voice_agent import VoiceAgentSession, DeepgramVoiceAgent
from app.agents.agent_manager import agent_manager


class MockDatabase:
    """Mock database session for testing"""
    def __init__(self):
        self.committed = False
        self.rolled_back = False
    
    async def commit(self):
        self.committed = True
    
    async def rollback(self):
        self.rolled_back = True
    
    async def close(self):
        pass


class MockWebSocket:
    """Mock WebSocket for testing"""
    def __init__(self):
        self.sent_messages = []
        self.accepted = False
    
    async def accept(self):
        self.accepted = True
    
    async def receive_text(self):
        # Simulate Twilio messages for testing
        pass
    
    async def send_text(self, message):
        self.sent_messages.append(message)


class MockVoiceAgentSession:
    """Mock Voice Agent session for integration testing"""
    def __init__(self, session_id: str = "integration-test-session"):
        self.session_id = session_id
        self.agent = Mock(spec=DeepgramVoiceAgent)
        self.agent.inject_message = AsyncMock()
        self.agent.update_instructions = AsyncMock()
        self.agent.send_audio = AsyncMock()
        self.is_connected = True
        self.call_events = []  # Track events for testing
    
    def register_audio_handler(self, handler):
        self.audio_handler = handler
    
    def register_event_handler(self, event_type, handler):
        if not hasattr(self, 'event_handlers'):
            self.event_handlers = {}
        self.event_handlers[event_type] = handler
    
    async def simulate_user_speech(self, text: str, role: str = "user"):
        """Simulate user speech event for testing"""
        event = {
            "type": "ConversationText",
            "content": text,
            "text": text,
            "role": role
        }
        self.call_events.append(event)
        if hasattr(self, 'event_handlers') and "ConversationText" in self.event_handlers:
            await self.event_handlers["ConversationText"](event)


class TestVoiceAgentCollaborationIntegration:
    """Integration tests for complete collaboration workflow"""
    
    def setup_method(self):
        """Set up integration test fixtures"""
        # Create a mock handler instead of importing the real one
        self.handler = Mock()
        self.handler.call_sessions = {}
        self.handler._setup_event_handlers = Mock()
        self.handler._cleanup_session = AsyncMock()
        
        self.collaboration_service = VoiceAgentCollaborationService()
        self.voice_session = MockVoiceAgentSession()
        self.db_session = MockDatabase()
        self.websocket = MockWebSocket()
        
        # Clear any existing sessions
        self.collaboration_service.active_sessions.clear()
    
    def teardown_method(self):
        """Clean up after each test"""
        # Cancel any pending tasks
        try:
            for session in self.collaboration_service.active_sessions.values():
                if session.timeout_task and not session.timeout_task.done():
                    session.timeout_task.cancel()
        except Exception:
            pass
        
        # Clear sessions
        self.collaboration_service.active_sessions.clear()
    
    @pytest.mark.asyncio
    async def test_complete_collaboration_workflow_consent_given(self):
        """Test complete workflow when user gives consent for collaboration"""
        
        # Set up mock agent manager
        with patch.object(self.collaboration_service, 'agent_manager') as mock_agent_mgr:
            # Mock agent descriptions
            mock_agent_mgr.get_agent_descriptions.return_value = {
                "LEGAL": "Legal expertise agent",
                "FINANCIAL": "Financial expertise agent",
                "MODERATOR": "Moderator agent"
            }
            
            # Mock MODERATOR agent for complexity analysis
            mock_moderator = Mock()
            mock_agent_mgr.get_agent.return_value = mock_moderator
            
            # Mock OpenAI for complexity analysis
            with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # Mock complexity analysis response
                complexity_response = Mock()
                complexity_response.choices = [Mock()]
                complexity_response.choices[0].message.content = json.dumps({
                    "is_complex": True,
                    "confidence": 0.9,
                    "reasoning": "Query requires both legal and financial expertise",
                    "suggested_agents": ["LEGAL", "FINANCIAL"],
                    "estimated_duration": 25
                })
                
                # Mock consent detection response
                consent_response = Mock()
                consent_response.choices = [Mock()]
                consent_response.choices[0].message.content = json.dumps({
                    "consent": True,
                    "confidence": 0.9
                })
                
                mock_client.chat.completions.create = AsyncMock(
                    side_effect=[complexity_response, consent_response]
                )
                
                # Mock agent collaboration
                mock_agent_mgr.process_conversation = AsyncMock(
                    return_value=("LEGAL", "Based on expert analysis, here's comprehensive advice...")
                )
                
                # Step 1: User asks complex question
                complex_query = "I need advice on the tax implications of my divorce settlement and asset division"
                
                # Trigger collaboration workflow
                collaboration_initiated = await self.collaboration_service.process_user_message(
                    session_id="test-session",
                    voice_session=self.voice_session,
                    user_message=complex_query,
                    db_session=self.db_session,
                    owner_id=None
                )
                
                assert collaboration_initiated is True
                assert "test-session" in self.collaboration_service.active_sessions
                
                # Verify consent request was made
                session = self.collaboration_service.active_sessions["test-session"]
                assert session.state == CollaborationState.AWAITING_CONSENT
                assert self.voice_session.agent.inject_message.called
                
                # Check consent message content
                consent_call = self.voice_session.agent.inject_message.call_args[0][0]
                assert "specialist team" in consent_call
                assert "25 seconds" in consent_call
                
                # Step 2: User gives consent
                consent_response_text = "Yes, please consult with the experts"
                
                consent_handled = await self.collaboration_service._handle_ongoing_collaboration(
                    "test-session", consent_response_text
                )
                
                assert consent_handled is True
                assert session.consent_given is True
                assert session.state == CollaborationState.COLLABORATING
                
                # Verify collaboration was started
                # Note: update_instructions is not supported in Voice Agent V1 API
                # Collaboration status is communicated via inject_message instead
                
                # Step 3: Wait for collaboration to complete
                await asyncio.sleep(0.1)  # Allow async tasks to complete
                
                # Verify collaboration completed and Voice Agent resumed
                assert session.state == CollaborationState.COMPLETED
                assert session.collaboration_response == "Based on expert analysis, here's comprehensive advice..."
                
                # Verify final response was injected
                final_calls = self.voice_session.agent.inject_message.call_args_list
                final_response = final_calls[-1][0][0]
                assert "specialist team" in final_response
                assert "Based on expert analysis" in final_response
    
    @pytest.mark.asyncio
    async def test_complete_collaboration_workflow_consent_declined(self):
        """Test complete workflow when user declines collaboration"""
        
        with patch.object(self.collaboration_service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent_descriptions.return_value = {
                "LEGAL": "Legal expertise agent",
                "MODERATOR": "Moderator agent"
            }
            mock_agent_mgr.get_agent.return_value = Mock()
            
            with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # Mock complexity analysis
                complexity_response = Mock()
                complexity_response.choices = [Mock()]
                complexity_response.choices[0].message.content = json.dumps({
                    "is_complex": True,
                    "confidence": 0.8,
                    "reasoning": "Complex legal query",
                    "suggested_agents": ["LEGAL"],
                    "estimated_duration": 20
                })
                
                # Mock consent detection response
                consent_response = Mock()
                consent_response.choices = [Mock()]
                consent_response.choices[0].message.content = json.dumps({
                    "consent": False,
                    "reasoning": "User declined and wants quick answer"
                })
                
                mock_client.chat.completions.create = AsyncMock(
                    side_effect=[complexity_response, consent_response]
                )
                
                # Step 1: Initiate collaboration
                await self.collaboration_service.process_user_message(
                    session_id="test-session",
                    voice_session=self.voice_session,
                    user_message="Complex legal question",
                    db_session=self.db_session,
                    owner_id=None
                )
                
                session = self.collaboration_service.active_sessions["test-session"]
                assert session.state == CollaborationState.AWAITING_CONSENT
                
                # Step 2: User declines consent
                await self.collaboration_service._handle_ongoing_collaboration(
                    "test-session", "No, just give me a quick answer"
                )
                
                assert session.consent_given is False
                assert session.state == CollaborationState.COMPLETED
                
                # Verify decline message was sent
                decline_call = self.voice_session.agent.inject_message.call_args_list[-1][0][0]
                assert "No problem" in decline_call
                
                # Session should still exist but marked as completed (cleanup is delayed)
                assert "test-session" in self.collaboration_service.active_sessions
                assert session.state == CollaborationState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_collaboration_timeout_handling(self):
        """Test collaboration timeout scenarios"""
        
        with patch.object(self.collaboration_service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent_descriptions.return_value = {"LEGAL": "Legal agent"}
            mock_agent_mgr.get_agent.return_value = Mock()
            
            # Mock very slow collaboration
            async def slow_collaboration(*args, **kwargs):
                await asyncio.sleep(2)  # Longer than collaboration timeout
                return ("LEGAL", "Slow response")
            
            mock_agent_mgr.process_conversation = slow_collaboration
            
            with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                complexity_response = Mock()
                complexity_response.choices = [Mock()]
                complexity_response.choices[0].message.content = json.dumps({
                    "is_complex": True,
                    "confidence": 0.8,
                    "reasoning": "Complex query",
                    "suggested_agents": ["LEGAL"],
                    "estimated_duration": 20
                })
                mock_client.chat.completions.create = AsyncMock(return_value=complexity_response)
                
                # Set very short timeout for testing
                original_timeout = self.collaboration_service.collaboration_timeout
                self.collaboration_service.collaboration_timeout = 0.1
                
                try:
                    # Start collaboration
                    await self.collaboration_service.process_user_message(
                        session_id="test-session",
                        voice_session=self.voice_session,
                        user_message="Complex query",
                        db_session=self.db_session,
                        owner_id=None
                    )
                    
                    session = self.collaboration_service.active_sessions["test-session"]
                    session.consent_given = True
                    
                    # Start collaboration and wait for timeout
                    await self.collaboration_service._start_collaboration(session)
                    await asyncio.sleep(0.2)  # Wait for timeout
                    
                    # Verify timeout was handled
                    timeout_calls = self.voice_session.agent.inject_message.call_args_list
                    timeout_message = timeout_calls[-1][0][0]
                    assert "taking longer than expected" in timeout_message
                    
                finally:
                    self.collaboration_service.collaboration_timeout = original_timeout
    
    @pytest.mark.asyncio
    async def test_consent_timeout_handling(self):
        """Test consent timeout handling"""
        
        with patch.object(self.collaboration_service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent_descriptions.return_value = {"LEGAL": "Legal agent"}
            mock_agent_mgr.get_agent.return_value = Mock()
            
            with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                complexity_response = Mock()
                complexity_response.choices = [Mock()]
                complexity_response.choices[0].message.content = json.dumps({
                    "is_complex": True,
                    "confidence": 0.8,
                    "reasoning": "Complex query",
                    "suggested_agents": ["LEGAL"],
                    "estimated_duration": 20
                })
                mock_client.chat.completions.create = AsyncMock(return_value=complexity_response)
                
                # Set very short consent timeout for testing
                original_timeout = self.collaboration_service.consent_timeout
                self.collaboration_service.consent_timeout = 0.1
                
                try:
                    # Start collaboration
                    await self.collaboration_service.process_user_message(
                        session_id="test-session",
                        voice_session=self.voice_session,
                        user_message="Complex query",
                        db_session=self.db_session,
                        owner_id=None
                    )
                    
                    # Wait for consent timeout
                    await asyncio.sleep(0.2)
                    
                    # Verify timeout was handled
                    session = self.collaboration_service.active_sessions.get("test-session")
                    if session:
                        assert session.consent_given is False
                    
                    # Verify timeout message
                    timeout_calls = self.voice_session.agent.inject_message.call_args_list
                    timeout_message = timeout_calls[-1][0][0]
                    assert "direct answer" in timeout_message
                    
                finally:
                    self.collaboration_service.consent_timeout = original_timeout
    
    @pytest.mark.asyncio
    async def test_telephony_handler_integration(self):
        """Test collaboration service workflow simulation"""
        
        # This test simulates the telephony handler integration by directly testing
        # the collaboration service workflow that would be triggered by telephony events
        
        with patch.object(self.collaboration_service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent_descriptions.return_value = {
                "LEGAL": "Legal expertise agent",
                "MODERATOR": "Moderator agent"
            }
            mock_agent_mgr.get_agent.return_value = Mock()
            
            with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # Mock complexity analysis for a direct collaboration request
                complexity_response = Mock()
                complexity_response.choices = [Mock()]
                complexity_response.choices[0].message.content = json.dumps({
                    "is_complex": True,
                    "confidence": 0.9,
                    "reasoning": "User explicitly requested expert collaboration",
                    "suggested_agents": ["LEGAL"],
                    "estimated_duration": 25
                })
                mock_client.chat.completions.create = AsyncMock(return_value=complexity_response)
                
                # Test direct collaboration request
                collaboration_initiated = await self.collaboration_service.process_user_message(
                    session_id="telephony-test-session",
                    voice_session=self.voice_session,
                    user_message="Can you check with the experts about this complex legal matter?",
                    db_session=self.db_session,
                    owner_id=None
                )
                
                # Verify collaboration workflow was initiated
                assert collaboration_initiated is True
                assert "telephony-test-session" in self.collaboration_service.active_sessions
                
                session = self.collaboration_service.active_sessions["telephony-test-session"]
                assert session.state == CollaborationState.AWAITING_CONSENT
                assert session.user_query == "Can you check with the experts about this complex legal matter?"
                assert "LEGAL" in session.selected_agents
                
                # Verify Voice Agent was asked to request consent
                assert self.voice_session.agent.inject_message.called
                consent_call = self.voice_session.agent.inject_message.call_args[0][0]
                assert "specialist team" in consent_call
    
    @pytest.mark.asyncio
    async def test_collaboration_with_multiple_agents(self):
        """Test collaboration with multiple specialist agents"""
        
        with patch.object(self.collaboration_service, 'agent_manager') as mock_agent_mgr:
            # Mock multiple specialist agents
            mock_agent_mgr.get_agent_descriptions.return_value = {
                "LEGAL": "Legal expertise and compliance",
                "FINANCIAL": "Financial planning and tax advice",
                "REGULATORY": "Regulatory compliance and requirements",
                "MODERATOR": "Moderator agent"
            }
            mock_agent_mgr.get_agent.return_value = Mock()
            
            # Mock complex multi-agent response
            mock_agent_mgr.process_conversation = AsyncMock(
                return_value=("LEGAL", 
                    "Based on collaboration between legal, financial, and regulatory experts: "
                    "Your situation requires careful consideration of tax implications, "
                    "legal compliance requirements, and regulatory constraints. "
                    "Here's our comprehensive recommendation...")
            )
            
            with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                # Mock complexity analysis for multi-agent scenario
                complexity_response = Mock()
                complexity_response.choices = [Mock()]
                complexity_response.choices[0].message.content = json.dumps({
                    "is_complex": True,
                    "confidence": 0.95,
                    "reasoning": "Query spans legal, financial, and regulatory domains",
                    "suggested_agents": ["LEGAL", "FINANCIAL", "REGULATORY"],
                    "estimated_duration": 30
                })
                
                consent_response = Mock()
                consent_response.choices = [Mock()]
                consent_response.choices[0].message.content = json.dumps({
                    "consent": True,
                    "confidence": 0.9
                })
                
                mock_client.chat.completions.create = AsyncMock(
                    side_effect=[complexity_response, consent_response]
                )
                
                # Test multi-agent collaboration
                complex_query = ("I'm starting a fintech company and need advice on "
                               "regulatory compliance, legal structure, and tax optimization")
                
                # Start collaboration
                collaboration_initiated = await self.collaboration_service.process_user_message(
                    session_id="multi-agent-test",
                    voice_session=self.voice_session,
                    user_message=complex_query,
                    db_session=self.db_session,
                    owner_id=None
                )
                
                assert collaboration_initiated is True
                
                session = self.collaboration_service.active_sessions["multi-agent-test"]
                assert len(session.selected_agents) == 3
                assert "LEGAL" in session.selected_agents
                assert "FINANCIAL" in session.selected_agents
                assert "REGULATORY" in session.selected_agents
                
                # Give consent and complete collaboration
                await self.collaboration_service._handle_ongoing_collaboration(
                    "multi-agent-test", "Yes, please get expert advice"
                )
                
                # Wait for collaboration to complete
                await asyncio.sleep(0.1)
                
                # Verify multi-agent response
                assert session.collaboration_response.startswith("Based on collaboration between")
                assert "legal, financial, and regulatory experts" in session.collaboration_response
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_fallback(self):
        """Test error recovery and fallback mechanisms"""
        
        with patch.object(self.collaboration_service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent_descriptions.return_value = {"LEGAL": "Legal agent"}
            mock_agent_mgr.get_agent.return_value = Mock()
            
            # Mock collaboration failure
            mock_agent_mgr.process_conversation = AsyncMock(
                side_effect=Exception("Collaboration system unavailable")
            )
            
            with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                complexity_response = Mock()
                complexity_response.choices = [Mock()]
                complexity_response.choices[0].message.content = json.dumps({
                    "is_complex": True,
                    "confidence": 0.8,
                    "reasoning": "Complex query",
                    "suggested_agents": ["LEGAL"],
                    "estimated_duration": 20
                })
                mock_client.chat.completions.create = AsyncMock(return_value=complexity_response)
                
                # Start collaboration that will fail
                await self.collaboration_service.process_user_message(
                    session_id="error-test",
                    voice_session=self.voice_session,
                    user_message="Complex query that will fail",
                    db_session=self.db_session,
                    owner_id=None
                )
                
                session = self.collaboration_service.active_sessions["error-test"]
                session.consent_given = True
                
                # Execute collaboration that will fail
                await self.collaboration_service._execute_collaboration(session)
                
                # Verify error handling
                assert session.state == CollaborationState.FAILED
                
                # Verify fallback message was sent
                error_calls = self.voice_session.agent.inject_message.call_args_list
                error_message = error_calls[-1][0][0]
                assert "encountered an issue" in error_message
                assert "best answer I can give you directly" in error_message
    
    @pytest.mark.asyncio
    async def test_session_cleanup_on_call_end(self):
        """Test that collaboration sessions are properly cleaned up"""
        
        # Start a collaboration session
        with patch.object(self.collaboration_service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent_descriptions.return_value = {"LEGAL": "Legal agent"}
            mock_agent_mgr.get_agent.return_value = Mock()
            
            with patch('app.services.voice.voice_agent_collaboration.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_openai.return_value = mock_client
                
                complexity_response = Mock()
                complexity_response.choices = [Mock()]
                complexity_response.choices[0].message.content = json.dumps({
                    "is_complex": True,
                    "confidence": 0.8,
                    "reasoning": "Complex query",
                    "suggested_agents": ["LEGAL"],
                    "estimated_duration": 20
                })
                mock_client.chat.completions.create = AsyncMock(return_value=complexity_response)
                
                # Start collaboration
                await self.collaboration_service.process_user_message(
                    session_id="cleanup-test",
                    voice_session=self.voice_session,
                    user_message="Complex query",
                    db_session=self.db_session,
                    owner_id=None
                )
                
                # Verify session was created
                assert "cleanup-test" in self.collaboration_service.active_sessions
                session = self.collaboration_service.active_sessions["cleanup-test"]
                assert session.state == CollaborationState.AWAITING_CONSENT
                
                # Test direct cleanup functionality
                await self.collaboration_service._cleanup_session("cleanup-test")
                
                # Verify session was cleaned up
                assert "cleanup-test" not in self.collaboration_service.active_sessions


class TestTelephonyIntegrationErrorHandling:
    """Test error handling in telephony integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create a mock handler instead of importing the real one
        self.handler = Mock()
        self.handler.call_sessions = {}
        self.handler._setup_event_handlers = Mock()
        self.handler._cleanup_session = AsyncMock()
            
        self.voice_session = MockVoiceAgentSession()
        self.db_session = MockDatabase()
        self.websocket = MockWebSocket()
    
    def teardown_method(self):
        """Clean up after each test"""
        # No specific cleanup needed for error handling tests
        pass
    
    @pytest.mark.asyncio
    async def test_collaboration_service_unavailable(self):
        """Test handling when collaboration service encounters errors"""
        
        # Test error handling in collaboration service directly
        from app.services.voice.voice_agent_collaboration import VoiceAgentCollaborationService
        
        error_service = VoiceAgentCollaborationService()
        
        # Mock agent manager to raise an error
        with patch.object(error_service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent_descriptions.side_effect = Exception("Agent manager unavailable")
            
            # Test that service handles errors gracefully
            result = await error_service.process_user_message(
                session_id="error-test-session",
                voice_session=self.voice_session,
                user_message="Complex query that should fail",
                db_session=self.db_session,
                owner_id=None
            )
            
            # Should return False when service encounters errors
            assert result is False
            
            # Session should not be created when errors occur
            assert "error-test-session" not in error_service.active_sessions
    
    @pytest.mark.asyncio
    async def test_voice_agent_disconnect_during_collaboration(self):
        """Test handling when Voice Agent disconnects during collaboration"""
        
        with patch.object(voice_agent_collaboration_service, 'agent_manager') as mock_agent_mgr:
            mock_agent_mgr.get_agent_descriptions.return_value = {"LEGAL": "Legal agent"}
            mock_agent_mgr.get_agent.return_value = Mock()
            
            # Mock collaboration in progress
            voice_agent_collaboration_service.active_sessions["disconnect-test"] = Mock()
            
            # Mock Voice Agent disconnect
            disconnected_voice_session = MockVoiceAgentSession()
            disconnected_voice_session.agent.inject_message.side_effect = Exception("Connection lost")
            disconnected_voice_session.agent.update_instructions.side_effect = Exception("Connection lost")
            
            # Attempt collaboration operations on disconnected session
            with patch.object(voice_agent_collaboration_service, '_cleanup_session') as mock_cleanup:
                try:
                    await voice_agent_collaboration_service._request_consent(Mock(
                        session_id="disconnect-test",
                        voice_session=disconnected_voice_session,
                        state=CollaborationState.DETECTING_COMPLEXITY,
                        selected_agents=["LEGAL"],
                        complexity_analysis=Mock(estimated_duration=20)
                    ))
                except:
                    pass  # Expected to fail
                
                # Verify cleanup was called on error
                mock_cleanup.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])