"""
Test fixtures for Voice Agent Collaboration testing
Provides reusable mock objects and test data
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.services.voice.voice_agent_collaboration import (
    ComplexityAnalysis,
    CollaborationSession,
    CollaborationState
)


@pytest.fixture
def mock_voice_agent():
    """Mock Deepgram Voice Agent"""
    agent = Mock()
    agent.inject_message = AsyncMock()
    agent.update_instructions = AsyncMock()
    agent.send_audio = AsyncMock()
    return agent


@pytest.fixture
def mock_voice_session(mock_voice_agent):
    """Mock Voice Agent Session"""
    session = Mock()
    session.session_id = "test-session-123"
    session.agent = mock_voice_agent
    session.register_audio_handler = Mock()
    session.register_event_handler = Mock()
    return session


@pytest.fixture
def sample_complexity_analysis():
    """Sample complexity analysis for testing"""
    return ComplexityAnalysis(
        is_complex=True,
        confidence=0.85,
        reasoning="Query requires specialized legal and financial expertise",
        suggested_agents=["LEGAL", "FINANCIAL"],
        estimated_duration=25
    )


@pytest.fixture
def simple_complexity_analysis():
    """Simple query complexity analysis for testing"""
    return ComplexityAnalysis(
        is_complex=False,
        confidence=0.3,
        reasoning="Simple query can be handled by basic assistant",
        suggested_agents=[],
        estimated_duration=15
    )


@pytest.fixture
def collaboration_session(mock_voice_session, sample_complexity_analysis):
    """Sample collaboration session for testing"""
    return CollaborationSession(
        session_id="test-session-123",
        voice_session=mock_voice_session,
        state=CollaborationState.IDLE,
        user_query="I need help with complex legal and financial matters",
        complexity_analysis=sample_complexity_analysis,
        selected_agents=["LEGAL", "FINANCIAL"],
        consent_given=None,
        collaboration_response=None,
        start_time=datetime.utcnow()
    )


@pytest.fixture
def awaiting_consent_session(collaboration_session):
    """Collaboration session awaiting user consent"""
    collaboration_session.state = CollaborationState.AWAITING_CONSENT
    return collaboration_session


@pytest.fixture
def collaborating_session(collaboration_session):
    """Collaboration session in collaborating state"""
    collaboration_session.state = CollaborationState.COLLABORATING
    collaboration_session.consent_given = True
    return collaboration_session


@pytest.fixture
def completed_session(collaboration_session):
    """Completed collaboration session"""
    collaboration_session.state = CollaborationState.COMPLETED
    collaboration_session.consent_given = True
    collaboration_session.collaboration_response = "Expert consultation complete"
    return collaboration_session


@pytest.fixture
def mock_database():
    """Mock database session"""
    db = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for telephony testing"""
    ws = Mock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.sent_messages = []
    
    async def track_sent_messages(message):
        ws.sent_messages.append(message)
    
    ws.send_text.side_effect = track_sent_messages
    return ws


@pytest.fixture
def telephony_session_info(mock_database):
    """Mock telephony session info"""
    mock_config = Mock()
    mock_config.tenant_id = uuid4()
    mock_config.voice_id = "aura-2-thalia-en"
    mock_config.custom_prompt = None
    
    mock_phone_call = Mock()
    mock_phone_call.id = str(uuid4())
    mock_phone_call.customer_phone_number = "+1234567890"
    
    mock_conversation = Mock()
    mock_conversation.id = uuid4()
    
    return {
        "stream_sid": "test-stream-123",
        "call_sid": "test-call-456",
        "phone_call": mock_phone_call,
        "conversation": mock_conversation,
        "config": mock_config,
        "from_number": "+1234567890",
        "to_number": "+0987654321",
        "start_time": datetime.utcnow(),
        "pending_messages": []
    }


@pytest.fixture
def mock_agent_manager():
    """Mock agent manager with common setup"""
    manager = Mock()
    manager.get_agent_descriptions.return_value = {
        "LEGAL": "Legal expertise and compliance agent",
        "FINANCIAL": "Financial planning and tax advice agent",
        "REGULATORY": "Regulatory compliance and requirements agent",
        "CULTURAL_ARMENIAN": "Armenian cultural and language support",
        "GRIEF_SUPPORT": "Grief counseling and support services",
        "MODERATOR": "Query routing and agent coordination"
    }
    
    # Mock MODERATOR agent
    mock_moderator = Mock()
    manager.get_agent.return_value = mock_moderator
    
    # Mock successful collaboration
    manager.process_conversation = AsyncMock(
        return_value=("LEGAL", "Based on expert analysis, here's comprehensive advice...")
    )
    
    return manager


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for LLM operations"""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def complex_query_samples():
    """Sample complex queries for testing"""
    return [
        "I need advice on the tax implications of my divorce settlement and asset division",
        "What are the regulatory requirements for starting a fintech company in multiple states?",
        "Help me understand the legal and financial aspects of international business expansion",
        "I'm dealing with grief after losing a spouse and need help with financial planning",
        "What are the compliance requirements for healthcare data privacy across different jurisdictions?"
    ]


@pytest.fixture
def simple_query_samples():
    """Sample simple queries for testing"""
    return [
        "What time is it?",
        "What's the weather like today?",
        "Can you tell me a joke?",
        "How do I reset my password?",
        "What are your office hours?"
    ]


@pytest.fixture
def consent_responses():
    """Sample consent responses for testing"""
    return {
        "positive": [
            "Yes, please consult with the experts",
            "Yeah, go ahead and check with them",
            "Sure, I'd like expert advice",
            "Okay, please get specialist input",
            "Yes, that would be helpful"
        ],
        "negative": [
            "No, just give me a quick answer",
            "No thanks, I need a fast response",
            "Skip it, I'm in a hurry",
            "Not now, just answer directly",
            "No, keep it simple"
        ],
        "ambiguous": [
            "I'm not sure",
            "What do you think?",
            "Maybe that would be good",
            "Um, I don't know",
            "What does that involve?"
        ]
    }


@pytest.fixture
def collaboration_timeout_config():
    """Configuration for testing timeouts"""
    return {
        "complexity_threshold": 0.7,
        "consent_timeout": 0.1,  # Very short for testing
        "collaboration_timeout": 0.2  # Very short for testing
    }


class ConversationEventBuilder:
    """Builder for creating conversation events for testing"""
    
    @staticmethod
    def user_speech(text: str, role: str = "user"):
        """Create user speech event"""
        return {
            "type": "ConversationText",
            "content": text,
            "text": text,
            "role": role
        }
    
    @staticmethod
    def agent_speech(text: str, role: str = "assistant"):
        """Create agent speech event"""
        return {
            "type": "ConversationText",
            "content": text,
            "text": text,
            "role": role
        }
    
    @staticmethod
    def user_started_speaking():
        """Create user started speaking event"""
        return {
            "type": "UserStartedSpeaking"
        }
    
    @staticmethod
    def agent_started_speaking():
        """Create agent started speaking event"""
        return {
            "type": "AgentStartedSpeaking"
        }


@pytest.fixture
def conversation_event_builder():
    """Conversation event builder fixture"""
    return ConversationEventBuilder


class CollaborationTestHelper:
    """Helper class for collaboration testing scenarios"""
    
    @staticmethod
    async def simulate_complete_workflow(
        collaboration_service,
        voice_session,
        user_query,
        consent_response,
        mock_agent_manager,
        mock_openai_client,
        collaboration_response="Expert advice provided"
    ):
        """Simulate complete collaboration workflow"""
        
        # Set up mocks
        mock_openai_client.chat.completions.create.return_value.choices = [Mock()]
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = """
        {
            "is_complex": true,
            "confidence": 0.9,
            "reasoning": "Complex multi-domain query",
            "suggested_agents": ["LEGAL", "FINANCIAL"],
            "estimated_duration": 25
        }
        """
        
        mock_agent_manager.process_conversation.return_value = ("LEGAL", collaboration_response)
        
        # Step 1: Process user message
        collaboration_initiated = await collaboration_service.process_user_message(
            session_id="test-workflow",
            voice_session=voice_session,
            user_message=user_query,
            db_session=None,
            owner_id=None
        )
        
        # Step 2: Handle consent
        if collaboration_initiated:
            await collaboration_service._handle_ongoing_collaboration(
                "test-workflow", consent_response
            )
        
        return collaboration_initiated, collaboration_service.active_sessions.get("test-workflow")


@pytest.fixture
def collaboration_test_helper():
    """Collaboration test helper fixture"""
    return CollaborationTestHelper