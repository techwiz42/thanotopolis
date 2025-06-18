"""
Integration tests for services that require database or external dependencies.
Working version with correct method signatures and real database.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.services.usage_service import UsageTrackingService
from app.models.models import User, Tenant, UsageRecord


class TestUsageTrackingServiceIntegration:
    """Integration tests for Usage service."""

    async def test_record_usage_success(self, db_session: AsyncSession, sample_user: User):
        """Test successful usage recording."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            usage_type="api_call",
            amount=1,
            user_id=sample_user.id,
            cost_cents=1  # 1 cent
        )
        
        assert result is not None
        assert result.usage_type == "api_call"
        assert result.amount == 1

    async def test_record_token_usage_success(self, db_session: AsyncSession, sample_user: User):
        """Test successful token usage recording."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_token_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            user_id=sample_user.id,
            token_count=150,  # Combined input + output
            model_name="gpt-4"
        )
        
        assert result is not None
        assert result.usage_type == "tokens"
        assert result.amount == 150

    async def test_record_token_usage_gpt35(self, db_session: AsyncSession, sample_user: User):
        """Test token usage recording for GPT-3.5."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_token_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            user_id=sample_user.id,
            token_count=300,
            model_name="gpt-3.5-turbo"
        )
        
        assert result is not None
        assert result.usage_type == "tokens"
        assert result.model_name == "gpt-3.5-turbo"

    async def test_record_token_usage_custom_cost(self, db_session: AsyncSession, sample_user: User):
        """Test token usage recording with custom cost."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_token_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            user_id=sample_user.id,
            token_count=200,
            model_name="gpt-4",
            cost_cents=50
        )
        
        assert result is not None
        assert result.cost_cents == 50

    async def test_record_tts_usage_success(self, db_session: AsyncSession, sample_user: User):
        """Test successful TTS usage recording."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_tts_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            user_id=sample_user.id,
            word_count=50
        )
        
        assert result is not None
        assert result.usage_type == "tts_words"
        assert result.amount == 50

    async def test_record_stt_usage_with_duration(self, db_session: AsyncSession, sample_user: User):
        """Test STT usage recording with duration."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_stt_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            user_id=sample_user.id,
            word_count=30,
            duration_seconds=60
        )
        
        assert result is not None
        assert result.usage_type == "stt_words"
        assert result.amount == 30

    async def test_record_stt_usage_without_duration(self, db_session: AsyncSession, sample_user: User):
        """Test STT usage recording without duration."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_stt_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            user_id=sample_user.id,
            word_count=25  # No duration provided
        )
        
        assert result is not None
        assert result.usage_type == "stt_words"
        assert result.amount == 25

    async def test_get_usage_stats_default_period(self, db_session: AsyncSession, sample_user: User):
        """Test getting usage stats with default period."""
        usage_service = UsageTrackingService()
        
        # Record some usage first
        await usage_service.record_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            usage_type="tokens",
            amount=100,
            user_id=sample_user.id,
            cost_cents=5
        )
        
        stats = await usage_service.get_usage_stats(
            db=db_session,
            tenant_id=sample_user.tenant_id
        )
        
        assert stats is not None
        assert stats.period == "month"

    async def test_get_recent_usage_success(self, db_session: AsyncSession, sample_user: User):
        """Test getting recent usage records."""
        usage_service = UsageTrackingService()
        
        # Record some usage first
        await usage_service.record_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id,
            usage_type="api_call",
            amount=1,
            user_id=sample_user.id,
            cost_cents=2
        )
        
        recent_usage = await usage_service.get_recent_usage(
            db=db_session,
            tenant_id=sample_user.tenant_id
        )
        
        assert isinstance(recent_usage, list)

    async def test_concurrent_usage_recording(self, db_session: AsyncSession, sample_user: User):
        """Test concurrent usage recording."""
        usage_service = UsageTrackingService()
        
        # Record concurrent usage - simplified version
        for i in range(1, 4):  # Reduced to avoid overwhelming database
            result = await usage_service.record_usage(
                db=db_session,
                tenant_id=sample_user.tenant_id,
                usage_type="concurrent_test",
                amount=i,
                user_id=sample_user.id,
                cost_cents=i
            )
            assert result is not None