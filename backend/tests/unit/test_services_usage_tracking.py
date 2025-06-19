import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from decimal import Decimal

from app.services.usage_service import UsageTrackingService, usage_service
from app.models.models import UsageRecord, SystemMetrics
from app.schemas.schemas import UsageStats


class TestUsageTrackingService:
    """Test suite for UsageTrackingService."""
    
    @pytest.fixture
    def usage_service_instance(self):
        """Create a test UsageTrackingService instance."""
        return UsageTrackingService()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    @pytest.fixture
    def sample_tenant_id(self):
        """Create a sample tenant ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_user_id(self):
        """Create a sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_conversation_id(self):
        """Create a sample conversation ID."""
        return uuid4()
    
    def test_usage_service_initialization(self, usage_service_instance):
        """Test UsageTrackingService initialization."""
        assert usage_service_instance.db is None
    
    @pytest.mark.asyncio
    async def test_record_usage_basic(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test basic usage recording."""
        # Mock the created usage record
        mock_usage_record = MagicMock()
        mock_usage_record.id = uuid4()
        mock_usage_record.tenant_id = sample_tenant_id
        mock_usage_record.user_id = sample_user_id
        mock_usage_record.usage_type = "tokens"
        mock_usage_record.amount = 100
        mock_usage_record.cost_cents = 5
        
        # Mock db.refresh to set the record attributes
        async def mock_refresh(record):
            for attr, value in vars(mock_usage_record).items():
                setattr(record, attr, value)
        
        mock_db.refresh.side_effect = mock_refresh
        
        result = await usage_service_instance.record_usage(
            db=mock_db,
            tenant_id=sample_tenant_id,
            usage_type="tokens",
            amount=100,
            user_id=sample_user_id,
            cost_cents=5
        )
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify the returned record
        assert isinstance(result, UsageRecord)
        assert result.tenant_id == sample_tenant_id
        assert result.user_id == sample_user_id
        assert result.usage_type == "tokens"
        assert result.amount == 100
        assert result.cost_cents == 5
    
    @pytest.mark.asyncio
    async def test_record_usage_with_all_parameters(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id, sample_conversation_id):
        """Test usage recording with all optional parameters."""
        additional_data = {"model_version": "v1.0", "processing_time": 1.5}
        
        mock_usage_record = MagicMock()
        mock_usage_record.conversation_id = sample_conversation_id
        mock_usage_record.service_provider = "openai"
        mock_usage_record.model_name = "gpt-4"
        mock_usage_record.additional_data = additional_data
        
        async def mock_refresh(record):
            for attr, value in vars(mock_usage_record).items():
                setattr(record, attr, value)
        
        mock_db.refresh.side_effect = mock_refresh
        
        result = await usage_service_instance.record_usage(
            db=mock_db,
            tenant_id=sample_tenant_id,
            usage_type="tokens",
            amount=100,
            user_id=sample_user_id,
            conversation_id=sample_conversation_id,
            service_provider="openai",
            model_name="gpt-4",
            cost_cents=10,
            additional_data=additional_data
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Check that the UsageRecord was created with correct parameters
        call_args = mock_db.add.call_args[0][0]
        assert isinstance(call_args, UsageRecord)
        assert call_args.tenant_id == sample_tenant_id
        assert call_args.user_id == sample_user_id
        assert call_args.conversation_id == sample_conversation_id
        assert call_args.service_provider == "openai"
        assert call_args.model_name == "gpt-4"
        assert call_args.additional_data == additional_data
    
    @pytest.mark.asyncio
    async def test_record_token_usage_gpt4(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test token usage recording for GPT-4."""
        with patch.object(usage_service_instance, 'record_usage') as mock_record:
            mock_record.return_value = MagicMock()
            
            await usage_service_instance.record_token_usage(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                token_count=1000,
                service_provider="openai",
                model_name="gpt-4"
            )
            
            mock_record.assert_called_once_with(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                usage_type="tokens",
                amount=1000,
                conversation_id=None,
                service_provider="openai",
                model_name="gpt-4",
                cost_cents=3  # 1000 * 0.003
            )
    
    @pytest.mark.asyncio
    async def test_record_token_usage_gpt35(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test token usage recording for GPT-3.5."""
        with patch.object(usage_service_instance, 'record_usage') as mock_record:
            mock_record.return_value = MagicMock()
            
            await usage_service_instance.record_token_usage(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                token_count=1000,
                service_provider="openai",
                model_name="gpt-3.5-turbo"
            )
            
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args["cost_cents"] == 0  # 1000 * 0.0002 = 0.2, rounded to 0
    
    @pytest.mark.asyncio
    async def test_record_token_usage_custom_cost(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test token usage recording with custom cost."""
        with patch.object(usage_service_instance, 'record_usage') as mock_record:
            mock_record.return_value = MagicMock()
            
            await usage_service_instance.record_token_usage(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                token_count=500,
                cost_cents=25
            )
            
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args["cost_cents"] == 25
    
    @pytest.mark.asyncio
    async def test_record_tts_usage(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test TTS usage recording."""
        with patch.object(usage_service_instance, 'record_usage') as mock_record:
            mock_record.return_value = MagicMock()
            
            await usage_service_instance.record_tts_usage(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                word_count=100,
                service_provider="elevenlabs",
                model_name="eleven_turbo_v2",
                duration_seconds=30
            )
            
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args["usage_type"] == "tts_words"
            assert call_args["amount"] == 100
            assert call_args["service_provider"] == "elevenlabs"
            assert call_args["model_name"] == "eleven_turbo_v2"
            assert call_args["additional_data"]["duration_seconds"] == 30
            # Cost: 100 words * 5 chars/word * 0.00003 * 100 = 1.5 cents
            assert call_args["cost_cents"] == 1
    
    @pytest.mark.asyncio
    async def test_record_stt_usage_with_duration(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test STT usage recording with duration."""
        with patch.object(usage_service_instance, 'record_usage') as mock_record:
            mock_record.return_value = MagicMock()
            
            await usage_service_instance.record_stt_usage(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                word_count=150,
                service_provider="deepgram",
                model_name="nova-2",
                duration_seconds=60  # 1 minute
            )
            
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            assert call_args["usage_type"] == "stt_words"
            assert call_args["amount"] == 150
            assert call_args["additional_data"]["duration_seconds"] == 60
            # Cost: 60 seconds / 60 * 0.25 * 100 = 25 cents
            assert call_args["cost_cents"] == 25
    
    @pytest.mark.asyncio
    async def test_record_stt_usage_without_duration(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test STT usage recording without duration (estimated from word count)."""
        with patch.object(usage_service_instance, 'record_usage') as mock_record:
            mock_record.return_value = MagicMock()
            
            await usage_service_instance.record_stt_usage(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                word_count=150  # 150 words / 150 words per minute = 1 minute estimated
            )
            
            mock_record.assert_called_once()
            call_args = mock_record.call_args[1]
            # Cost estimated from word count: 150/150 minutes * 0.25 * 100 = 25 cents
            assert call_args["cost_cents"] == 25
    
    @pytest.mark.asyncio
    async def test_get_usage_stats_default_period(self, usage_service_instance, mock_db, sample_tenant_id):
        """Test getting usage statistics with default period."""
        # Mock database query result
        mock_result = MagicMock()
        mock_stats = [
            MagicMock(usage_type="tokens", total_amount=5000, total_cost=150),
            MagicMock(usage_type="tts_words", total_amount=1000, total_cost=50),
            MagicMock(usage_type="stt_words", total_amount=800, total_cost=40)
        ]
        mock_result.all.return_value = mock_stats
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_usage_stats(
            db=mock_db,
            tenant_id=sample_tenant_id
        )
        
        assert isinstance(result, UsageStats)
        assert result.period == "month"
        assert result.total_tokens == 5000
        assert result.total_tts_words == 1000
        assert result.total_stt_words == 800
        assert result.total_cost_cents == 240  # 150 + 50 + 40
        assert result.start_date is not None
        assert result.end_date is not None
    
    @pytest.mark.asyncio
    async def test_get_usage_stats_custom_period(self, usage_service_instance, mock_db, sample_tenant_id):
        """Test getting usage statistics with custom date period."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_usage_stats(
            db=mock_db,
            tenant_id=sample_tenant_id,
            start_date=start_date,
            end_date=end_date,
            period="custom"
        )
        
        assert result.period == "custom"
        assert result.start_date == start_date
        assert result.end_date == end_date
        assert result.total_tokens == 0
        assert result.total_cost_cents == 0
    
    @pytest.mark.asyncio
    async def test_get_usage_stats_by_user(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test getting usage statistics filtered by user."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        await usage_service_instance.get_usage_stats(
            db=mock_db,
            tenant_id=sample_tenant_id,
            user_id=sample_user_id
        )
        
        # Verify that the query was called (we can't easily verify the exact SQL)
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_usage_stats_week_period(self, usage_service_instance, mock_db):
        """Test getting usage statistics for week period."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_usage_stats(
            db=mock_db,
            period="week"
        )
        
        assert result.period == "week"
        # Verify that start_date is approximately 1 week ago
        expected_start = result.end_date - timedelta(weeks=1)
        assert abs((result.start_date - expected_start).total_seconds()) < 3600  # Within 1 hour
    
    @pytest.mark.asyncio
    async def test_get_usage_stats_day_period(self, usage_service_instance, mock_db):
        """Test getting usage statistics for day period."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_usage_stats(
            db=mock_db,
            period="day"
        )
        
        assert result.period == "day"
        # Verify that start_date is approximately 1 day ago
        expected_start = result.end_date - timedelta(days=1)
        assert abs((result.start_date - expected_start).total_seconds()) < 3600  # Within 1 hour
    
    @pytest.mark.asyncio
    async def test_record_system_metric(self, usage_service_instance, mock_db, sample_tenant_id):
        """Test recording system metrics."""
        additional_data = {"cpu_cores": 4, "load_avg": 0.75}
        
        mock_metric = MagicMock()
        mock_metric.metric_type = "cpu_usage"
        mock_metric.value = 85
        mock_metric.tenant_id = sample_tenant_id
        mock_metric.additional_data = additional_data
        
        async def mock_refresh(record):
            for attr, value in vars(mock_metric).items():
                setattr(record, attr, value)
        
        mock_db.refresh.side_effect = mock_refresh
        
        result = await usage_service_instance.record_system_metric(
            db=mock_db,
            metric_type="cpu_usage",
            value=85,
            tenant_id=sample_tenant_id,
            additional_data=additional_data
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Check that the SystemMetrics was created with correct parameters
        call_args = mock_db.add.call_args[0][0]
        assert isinstance(call_args, SystemMetrics)
        assert call_args.metric_type == "cpu_usage"
        assert call_args.value == 85
        assert call_args.tenant_id == sample_tenant_id
        assert call_args.additional_data == additional_data
    
    @pytest.mark.asyncio
    async def test_record_system_metric_without_tenant(self, usage_service_instance, mock_db):
        """Test recording system metrics without tenant ID."""
        mock_metric = MagicMock()
        
        async def mock_refresh(record):
            for attr, value in vars(mock_metric).items():
                setattr(record, attr, value)
        
        mock_db.refresh.side_effect = mock_refresh
        
        result = await usage_service_instance.record_system_metric(
            db=mock_db,
            metric_type="memory_usage",
            value=70
        )
        
        call_args = mock_db.add.call_args[0][0]
        assert call_args.tenant_id is None
        assert call_args.additional_data == {}
    
    @pytest.mark.asyncio
    async def test_get_recent_usage(self, usage_service_instance, mock_db, sample_tenant_id):
        """Test getting recent usage records."""
        mock_usage_records = [
            MagicMock(id=uuid4(), usage_type="tokens", amount=100),
            MagicMock(id=uuid4(), usage_type="tts_words", amount=50)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_usage_records
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_recent_usage(
            db=mock_db,
            tenant_id=sample_tenant_id,
            limit=10
        )
        
        assert result == mock_usage_records
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_recent_usage_no_tenant(self, usage_service_instance, mock_db):
        """Test getting recent usage records without tenant filter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_recent_usage(db=mock_db, limit=25)
        
        assert result == []
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self, usage_service_instance, mock_db):
        """Test getting system metrics."""
        mock_metrics = [
            MagicMock(metric_type="cpu_usage", value=80),
            MagicMock(metric_type="memory_usage", value=65)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_metrics
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_system_metrics(
            db=mock_db,
            metric_type="cpu_usage",
            hours=12,
            limit=50
        )
        
        assert result == mock_metrics
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_system_metrics_all_types(self, usage_service_instance, mock_db):
        """Test getting system metrics for all types."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_system_metrics(db=mock_db)
        
        assert result == []
        mock_db.execute.assert_called_once()


class TestUsageServiceSingleton:
    """Test the usage service singleton."""
    
    def test_singleton_exists(self):
        """Test that usage service singleton exists."""
        assert usage_service is not None
        assert isinstance(usage_service, UsageTrackingService)
    
    def test_singleton_initialization(self):
        """Test singleton initialization."""
        assert usage_service.db is None


class TestUsageStatsCalculations:
    """Test usage statistics calculations and edge cases."""
    
    @pytest.fixture
    def usage_service_instance(self):
        return UsageTrackingService()
    
    @pytest.fixture 
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    @pytest.fixture
    def sample_tenant_id(self):
        """Create a sample tenant ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_user_id(self):
        """Create a sample user ID."""
        return uuid4()
    
    @pytest.mark.asyncio
    async def test_partial_usage_stats(self, usage_service_instance, mock_db):
        """Test usage stats with partial data (some usage types missing)."""
        mock_result = MagicMock()
        mock_stats = [
            MagicMock(usage_type="tokens", total_amount=1000, total_cost=30)
            # Missing tts_words and stt_words
        ]
        mock_result.all.return_value = mock_stats
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_usage_stats(db=mock_db)
        
        assert result.total_tokens == 1000
        assert result.total_tts_words == 0
        assert result.total_stt_words == 0
        assert result.total_cost_cents == 30
    
    @pytest.mark.asyncio
    async def test_null_amounts_in_stats(self, usage_service_instance, mock_db):
        """Test usage stats with null amounts."""
        mock_result = MagicMock()
        mock_stats = [
            MagicMock(usage_type="tokens", total_amount=None, total_cost=None),
            MagicMock(usage_type="tts_words", total_amount=500, total_cost=25)
        ]
        mock_result.all.return_value = mock_stats
        mock_db.execute.return_value = mock_result
        
        result = await usage_service_instance.get_usage_stats(db=mock_db)
        
        assert result.total_tokens == 0  # None should be converted to 0
        assert result.total_tts_words == 500
        assert result.total_cost_cents == 25  # Only the non-null cost
    
    @pytest.mark.asyncio
    async def test_cost_calculation_edge_cases(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test cost calculations for edge cases."""
        with patch.object(usage_service_instance, 'record_usage') as mock_record:
            mock_record.return_value = MagicMock()
            
            # Test very small token count
            await usage_service_instance.record_token_usage(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                token_count=1,
                model_name="gpt-4"
            )
            
            call_args = mock_record.call_args[1]
            assert call_args["cost_cents"] == 0  # 1 * 0.003 = 0.003, rounded to 0
    
    @pytest.mark.asyncio
    async def test_unknown_model_cost_estimation(self, usage_service_instance, mock_db, sample_tenant_id, sample_user_id):
        """Test cost estimation for unknown models."""
        with patch.object(usage_service_instance, 'record_usage') as mock_record:
            mock_record.return_value = MagicMock()
            
            await usage_service_instance.record_token_usage(
                db=mock_db,
                tenant_id=sample_tenant_id,
                user_id=sample_user_id,
                token_count=1000,
                model_name="unknown-model"
            )
            
            call_args = mock_record.call_args[1]
            assert call_args["cost_cents"] == 1  # 1000 * 0.001 = 1 cent (default rate)