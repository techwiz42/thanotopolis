"""
Automated billing job for monthly usage charges
"""
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from app.db.database import AsyncSessionLocal
from app.models.models import Tenant
from app.models.stripe_models import StripeCustomer, StripeSubscription
from app.schemas.schemas import UsageBillingCreate
from app.services.stripe_service import stripe_service

logger = logging.getLogger(__name__)


class BillingAutomationService:
    """Service for automated monthly billing of usage charges"""
    
    async def process_monthly_billing(self, target_month: datetime = None, db_session: AsyncSession = None) -> Dict[str, Any]:
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
        
        # Check if billing is enabled
        if not stripe_service.is_enabled:
            logger.info("Billing automation disabled - Stripe service not configured")
            results["errors"].append("Billing automation disabled - Stripe service not configured")
            return results
        
        # Process billing with provided session or create new one
        async def _process_billing_with_db(db: AsyncSession):
            # Get all active organizations with subscriptions (excluding demo accounts)
            orgs_result = await db.execute(
                select(Tenant)
                .join(StripeCustomer)
                .join(StripeSubscription)
                .where(
                    and_(
                        Tenant.is_active == True,
                        Tenant.is_demo == False,  # Exclude demo accounts from billing
                        StripeSubscription.status.in_(['active', 'past_due'])
                    )
                )
            )
            organizations = orgs_result.scalars().all()
            
            for org in organizations:
                try:
                    # Get Stripe customer
                    customer_result = await db.execute(
                        select(StripeCustomer).where(StripeCustomer.tenant_id == org.id)
                    )
                    stripe_customer = customer_result.scalar_one_or_none()
                    
                    if not stripe_customer:
                        logger.warning(f"No Stripe customer found for organization {org.name}")
                        results["failed_invoices"] += 1
                        results["errors"].append(f"No Stripe customer for {org.name}")
                        continue
                    
                    # Create invoice items for usage
                    invoice_items = await stripe_service.create_invoice_items_for_usage(
                        customer_id=stripe_customer.stripe_customer_id,
                        tenant_id=org.id,
                        db=db,
                        period_start=period_start,
                        period_end=period_end
                    )
                    
                    if invoice_items:
                        # Create and finalize invoice
                        invoice = await stripe_service.create_invoice(
                            customer_id=stripe_customer.stripe_customer_id,
                            auto_advance=True
                        )
                        
                        # Calculate total usage charges
                        usage_charges = sum(item.amount for item in invoice_items)
                        results["total_usage_charges"] += usage_charges
                        results["successful_invoices"] += 1
                        
                        logger.info(f"Created invoice for {org.name}: ${usage_charges/100:.2f}")
                    else:
                        logger.info(f"No usage charges for {org.name} in period")
                    
                    results["processed_organizations"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing billing for {org.name}: {str(e)}")
                    results["failed_invoices"] += 1
                    results["errors"].append(f"Error for {org.name}: {str(e)}")
        
        # Use provided session or create new one
        if db_session:
            await _process_billing_with_db(db_session)
        else:
            async with AsyncSessionLocal() as db:
                await _process_billing_with_db(db)
        
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
async def trigger_manual_billing(target_month: datetime = None, db_session: AsyncSession = None):
    """Manually trigger billing for a specific month (for testing/admin use)"""
    return await billing_automation.process_monthly_billing(target_month, db_session)