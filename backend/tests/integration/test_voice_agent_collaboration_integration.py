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

from app.api.telephony_voice_agent import TelephonyVoiceAgentHandler
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
        self.handler = TelephonyVoiceAgentHandler()
        self.collaboration_service = VoiceAgentCollaborationService()
        self.voice_session = MockVoiceAgentSession()
        self.db_session = MockDatabase()
        self.websocket = MockWebSocket()
        
        # Clear any existing sessions
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
                assert "LEGAL, FINANCIAL" in consent_call
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
                assert self.voice_session.agent.update_instructions.called
                instructions_call = self.voice_session.agent.update_instructions.call_args[0][0]
                assert "Please hold while I consult with specialists" in instructions_call
                
                # Step 3: Wait for collaboration to complete
                await asyncio.sleep(0.1)  # Allow async tasks to complete
                
                # Verify collaboration completed and Voice Agent resumed
                assert session.state == CollaborationState.COMPLETED
                assert session.collaboration_response == "Based on expert analysis, here's comprehensive advice..."
                
                # Verify final response was injected
                final_calls = self.voice_session.agent.inject_message.call_args_list
                final_response = final_calls[-1][0][0]
                assert "expert consultation" in final_response
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
                mock_client.chat.completions.create = AsyncMock(return_value=complexity_response)
                
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
                
                # Verify session was cleaned up
                assert "test-session" not in self.collaboration_service.active_sessions
    
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
        """Test integration with telephony handler"""
        
        # Mock telephony configuration and call setup
        mock_config = Mock()
        mock_config.tenant_id = uuid4()
        mock_config.voice_id = "aura-2-thalia-en"
        mock_config.custom_prompt = None
        
        mock_phone_call = Mock()
        mock_phone_call.id = str(uuid4())
        mock_phone_call.customer_phone_number = "+1234567890"
        
        mock_conversation = Mock()
        mock_conversation.id = uuid4()
        
        # Set up session info
        session_id = "telephony-test-session"
        session_info = {
            "stream_sid": session_id,
            "call_sid": "test-call-sid",
            "phone_call": mock_phone_call,
            "conversation": mock_conversation,
            "config": mock_config,
            "from_number": "+1234567890",
            "to_number": "+0987654321",
            "start_time": datetime.utcnow(),
            "pending_messages": []
        }
        
        self.handler.call_sessions[session_id] = session_info
        
        # Mock voice session creation
        with patch.object(self.handler, '_create_voice_agent_session') as mock_create_session:
            mock_create_session.return_value = self.voice_session
            
            # Mock collaboration service
            with patch('app.api.telephony_voice_agent.voice_agent_collaboration_service') as mock_collab_service:
                mock_collab_service.process_user_message = AsyncMock(return_value=True)
                
                # Set up event handlers
                self.handler._setup_event_handlers(
                    self.voice_session,
                    session_id,
                    self.websocket,
                    self.db_session
                )
                
                # Simulate user speech that triggers collaboration
                await self.voice_session.simulate_user_speech(
                    "I need help with complex legal and financial planning",
                    role="user"
                )
                
                # Verify collaboration was triggered
                mock_collab_service.process_user_message.assert_called_once()
                call_args = mock_collab_service.process_user_message.call_args
                
                assert call_args[1]['session_id'] == session_id
                assert call_args[1]['voice_session'] == self.voice_session
                assert call_args[1]['user_message'] == "I need help with complex legal and financial planning"
                assert call_args[1]['db_session'] == self.db_session
    
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
        """Test that collaboration sessions are cleaned up when calls end"""
        
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
                
                assert "cleanup-test" in self.collaboration_service.active_sessions
                
                # Mock call session with proper phone call Mock
                mock_phone_call = Mock()
                mock_phone_call.start_time = datetime.utcnow()
                mock_phone_call.duration_seconds = 120
                
                self.handler.call_sessions["cleanup-test"] = {
                    "phone_call": mock_phone_call,
                    "conversation": Mock(),
                    "config": Mock(tenant_id=uuid4()),
                    "call_sid": "test-call-sid",
                    "pending_messages": []
                }
                
                # Patch the voice_agent_collaboration_service
                with patch('app.api.telephony_voice_agent.voice_agent_collaboration_service') as mock_collab_service:
                    mock_collab_service._cleanup_session = AsyncMock()
                    
                    # Trigger cleanup
                    await self.handler._cleanup_session("cleanup-test", self.db_session)
                    
                    # Verify collaboration cleanup was called
                    mock_collab_service._cleanup_session.assert_called_once_with("cleanup-test")


class TestTelephonyIntegrationErrorHandling:
    """Test error handling in telephony integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = TelephonyVoiceAgentHandler()
        self.voice_session = MockVoiceAgentSession()
        self.db_session = MockDatabase()
        self.websocket = MockWebSocket()
    
    @pytest.mark.asyncio
    async def test_collaboration_service_unavailable(self):
        """Test handling when collaboration service is unavailable"""
        
        session_id = "error-test-session"
        session_info = {
            "phone_call": Mock(),
            "conversation": Mock(),
            "config": Mock(),
            "from_number": "+1234567890",
            "to_number": "+0987654321",
            "call_sid": "test-call-sid",
            "pending_messages": []
        }
        self.handler.call_sessions[session_id] = session_info
        
        # Mock collaboration service failure
        with patch('app.api.telephony_voice_agent.voice_agent_collaboration_service') as mock_collab_service:
            mock_collab_service.process_user_message = AsyncMock(
                side_effect=Exception("Collaboration service error")
            )
            
            # Set up event handlers
            self.handler._setup_event_handlers(
                self.voice_session,
                session_id,
                self.websocket,
                self.db_session
            )
            
            # Simulate user speech
            await self.voice_session.simulate_user_speech(
                "Complex query that should trigger collaboration",
                role="user"
            )
            
            # Verify that error was handled gracefully
            # The conversation should continue normally even if collaboration fails
            assert len(session_info["pending_messages"]) > 0  # Message was still processed
    
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