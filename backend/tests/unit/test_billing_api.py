"""
Tests for billing API endpoints.
Tests billing dashboard and usage statistics functionality.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from app.main import app
from app.auth.auth import get_current_user
from app.db.database import get_db
from app.models.models import User, Tenant
from app.schemas.schemas import UsageStats


@pytest.mark.asyncio
async def test_get_billing_dashboard_organization():
    """Test billing dashboard for organization user."""
    from httpx import ASGITransport
    
    # Create mock user with proper tenant_id
    mock_user = Mock(spec=User)
    mock_user.id = uuid4()
    mock_user.email = "test@example.com"
    mock_user.role = "user"
    mock_user.tenant_id = uuid4()
    mock_user.is_active = True
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        with patch('app.services.usage_service.usage_service.get_usage_stats') as mock_usage:
            mock_usage.return_value = UsageStats(
                period="month",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                total_tokens=50000,
                total_tts_words=1000,
                total_stt_words=800,
                total_cost_cents=500
            )
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/billing/dashboard")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "current_subscription" in data
            assert "current_period_usage" in data
            assert "upcoming_charges" in data
            assert data["current_subscription"] is None  # No Stripe integration
            assert data["recent_invoices"] == []  # No Stripe invoices
            
            # Check usage stats
            assert data["current_period_usage"]["total_tokens"] == 50000
            assert data["current_period_usage"]["total_tts_words"] == 1000
            assert data["current_period_usage"]["total_stt_words"] == 800
            
            # Check upcoming charges calculation
            total_voice_words = 1000 + 800  # TTS + STT
            expected_cents = int((total_voice_words / 1000) * 100)  # $1.00 per 1000 words
            assert data["upcoming_charges"]["voice_usage_cents"] == expected_cents
            assert data["upcoming_charges"]["voice_words_count"] == total_voice_words
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_billing_dashboard_no_usage():
    """Test billing dashboard when organization has no usage."""
    from httpx import ASGITransport
    
    # Create mock user
    mock_user = Mock(spec=User)
    mock_user.id = uuid4()
    mock_user.email = "test@example.com"
    mock_user.role = "user"
    mock_user.tenant_id = uuid4()
    mock_user.is_active = True
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        with patch('app.services.usage_service.usage_service.get_usage_stats') as mock_usage:
            mock_usage.return_value = UsageStats(
                period="month",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                total_tokens=0,
                total_tts_words=0,
                total_stt_words=0,
                total_cost_cents=0
            )
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/billing/dashboard")
        
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Check usage stats are zero
            assert data["current_period_usage"]["total_tokens"] == 0
            assert data["current_period_usage"]["total_tts_words"] == 0
            assert data["current_period_usage"]["total_stt_words"] == 0
            assert data["current_period_usage"]["total_cost_cents"] == 0
            
            # Check upcoming charges are zero
            assert data["upcoming_charges"]["voice_usage_cents"] == 0
            assert data["upcoming_charges"]["voice_words_count"] == 0
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_billing_dashboard_org_admin():
    """Test billing dashboard access for organization admin."""
    from httpx import ASGITransport
    
    # Create mock org admin user
    mock_user = Mock(spec=User)
    mock_user.id = uuid4()
    mock_user.email = "orgadmin@example.com"
    mock_user.role = "org_admin"
    mock_user.tenant_id = uuid4()
    mock_user.is_active = True
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        with patch('app.services.usage_service.usage_service.get_usage_stats') as mock_usage:
            mock_usage.return_value = UsageStats(
                period="month",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                total_tokens=25000,
                total_tts_words=500,
                total_stt_words=400,
                total_cost_cents=250
            )
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/billing/dashboard")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Org admin should see their organization's dashboard
            assert "current_period_usage" in data
            assert "upcoming_charges" in data
            assert data["current_period_usage"]["total_tokens"] == 25000
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_billing_dashboard_regular_admin():
    """Test billing dashboard access for regular admin."""
    from httpx import ASGITransport
    
    # Create mock admin user
    mock_user = Mock(spec=User)
    mock_user.id = uuid4()
    mock_user.email = "admin@example.com"
    mock_user.role = "admin"
    mock_user.tenant_id = uuid4()
    mock_user.is_active = True
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        with patch('app.services.usage_service.usage_service.get_usage_stats') as mock_usage:
            mock_usage.return_value = UsageStats(
                period="month",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                total_tokens=35000,
                total_tts_words=700,
                total_stt_words=600,
                total_cost_cents=350
            )
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/billing/dashboard")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Regular admin should see their organization's dashboard
            assert "current_period_usage" in data
            assert "upcoming_charges" in data
            assert data["current_period_usage"]["total_tokens"] == 35000
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_billing_dashboard_requires_auth():
    """Test that billing dashboard requires authentication."""
    from httpx import ASGITransport
    
    # Clear any dependency overrides to ensure no auth
    app.dependency_overrides.clear()
    
    # No auth mock, should get 401 or 403
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/billing/dashboard")
    
    # Note: FastAPI returns 403 when dependency injection fails, not 401
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.asyncio
async def test_billing_dashboard_usage_calculation():
    """Test correct calculation of voice usage charges."""
    from httpx import ASGITransport
    
    # Create mock user
    mock_user = Mock(spec=User)
    mock_user.id = uuid4()
    mock_user.email = "test@example.com"
    mock_user.role = "user"
    mock_user.tenant_id = uuid4()
    mock_user.is_active = True
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    test_cases = [
        # (tts_words, stt_words, expected_cents)
        (0, 0, 0),          # No usage
        (500, 500, 100),    # Exactly 1000 words = $1.00
        (1500, 500, 200),   # 2000 words = $2.00
        (999, 0, 99),       # Just under 1000 words
        (1001, 0, 100),     # Just over 1000 words
        (2500, 2500, 500),  # 5000 words = $5.00
    ]
    
    for tts_words, stt_words, expected_cents in test_cases:
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            with patch('app.services.usage_service.usage_service.get_usage_stats') as mock_usage:
                mock_usage.return_value = UsageStats(
                    period="month",
                    start_date=datetime.utcnow() - timedelta(days=30),
                    end_date=datetime.utcnow(),
                    total_tokens=10000,
                    total_tts_words=tts_words,
                    total_stt_words=stt_words,
                    total_cost_cents=0  # Not used in calculation
                )
                
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.get("/api/billing/dashboard")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                
                total_words = tts_words + stt_words
                assert data["upcoming_charges"]["voice_words_count"] == total_words
                assert data["upcoming_charges"]["voice_usage_cents"] == expected_cents
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()
