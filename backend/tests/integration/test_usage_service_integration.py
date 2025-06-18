"""
Integration tests for usage tracking service.
Tests usage recording, statistics calculation, and metric tracking with real database operations.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services.usage_service import usage_service
from app.models.models import User, Tenant, UsageRecord, SystemMetrics
from app.schemas.schemas import UsageStats

# Import integration test fixtures
from tests.conftest_integration_simple import *


@pytest.mark.asyncio
async def test_record_usage_success(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test successful usage recording."""
    
    usage_record = await usage_service.record_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        usage_type="tokens",
        amount=1000,
        user_id=sample_user.id,
        service_provider="openai",
        model_name="gpt-4",
        cost_cents=30,
        additional_data={"request_id": "req_123"}
    )
    
    assert usage_record.id is not None
    assert usage_record.tenant_id == sample_tenant.id
    assert usage_record.user_id == sample_user.id
    assert usage_record.usage_type == "tokens"
    assert usage_record.amount == 1000
    assert usage_record.service_provider == "openai"
    assert usage_record.model_name == "gpt-4"
    assert usage_record.cost_cents == 30
    assert usage_record.additional_data["request_id"] == "req_123"
    assert usage_record.created_at is not None


@pytest.mark.asyncio
async def test_record_token_usage_success(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test token usage recording with cost estimation."""
    
    usage_record = await usage_service.record_token_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        token_count=2000,
        service_provider="openai",
        model_name="gpt-4"
    )
    
    assert usage_record.usage_type == "tokens"
    assert usage_record.amount == 2000
    assert usage_record.service_provider == "openai"
    assert usage_record.model_name == "gpt-4"
    # GPT-4 cost estimation: 2000 * 0.003 = 6 cents
    assert usage_record.cost_cents == 6


@pytest.mark.asyncio
async def test_record_token_usage_gpt35(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test token usage recording with GPT-3.5 cost estimation."""
    
    usage_record = await usage_service.record_token_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        token_count=5000,
        model_name="gpt-3.5-turbo"
    )
    
    assert usage_record.model_name == "gpt-3.5-turbo"
    # GPT-3.5 cost estimation: 5000 * 0.0002 = 1 cent
    assert usage_record.cost_cents == 1


@pytest.mark.asyncio
async def test_record_token_usage_custom_cost(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test token usage recording with custom cost."""
    
    usage_record = await usage_service.record_token_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        token_count=1000,
        cost_cents=50
    )
    
    assert usage_record.cost_cents == 50


@pytest.mark.asyncio
async def test_record_tts_usage_success(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test TTS usage recording."""
    
    usage_record = await usage_service.record_tts_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        word_count=500,
        service_provider="elevenlabs",
        model_name="eleven_turbo_v2",
        duration_seconds=30
    )
    
    assert usage_record.usage_type == "tts_words"
    assert usage_record.amount == 500
    assert usage_record.service_provider == "elevenlabs"
    assert usage_record.model_name == "eleven_turbo_v2"
    assert usage_record.additional_data["duration_seconds"] == 30
    # ElevenLabs cost estimation: 500 words * 5 chars * 0.00003 * 100 = 7.5 -> 7 cents
    assert usage_record.cost_cents == 7


@pytest.mark.asyncio
async def test_record_stt_usage_with_duration(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test STT usage recording with duration."""
    
    usage_record = await usage_service.record_stt_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        word_count=300,
        service_provider="deepgram",
        model_name="nova-2",
        duration_seconds=120  # 2 minutes
    )
    
    assert usage_record.usage_type == "stt_words"
    assert usage_record.amount == 300
    assert usage_record.service_provider == "deepgram"
    assert usage_record.model_name == "nova-2"
    assert usage_record.additional_data["duration_seconds"] == 120
    # Deepgram cost estimation: 2 minutes * 0.25 * 100 = 50 cents
    assert usage_record.cost_cents == 50


@pytest.mark.asyncio
async def test_record_stt_usage_without_duration(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test STT usage recording without duration (estimated from word count)."""
    
    usage_record = await usage_service.record_stt_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        word_count=450  # ~3 minutes at 150 words/minute
    )
    
    assert usage_record.usage_type == "stt_words"
    assert usage_record.amount == 450
    # Estimated duration: 450/150 = 3 minutes, cost: 3 * 0.25 * 100 = 75 cents
    assert usage_record.cost_cents == 75


@pytest.mark.asyncio
async def test_get_usage_stats_default_period(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test getting usage stats with default period."""
    
    # Create test usage records
    now = datetime.now(timezone.utc)
    recent_date = now - timedelta(days=5)
    
    # Token usage
    await usage_service.record_token_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        token_count=1000,
        cost_cents=30
    )
    
    # TTS usage
    await usage_service.record_tts_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        word_count=200,
        duration_seconds=15
    )
    
    # STT usage
    await usage_service.record_stt_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        word_count=150,
        duration_seconds=60
    )
    
    stats = await usage_service.get_usage_stats(
        db=db_session,
        tenant_id=sample_tenant.id
    )
    
    assert stats.period == "month"
    assert stats.total_tokens == 1000
    assert stats.total_tts_words == 200
    assert stats.total_stt_words == 150
    assert stats.total_cost_cents >= 30  # At least the token cost


@pytest.mark.asyncio
async def test_get_usage_stats_custom_date_range(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test getting usage stats with custom date range."""
    
    start_date = datetime.now(timezone.utc) - timedelta(days=7)
    end_date = datetime.now(timezone.utc) + timedelta(hours=1)  # Include current time
    
    # Create usage record within range
    await usage_service.record_token_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        token_count=500
    )
    
    stats = await usage_service.get_usage_stats(
        db=db_session,
        tenant_id=sample_tenant.id,
        start_date=start_date,
        end_date=end_date,
        period="week"
    )
    
    assert stats.period == "week"
    assert stats.start_date == start_date
    assert stats.end_date == end_date
    assert stats.total_tokens == 500


@pytest.mark.asyncio
async def test_get_usage_stats_by_user(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User,
    other_user: User
):
    """Test getting usage stats filtered by user."""
    
    # Create usage for sample_user
    await usage_service.record_token_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        token_count=1000
    )
    
    # Create usage for other_user (same tenant)
    await usage_service.record_token_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=other_user.id,
        token_count=2000
    )
    
    # Get stats for specific user
    stats = await usage_service.get_usage_stats(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id
    )
    
    assert stats.total_tokens == 1000  # Only sample_user's usage


@pytest.mark.asyncio
async def test_get_usage_stats_no_data(
    db_session: AsyncSession,
    sample_tenant: Tenant
):
    """Test getting usage stats when no data exists."""
    
    stats = await usage_service.get_usage_stats(
        db=db_session,
        tenant_id=sample_tenant.id
    )
    
    assert stats.total_tokens == 0
    assert stats.total_tts_words == 0
    assert stats.total_stt_words == 0
    assert stats.total_cost_cents == 0


@pytest.mark.asyncio
async def test_record_system_metric_success(
    db_session: AsyncSession,
    sample_tenant: Tenant
):
    """Test recording system metrics."""
    
    metric = await usage_service.record_system_metric(
        db=db_session,
        metric_type="active_connections",
        value=25,
        tenant_id=sample_tenant.id,
        additional_data={"server": "ws-1"}
    )
    
    assert metric.id is not None
    assert metric.metric_type == "active_connections"
    assert metric.value == 25
    assert metric.tenant_id == sample_tenant.id
    assert metric.additional_data["server"] == "ws-1"
    assert metric.created_at is not None


@pytest.mark.asyncio
async def test_record_system_metric_global(
    db_session: AsyncSession
):
    """Test recording global system metrics."""
    
    metric = await usage_service.record_system_metric(
        db=db_session,
        metric_type="memory_usage",
        value=85,
        additional_data={"unit": "percent"}
    )
    
    assert metric.metric_type == "memory_usage"
    assert metric.value == 85
    assert metric.tenant_id is None  # Global metric
    assert metric.additional_data["unit"] == "percent"


@pytest.mark.asyncio
async def test_get_recent_usage_success(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test getting recent usage records."""
    
    # Create multiple usage records
    for i in range(5):
        await usage_service.record_token_usage(
            db=db_session,
            tenant_id=sample_tenant.id,
            user_id=sample_user.id,
            token_count=100 * (i + 1)
        )
    
    recent_usage = await usage_service.get_recent_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        limit=3
    )
    
    assert len(recent_usage) == 3
    # Should be ordered by created_at desc
    assert recent_usage[0].amount == 500  # Most recent (100 * 5)
    assert recent_usage[1].amount == 400
    assert recent_usage[2].amount == 300


@pytest.mark.asyncio
async def test_get_recent_usage_all_tenants(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    other_tenant: Tenant,
    sample_user: User
):
    """Test getting recent usage records across all tenants."""
    
    # Create usage for different tenants
    await usage_service.record_token_usage(
        db=db_session,
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        token_count=1000
    )
    
    await usage_service.record_token_usage(
        db=db_session,
        tenant_id=other_tenant.id,
        user_id=sample_user.id,
        token_count=2000
    )
    
    # Get usage without tenant filter
    recent_usage = await usage_service.get_recent_usage(
        db=db_session,
        limit=10
    )
    
    assert len(recent_usage) == 2
    # Should include both tenants
    amounts = [record.amount for record in recent_usage]
    assert 1000 in amounts
    assert 2000 in amounts


@pytest.mark.asyncio
async def test_get_system_metrics_success(
    db_session: AsyncSession,
    sample_tenant: Tenant
):
    """Test getting system metrics."""
    
    # Create test metrics
    await usage_service.record_system_metric(
        db=db_session,
        metric_type="cpu_usage",
        value=75
    )
    
    await usage_service.record_system_metric(
        db=db_session,
        metric_type="memory_usage",
        value=60
    )
    
    await usage_service.record_system_metric(
        db=db_session,
        metric_type="cpu_usage",
        value=80
    )
    
    # Get all metrics
    metrics = await usage_service.get_system_metrics(
        db=db_session,
        hours=24
    )
    
    assert len(metrics) == 3
    
    # Get specific metric type
    cpu_metrics = await usage_service.get_system_metrics(
        db=db_session,
        metric_type="cpu_usage",
        hours=24
    )
    
    assert len(cpu_metrics) == 2
    assert all(m.metric_type == "cpu_usage" for m in cpu_metrics)


@pytest.mark.asyncio
async def test_get_system_metrics_time_filter(
    db_session: AsyncSession
):
    """Test system metrics time filtering."""
    
    # Create old metric (should be filtered out)
    old_metric = SystemMetrics(
        metric_type="old_metric",
        value=100,
        created_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    db_session.add(old_metric)
    
    # Create recent metric
    await usage_service.record_system_metric(
        db=db_session,
        metric_type="recent_metric",
        value=200
    )
    
    await db_session.commit()
    
    # Get metrics from last 1 hour
    metrics = await usage_service.get_system_metrics(
        db=db_session,
        hours=1
    )
    
    # Should only include recent metric
    assert len(metrics) == 1
    assert metrics[0].metric_type == "recent_metric"


@pytest.mark.asyncio
async def test_usage_stats_period_calculations(
    db_session: AsyncSession,
    sample_tenant: Tenant
):
    """Test usage stats period calculations."""
    
    # Test day period
    stats_day = await usage_service.get_usage_stats(
        db=db_session,
        tenant_id=sample_tenant.id,
        period="day"
    )
    assert stats_day.period == "day"
    expected_start = stats_day.end_date - timedelta(days=1)
    assert abs((stats_day.start_date - expected_start).total_seconds()) < 60
    
    # Test week period
    stats_week = await usage_service.get_usage_stats(
        db=db_session,
        tenant_id=sample_tenant.id,
        period="week"
    )
    assert stats_week.period == "week"
    expected_start = stats_week.end_date - timedelta(weeks=1)
    assert abs((stats_week.start_date - expected_start).total_seconds()) < 60
    
    # Test month period (default)
    stats_month = await usage_service.get_usage_stats(
        db=db_session,
        tenant_id=sample_tenant.id,
        period="month"
    )
    assert stats_month.period == "month"
    expected_start = stats_month.end_date - timedelta(days=30)
    assert abs((stats_month.start_date - expected_start).total_seconds()) < 60


@pytest.mark.asyncio
async def test_concurrent_usage_recording(
    test_db_engine,
    sample_tenant: Tenant,
    sample_user: User
):
    """Test concurrent usage recording."""
    import asyncio
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    # Create session factory for concurrent operations
    SessionLocal = async_sessionmaker(
        test_db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async def record_usage():
        async with SessionLocal() as session:
            return await usage_service.record_token_usage(
                db=session,
                tenant_id=sample_tenant.id,
                user_id=sample_user.id,
                token_count=100
            )
    
    # Record multiple usage records concurrently
    tasks = [record_usage() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 5
    assert all(record.amount == 100 for record in results)
    
    # Verify all records were saved using a new session
    async with SessionLocal() as session:
        stats = await usage_service.get_usage_stats(
            db=session,
            tenant_id=sample_tenant.id
        )
        assert stats.total_tokens == 500