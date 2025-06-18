# backend/tests/unit/test_telephony_service.py
"""
Unit tests for telephony service functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.telephony_service import TelephonyService, telephony_service
from app.models.models import (
    TelephonyConfiguration, PhoneVerificationAttempt, PhoneCall,
    PhoneVerificationStatus, CallStatus, CallDirection, Tenant
)


class TestTelephonyService:
    """Test cases for TelephonyService"""
    
    @pytest.fixture
    def service(self):
        """Create telephony service instance for testing"""
        return TelephonyService()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def sample_tenant_id(self):
        """Sample tenant ID for testing"""
        return uuid4()
    
    def test_normalize_phone_number(self, service):
        """Test phone number normalization"""
        # Test various input formats
        test_cases = [
            ("(555) 123-4567", "+15551234567"),
            ("555-123-4567", "+15551234567"),
            ("555.123.4567", "+15551234567"),
            ("5551234567", "+15551234567"),
            ("+1 555 123 4567", "+15551234567"),
            ("1-555-123-4567", "+15551234567"),
            ("", None),
            ("invalid", None)
        ]
        
        for input_number, expected in test_cases:
            result = service._normalize_phone_number(input_number)
            assert result == expected, f"Failed for input: {input_number}"
    
    def test_format_phone_number(self, service):
        """Test phone number formatting for display"""
        test_cases = [
            ("+15551234567", "(555) 123-4567"),
            ("+15551234567", "(555) 123-4567"),
            ("", ""),
            ("+441234567890", "+441234567890")  # Non-US number
        ]
        
        for input_number, expected in test_cases:
            result = service._format_phone_number(input_number)
            assert result == expected, f"Failed for input: {input_number}"
    
    def test_extract_country_code(self, service):
        """Test country code extraction"""
        test_cases = [
            ("+15551234567", "US"),
            ("+441234567890", "US"),  # Default to US for now
            ("", "US")
        ]
        
        for input_number, expected in test_cases:
            result = service._extract_country_code(input_number)
            assert result == expected
    
    def test_default_business_hours(self, service):
        """Test default business hours configuration"""
        hours = service._default_business_hours()
        
        # Check structure
        assert isinstance(hours, dict)
        
        # Check weekdays
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        for day in weekdays:
            assert day in hours
            assert hours[day]['start'] == '09:00'
            assert hours[day]['end'] == '17:00'
        
        # Check weekend
        assert hours['saturday']['start'] == '10:00'
        assert hours['saturday']['end'] == '14:00'
        assert hours['sunday']['start'] == 'closed'
        assert hours['sunday']['end'] == 'closed'
    
    @pytest.mark.asyncio
    async def test_setup_organization_phone_new(self, service, mock_db, sample_tenant_id):
        """Test setting up phone for new organization"""
        phone_number = "(555) 123-4567"
        welcome_message = "Hello, welcome to our service!"
        
        # Mock database responses
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = Mock()
        
        # Mock no existing config
        config_result = Mock()
        config_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.return_value = config_result
        
        # Mock platform phone number assignment
        with patch.object(service, '_assign_platform_phone_number', return_value="+15559999999"):
            # Test
            result = await service.setup_organization_phone(
                db=mock_db,
                tenant_id=sample_tenant_id,
                organization_phone_number=phone_number,
                welcome_message=welcome_message
            )
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_organization_phone_duplicate(self, service, mock_db, sample_tenant_id):
        """Test error when phone number already exists"""
        phone_number = "(555) 123-4567"
        
        # Mock existing config with updated configuration
        existing_config = TelephonyConfiguration(
            id=uuid4(),
            tenant_id=sample_tenant_id,
            organization_phone_number="+15551234567",
            formatted_phone_number="(555) 123-4567",
            country_code="US",
            platform_phone_number="+15559999999",
            verification_status=PhoneVerificationStatus.PENDING.value
        )
        
        existing_result = Mock()
        existing_result.scalar_one_or_none.return_value = existing_config
        
        # Mock database responses
        mock_db.execute = AsyncMock(return_value=existing_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test should update existing configuration
        result = await service.setup_organization_phone(
            db=mock_db,
            tenant_id=sample_tenant_id,
            organization_phone_number=phone_number
        )
        
        # Verify config was updated (commit called)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_organization_phone_invalid_number(self, service, mock_db, sample_tenant_id):
        """Test error with invalid phone number"""
        invalid_phone = "invalid-phone"
        
        # Test should raise ValueError
        with pytest.raises(ValueError, match="Invalid phone number format"):
            await service.setup_organization_phone(
                db=mock_db,
                tenant_id=sample_tenant_id,
                organization_phone_number=invalid_phone
            )
    
    @pytest.mark.asyncio
    @patch('app.services.telephony_service.secrets.randbelow')
    async def test_initiate_phone_verification(self, mock_randbelow, service, mock_db, sample_tenant_id):
        """Test initiating phone verification"""
        mock_randbelow.return_value = 123456  # Fixed verification code
        
        # Mock telephony config
        config = TelephonyConfiguration(
            id=uuid4(),
            tenant_id=sample_tenant_id,
            organization_phone_number="+15551234567",
            formatted_phone_number="(555) 123-4567",
            country_code="US",
            platform_phone_number="+15559999999",
            verification_status=PhoneVerificationStatus.PENDING.value
        )
        
        config_result = Mock()
        config_result.scalar_one_or_none.return_value = config
        
        mock_db.execute = AsyncMock(return_value=config_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock successful SMS sending
        with patch.object(service, '_send_verification_code', return_value=True):
            result = await service.initiate_phone_verification(
                db=mock_db,
                tenant_id=sample_tenant_id
            )
        
        # Verify verification attempt was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        
        # Check verification code was set
        verification_attempt = mock_db.add.call_args[0][0]
        assert verification_attempt.verification_code == "223456"  # 100000 + 123456
    
    @pytest.mark.asyncio
    async def test_verify_phone_number_success(self, service, mock_db, sample_tenant_id):
        """Test successful phone verification"""
        verification_code = "123456"
        
        # Mock verification attempt
        verification = PhoneVerificationAttempt(
            id=uuid4(),
            telephony_config_id=uuid4(),
            verification_code=verification_code,
            status=PhoneVerificationStatus.PENDING.value,
            attempts_count=0,
            max_attempts=3,
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        
        verification_result = Mock()
        verification_result.scalar_one_or_none.return_value = verification
        
        mock_db.execute = AsyncMock(return_value=verification_result)
        mock_db.commit = AsyncMock()
        
        # Test successful verification
        result = await service.verify_phone_number(
            db=mock_db,
            tenant_id=sample_tenant_id,
            verification_code=verification_code
        )
        
        assert result is True
        assert verification.status == PhoneVerificationStatus.VERIFIED.value
        assert verification.verified_at is not None
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_verify_phone_number_invalid_code(self, service, mock_db, sample_tenant_id):
        """Test phone verification with invalid code"""
        verification_code = "123456"
        wrong_code = "654321"
        
        # Mock verification attempt
        verification = PhoneVerificationAttempt(
            id=uuid4(),
            telephony_config_id=uuid4(),
            verification_code=verification_code,
            status=PhoneVerificationStatus.PENDING.value,
            attempts_count=0,
            max_attempts=3,
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        
        verification_result = Mock()
        verification_result.scalar_one_or_none.return_value = verification
        
        mock_db.execute = AsyncMock(return_value=verification_result)
        mock_db.commit = AsyncMock()
        
        # Test failed verification
        result = await service.verify_phone_number(
            db=mock_db,
            tenant_id=sample_tenant_id,
            verification_code=wrong_code
        )
        
        assert result is False
        assert verification.attempts_count == 1
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_incoming_call(self, service, mock_db):
        """Test handling incoming call"""
        call_sid = "CA123456789"
        caller_number = "+15551234567"
        called_number = "+15559876543"
        
        # Mock telephony config
        config = TelephonyConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            organization_phone_number=called_number,
            platform_phone_number=called_number,
            formatted_phone_number="(555) 987-6543",
            country_code="US",
            is_enabled=True,
            verification_status=PhoneVerificationStatus.VERIFIED.value,
            max_concurrent_calls=5
        )
        
        # Mock no active calls
        config_result = Mock()
        config_result.scalar_one_or_none.return_value = config
        
        active_calls_result = Mock()
        active_calls_result.all.return_value = []  # No active calls
        
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [config_result, active_calls_result]
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await service.handle_incoming_call(
            db=mock_db,
            call_sid=call_sid,
            customer_number=caller_number,
            platform_number=called_number
        )
        
        # Verify call was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Check call properties
        call = mock_db.add.call_args[0][0]
        assert call.call_sid == call_sid
        assert call.customer_phone_number == caller_number
        assert call.platform_phone_number == called_number
        assert call.direction == CallDirection.INBOUND.value
        assert call.status == CallStatus.INCOMING.value
    
    @pytest.mark.asyncio
    async def test_handle_incoming_call_max_concurrent_reached(self, service, mock_db):
        """Test error when max concurrent calls reached"""
        call_sid = "CA123456789"
        caller_number = "+15551234567"
        called_number = "+15559876543"
        
        # Mock telephony config
        config = TelephonyConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            organization_phone_number=called_number,
            platform_phone_number=called_number,
            formatted_phone_number="(555) 987-6543",
            country_code="US",
            is_enabled=True,
            verification_status=PhoneVerificationStatus.VERIFIED.value,
            max_concurrent_calls=1
        )
        
        # Mock one active call (at limit)
        config_result = Mock()
        config_result.scalar_one_or_none.return_value = config
        
        active_calls_result = Mock()
        active_calls_result.all.return_value = [Mock()]  # One active call
        
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [config_result, active_calls_result]
        
        # Test should raise ValueError
        with pytest.raises(ValueError, match="Maximum concurrent calls reached"):
            await service.handle_incoming_call(
                db=mock_db,
                call_sid=call_sid,
                customer_number=caller_number,
                platform_number=called_number
            )
    
    @pytest.mark.asyncio
    async def test_update_call_status(self, service, mock_db):
        """Test updating call status"""
        call_sid = "CA123456789"
        new_status = CallStatus.COMPLETED
        
        # Mock existing call
        call = PhoneCall(
            id=uuid4(),
            call_sid=call_sid,
            status=CallStatus.IN_PROGRESS.value,
            answer_time=datetime.utcnow() - timedelta(minutes=5)  # 5 minutes ago
        )
        
        call_result = Mock()
        call_result.scalar_one_or_none.return_value = call
        
        mock_db.execute = AsyncMock(return_value=call_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock usage recording
        with patch.object(service, '_record_call_usage', return_value=None):
            result = await service.update_call_status(
                db=mock_db,
                call_sid=call_sid,
                status=new_status
            )
        
        # Verify status updated
        assert call.status == CallStatus.COMPLETED.value
        assert call.end_time is not None
        assert call.duration_seconds is not None
        assert call.duration_seconds > 0
        
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called()
    
    @patch('app.services.telephony_service.TwilioClient')
    def test_send_verification_code_mock_mode(self, mock_twilio_client, service):
        """Test sending verification code in mock mode"""
        # Service without Twilio client (mock mode)
        service.twilio_client = None
        
        result = asyncio.run(service._send_verification_code(
            organization_phone_number="+15551234567",
            verification_code="123456",
            method="sms"
        ))
        
        # Should return True in mock mode
        assert result is True


@pytest.mark.integration
class TestTelephonyServiceIntegration:
    """Integration tests for telephony service"""
    
    @pytest.mark.asyncio
    async def test_full_phone_setup_workflow(self):
        """Test complete phone setup workflow"""
        # This would test the full workflow with a real database
        # Placeholder for integration test
        pass
    
    @pytest.mark.asyncio 
    async def test_verification_workflow(self):
        """Test complete verification workflow"""
        # This would test verification with real database
        # Placeholder for integration test
        pass
