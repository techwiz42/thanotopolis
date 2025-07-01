"""
Billing API endpoints for Stripe integration
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import stripe
import logging
from pydantic import BaseModel

from app.db.database import get_db
from app.auth.auth import get_current_user
from app.models.models import User, Tenant, UsageRecord
from app.models.stripe_models import StripeCustomer, StripeSubscription, StripeInvoice
from app.schemas.schemas import UsageStats
from app.services.usage_service import usage_service
from app.services.stripe_service import stripe_service
from app.core.config import settings

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger(__name__)


class CreateSubscriptionRequest(BaseModel):
    price_id: Optional[str] = None
    trial_days: int = 0


class CreateCheckoutSessionRequest(BaseModel):
    success_url: str
    cancel_url: str
    trial_days: int = 0


class OrganizationSignupRequest(BaseModel):
    success_url: str
    cancel_url: str
    trial_days: int = 0
    customer_email: str
    organization_name: str


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a Stripe checkout session for new subscription"""
    
    try:
        checkout_session_data = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price': settings.STRIPE_MONTHLY_PRICE_ID,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': request.success_url,
            'cancel_url': request.cancel_url,
            'allow_promotion_codes': True,
            'automatic_tax': {'enabled': True},
        }
        
        # Add trial period if specified
        if request.trial_days > 0:
            checkout_session_data['subscription_data'] = {
                'trial_period_days': request.trial_days
            }
        
        # If user is authenticated, use existing customer
        if current_user and current_user.tenant_id:
            if current_user.role not in ["admin", "super_admin"]:
                raise HTTPException(status_code=403, detail="Only admins can manage billing")
            
            tenant = await db.get(Tenant, current_user.tenant_id)
            if tenant:
                customer = await stripe_service.get_or_create_customer(
                    tenant_id=tenant.id,
                    email=current_user.email,
                    name=tenant.name,
                    db=db
                )
                checkout_session_data['customer'] = customer.id
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(**checkout_session_data)
        
        return {"checkout_url": checkout_session.url}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/organization-signup")
async def organization_signup_checkout(
    request: OrganizationSignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe checkout session for new organization signup"""
    
    try:
        # Create checkout session for new organization
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_MONTHLY_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            allow_promotion_codes=True,
            automatic_tax={'enabled': True},
            customer_email=request.customer_email,
            subscription_data={
                'trial_period_days': request.trial_days,
                'metadata': {
                    'organization_name': request.organization_name,
                    'signup_type': 'new_organization'
                }
            }
        )
        
        return {"checkout_url": checkout_session.url}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-subscription")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a subscription directly (requires payment method on file)"""
    
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can manage billing")
    
    try:
        # Get existing customer
        result = await db.execute(
            select(StripeCustomer).where(StripeCustomer.tenant_id == current_user.tenant_id)
        )
        stripe_customer = result.scalar_one_or_none()
        
        if not stripe_customer:
            raise HTTPException(status_code=404, detail="No Stripe customer found. Please use checkout first.")
        
        # Create subscription
        subscription = await stripe_service.create_subscription(
            customer_id=stripe_customer.stripe_customer_id,
            price_id=request.price_id,
            trial_days=request.trial_days
        )
        
        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel the current subscription"""
    
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can manage billing")
    
    try:
        # Get Stripe customer and subscription
        result = await db.execute(
            select(StripeCustomer, StripeSubscription)
            .join(StripeSubscription)
            .where(
                and_(
                    StripeCustomer.tenant_id == current_user.tenant_id,
                    StripeSubscription.status.in_(['active', 'trialing', 'past_due'])
                )
            )
        )
        customer_subscription = result.first()
        
        if not customer_subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        stripe_customer, stripe_subscription = customer_subscription
        
        # Cancel the subscription at period end in Stripe
        updated_subscription = stripe.Subscription.modify(
            stripe_subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Update local database
        stripe_subscription.cancel_at_period_end = True
        stripe_subscription.updated_at = datetime.utcnow()
        await db.commit()
        
        return {
            "message": "Subscription will be canceled at the end of the current billing period",
            "period_end": stripe_subscription.current_period_end.isoformat(),
            "status": updated_subscription.status
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reactivate-subscription")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a subscription that's set to cancel"""
    
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can manage billing")
    
    try:
        # Get Stripe customer and subscription
        result = await db.execute(
            select(StripeCustomer, StripeSubscription)
            .join(StripeSubscription)
            .where(
                and_(
                    StripeCustomer.tenant_id == current_user.tenant_id,
                    StripeSubscription.cancel_at_period_end == True
                )
            )
        )
        customer_subscription = result.first()
        
        if not customer_subscription:
            raise HTTPException(status_code=404, detail="No subscription pending cancellation found")
        
        stripe_customer, stripe_subscription = customer_subscription
        
        # Reactivate the subscription in Stripe
        updated_subscription = stripe.Subscription.modify(
            stripe_subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        # Update local database
        stripe_subscription.cancel_at_period_end = False
        stripe_subscription.updated_at = datetime.utcnow()
        await db.commit()
        
        return {
            "message": "Subscription has been reactivated",
            "status": updated_subscription.status
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/customer-portal")
async def get_customer_portal_url(
    return_url: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get Stripe customer portal URL for managing subscription"""
    
    try:
        # Get Stripe customer
        result = await db.execute(
            select(StripeCustomer).where(StripeCustomer.tenant_id == current_user.tenant_id)
        )
        stripe_customer = result.scalar_one_or_none()
        
        if not stripe_customer:
            raise HTTPException(status_code=404, detail="No billing account found")
        
        portal_url = await stripe_service.get_customer_portal_url(
            customer_id=stripe_customer.stripe_customer_id,
            return_url=return_url
        )
        
        return {"portal_url": portal_url}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/set-demo-status/{tenant_id}")
async def set_demo_status(
    tenant_id: UUID,
    is_demo: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set demo status for an organization (super admin only)"""
    
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admins can modify demo status")
    
    try:
        # Get the tenant
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Update demo status
        tenant.is_demo = is_demo
        tenant.updated_at = datetime.utcnow()
        await db.commit()
        
        return {
            "message": f"Organization '{tenant.name}' demo status updated to {is_demo}",
            "tenant_id": str(tenant_id),
            "is_demo": is_demo
        }
        
    except Exception as e:
        logger.error(f"Error updating demo status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events"""
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    try:
        result = await stripe_service.handle_webhook(
            payload=payload.decode('utf-8'),
            sig_header=sig_header,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


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
    
    # Check if this is a demo account
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # For demo accounts, return simplified dashboard
    if tenant.is_demo:
        return {
            "is_demo": True,
            "current_subscription": None,
            "recent_invoices": [],
            "current_period_usage": None,
            "upcoming_charges": {
                "voice_usage_cents": 0,
                "voice_words_count": 0,
                "call_count": 0,
                "call_charges_cents": 0,
                "total_charges_cents": 0
            },
            "demo_message": "This is a demo account and is exempt from billing charges."
        }
    
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
    
    # Get Stripe subscription info
    subscription_info = await stripe_service.get_subscription_status(tenant_id, db)
    
    # Get recent invoices
    recent_invoices = []
    if subscription_info:
        result = await db.execute(
            select(StripeInvoice)
            .join(StripeCustomer)
            .where(StripeCustomer.tenant_id == tenant_id)
            .order_by(StripeInvoice.created_at.desc())
            .limit(10)
        )
        invoices = result.scalars().all()
        recent_invoices = [
            {
                "id": str(inv.id),
                "stripe_invoice_id": inv.stripe_invoice_id,
                "status": inv.status,
                "amount_due_cents": inv.amount_due_cents,
                "amount_paid_cents": inv.amount_paid_cents,
                "currency": inv.currency,
                "period_start": inv.period_start.isoformat(),
                "period_end": inv.period_end.isoformat(),
                "voice_words_count": inv.voice_words_count,
                "voice_usage_cents": inv.voice_usage_cents,
                "created_at": inv.created_at.isoformat(),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None
            }
            for inv in invoices
        ]
    
    # Calculate costs using proper pricing model
    upcoming_voice_words = current_period_usage.total_stt_words + current_period_usage.total_tts_words
    
    # Calculate voice usage costs: $1.00 per 1,000 words
    voice_usage_cents = int((upcoming_voice_words / 1000) * 100)
    
    # Calculate call costs: $1.00 base per call + voice usage
    base_call_cost = current_period_usage.total_phone_calls * 100  # $1.00 base per call
    total_calculated_cost = base_call_cost + voice_usage_cents
    
    upcoming_charges = {
        "voice_usage_cents": voice_usage_cents,
        "voice_words_count": upcoming_voice_words,
        "call_count": current_period_usage.total_phone_calls,
        "call_charges_cents": base_call_cost,
        "total_charges_cents": total_calculated_cost
    }
    
    return {
        "is_demo": False,
        "current_subscription": subscription_info,
        "recent_invoices": recent_invoices,
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
    total_phone_calls = 0
    
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    for org in organizations:
        # Get subscription info
        subscription_info = await stripe_service.get_subscription_status(org.id, db)
        
        # Get usage stats
        usage_stats = await usage_service.get_usage_stats(
            db=db,
            tenant_id=org.id,
            start_date=period_start,
            end_date=now,
            period="month"
        )
        
        # Get recent invoices
        recent_invoices = []
        if subscription_info:
            result = await db.execute(
                select(StripeInvoice)
                .join(StripeCustomer)
                .where(
                    and_(
                        StripeCustomer.tenant_id == org.id,
                        StripeInvoice.status == 'paid'
                    )
                )
                .order_by(StripeInvoice.created_at.desc())
                .limit(5)
            )
            invoices = result.scalars().all()
            recent_invoices = [
                {
                    "id": str(inv.id),
                    "amount_paid_cents": inv.amount_paid_cents,
                    "period_start": inv.period_start.isoformat(),
                    "period_end": inv.period_end.isoformat(),
                    "paid_at": inv.paid_at.isoformat() if inv.paid_at else None
                }
                for inv in invoices
            ]
        
        voice_words = usage_stats.total_stt_words + usage_stats.total_tts_words
        subscription_revenue = subscription_info['amount_cents'] if subscription_info else 0
        
        # Calculate costs using proper pricing model
        voice_charges_cents = int((voice_words / 1000) * 100)  # $1.00 per 1,000 words
        call_charges_cents = usage_stats.total_phone_calls * 100  # $1.00 base per call
        total_calculated_cost = call_charges_cents + voice_charges_cents
        
        total_revenue += subscription_revenue + total_calculated_cost
        total_voice_words += voice_words
        total_phone_calls += usage_stats.total_phone_calls
        
        org_billing_data.append({
            "organization_id": str(org.id),
            "organization_name": org.name,
            "subdomain": org.subdomain,
            "is_demo": org.is_demo,
            "subscription": subscription_info,
            "subscription_revenue_cents": subscription_revenue,
            "voice_words_count": voice_words,
            "voice_charges_cents": voice_charges_cents,
            "call_count": usage_stats.total_phone_calls,
            "call_charges_cents": call_charges_cents,
            "total_charges_cents": subscription_revenue + total_calculated_cost,
            "recent_invoices": recent_invoices,
            "usage_stats": usage_stats
        })
    
    return {
        "view_type": "super_admin",
        "total_organizations": len(organizations),
        "total_revenue_cents": total_revenue,
        "total_voice_words": total_voice_words,
        "total_phone_calls": total_phone_calls,
        "organizations": org_billing_data,
        "summary": {
            "period_start": period_start,
            "period_end": now,
            "total_subscription_revenue": sum(org["subscription_revenue_cents"] for org in org_billing_data),
            "total_voice_revenue": sum(org["voice_charges_cents"] for org in org_billing_data),
            "total_call_revenue": sum(org["call_charges_cents"] for org in org_billing_data),
            "total_usage_revenue": sum(org["total_charges_cents"] - org["subscription_revenue_cents"] for org in org_billing_data)
        }
    }