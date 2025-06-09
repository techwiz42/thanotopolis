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
from app.models.models import User, Tenant, StripeCustomer, StripeSubscription, StripeInvoice
from app.schemas.schemas import (
    StripeCustomerCreate, StripeCustomerResponse,
    StripeSubscriptionCreate, StripeSubscriptionResponse,
    StripeInvoiceResponse, BillingDashboardResponse,
    UsageStats
)
from app.services.stripe_service import stripe_service
from app.services.usage_service import usage_service

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger(__name__)


@router.post("/customer", response_model=StripeCustomerResponse)
async def create_customer(
    customer_data: StripeCustomerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe customer for the organization"""
    
    try:
        customer = await stripe_service.create_customer(
            db=db,
            tenant_id=current_user.tenant_id,
            customer_data=customer_data
        )
        return customer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating customer: {e}")
        raise HTTPException(status_code=500, detail="Failed to create customer")


@router.get("/customer", response_model=StripeCustomerResponse)
async def get_customer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the Stripe customer for the organization"""
    
    result = await db.execute(
        select(StripeCustomer).where(StripeCustomer.tenant_id == current_user.tenant_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="No billing customer found")
    
    return customer


@router.post("/subscription", response_model=StripeSubscriptionResponse)
async def create_subscription(
    subscription_data: StripeSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a monthly subscription for the organization"""
    
    # Get customer
    customer_result = await db.execute(
        select(StripeCustomer).where(StripeCustomer.tenant_id == current_user.tenant_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="No billing customer found. Create customer first.")
    
    try:
        subscription = await stripe_service.create_subscription(
            db=db,
            customer_id=customer.id,
            subscription_data=subscription_data
        )
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.get("/subscription", response_model=StripeSubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current subscription for the organization"""
    
    # Get customer and subscription
    result = await db.execute(
        select(StripeSubscription)
        .join(StripeCustomer)
        .where(StripeCustomer.tenant_id == current_user.tenant_id)
        .where(StripeSubscription.status.in_(["active", "trialing", "past_due"]))
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    return subscription


@router.get("/invoices", response_model=List[StripeInvoiceResponse])
async def get_invoices(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent invoices for the organization"""
    
    result = await db.execute(
        select(StripeInvoice)
        .join(StripeCustomer)
        .where(StripeCustomer.tenant_id == current_user.tenant_id)
        .order_by(StripeInvoice.created_at.desc())
        .limit(limit)
    )
    invoices = result.scalars().all()
    
    return invoices


@router.get("/dashboard", response_model=BillingDashboardResponse)
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


async def get_organization_billing_dashboard(db: AsyncSession, tenant_id: UUID) -> BillingDashboardResponse:
    """Get billing dashboard for a specific organization"""
    
    # Get current subscription
    subscription_result = await db.execute(
        select(StripeSubscription)
        .join(StripeCustomer)
        .where(StripeCustomer.tenant_id == tenant_id)
        .where(StripeSubscription.status.in_(["active", "trialing", "past_due"]))
    )
    current_subscription = subscription_result.scalar_one_or_none()
    
    # Get recent invoices
    invoices_result = await db.execute(
        select(StripeInvoice)
        .join(StripeCustomer)
        .where(StripeCustomer.tenant_id == tenant_id)
        .order_by(StripeInvoice.created_at.desc())
        .limit(5)
    )
    recent_invoices = invoices_result.scalars().all()
    
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
    
    return BillingDashboardResponse(
        current_subscription=current_subscription,
        recent_invoices=recent_invoices,
        current_period_usage=current_period_usage,
        upcoming_charges=upcoming_charges
    )


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
        # Get subscription
        subscription_result = await db.execute(
            select(StripeSubscription)
            .join(StripeCustomer)
            .where(StripeCustomer.tenant_id == org.id)
            .where(StripeSubscription.status.in_(["active", "trialing", "past_due"]))
        )
        subscription = subscription_result.scalar_one_or_none()
        
        # Get usage stats
        usage_stats = await usage_service.get_usage_stats(
            db=db,
            tenant_id=org.id,
            start_date=period_start,
            end_date=now,
            period="month"
        )
        
        # Get recent invoices
        invoices_result = await db.execute(
            select(StripeInvoice)
            .join(StripeCustomer)
            .where(StripeCustomer.tenant_id == org.id)
            .order_by(StripeInvoice.created_at.desc())
            .limit(3)
        )
        invoices = invoices_result.scalars().all()
        
        voice_words = usage_stats.total_stt_words + usage_stats.total_tts_words
        voice_charges = int((voice_words / 1000) * 100)
        subscription_revenue = subscription.amount_cents if subscription else 0
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


@router.post("/generate-usage-invoice")
async def generate_usage_invoice(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate usage invoice for the current billing period (admin/testing only)"""
    
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get customer
    customer_result = await db.execute(
        select(StripeCustomer).where(StripeCustomer.tenant_id == current_user.tenant_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="No billing customer found")
    
    # Calculate usage for current month
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    usage = await stripe_service.calculate_monthly_usage(
        db=db,
        tenant_id=current_user.tenant_id,
        period_start=period_start,
        period_end=now
    )
    
    if usage["voice_usage_cents"] == 0:
        return {"message": "No usage charges for current period"}
    
    # Create usage invoice
    from app.schemas.schemas import UsageBillingCreate
    usage_data = UsageBillingCreate(
        period_start=period_start,
        period_end=now,
        voice_words_count=usage["voice_words_count"],
        voice_usage_cents=usage["voice_usage_cents"]
    )
    
    try:
        invoice = await stripe_service.create_usage_invoice(
            db=db,
            customer_id=customer.id,
            usage_data=usage_data
        )
        return {"message": "Usage invoice created", "invoice_id": str(invoice.id)}
    except Exception as e:
        logger.error(f"Error creating usage invoice: {e}")
        raise HTTPException(status_code=500, detail="Failed to create usage invoice")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    # Verify webhook signature
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        if endpoint_secret and endpoint_secret != "whsec_":
            # Verify signature for security
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            # For development/testing - parse directly (INSECURE)
            import json
            event = json.loads(payload)
            logger.warning("Webhook signature verification disabled - for development only")
        
        success = await stripe_service.handle_webhook(event)
        
        if success:
            return JSONResponse(content={"status": "success"})
        else:
            return JSONResponse(content={"status": "error"}, status_code=400)
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(content={"status": "error"}, status_code=400)


@router.get("/subscription-plans")
async def get_subscription_plans():
    """Get available subscription plans"""
    from app.core.config import settings
    
    plans = []
    
    if hasattr(settings, 'STRIPE_PRICE_BASIC_SUB') and settings.STRIPE_PRICE_BASIC_SUB:
        plans.append({
            "id": "basic",
            "name": "Basic Plan",
            "price_id": settings.STRIPE_PRICE_BASIC_SUB,
            "amount_cents": 2900,  # $29.00
            "currency": "usd",
            "interval": "month",
            "features": [
                "Up to 5 users",
                "Voice transcription",
                "Basic support"
            ]
        })
    
    if hasattr(settings, 'STRIPE_PRICE_PRO_SUB') and settings.STRIPE_PRICE_PRO_SUB:
        plans.append({
            "id": "pro",
            "name": "Subscription to Thanotopolis.com", 
            "price_id": settings.STRIPE_PRICE_PRO_SUB,
            "amount_cents": 9900,  # $99.00
            "currency": "usd",
            "interval": "month",
            "features": [
                "Unlimited users",
                "Voice transcription & synthesis",
                "Priority support",
                "Advanced analytics"
            ]
        })
    
    return {"plans": plans}


@router.post("/start-subscription")
async def start_subscription(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start subscription process - returns Stripe checkout URL"""
    
    body = await request.json()
    plan_id = body.get("plan_id")
    
    if not plan_id:
        raise HTTPException(status_code=400, detail="Plan ID required")
    
    # Get or create customer
    customer_result = await db.execute(
        select(StripeCustomer).where(StripeCustomer.tenant_id == current_user.tenant_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        # Create customer first
        from app.schemas.schemas import StripeCustomerCreate
        customer_data = StripeCustomerCreate(
            email=current_user.email,
            name=f"{current_user.first_name} {current_user.last_name}".strip() or current_user.username
        )
        customer = await stripe_service.create_customer(
            db=db,
            tenant_id=current_user.tenant_id,
            customer_data=customer_data
        )
    
    # Get plan details
    plans_response = await get_subscription_plans()
    plan = next((p for p in plans_response["plans"] if p["id"] == plan_id), None)
    
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan selected")
    
    try:
        # Create Stripe checkout session
        import stripe
        checkout_session = stripe.checkout.Session.create(
            customer=customer.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan["price_id"],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{request.headers.get('referer', 'http://localhost:3000')}/billing?success=true",
            cancel_url=f"{request.headers.get('referer', 'http://localhost:3000')}/billing?cancelled=true",
            metadata={
                'tenant_id': str(current_user.tenant_id),
                'user_id': str(current_user.id)
            }
        )
        
        return {"checkout_url": checkout_session.url}
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")