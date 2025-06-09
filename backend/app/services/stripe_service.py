"""
Stripe billing service for subscription and usage-based billing
"""
import stripe
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.core.config import settings
from app.models.models import (
    Tenant, StripeCustomer, StripeSubscription, StripeInvoice, UsageRecord
)
from app.schemas.schemas import (
    StripeCustomerCreate, StripeSubscriptionCreate, UsageBillingCreate
)

# Initialize Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)

# For sandbox testing, ensure we're using test mode
if stripe.api_key and stripe.api_key.startswith('sk_test_'):
    print("🧪 Stripe initialized in TEST mode")
elif stripe.api_key and stripe.api_key.startswith('sk_live_'):
    print("🚀 Stripe initialized in LIVE mode")
else:
    print("⚠️  Stripe not properly configured")


class StripeService:
    """Service for handling Stripe billing operations"""
    
    def __init__(self):
        if not stripe.api_key:
            raise ValueError("STRIPE_SECRET_KEY not configured")
    
    async def create_customer(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        customer_data: StripeCustomerCreate
    ) -> StripeCustomer:
        """Create a Stripe customer and store in database"""
        
        # Check if customer already exists
        existing = await db.execute(
            select(StripeCustomer).where(StripeCustomer.tenant_id == tenant_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Customer already exists for this organization")
        
        # Create Stripe customer
        stripe_customer = stripe.Customer.create(
            email=customer_data.email,
            name=customer_data.name,
            phone=customer_data.phone,
            metadata={"tenant_id": str(tenant_id)}
        )
        
        # Store in database
        db_customer = StripeCustomer(
            tenant_id=tenant_id,
            stripe_customer_id=stripe_customer.id,
            email=customer_data.email,
            name=customer_data.name,
            phone=customer_data.phone
        )
        
        db.add(db_customer)
        await db.commit()
        await db.refresh(db_customer)
        
        return db_customer
    
    async def create_subscription(
        self,
        db: AsyncSession,
        customer_id: UUID,
        subscription_data: StripeSubscriptionCreate
    ) -> StripeSubscription:
        """Create a monthly subscription for an organization"""
        
        # Get customer
        customer = await db.get(StripeCustomer, customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        # Create Stripe subscription
        stripe_subscription = stripe.Subscription.create(
            customer=customer.stripe_customer_id,
            items=[{"price": subscription_data.stripe_price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        
        # Store in database
        db_subscription = StripeSubscription(
            customer_id=customer_id,
            stripe_subscription_id=stripe_subscription.id,
            stripe_price_id=subscription_data.stripe_price_id,
            status=stripe_subscription.status,
            current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
            amount_cents=stripe_subscription.items.data[0].price.unit_amount,
            currency=stripe_subscription.items.data[0].price.currency
        )
        
        db.add(db_subscription)
        await db.commit()
        await db.refresh(db_subscription)
        
        return db_subscription
    
    async def create_usage_invoice(
        self,
        db: AsyncSession,
        customer_id: UUID,
        usage_data: UsageBillingCreate
    ) -> StripeInvoice:
        """Create usage-based invoice for voice services"""
        
        # Get customer
        customer = await db.get(StripeCustomer, customer_id)
        if not customer:
            raise ValueError("Customer not found")
        
        # Create Stripe invoice
        stripe_invoice = stripe.Invoice.create(
            customer=customer.stripe_customer_id,
            collection_method="charge_automatically",
            auto_advance=True,
            description=f"Voice usage charges for {usage_data.period_start.strftime('%B %Y')}",
            metadata={
                "period_start": usage_data.period_start.isoformat(),
                "period_end": usage_data.period_end.isoformat(),
                "voice_words": str(usage_data.voice_words_count)
            }
        )
        
        # Add voice usage line item
        if usage_data.voice_usage_cents > 0:
            stripe.InvoiceItem.create(
                customer=customer.stripe_customer_id,
                invoice=stripe_invoice.id,
                amount=usage_data.voice_usage_cents,
                currency="usd",
                description=f"Voice services: {usage_data.voice_words_count:,} words @ $1.00/1000 words"
            )
        
        # Finalize invoice
        stripe_invoice.finalize_invoice()
        
        # Store in database
        db_invoice = StripeInvoice(
            customer_id=customer_id,
            stripe_invoice_id=stripe_invoice.id,
            status=stripe_invoice.status,
            amount_due_cents=stripe_invoice.amount_due,
            amount_paid_cents=stripe_invoice.amount_paid,
            currency=stripe_invoice.currency,
            period_start=usage_data.period_start,
            period_end=usage_data.period_end,
            voice_words_count=usage_data.voice_words_count,
            voice_usage_cents=usage_data.voice_usage_cents,
            due_date=datetime.fromtimestamp(stripe_invoice.due_date) if stripe_invoice.due_date else None
        )
        
        db.add(db_invoice)
        await db.commit()
        await db.refresh(db_invoice)
        
        return db_invoice
    
    async def calculate_monthly_usage(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, int]:
        """Calculate usage charges for a billing period"""
        
        # Get voice usage (STT + TTS words)
        usage_query = select(
            func.sum(UsageRecord.amount).label('total_words')
        ).where(
            and_(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.usage_type.in_(['stt_words', 'tts_words']),
                UsageRecord.created_at >= period_start,
                UsageRecord.created_at < period_end
            )
        )
        
        result = await db.execute(usage_query)
        total_words = result.scalar() or 0
        
        # Calculate cost: $1.00 per 1000 words
        usage_cents = int((total_words / 1000) * 100)  # Convert to cents
        
        return {
            "voice_words_count": total_words,
            "voice_usage_cents": usage_cents
        }
    
    async def handle_webhook(self, event: Dict[str, Any]) -> bool:
        """Handle Stripe webhook events"""
        
        event_type = event["type"]
        
        if event_type == "invoice.payment_succeeded":
            return await self._handle_payment_succeeded(event["data"]["object"])
        elif event_type == "invoice.payment_failed":
            return await self._handle_payment_failed(event["data"]["object"])
        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(event["data"]["object"])
        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(event["data"]["object"])
        
        return True
    
    async def _handle_payment_succeeded(self, invoice_data: Dict[str, Any]) -> bool:
        """Handle successful payment webhook"""
        # Update invoice status in database
        # Implementation depends on your specific needs
        return True
    
    async def _handle_payment_failed(self, invoice_data: Dict[str, Any]) -> bool:
        """Handle failed payment webhook"""
        # Handle failed payment (notify admin, suspend service, etc.)
        return True
    
    async def _handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> bool:
        """Handle subscription update webhook"""
        # Update subscription status in database
        return True
    
    async def _handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> bool:
        """Handle subscription cancellation webhook"""
        # Update subscription status, handle service suspension
        return True


# Global instance
stripe_service = StripeService()