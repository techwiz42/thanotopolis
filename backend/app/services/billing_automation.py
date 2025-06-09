"""
Automated billing job for monthly usage charges
"""
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.db.database import async_session_maker
from app.models.models import Tenant, StripeCustomer, StripeSubscription
from app.services.stripe_service import stripe_service
from app.schemas.schemas import UsageBillingCreate

logger = logging.getLogger(__name__)


class BillingAutomationService:
    """Service for automated monthly billing of usage charges"""
    
    async def process_monthly_billing(self, target_month: datetime = None) -> Dict[str, Any]:
        """Process monthly billing for all active organizations"""
        
        if target_month is None:
            # Default to previous month
            now = datetime.utcnow()
            if now.month == 1:
                target_month = now.replace(year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                target_month = now.replace(month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate period bounds
        period_start = target_month
        if target_month.month == 12:
            period_end = target_month.replace(year=target_month.year + 1, month=1)
        else:
            period_end = target_month.replace(month=target_month.month + 1)
        
        logger.info(f"Processing monthly billing for period: {period_start} to {period_end}")
        
        results = {
            "period_start": period_start,
            "period_end": period_end,
            "processed_organizations": 0,
            "successful_invoices": 0,
            "failed_invoices": 0,
            "total_usage_charges": 0,
            "errors": []
        }
        
        async with async_session_maker() as db:
            # Get all active organizations with Stripe customers and subscriptions
            query = select(StripeCustomer).join(
                StripeSubscription,
                StripeSubscription.customer_id == StripeCustomer.id
            ).where(
                StripeSubscription.status.in_(["active", "trialing"])
            )
            
            result = await db.execute(query)
            customers = result.scalars().all()
            
            logger.info(f"Found {len(customers)} active customers to process")
            
            for customer in customers:
                try:
                    results["processed_organizations"] += 1
                    
                    # Calculate usage for the billing period
                    usage = await stripe_service.calculate_monthly_usage(
                        db=db,
                        tenant_id=customer.tenant_id,
                        period_start=period_start,
                        period_end=period_end
                    )
                    
                    # Skip if no usage charges
                    if usage["voice_usage_cents"] == 0:
                        logger.info(f"No usage charges for customer {customer.stripe_customer_id}")
                        continue
                    
                    # Create usage invoice
                    usage_data = UsageBillingCreate(
                        period_start=period_start,
                        period_end=period_end,
                        voice_words_count=usage["voice_words_count"],
                        voice_usage_cents=usage["voice_usage_cents"]
                    )
                    
                    invoice = await stripe_service.create_usage_invoice(
                        db=db,
                        customer_id=customer.id,
                        usage_data=usage_data
                    )
                    
                    results["successful_invoices"] += 1
                    results["total_usage_charges"] += usage["voice_usage_cents"]
                    
                    logger.info(
                        f"Created usage invoice for {customer.stripe_customer_id}: "
                        f"{usage['voice_words_count']} words, ${usage['voice_usage_cents']/100:.2f}"
                    )
                    
                except Exception as e:
                    results["failed_invoices"] += 1
                    error_msg = f"Failed to process customer {customer.stripe_customer_id}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"Monthly billing complete: {results}")
        return results
    
    async def run_daily_check(self):
        """Daily job to check if monthly billing should run"""
        
        now = datetime.utcnow()
        
        # Run on the 1st of each month
        if now.day == 1 and now.hour < 2:  # Run in early morning hours
            logger.info("Running monthly billing automation...")
            try:
                results = await self.process_monthly_billing()
                
                # You could send notifications here (email, Slack, etc.)
                if results["failed_invoices"] > 0:
                    logger.warning(f"Monthly billing completed with {results['failed_invoices']} failures")
                else:
                    logger.info("Monthly billing completed successfully")
                    
            except Exception as e:
                logger.error(f"Monthly billing automation failed: {e}")
                # You could send failure notifications here
    
    async def start_automation(self):
        """Start the billing automation background task"""
        
        logger.info("Starting billing automation service...")
        
        while True:
            try:
                await self.run_daily_check()
                
                # Sleep for 1 hour before checking again
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                logger.info("Billing automation cancelled")
                break
            except Exception as e:
                logger.error(f"Error in billing automation: {e}")
                # Sleep for 10 minutes before retrying
                await asyncio.sleep(600)


# Global instance
billing_automation = BillingAutomationService()


# Utility function to manually trigger billing
async def trigger_manual_billing(target_month: datetime = None):
    """Manually trigger billing for a specific month (for testing/admin use)"""
    return await billing_automation.process_monthly_billing(target_month)