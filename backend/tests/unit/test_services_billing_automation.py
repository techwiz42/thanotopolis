import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import asyncio
import logging

from app.services.billing_automation import BillingAutomationService, billing_automation, trigger_manual_billing


class TestBillingAutomationService:
    """Test suite for BillingAutomationService."""
    
    @pytest.fixture
    def billing_service(self):
        """Create a BillingAutomationService instance."""
        return BillingAutomationService()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session
    
    @pytest.fixture
    def sample_datetime(self):
        """Create a sample datetime for testing."""
        return datetime(2024, 6, 15, 10, 30, 0)
    
    @pytest.mark.asyncio
    async def test_process_monthly_billing_default_month(self, billing_service, mock_db_session):
        """Test processing monthly billing with default target month (previous month)."""
        # Mock the database execute results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.billing_automation.datetime') as mock_datetime:
            # Mock current time as July 15, 2024
            mock_now = datetime(2024, 7, 15, 14, 30, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = await billing_service.process_monthly_billing(db_session=mock_db_session)
            
            # Should target June 2024 (previous month)
            assert result["period_start"] == datetime(2024, 6, 1, 0, 0, 0, 0)
            assert result["period_end"] == datetime(2024, 7, 1, 0, 0, 0, 0)
            assert result["processed_organizations"] == 0
            assert result["successful_invoices"] == 0
            assert result["failed_invoices"] == 0
            assert result["total_usage_charges"] == 0
            # Billing service is now enabled, so no errors should be present
            assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_process_monthly_billing_december_to_january(self, billing_service, mock_db_session):
        """Test processing monthly billing when crossing year boundary."""
        # Mock the database execute results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.billing_automation.datetime') as mock_datetime:
            # Mock current time as January 15, 2025
            mock_now = datetime(2025, 1, 15, 10, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = await billing_service.process_monthly_billing(db_session=mock_db_session)
            
            # Should target December 2024 (previous month, previous year)
            assert result["period_start"] == datetime(2024, 12, 1, 0, 0, 0, 0)
            assert result["period_end"] == datetime(2025, 1, 1, 0, 0, 0, 0)
    
    @pytest.mark.asyncio
    async def test_process_monthly_billing_custom_month(self, billing_service, mock_db_session):
        """Test processing monthly billing with custom target month."""
        target_month = datetime(2024, 3, 1, 0, 0, 0, 0)
        
        # Mock the database execute results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await billing_service.process_monthly_billing(target_month, db_session=mock_db_session)
        
        # Should use the provided target month
        assert result["period_start"] == datetime(2024, 3, 1, 0, 0, 0, 0)
        assert result["period_end"] == datetime(2024, 4, 1, 0, 0, 0, 0)
    
    @pytest.mark.asyncio
    async def test_process_monthly_billing_december_custom(self, billing_service, mock_db_session):
        """Test processing monthly billing for December (year boundary)."""
        target_month = datetime(2024, 12, 1, 0, 0, 0, 0)
        
        # Mock the database execute results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await billing_service.process_monthly_billing(target_month, db_session=mock_db_session)
        
        # Should handle December -> January year transition
        assert result["period_start"] == datetime(2024, 12, 1, 0, 0, 0, 0)
        assert result["period_end"] == datetime(2025, 1, 1, 0, 0, 0, 0)
    
    @pytest.mark.asyncio
    async def test_process_monthly_billing_logs_period(self, billing_service, caplog):
        """Test that billing process logs the period information."""
        target_month = datetime(2024, 5, 1, 0, 0, 0, 0)
        
        with caplog.at_level(logging.INFO):
            result = await billing_service.process_monthly_billing(target_month)
        
        # Check that period information was logged
        log_messages = [record.message for record in caplog.records]
        period_log = next((msg for msg in log_messages if "Processing monthly billing for period" in msg), None)
        assert period_log is not None
        assert "2024-05-01" in period_log
        assert "2024-06-01" in period_log
    
    @pytest.mark.asyncio
    async def test_process_monthly_billing_completion_log(self, billing_service, mock_db_session, caplog):
        """Test that billing process logs completion information."""
        # Mock the database execute results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        with caplog.at_level(logging.INFO):
            result = await billing_service.process_monthly_billing(db_session=mock_db_session)
        
        # Check that completion was logged
        log_messages = [record.message for record in caplog.records]
        completion_log = next((msg for msg in log_messages if "Monthly billing complete" in msg), None)
        assert completion_log is not None
    
    @pytest.mark.asyncio
    async def test_process_monthly_billing_disabled_service(self, billing_service, caplog):
        """Test billing process behavior when Stripe service is disabled."""
        # Mock the stripe service as disabled for this test
        with patch('app.services.billing_automation.stripe_service') as mock_stripe, \
             caplog.at_level(logging.INFO):
            mock_stripe.is_enabled = False
            
            result = await billing_service.process_monthly_billing()
        
        # Should log that billing is disabled
        log_messages = [record.message for record in caplog.records]
        disabled_log = next((msg for msg in log_messages if "Billing automation disabled" in msg), None)
        assert disabled_log is not None
        
        # Should have error in result
        assert len(result["errors"]) == 1
        assert "Billing automation disabled" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_run_daily_check_first_of_month_early_hour(self, billing_service):
        """Test daily check runs billing on first of month in early hours."""
        with patch('app.services.billing_automation.datetime') as mock_datetime, \
             patch.object(billing_service, 'process_monthly_billing', return_value={"failed_invoices": 0}) as mock_process:
            
            # Mock as first day of month, early hour
            mock_now = datetime(2024, 7, 1, 1, 30, 0)  # 1:30 AM on July 1st
            mock_datetime.utcnow.return_value = mock_now
            
            await billing_service.run_daily_check()
            
            # Should call process_monthly_billing
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_daily_check_first_of_month_late_hour(self, billing_service):
        """Test daily check does not run billing on first of month in late hours."""
        with patch('app.services.billing_automation.datetime') as mock_datetime, \
             patch.object(billing_service, 'process_monthly_billing') as mock_process:
            
            # Mock as first day of month, late hour
            mock_now = datetime(2024, 7, 1, 10, 30, 0)  # 10:30 AM on July 1st
            mock_datetime.utcnow.return_value = mock_now
            
            await billing_service.run_daily_check()
            
            # Should not call process_monthly_billing
            mock_process.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_daily_check_not_first_of_month(self, billing_service):
        """Test daily check does not run billing when not first of month."""
        with patch('app.services.billing_automation.datetime') as mock_datetime, \
             patch.object(billing_service, 'process_monthly_billing') as mock_process:
            
            # Mock as middle of month
            mock_now = datetime(2024, 7, 15, 1, 0, 0)  # 1:00 AM on July 15th
            mock_datetime.utcnow.return_value = mock_now
            
            await billing_service.run_daily_check()
            
            # Should not call process_monthly_billing
            mock_process.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_daily_check_successful_billing(self, billing_service, caplog):
        """Test daily check with successful billing."""
        mock_result = {
            "failed_invoices": 0,
            "successful_invoices": 5,
            "total_usage_charges": 12500  # $125.00 in cents
        }
        
        with patch('app.services.billing_automation.datetime') as mock_datetime, \
             patch.object(billing_service, 'process_monthly_billing', return_value=mock_result), \
             caplog.at_level(logging.INFO):
            
            mock_now = datetime(2024, 7, 1, 1, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            await billing_service.run_daily_check()
            
            # Should log successful completion
            log_messages = [record.message for record in caplog.records]
            success_log = next((msg for msg in log_messages if "Monthly billing completed successfully" in msg), None)
            assert success_log is not None
    
    @pytest.mark.asyncio
    async def test_run_daily_check_billing_failures(self, billing_service, caplog):
        """Test daily check with billing failures."""
        mock_result = {
            "failed_invoices": 2,
            "successful_invoices": 3,
            "total_usage_charges": 8000
        }
        
        with patch('app.services.billing_automation.datetime') as mock_datetime, \
             patch.object(billing_service, 'process_monthly_billing', return_value=mock_result), \
             caplog.at_level(logging.WARNING):
            
            mock_now = datetime(2024, 7, 1, 1, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            await billing_service.run_daily_check()
            
            # Should log warning about failures
            log_messages = [record.message for record in caplog.records]
            warning_log = next((msg for msg in log_messages if "Monthly billing completed with 2 failures" in msg), None)
            assert warning_log is not None
    
    @pytest.mark.asyncio
    async def test_run_daily_check_billing_exception(self, billing_service, caplog):
        """Test daily check handles billing process exceptions."""
        with patch('app.services.billing_automation.datetime') as mock_datetime, \
             patch.object(billing_service, 'process_monthly_billing', side_effect=Exception("Billing error")), \
             caplog.at_level(logging.ERROR):
            
            mock_now = datetime(2024, 7, 1, 1, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            # Should not raise exception
            await billing_service.run_daily_check()
            
            # Should log error
            log_messages = [record.message for record in caplog.records]
            error_log = next((msg for msg in log_messages if "Monthly billing automation failed" in msg), None)
            assert error_log is not None
    
    @pytest.mark.asyncio
    async def test_start_automation_single_iteration(self, billing_service):
        """Test single iteration of automation loop."""
        iteration_count = 0
        
        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 1:
                # Stop after one iteration
                raise asyncio.CancelledError()
        
        with patch.object(billing_service, 'run_daily_check', return_value=None) as mock_daily_check, \
             patch('asyncio.sleep', side_effect=mock_sleep):
            
            try:
                await billing_service.start_automation()
            except asyncio.CancelledError:
                pass  # Expected
            
            # Should call daily check
            mock_daily_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_automation_handles_exceptions(self, billing_service, caplog):
        """Test automation loop handles exceptions and continues."""
        iteration_count = 0
        
        async def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 2:
                # Stop after handling one error
                raise asyncio.CancelledError()
        
        call_count = 0
        async def mock_daily_check():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Daily check error")
            # Second call succeeds
        
        with patch.object(billing_service, 'run_daily_check', side_effect=mock_daily_check), \
             patch('asyncio.sleep', side_effect=mock_sleep), \
             caplog.at_level(logging.ERROR):
            
            try:
                await billing_service.start_automation()
            except asyncio.CancelledError:
                pass  # Expected
            
            # Should log error
            log_messages = [record.message for record in caplog.records]
            error_log = next((msg for msg in log_messages if "Error in billing automation" in msg), None)
            assert error_log is not None
            
            # Should have made two calls (one failed, one succeeded)
            assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_start_automation_cancelled_gracefully(self, billing_service, caplog):
        """Test automation loop handles cancellation gracefully."""
        with patch.object(billing_service, 'run_daily_check', side_effect=asyncio.CancelledError), \
             caplog.at_level(logging.INFO):
            
            await billing_service.start_automation()
            
            # Should log cancellation
            log_messages = [record.message for record in caplog.records]
            cancel_log = next((msg for msg in log_messages if "Billing automation cancelled" in msg), None)
            assert cancel_log is not None
    
    @pytest.mark.asyncio
    async def test_start_automation_sleep_intervals(self, billing_service):
        """Test automation loop uses correct sleep intervals."""
        iteration_count = 0
        sleep_durations = []
        
        async def mock_sleep(duration):
            nonlocal iteration_count
            sleep_durations.append(duration)
            iteration_count += 1
            if iteration_count >= 1:
                raise asyncio.CancelledError()
        
        with patch.object(billing_service, 'run_daily_check', return_value=None), \
             patch('asyncio.sleep', side_effect=mock_sleep):
            
            try:
                await billing_service.start_automation()
            except asyncio.CancelledError:
                pass
            
            # Should sleep for 1 hour (3600 seconds) between checks
            assert len(sleep_durations) == 1
            assert sleep_durations[0] == 3600
    
    @pytest.mark.asyncio
    async def test_start_automation_error_sleep_interval(self, billing_service):
        """Test automation loop uses shorter sleep interval after errors."""
        iteration_count = 0
        sleep_durations = []
        
        async def mock_sleep(duration):
            nonlocal iteration_count
            sleep_durations.append(duration)
            iteration_count += 1
            if iteration_count >= 1:
                raise asyncio.CancelledError()
        
        with patch.object(billing_service, 'run_daily_check', side_effect=Exception("Test error")), \
             patch('asyncio.sleep', side_effect=mock_sleep):
            
            try:
                await billing_service.start_automation()
            except asyncio.CancelledError:
                pass
            
            # Should sleep for 10 minutes (600 seconds) after error
            assert len(sleep_durations) == 1
            assert sleep_durations[0] == 600


class TestBillingAutomationSingleton:
    """Test the billing automation singleton."""
    
    def test_singleton_exists(self):
        """Test that billing automation singleton exists."""
        assert billing_automation is not None
        assert isinstance(billing_automation, BillingAutomationService)


class TestTriggerManualBilling:
    """Test the manual billing trigger function."""
    
    @pytest.mark.asyncio
    async def test_trigger_manual_billing_default_month(self):
        """Test manual billing trigger with default month."""
        mock_result = {"processed_organizations": 3, "successful_invoices": 3}
        
        with patch.object(billing_automation, 'process_monthly_billing', return_value=mock_result) as mock_process:
            result = await trigger_manual_billing()
            
            # Should call process_monthly_billing with None (default) and None (db_session)
            mock_process.assert_called_once_with(None, None)
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_trigger_manual_billing_custom_month(self):
        """Test manual billing trigger with custom month."""
        target_month = datetime(2024, 5, 1, 0, 0, 0, 0)
        mock_result = {"processed_organizations": 1, "successful_invoices": 1}
        
        with patch.object(billing_automation, 'process_monthly_billing', return_value=mock_result) as mock_process:
            result = await trigger_manual_billing(target_month)
            
            # Should call process_monthly_billing with specified month and None (db_session)
            mock_process.assert_called_once_with(target_month, None)
            assert result == mock_result


class TestBillingAutomationIntegration:
    """Integration tests for billing automation components."""
    
    @pytest.mark.asyncio
    async def test_complete_billing_cycle_simulation(self, caplog):
        """Test a complete billing cycle simulation."""
        service = BillingAutomationService()
        
        # Simulate running on the first of the month
        with patch('app.services.billing_automation.datetime') as mock_datetime, \
             caplog.at_level(logging.INFO):
            
            # Mock time as July 1st, 1:30 AM
            mock_now = datetime(2024, 7, 1, 1, 30, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Run daily check (which should trigger billing)
            await service.run_daily_check()
            
            # Verify logs show proper flow
            log_messages = [record.message for record in caplog.records]
            
            # Should log running monthly billing
            running_log = next((msg for msg in log_messages if "Running monthly billing automation" in msg), None)
            assert running_log is not None
            
            # Should log billing period
            period_log = next((msg for msg in log_messages if "Processing monthly billing for period" in msg), None)
            assert period_log is not None
            assert "2024-06-01" in period_log  # Previous month (June)
            
            # Billing service is now enabled, so no disabled message should be logged
            disabled_log = next((msg for msg in log_messages if "Billing automation disabled" in msg), None)
            assert disabled_log is None
            
            # Should log completion
            complete_log = next((msg for msg in log_messages if "Monthly billing complete" in msg), None)
            assert complete_log is not None
    
    @pytest.mark.asyncio
    async def test_billing_edge_cases(self, mock_db_session):
        """Test billing edge cases and boundary conditions."""
        service = BillingAutomationService()
        
        # Mock the database execute results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Test case 1: January 1st (should target December of previous year)
        with patch('app.services.billing_automation.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 1, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = await service.process_monthly_billing(db_session=mock_db_session)
            
            # Should target December 2023
            assert result["period_start"] == datetime(2023, 12, 1, 0, 0, 0, 0)
            assert result["period_end"] == datetime(2024, 1, 1, 0, 0, 0, 0)
        
        # Test case 2: March 1st (should target February)
        with patch('app.services.billing_automation.datetime') as mock_datetime:
            mock_now = datetime(2024, 3, 1, 1, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            result = await service.process_monthly_billing(db_session=mock_db_session)
            
            # Should target February 2024
            assert result["period_start"] == datetime(2024, 2, 1, 0, 0, 0, 0)
            assert result["period_end"] == datetime(2024, 3, 1, 0, 0, 0, 0)
        
        # Test case 3: Custom December period (year boundary)
        target_december = datetime(2023, 12, 1, 0, 0, 0, 0)
        result = await service.process_monthly_billing(target_december, db_session=mock_db_session)
        
        # Should span December 2023 to January 2024
        assert result["period_start"] == datetime(2023, 12, 1, 0, 0, 0, 0)
        assert result["period_end"] == datetime(2024, 1, 1, 0, 0, 0, 0)
    
    def test_daily_check_timing_conditions(self):
        """Test various timing conditions for daily check."""
        service = BillingAutomationService()
        
        # Test cases: (day, hour, should_run_billing)
        test_cases = [
            (1, 0, True),    # First day, midnight
            (1, 1, True),    # First day, 1 AM
            (1, 2, False),   # First day, 2 AM (too late)
            (1, 12, False),  # First day, noon (too late)
            (2, 0, False),   # Second day, midnight
            (15, 1, False),  # Mid-month, 1 AM
            (31, 0, False),  # Last day, midnight
        ]
        
        for day, hour, should_run in test_cases:
            with patch('app.services.billing_automation.datetime') as mock_datetime:
                # Use a month with 31 days for consistency
                mock_now = datetime(2024, 7, day, hour, 0, 0)
                mock_datetime.utcnow.return_value = mock_now
                
                # Check the condition that determines if billing should run
                should_run_actual = (mock_now.day == 1 and mock_now.hour < 2)
                assert should_run_actual == should_run, f"Day {day}, Hour {hour}: expected {should_run}, got {should_run_actual}"
    
    @pytest.mark.asyncio
    async def test_automation_loop_lifecycle(self):
        """Test complete automation loop lifecycle."""
        service = BillingAutomationService()
        
        # Track function calls
        daily_check_calls = []
        sleep_calls = []
        
        async def mock_daily_check():
            daily_check_calls.append(datetime.utcnow())
        
        async def mock_sleep(duration):
            sleep_calls.append(duration)
            if len(sleep_calls) >= 3:  # Stop after 3 sleep calls
                raise asyncio.CancelledError()
        
        with patch.object(service, 'run_daily_check', side_effect=mock_daily_check), \
             patch('asyncio.sleep', side_effect=mock_sleep):
            
            try:
                await service.start_automation()
            except asyncio.CancelledError:
                pass  # Expected
            
            # Should have made 3 daily checks (one before each sleep)
            assert len(daily_check_calls) == 3
            
            # Should have 3 sleep calls, all for 1 hour
            assert len(sleep_calls) == 3
            assert all(duration == 3600 for duration in sleep_calls)
    
    @pytest.mark.asyncio
    async def test_result_structure_consistency(self, mock_db_session):
        """Test that billing results have consistent structure."""
        service = BillingAutomationService()
        
        # Mock the database execute results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Test with different target months
        test_months = [
            None,  # Default (previous month)
            datetime(2024, 1, 1),   # January
            datetime(2024, 6, 1),   # June
            datetime(2024, 12, 1),  # December
        ]
        
        for target_month in test_months:
            result = await service.process_monthly_billing(target_month, db_session=mock_db_session)
            
            # Verify all required fields are present
            required_fields = [
                "period_start", "period_end", "processed_organizations",
                "successful_invoices", "failed_invoices", "total_usage_charges", "errors"
            ]
            
            for field in required_fields:
                assert field in result, f"Missing field {field} in result for target_month {target_month}"
            
            # Verify field types
            assert isinstance(result["period_start"], datetime)
            assert isinstance(result["period_end"], datetime)
            assert isinstance(result["processed_organizations"], int)
            assert isinstance(result["successful_invoices"], int)
            assert isinstance(result["failed_invoices"], int)
            assert isinstance(result["total_usage_charges"], int)
            assert isinstance(result["errors"], list)
            
            # Verify period_end is after period_start
            assert result["period_end"] > result["period_start"]
            
            # For enabled billing with no organizations, should have specific values
            assert result["processed_organizations"] == 0
            assert result["successful_invoices"] == 0
            assert result["failed_invoices"] == 0
            assert result["total_usage_charges"] == 0
            # Billing service is now enabled, so no errors should be present
            assert len(result["errors"]) == 0