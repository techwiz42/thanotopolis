"""
Billing API endpoints for Stripe integration
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import stripe
import logging

from app.db.database import get_db
from app.auth.auth import get_current_user
from app.models.models import User, Tenant
from app.schemas.schemas import UsageStats
from app.services.usage_service import usage_service

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger(__name__)


# Stripe billing endpoints temporarily disabled










@router.get("/dashboard")
async def get_billing_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive billing dashboard data"""
    
    if current_user.role == "super_admin":
        # Super admin sees all organizations
        return await get_super_admin_billing_dashboard(db)
    else:
        # Regular admin sees only their organization
        return await get_organization_billing_dashboard(db, current_user.tenant_id)


async def get_organization_billing_dashboard(db: AsyncSession, tenant_id: UUID) -> Dict[str, Any]:
    """Get billing dashboard for a specific organization"""
    
    # Get current period usage
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    current_period_usage = await usage_service.get_usage_stats(
        db=db,
        tenant_id=tenant_id,
        start_date=period_start,
        end_date=now,
        period="month"
    )
    
    # Calculate upcoming charges
    upcoming_voice_words = current_period_usage.total_stt_words + current_period_usage.total_tts_words
    upcoming_voice_cents = int((upcoming_voice_words / 1000) * 100)  # $1.00 per 1000 words
    
    upcoming_charges = {
        "voice_usage_cents": upcoming_voice_cents,
        "voice_words_count": upcoming_voice_words
    }
    
    return {
        "current_subscription": None,
        "recent_invoices": [],
        "current_period_usage": current_period_usage,
        "upcoming_charges": upcoming_charges
    }


async def get_super_admin_billing_dashboard(db: AsyncSession) -> Dict[str, Any]:
    """Get billing dashboard for super admin showing all organizations"""
    
    # Get all organizations with their billing data
    organizations_result = await db.execute(
        select(Tenant).where(Tenant.is_active == True)
    )
    organizations = organizations_result.scalars().all()
    
    org_billing_data = []
    total_revenue = 0
    total_voice_words = 0
    
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    for org in organizations:
        # No subscription data available
        subscription = None
        
        # Get usage stats
        usage_stats = await usage_service.get_usage_stats(
            db=db,
            tenant_id=org.id,
            start_date=period_start,
            end_date=now,
            period="month"
        )
        
        # No invoice data available
        invoices = []
        
        voice_words = usage_stats.total_stt_words + usage_stats.total_tts_words
        voice_charges = int((voice_words / 1000) * 100)
        subscription_revenue = 0
        total_revenue += subscription_revenue + voice_charges
        total_voice_words += voice_words
        
        org_billing_data.append({
            "organization_id": str(org.id),
            "organization_name": org.name,
            "subdomain": org.subdomain,
            "subscription": subscription,
            "subscription_revenue_cents": subscription_revenue,
            "voice_words_count": voice_words,
            "voice_charges_cents": voice_charges,
            "total_charges_cents": subscription_revenue + voice_charges,
            "recent_invoices": invoices,
            "usage_stats": usage_stats
        })
    
    return {
        "view_type": "super_admin",
        "total_organizations": len(organizations),
        "total_revenue_cents": total_revenue,
        "total_voice_words": total_voice_words,
        "organizations": org_billing_data,
        "summary": {
            "period_start": period_start,
            "period_end": now,
            "total_subscription_revenue": sum(org["subscription_revenue_cents"] for org in org_billing_data),
            "total_usage_revenue": sum(org["voice_charges_cents"] for org in org_billing_data)
        }
    }








