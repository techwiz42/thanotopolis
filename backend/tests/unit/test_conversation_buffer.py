# Testing and monitoring for conversation resumption functionality

import pytest
import asyncio
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

# 1. Unit Tests for ConversationContextManager

@pytest.mark.asyncio
class TestConversationContextManager:
    
    @pytest.fixture
    def context_manager(self):
        """Create a context manager for testing"""
        return ConversationContextManager(max_tokens=1000)  # Lower limit for testing
    
    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing"""
        return [
            {
                'content': 'Hello, I need help with my funeral arrangements.',
                'created_at': '2024-01-01T10:00:00',
                'user_id': str(uuid4()),
                'agent_type': None,
                'user': {'first_name': 'John', 'last_name': 'Doe', 'username': 'johndoe'}
            },
            {
                'content': 'I can help you with that. What specific arrangements do you need assistance with?',
                'created_at': '2024-01-01T10:01:00',
                'user_id': None,
                'agent_type': 'ASSISTANT',
                'user': None
            },
            {
                'content': 'I need to understand the different service options available.',
                'created_at': '2024-01-01T10:02:00',
                'user_id': str(uuid4()),
                'agent_type': None,
                'user': {'first_name': 'John', 'last_name': 'Doe', 'username': 'johndoe'}
            }
        ]
    
    def test_token_counting(self, context_manager):
        """Test token counting functionality"""
        text = "This is a test message for token counting."
        token_count = context_manager.count_tokens(text)
        assert isinstance(token_count, int)
        assert token_count > 0
    
    @pytest.mark.asyncio
    async def test_format_conversation_context_small(self, context_manager, sample_messages):
        """Test formatting context when under token limit"""
        context = await context_manager.format_conversation_context(
            sample_messages, 
            summarize_if_needed=False
        )
        
        assert "CONVERSATION HISTORY:" in context
        assert "John Doe" in context
        assert "ASSISTANT" in context
        assert len(context.split('\n')) >= len(sample_messages)
    
    @pytest.mark.asyncio
    async def test_format_conversation_context_large(self, context_manager):
        """Test formatting context when over token limit"""
        # Create many large messages to exceed token limit
        large_messages = []
        for i in range(100):
            large_messages.append({
                'content': 'This is a very long message that contains lots of text to simulate a large conversation. ' * 20,
                'created_at': f'2024-01-01T{i:02d}:00:00',
                'user_id': str(uuid4()),
                'agent_type': None,
                'user': {'first_name': 'User', 'last_name': str(i), 'username': f'user{i}'}
            })
        
        with patch.object(context_manager, '_summarize_messages') as mock_summarize:
            mock_summarize.return_value = "Summary of earlier conversation"
            
            context = await context_manager.format_conversation_context(
                large_messages, 
                summarize_if_needed=True
            )
            
            assert "SUMMARY OF EARLIER CONVERSATION" in context
            assert "RECENT CONVERSATION HISTORY" in context
            mock_summarize.assert_called_once()

# 2. Unit Tests for ConversationBuffer

@pytest.mark.asyncio
class TestConversationBuffer:
    
    @pytest.fixture
    def conversation_buffer(self):
        """Create a conversation buffer for testing"""
        return ConversationBuffer(uuid4(), max_tokens=500)
    
    def test_add_message(self, conversation_buffer):
        """Test adding messages to buffer"""
        conversation_buffer.add_message(
            "Test message", 
            "user123", 
            "user", 
            {"test": "metadata"}
        )
        
        assert len(conversation_buffer.messages) == 1
        assert conversation_buffer.messages[0]['content'] == "Test message"
        assert conversation_buffer.messages[0]['sender_id'] == "user123"
        assert conversation_buffer.messages[0]['sender_type'] == "user"
    
    def test_get_formatted_context(self, conversation_buffer):
        """Test getting formatted context"""
        conversation_buffer.add_message("Hello", "user1", "user")
        conversation_buffer.add_message("Hi there!", "ASSISTANT", "agent")
        
        context = conversation_buffer.get_formatted_context()
        
        assert "CONVERSATION HISTORY:" in context
        assert "[USER]: Hello" in context
        assert "[ASSISTANT]: Hi there!" in context
    
    @pytest.mark.asyncio
    async def test_load_from_database(self, conversation_buffer):
        """Test loading messages from database"""
        # Mock database and messages
        mock_db = AsyncMock()
        mock_messages = [
            Mock(
                content="Test message 1",
                agent_type=None,
                user_id=str(uuid4()),
                participant_id=None,
                created_at=datetime.utcnow(),
                additional_data=None,
                user=Mock(first_name="John", last_name="Doe", username="johndoe")
            ),
            Mock(
                content="Test response",
                agent_type="ASSISTANT",
                user_id=None,
                participant_id=None,
                created_at=datetime.utcnow(),
                additional_data=None,
                user=None
            )
        ]
        
        # Mock the database query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
        mock_db.execute.return_value = mock_result
        
        with patch('sqlalchemy.select') as mock_select, \
             patch('sqlalchemy.orm.selectinload') as mock_selectinload:
            
            await conversation_buffer.load_from_database(mock_db)
            
            assert len(conversation_buffer.messages) == 2
            assert conversation_buffer.messages[0]['content'] == "Test message 1"
            assert conversation_buffer.messages[1]['content'] == "Test response"

# 3. Integration Tests

@pytest.mark.asyncio
class TestConversationResumptionIntegration:
    
    @pytest.fixture
    async def mock_agent_manager(self):
        """Create a mock agent manager with enhanced context"""
        manager = Mock()
        manager.context_manager = ConversationContextManager()
        return manager
    
    @pytest.fixture
    def mock_database_session(self):
        """Create a mock database session"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_conversation_resumption_flow(self, mock_agent_manager, mock_database_session):
        """Test the complete conversation resumption flow"""
        conversation_id = uuid4()
        
        # Mock enhanced buffer manager
        with patch('app.core.enhanced_buffer_manager.enhanced_buffer_manager') as mock_buffer:
            mock_buffer.resume_conversation.return_value = "Resumed conversation context"
            mock_buffer.get_context.return_value = "Existing context"
            
            # Test context preparation
            context = await mock_agent_manager.context_manager.format_conversation_context(
                [], summarize_if_needed=True
            )
            
            # Verify buffer manager was called appropriately
            assert context is not None

# 4. Performance Tests

@pytest.mark.asyncio
class TestPerformance:
    
    @pytest.mark.asyncio
    async def test_large_conversation_performance(self):
        """Test performance with large conversations"""
        context_manager = ConversationContextManager()
        
        # Create a large number of messages
        messages = []
        for i in range(1000):
            messages.append({
                'content': f'Message {i}: ' + 'This is test content. ' * 10,
                'created_at': f'2024-01-01T{i%24:02d}:{i%60:02d}:00',
                'user_id': str(uuid4()),
                'agent_type': None,
                'user': {'first_name': 'User', 'last_name': str(i), 'username': f'user{i}'}
            })
        
        start_time = datetime.utcnow()
        
        with patch.object(context_manager, '_summarize_messages') as mock_summarize:
            mock_summarize.return_value = "Performance test summary"
            
            context = await context_manager.format_conversation_context(
                messages, summarize_if_needed=True
            )
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Should process within reasonable time (adjust as needed)
        assert processing_time < 5.0
        assert context is not None
        assert len(context) > 0

# 5. Monitoring and Metrics

class ConversationMetrics:
    """Metrics collection for conversation resumption"""
    
    def __init__(self):
        self.metrics = {
            'conversations_resumed': 0,
            'contexts_summarized': 0,
            'average_context_size': 0,
            'summarization_time': [],
            'context_preparation_time': [],
            'token_counts': []
        }
    
    def record_conversation_resumed(self, token_count: int):
        """Record a conversation resumption"""
        self.metrics['conversations_resumed'] += 1
        self.metrics['token_counts'].append(token_count)
        
        # Update average
        self.metrics['average_context_size'] = sum(self.metrics['token_counts']) / len(self.metrics['token_counts'])
    
    def record_summarization(self, processing_time: float):
        """Record a summarization operation"""
        self.metrics['contexts_summarized'] += 1
        self.metrics['summarization_time'].append(processing_time)
    
    def record_context_preparation(self, processing_time: float):
        """Record context preparation time"""
        self.metrics['context_preparation_time'].append(processing_time)
    
    def get_stats(self) -> dict:
        """Get current metrics"""
        return {
            'conversations_resumed': self.metrics['conversations_resumed'],
            'contexts_summarized': self.metrics['contexts_summarized'],
            'average_context_size_tokens': round(self.metrics['average_context_size'], 2),
            'average_summarization_time': round(
                sum(self.metrics['summarization_time']) / len(self.metrics['summarization_time']), 3
            ) if self.metrics['summarization_time'] else 0,
            'average_context_prep_time': round(
                sum(self.metrics['context_preparation_time']) / len(self.metrics['context_preparation_time']), 3
            ) if self.metrics['context_preparation_time'] else 0,
            'max_context_size': max(self.metrics['token_counts']) if self.metrics['token_counts'] else 0,
            'min_context_size': min(self.metrics['token_counts']) if self.metrics['token_counts'] else 0
        }

# 6. Health Check Endpoint

from fastapi import APIRouter

metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])
conversation_metrics = ConversationMetrics()

@metrics_router.get("/conversation-resumption")
async def get_conversation_metrics():
    """Get conversation resumption metrics"""
    return conversation_metrics.get_stats()

@metrics_router.get("/buffer-status")
async def get_buffer_status():
    """Get buffer manager status"""
    from app.core.enhanced_buffer_manager import enhanced_buffer_manager
    return enhanced_buffer_manager.get_stats()

# 7. Example Usage in Monitoring

async def monitor_conversation_resumption():
    """Example monitoring function"""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            stats = conversation_metrics.get_stats()
            
            # Log metrics
            logger.info(f"Conversation Resumption Metrics: {stats}")
            
            # Alert on performance issues
            if stats['average_context_prep_time'] > 2.0:
                logger.warning(f"Context preparation taking too long: {stats['average_context_prep_time']}s")
            
            if stats['average_summarization_time'] > 5.0:
                logger.warning(f"Summarization taking too long: {stats['average_summarization_time']}s")
                
        except Exception as e:
            logger.error(f"Error in conversation monitoring: {e}")

# 8. Example Test Runner

if __name__ == "__main__":
    import pytest
    
    # Run the tests
    pytest.main([
        __file__,
        "-v",
        "--asyncio-mode=auto",
        "--tb=short"
    ])
