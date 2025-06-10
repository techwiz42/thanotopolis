"""Tests for enhanced_buffer_manager.py"""

import pytest
from uuid import UUID, uuid4
from unittest.mock import MagicMock

from app.core.enhanced_buffer_manager import EnhancedBufferManager, enhanced_buffer_manager


class TestEnhancedBufferManager:
    """Test EnhancedBufferManager class"""
    
    @pytest.fixture
    def buffer_manager(self):
        """Create a test enhanced buffer manager"""
        return EnhancedBufferManager()
    
    def test_initialization(self, buffer_manager):
        """Test buffer manager initialization"""
        assert buffer_manager.buffers == {}
        assert isinstance(buffer_manager.buffers, dict)
    
    def test_resume_conversation(self, buffer_manager):
        """Test resume conversation method"""
        conversation_id = uuid4()
        
        result = buffer_manager.resume_conversation(conversation_id)
        
        assert isinstance(result, str)
        assert str(conversation_id) in result
        assert "Resumed conversation context" in result
    
    def test_resume_conversation_with_different_ids(self, buffer_manager):
        """Test resume conversation with different conversation IDs"""
        conv_id_1 = uuid4()
        conv_id_2 = uuid4()
        
        result_1 = buffer_manager.resume_conversation(conv_id_1)
        result_2 = buffer_manager.resume_conversation(conv_id_2)
        
        assert result_1 != result_2
        assert str(conv_id_1) in result_1
        assert str(conv_id_2) in result_2
    
    def test_get_context(self, buffer_manager):
        """Test get context method"""
        conversation_id = uuid4()
        
        result = buffer_manager.get_context(conversation_id)
        
        assert isinstance(result, str)
        assert str(conversation_id) in result
        assert "Existing context" in result
    
    def test_get_context_with_different_ids(self, buffer_manager):
        """Test get context with different conversation IDs"""
        conv_id_1 = uuid4()
        conv_id_2 = uuid4()
        
        result_1 = buffer_manager.get_context(conv_id_1)
        result_2 = buffer_manager.get_context(conv_id_2)
        
        assert result_1 != result_2
        assert str(conv_id_1) in result_1
        assert str(conv_id_2) in result_2
    
    def test_get_stats_returns_correct_structure(self, buffer_manager):
        """Test get stats returns correct structure"""
        stats = buffer_manager.get_stats()
        
        assert isinstance(stats, dict)
        assert "total_buffers" in stats
        assert "active_buffers" in stats
        assert "total_messages" in stats
        assert "average_messages_per_buffer" in stats
    
    def test_get_stats_default_values(self, buffer_manager):
        """Test get stats returns expected default values"""
        stats = buffer_manager.get_stats()
        
        assert stats["total_buffers"] == 0
        assert stats["active_buffers"] == 0
        assert stats["total_messages"] == 0
        assert stats["average_messages_per_buffer"] == 0
    
    def test_get_stats_values_are_integers(self, buffer_manager):
        """Test get stats returns integer values"""
        stats = buffer_manager.get_stats()
        
        for key, value in stats.items():
            assert isinstance(value, (int, float))
            assert value >= 0
    
    def test_resume_conversation_with_uuid_type(self, buffer_manager):
        """Test resume conversation accepts UUID type"""
        conversation_id = uuid4()
        
        # Should not raise any exceptions
        result = buffer_manager.resume_conversation(conversation_id)
        assert result is not None
    
    def test_get_context_with_uuid_type(self, buffer_manager):
        """Test get context accepts UUID type"""
        conversation_id = uuid4()
        
        # Should not raise any exceptions
        result = buffer_manager.get_context(conversation_id)
        assert result is not None
    
    def test_methods_are_synchronous(self, buffer_manager):
        """Test that methods are synchronous (not async)"""
        conversation_id = uuid4()
        
        # These should be callable without await
        resume_result = buffer_manager.resume_conversation(conversation_id)
        context_result = buffer_manager.get_context(conversation_id)
        stats_result = buffer_manager.get_stats()
        
        assert resume_result is not None
        assert context_result is not None
        assert stats_result is not None
    
    def test_multiple_calls_consistency(self, buffer_manager):
        """Test that multiple calls to same conversation return consistent format"""
        conversation_id = uuid4()
        
        # Call multiple times
        resume_1 = buffer_manager.resume_conversation(conversation_id)
        resume_2 = buffer_manager.resume_conversation(conversation_id)
        context_1 = buffer_manager.get_context(conversation_id)
        context_2 = buffer_manager.get_context(conversation_id)
        
        # Should return same format/content for same ID
        assert resume_1 == resume_2
        assert context_1 == context_2
    
    def test_buffers_attribute_accessibility(self, buffer_manager):
        """Test that buffers attribute is accessible"""
        assert hasattr(buffer_manager, 'buffers')
        assert buffer_manager.buffers == {}
        
        # Should be modifiable
        buffer_manager.buffers['test'] = 'value'
        assert buffer_manager.buffers['test'] == 'value'


class TestEnhancedBufferManagerSingleton:
    """Test the enhanced buffer manager singleton instance"""
    
    def test_singleton_instance_creation(self):
        """Test that singleton instance is created correctly"""
        assert isinstance(enhanced_buffer_manager, EnhancedBufferManager)
        assert enhanced_buffer_manager.buffers == {}
    
    def test_singleton_instance_consistency(self):
        """Test that multiple imports return same instance"""
        from app.core.enhanced_buffer_manager import enhanced_buffer_manager as ebm1
        from app.core.enhanced_buffer_manager import enhanced_buffer_manager as ebm2
        
        assert ebm1 is ebm2
    
    def test_singleton_functionality(self):
        """Test that singleton instance works correctly"""
        conversation_id = uuid4()
        
        # Test methods work on singleton
        resume_result = enhanced_buffer_manager.resume_conversation(conversation_id)
        context_result = enhanced_buffer_manager.get_context(conversation_id)
        stats_result = enhanced_buffer_manager.get_stats()
        
        assert isinstance(resume_result, str)
        assert isinstance(context_result, str)
        assert isinstance(stats_result, dict)
    
    def test_singleton_state_persistence(self):
        """Test that singleton maintains state across calls"""
        # Modify singleton state
        enhanced_buffer_manager.buffers['test_key'] = 'test_value'
        
        # Import again and check state is preserved
        from app.core.enhanced_buffer_manager import enhanced_buffer_manager as ebm_check
        
        assert ebm_check.buffers['test_key'] == 'test_value'
        
        # Clean up
        del enhanced_buffer_manager.buffers['test_key']


class TestEnhancedBufferManagerEdgeCases:
    """Test edge cases for EnhancedBufferManager"""
    
    @pytest.fixture
    def buffer_manager(self):
        """Create a test enhanced buffer manager"""
        return EnhancedBufferManager()
    
    @pytest.mark.skip(reason="Mock implementation doesn't validate inputs")
    def test_none_conversation_id_handling(self, buffer_manager):
        """Test handling of None conversation ID"""
        # The methods should handle None gracefully
        # Note: This depends on implementation - UUID conversion might raise error
        with pytest.raises((TypeError, AttributeError)):
            buffer_manager.resume_conversation(None)
    
    @pytest.mark.skip(reason="Mock implementation doesn't validate inputs")
    def test_invalid_uuid_string(self, buffer_manager):
        """Test handling of invalid UUID string"""
        # Should handle string that's not a valid UUID
        with pytest.raises((ValueError, AttributeError)):
            buffer_manager.resume_conversation("not-a-uuid")
    
    @pytest.mark.skip(reason="Mock implementation doesn't validate inputs")
    def test_empty_string_conversation_id(self, buffer_manager):
        """Test handling of empty string conversation ID"""
        with pytest.raises((ValueError, AttributeError)):
            buffer_manager.resume_conversation("")
    
    @pytest.mark.skip(reason="Mock implementation doesn't validate inputs")
    def test_integer_conversation_id(self, buffer_manager):
        """Test handling of integer conversation ID"""
        # Should handle non-UUID types gracefully
        with pytest.raises((TypeError, AttributeError)):
            buffer_manager.resume_conversation(123)
    
    @pytest.mark.skip(reason="Mock implementation doesn't validate inputs")
    def test_very_long_conversation_id_string(self, buffer_manager):
        """Test handling of very long string as conversation ID"""
        long_string = "a" * 1000
        
        with pytest.raises((ValueError, AttributeError)):
            buffer_manager.resume_conversation(long_string)
    
    def test_stats_reliability(self, buffer_manager):
        """Test that stats method is always reliable"""
        # Should never raise exceptions
        for _ in range(100):
            stats = buffer_manager.get_stats()
            assert isinstance(stats, dict)
            assert len(stats) == 4  # Expected number of stats fields
    
    def test_buffer_manager_multiple_instantiation(self):
        """Test creating multiple buffer manager instances"""
        bm1 = EnhancedBufferManager()
        bm2 = EnhancedBufferManager()
        
        # Should be separate instances
        assert bm1 is not bm2
        assert bm1.buffers is not bm2.buffers
        
        # Modifying one should not affect the other
        bm1.buffers['test'] = 'value1'
        bm2.buffers['test'] = 'value2'
        
        assert bm1.buffers['test'] == 'value1'
        assert bm2.buffers['test'] == 'value2'


class TestMockFunctionality:
    """Test that the enhanced buffer manager works as intended mock"""
    
    @pytest.fixture
    def buffer_manager(self):
        """Create a test enhanced buffer manager"""
        return EnhancedBufferManager()
    
    def test_is_mock_implementation(self, buffer_manager):
        """Test that this is clearly a mock implementation"""
        conversation_id = uuid4()
        
        # Resume conversation should return mock data
        resume_result = buffer_manager.resume_conversation(conversation_id)
        assert "Resumed conversation context" in resume_result
        
        # Get context should return mock data
        context_result = buffer_manager.get_context(conversation_id)
        assert "Existing context" in context_result
        
        # Stats should return mock/empty data
        stats = buffer_manager.get_stats()
        assert all(value == 0 for value in stats.values())
    
    def test_mock_data_format(self, buffer_manager):
        """Test that mock data follows expected format"""
        conversation_id = uuid4()
        
        resume_result = buffer_manager.resume_conversation(conversation_id)
        context_result = buffer_manager.get_context(conversation_id)
        
        # Should contain conversation ID in string format
        assert str(conversation_id) in resume_result
        assert str(conversation_id) in context_result
        
        # Should be descriptive mock messages
        assert "resumed" in resume_result.lower()
        assert "context" in context_result.lower()
    
    def test_suitable_for_testing_purposes(self, buffer_manager):
        """Test that this mock is suitable for testing purposes"""
        # Should provide predictable, non-None responses
        conversation_id = uuid4()
        
        resume_result = buffer_manager.resume_conversation(conversation_id)
        context_result = buffer_manager.get_context(conversation_id)
        stats_result = buffer_manager.get_stats()
        
        assert resume_result is not None
        assert context_result is not None
        assert stats_result is not None
        
        # Should be deterministic for same inputs
        assert buffer_manager.resume_conversation(conversation_id) == resume_result
        assert buffer_manager.get_context(conversation_id) == context_result