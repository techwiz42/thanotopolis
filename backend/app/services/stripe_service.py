"""
Stripe billing service for subscription and usage-based billing
"""
import stripe
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from app.core.config import settings
from app.models.models import Tenant
from app.schemas.schemas import UsageStats
from app.services.usage_service import usage_service

logger = logging.getLogger(__name__)

class StripeService:
    """Service for managing Stripe subscriptions and billing"""
    
    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        
        # Product IDs for our services
        self.MONTHLY_SUBSCRIPTION_PRICE_ID = settings.STRIPE_MONTHLY_PRICE_ID
        
        # Usage-based pricing configuration
        self.VOICE_USAGE_PRICE_PER_1000 = 100  # $1.00 per 1000 words
        self.CALL_BASE_PRICE = 100  # $1.00 per call
        
    async def create_customer(
        self,
        tenant_id: UUID,
        email: str,
        name: str,
        db: AsyncSession
    ) -> Any:
        """Create a Stripe customer for a tenant"""
        
        # Create customer in Stripe
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={
                'tenant_id': str(tenant_id),
                'platform': 'thanotopolis'
            }
        )
        
        # Store in our database
        from app.models.stripe_models import StripeCustomer
        
        db_customer = StripeCustomer(
            tenant_id=tenant_id,
            stripe_customer_id=customer.id,
            email=email,
            name=name
        )
        db.add(db_customer)
        await db.commit()
        
        logger.info(f"Created Stripe customer {customer.id} for tenant {tenant_id}")
        return customer
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: Optional[str] = None,
        trial_days: int = 0
    ) -> Any:
        """Create a subscription for the monthly fee"""
        
        if not price_id:
            price_id = self.MONTHLY_SUBSCRIPTION_PRICE_ID
        
        subscription_data = {
            'customer': customer_id,
            'items': [{'price': price_id}],
            'payment_behavior': 'default_incomplete',
            'payment_settings': {
                'save_default_payment_method': 'on_subscription'
            },
            'expand': ['latest_invoice.payment_intent']
        }
        
        if trial_days > 0:
            subscription_data['trial_period_days'] = trial_days
        
        subscription = stripe.Subscription.create(**subscription_data)
        
        logger.info(f"Created subscription {subscription.id} for customer {customer_id}")
        return subscription
    
    async def get_or_create_customer(
        self,
        tenant_id: UUID,
        email: str,
        name: str,
        db: AsyncSession
    ) -> Any:
        """Get existing customer or create new one"""
        
        from app.models.stripe_models import StripeCustomer
        
        # Check if customer exists
        result = await db.execute(
            select(StripeCustomer).where(StripeCustomer.tenant_id == tenant_id)
        )
        db_customer = result.scalar_one_or_none()
        
        if db_customer:
            try:
                # Verify customer exists in Stripe
                customer = stripe.Customer.retrieve(db_customer.stripe_customer_id)
                return customer
            except stripe.error.StripeError:
                logger.warning(f"Customer {db_customer.stripe_customer_id} not found in Stripe")
        
        # Create new customer
        return await self.create_customer(tenant_id, email, name, db)
    
    async def create_usage_record(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[int] = None,
        action: str = 'increment'
    ) -> Any:
        """Create a usage record for metered billing"""
        
        usage_record = stripe.usage_record.UsageRecord.create(
            subscription_item=subscription_item_id,
            quantity=quantity,
            timestamp=timestamp or int(datetime.utcnow().timestamp()),
            action=action
        )
        
        return usage_record
    
    async def create_invoice_items_for_usage(
        self,
        customer_id: str,
        tenant_id: UUID,
        db: AsyncSession,
        period_start: datetime,
        period_end: datetime
    ) -> List[Any]:
        """Create invoice items for usage-based charges"""
        
        # Get usage statistics for the period
        usage_stats = await usage_service.get_usage_stats(
            db=db,
            tenant_id=tenant_id,
            start_date=period_start,
            end_date=period_end,
            period="custom"
        )
        
        invoice_items = []
        
        # Voice usage (STT + TTS combined)
        total_voice_words = usage_stats.total_stt_words + usage_stats.total_tts_words
        if total_voice_words > 0:
            voice_amount = int((total_voice_words / 1000) * self.VOICE_USAGE_PRICE_PER_1000)
            
            item = stripe.InvoiceItem.create(
                customer=customer_id,
                amount=voice_amount,
                currency='usd',
                description=f'Voice Usage: {total_voice_words:,} words (STT: {usage_stats.total_stt_words:,}, TTS: {usage_stats.total_tts_words:,})',
                metadata={
                    'tenant_id': str(tenant_id),
                    'usage_type': 'voice',
                    'stt_words': usage_stats.total_stt_words,
                    'tts_words': usage_stats.total_tts_words,
                    'total_words': total_voice_words
                }
            )
            invoice_items.append(item)
        
        # Phone call charges
        if usage_stats.total_phone_calls > 0:
            call_amount = usage_stats.total_phone_calls * self.CALL_BASE_PRICE
            
            item = stripe.InvoiceItem.create(
                customer=customer_id,
                amount=call_amount,
                currency='usd',
                description=f'Phone Calls: {usage_stats.total_phone_calls} calls',
                metadata={
                    'tenant_id': str(tenant_id),
                    'usage_type': 'calls',
                    'call_count': usage_stats.total_phone_calls
                }
            )
            invoice_items.append(item)
        
        return invoice_items
    
    async def create_invoice(
        self,
        customer_id: str,
        auto_advance: bool = True,
        collection_method: str = 'charge_automatically'
    ) -> Any:
        """Create and optionally finalize an invoice"""
        
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=auto_advance,
            collection_method=collection_method
        )
        
        if auto_advance:
            # This will finalize the invoice and attempt to collect payment
            invoice = stripe.Invoice.finalize_invoice(invoice.id)
        
        return invoice
    
    async def get_customer_portal_url(
        self,
        customer_id: str,
        return_url: str
    ) -> str:
        """Generate a customer portal session URL"""
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        
        return session.url
    
    async def handle_webhook(
        self,
        payload: str,
        sig_header: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError:
            logger.error("Invalid webhook payload")
            return {"error": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            return {"error": "Invalid signature"}
        
        # Handle different event types
        if event['type'] == 'customer.subscription.created':
            await self._handle_subscription_created(event['data']['object'], db)
        
        elif event['type'] == 'customer.subscription.updated':
            await self._handle_subscription_updated(event['data']['object'], db)
        
        elif event['type'] == 'customer.subscription.deleted':
            await self._handle_subscription_deleted(event['data']['object'], db)
        
        elif event['type'] == 'invoice.payment_succeeded':
            await self._handle_payment_succeeded(event['data']['object'], db)
        
        elif event['type'] == 'invoice.payment_failed':
            await self._handle_payment_failed(event['data']['object'], db)
        
        return {"status": "success", "event_type": event['type']}
    
    async def _handle_subscription_created(self, subscription: Dict, db: AsyncSession):
        """Handle new subscription creation"""
        from app.models.stripe_models import StripeSubscription, StripeCustomer
        
        # Get customer from database
        result = await db.execute(
            select(StripeCustomer).where(
                StripeCustomer.stripe_customer_id == subscription['customer']
            )
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            logger.error(f"Customer {subscription['customer']} not found for subscription")
            return
        
        # Create subscription record
        db_subscription = StripeSubscription(
            customer_id=customer.id,
            stripe_subscription_id=subscription['id'],
            stripe_price_id=subscription['items']['data'][0]['price']['id'],
            status=subscription['status'],
            current_period_start=datetime.fromtimestamp(subscription['current_period_start']),
            current_period_end=datetime.fromtimestamp(subscription['current_period_end']),
            cancel_at_period_end=subscription.get('cancel_at_period_end', False),
            amount_cents=subscription['items']['data'][0]['price']['unit_amount'],
            currency=subscription['currency']
        )
        
        db.add(db_subscription)
        await db.commit()
        
        logger.info(f"Created subscription record for {subscription['id']}")
    
    async def _handle_subscription_updated(self, subscription: Dict, db: AsyncSession):
        """Handle subscription updates"""
        from app.models.stripe_models import StripeSubscription
        
        result = await db.execute(
            select(StripeSubscription).where(
                StripeSubscription.stripe_subscription_id == subscription['id']
            )
        )
        db_subscription = result.scalar_one_or_none()
        
        if db_subscription:
            db_subscription.status = subscription['status']
            db_subscription.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
            db_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
            db_subscription.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
            db_subscription.updated_at = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Updated subscription {subscription['id']}")
    
    async def _handle_subscription_deleted(self, subscription: Dict, db: AsyncSession):
        """Handle subscription cancellation"""
        from app.models.stripe_models import StripeSubscription
        
        result = await db.execute(
            select(StripeSubscription).where(
                StripeSubscription.stripe_subscription_id == subscription['id']
            )
        )
        db_subscription = result.scalar_one_or_none()
        
        if db_subscription:
            db_subscription.status = 'canceled'
            db_subscription.updated_at = datetime.utcnow()
            
            await db.commit()
            logger.info(f"Canceled subscription {subscription['id']}")
    
    async def _handle_payment_succeeded(self, invoice: Dict, db: AsyncSession):
        """Handle successful payment"""
        from app.models.stripe_models import StripeInvoice, StripeCustomer
        
        # Get customer
        result = await db.execute(
            select(StripeCustomer).where(
                StripeCustomer.stripe_customer_id == invoice['customer']
            )
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            logger.error(f"Customer {invoice['customer']} not found for invoice")
            return
        
        # Extract usage data from line items
        voice_words = 0
        voice_cents = 0
        
        for line in invoice.get('lines', {}).get('data', []):
            if 'voice' in line.get('description', '').lower():
                # Extract word count from metadata or description
                metadata = line.get('metadata', {})
                voice_words = metadata.get('total_words', 0)
                voice_cents = line.get('amount', 0)
        
        # Create invoice record
        db_invoice = StripeInvoice(
            customer_id=customer.id,
            stripe_invoice_id=invoice['id'],
            status='paid',
            amount_due_cents=invoice['amount_due'],
            amount_paid_cents=invoice['amount_paid'],
            currency=invoice['currency'],
            period_start=datetime.fromtimestamp(invoice['period_start']),
            period_end=datetime.fromtimestamp(invoice['period_end']),
            voice_words_count=voice_words,
            voice_usage_cents=voice_cents,
            paid_at=datetime.utcnow()
        )
        
        db.add(db_invoice)
        await db.commit()
        
        logger.info(f"Recorded successful payment for invoice {invoice['id']}")
    
    async def _handle_payment_failed(self, invoice: Dict, db: AsyncSession):
        """Handle failed payment"""
        # Log the failure
        logger.warning(f"Payment failed for invoice {invoice['id']}")
        
        # You could implement retry logic, notifications, etc. here
    
    async def get_subscription_status(
        self,
        tenant_id: UUID,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get current subscription status for a tenant"""
        
        from app.models.stripe_models import StripeCustomer, StripeSubscription
        
        # Get customer
        result = await db.execute(
            select(StripeCustomer).where(StripeCustomer.tenant_id == tenant_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            return None
        
        # Get active subscription
        result = await db.execute(
            select(StripeSubscription).where(
                and_(
                    StripeSubscription.customer_id == customer.id,
                    StripeSubscription.status.in_(['active', 'trialing'])
                )
            ).order_by(StripeSubscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return None
        
        return {
            'subscription_id': subscription.stripe_subscription_id,
            'status': subscription.status,
            'current_period_start': subscription.current_period_start,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'amount_cents': subscription.amount_cents
        }


# Global instance
stripe_service = StripeService()