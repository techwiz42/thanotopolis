"""
Integration tests for services that require database or external dependencies.
"""
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta

from app.services.stripe_service import StripeService
from app.services.usage_service import UsageTrackingService
from app.models.models import User, Tenant


class TestStripeServiceIntegration:
    """Integration tests for Stripe service."""

    @patch('stripe.Customer.create')
    async def test_create_customer_success(self, mock_create, db_session: AsyncSession, sample_user: User):
        """Test successful customer creation."""
        mock_create.return_value = {"id": "cus_test123"}
        
        stripe_service = StripeService()
        customer_id = await stripe_service.create_customer(
            email=sample_user.email,
            name=f"{sample_user.first_name} {sample_user.last_name}",
            db=db_session
        )
        
        assert customer_id == "cus_test123"
        mock_create.assert_called_once()

    @patch('stripe.Customer.create')
    async def test_create_customer_already_exists(self, mock_create, db_session: AsyncSession, sample_user: User):
        """Test customer creation when customer already exists."""
        # Simulate existing customer
        mock_create.side_effect = Exception("Customer already exists")
        
        stripe_service = StripeService()
        
        with pytest.raises(Exception):
            await stripe_service.create_customer(
                email=sample_user.email,
                name=f"{sample_user.first_name} {sample_user.last_name}",
                db=db_session
            )

    @patch('stripe.Subscription.create')
    async def test_create_subscription_success(self, mock_create, db_session: AsyncSession):
        """Test successful subscription creation."""
        mock_create.return_value = {
            "id": "sub_test123",
            "status": "active",
            "current_period_start": 1234567890,
            "current_period_end": 1234567890 + 2592000
        }
        
        stripe_service = StripeService()
        subscription = await stripe_service.create_subscription(
            customer_id="cus_test123",
            price_id="price_test",
            db=db_session
        )
        
        assert subscription["id"] == "sub_test123"
        assert subscription["status"] == "active"

    @patch('stripe.Customer.retrieve')
    async def test_create_subscription_customer_not_found(self, mock_retrieve, db_session: AsyncSession):
        """Test subscription creation with non-existent customer."""
        mock_retrieve.side_effect = Exception("No such customer")
        
        stripe_service = StripeService()
        
        with pytest.raises(Exception):
            await stripe_service.create_subscription(
                customer_id="cus_nonexistent",
                price_id="price_test",
                db=db_session
            )

    async def test_calculate_monthly_usage(self, db_session: AsyncSession, sample_user: User):
        """Test monthly usage calculation."""
        stripe_service = StripeService()
        
        # This would typically query usage records from database
        usage = await stripe_service.calculate_monthly_usage(
            user_id=sample_user.id,
            db=db_session
        )
        
        assert isinstance(usage, (int, float, Decimal))
        assert usage >= 0

    async def test_calculate_monthly_usage_empty(self, db_session: AsyncSession):
        """Test monthly usage calculation with no usage."""
        stripe_service = StripeService()
        
        from uuid import uuid4
        fake_user_id = uuid4()
        
        usage = await stripe_service.calculate_monthly_usage(
            user_id=fake_user_id,
            db=db_session
        )
        
        assert usage == 0

    @patch('stripe.api_requestor.APIRequestor.request')
    async def test_stripe_error_handling(self, mock_request, db_session: AsyncSession):
        """Test Stripe error handling."""
        import stripe
        mock_request.side_effect = stripe.error.StripeError("Test error")
        
        stripe_service = StripeService()
        
        with pytest.raises(stripe.error.StripeError):
            await stripe_service.create_customer(
                email="error@test.com",
                name="Error Test",
                db=db_session
            )


class TestUsageTrackingServiceIntegration:
    """Integration tests for Usage service."""

    async def test_record_usage_success(self, db_session: AsyncSession, sample_user: User):
        """Test successful usage recording."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            usage_type="api_call",
            amount=1,
            cost=Decimal("0.01"),
            db=db_session
        )
        
        assert result is True

    async def test_record_token_usage_success(self, db_session: AsyncSession, sample_user: User):
        """Test successful token usage recording."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_token_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            db=db_session
        )
        
        assert result is True

    async def test_record_token_usage_gpt35(self, db_session: AsyncSession, sample_user: User):
        """Test token usage recording for GPT-3.5."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_token_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            model="gpt-3.5-turbo",
            input_tokens=200,
            output_tokens=100,
            db=db_session
        )
        
        assert result is True

    async def test_record_token_usage_custom_cost(self, db_session: AsyncSession, sample_user: User):
        """Test token usage recording with custom cost."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_token_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            model="custom-model",
            input_tokens=50,
            output_tokens=25,
            cost_override=Decimal("0.05"),
            db=db_session
        )
        
        assert result is True

    async def test_record_tts_usage_success(self, db_session: AsyncSession, sample_user: User):
        """Test successful TTS usage recording."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_tts_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            characters=100,
            db=db_session
        )
        
        assert result is True

    async def test_record_stt_usage_with_duration(self, db_session: AsyncSession, sample_user: User):
        """Test STT usage recording with duration."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_stt_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            duration_seconds=30.5,
            db=db_session
        )
        
        assert result is True

    async def test_record_stt_usage_without_duration(self, db_session: AsyncSession, sample_user: User):
        """Test STT usage recording without duration."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_stt_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            db=db_session
        )
        
        assert result is True

    async def test_get_usage_stats_default_period(self, db_session: AsyncSession, sample_user: User):
        """Test getting usage stats for default period."""
        usage_service = UsageTrackingService()
        
        # First record some usage
        await usage_service.record_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            usage_type="test",
            amount=5,
            cost=Decimal("0.05"),
            db=db_session
        )
        
        stats = await usage_service.get_usage_stats(
            tenant_id=sample_user.tenant_id,
            db=db_session
        )
        
        assert isinstance(stats, dict)
        assert "total_cost" in stats
        assert "usage_by_type" in stats

    async def test_get_usage_stats_custom_date_range(self, db_session: AsyncSession, sample_user: User):
        """Test getting usage stats for custom date range."""
        usage_service = UsageTrackingService()
        
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        stats = await usage_service.get_usage_stats(
            tenant_id=sample_user.tenant_id,
            start_date=start_date,
            end_date=end_date,
            db=db_session
        )
        
        assert isinstance(stats, dict)

    async def test_get_usage_stats_by_user(self, db_session: AsyncSession, sample_user: User):
        """Test getting usage stats filtered by user."""
        usage_service = UsageTrackingService()
        
        stats = await usage_service.get_usage_stats(
            tenant_id=sample_user.tenant_id,
            user_id=sample_user.id,
            db=db_session
        )
        
        assert isinstance(stats, dict)

    async def test_get_usage_stats_no_data(self, db_session: AsyncSession):
        """Test getting usage stats with no data."""
        usage_service = UsageTrackingService()
        
        from uuid import uuid4
        fake_tenant_id = uuid4()
        
        stats = await usage_service.get_usage_stats(
            tenant_id=fake_tenant_id,
            db=db_session
        )
        
        assert isinstance(stats, dict)
        assert stats.get("total_cost", 0) == 0

    async def test_record_system_metric_success(self, db_session: AsyncSession):
        """Test successful system metric recording."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_system_metric(
            metric_name="cpu_usage",
            value=75.5,
            db=db_session
        )
        
        assert result is True

    async def test_record_system_metric_global(self, db_session: AsyncSession):
        """Test recording global system metric."""
        usage_service = UsageTrackingService()
        
        result = await usage_service.record_system_metric(
            metric_name="memory_usage",
            value=60.0,
            tenant_id=None,  # Global metric
            db=db_session
        )
        
        assert result is True

    async def test_get_recent_usage_success(self, db_session: AsyncSession, sample_user: User):
        """Test getting recent usage."""
        usage_service = UsageTrackingService()
        
        # Record some usage first
        await usage_service.record_usage(
            user_id=sample_user.id,
            tenant_id=sample_user.tenant_id,
            usage_type="recent_test",
            amount=1,
            cost=Decimal("0.01"),
            db=db_session
        )
        
        recent_usage = await usage_service.get_recent_usage(
            tenant_id=sample_user.tenant_id,
            limit=10,
            db=db_session
        )
        
        assert isinstance(recent_usage, list)

    async def test_get_recent_usage_all_tenants(self, db_session: AsyncSession):
        """Test getting recent usage across all tenants."""
        usage_service = UsageTrackingService()
        
        recent_usage = await usage_service.get_recent_usage(
            tenant_id=None,  # All tenants
            limit=5,
            db=db_session
        )
        
        assert isinstance(recent_usage, list)

    async def test_get_system_metrics_success(self, db_session: AsyncSession):
        """Test getting system metrics."""
        usage_service = UsageTrackingService()
        
        # Record a metric first
        await usage_service.record_system_metric(
            metric_name="test_metric",
            value=42.0,
            db=db_session
        )
        
        metrics = await usage_service.get_system_metrics(
            db=db_session
        )
        
        assert isinstance(metrics, list)

    async def test_get_system_metrics_time_filter(self, db_session: AsyncSession):
        """Test getting system metrics with time filter."""
        usage_service = UsageTrackingService()
        
        since = datetime.utcnow() - timedelta(hours=1)
        
        metrics = await usage_service.get_system_metrics(
            since=since,
            db=db_session
        )
        
        assert isinstance(metrics, list)

    async def test_usage_stats_period_calculations(self, db_session: AsyncSession, sample_user: User):
        """Test usage statistics period calculations."""
        usage_service = UsageTrackingService()
        
        # Test different period calculations
        for period in ["day", "week", "month"]:
            stats = await usage_service.get_usage_stats(
                tenant_id=sample_user.tenant_id,
                period=period,
                db=db_session
            )
            
            assert isinstance(stats, dict)

    async def test_concurrent_usage_recording(self, db_session: AsyncSession, sample_user: User):
        """Test concurrent usage recording."""
        import asyncio
        
        usage_service = UsageTrackingService()
        
        # Record multiple usage entries concurrently
        tasks = []
        for i in range(5):
            task = usage_service.record_usage(
                user_id=sample_user.id,
                tenant_id=sample_user.tenant_id,
                usage_type=f"concurrent_test_{i}",
                amount=1,
                cost=Decimal("0.01"),
                db=db_session
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)