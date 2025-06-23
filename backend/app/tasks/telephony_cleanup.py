# backend/app/tasks/telephony_cleanup.py
"""
Background task to clean up stale telephony calls
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.db.database import get_db_context
from app.models.models import PhoneCall, CallStatus, TelephonyConfiguration

logger = logging.getLogger(__name__)

async def cleanup_stale_calls():
    """Clean up calls that have been in active state for too long"""
    
    while True:
        try:
            async with get_db_context() as db:
                # Find all active calls older than 30 minutes
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
                
                active_statuses = [
                    CallStatus.INCOMING.value,
                    CallStatus.RINGING.value,
                    CallStatus.ANSWERED.value,
                    CallStatus.IN_PROGRESS.value
                ]
                
                stale_calls_query = select(PhoneCall).where(
                    and_(
                        PhoneCall.status.in_(active_statuses),
                        PhoneCall.created_at < cutoff_time
                    )
                )
                
                result = await db.execute(stale_calls_query)
                stale_calls = result.scalars().all()
                
                if stale_calls:
                    logger.info(f"🧹 Found {len(stale_calls)} stale calls to clean up")
                    
                    for call in stale_calls:
                        call.status = CallStatus.FAILED.value
                        call.end_time = datetime.now(timezone.utc)
                        
                        if call.call_metadata is None:
                            call.call_metadata = {}
                        call.call_metadata['cleanup_reason'] = 'Stale call timeout (30 minutes)'
                        call.call_metadata['cleanup_time'] = datetime.now(timezone.utc).isoformat()
                        
                        logger.info(f"✅ Cleaned up stale call: {call.call_sid}")
                    
                    await db.commit()
                    
        except Exception as e:
            logger.error(f"❌ Error in call cleanup task: {e}")
            
        # Run cleanup every 5 minutes
        await asyncio.sleep(300)

# Start the cleanup task when the module is imported
cleanup_task = None

def start_cleanup_task():
    """Start the cleanup task"""
    global cleanup_task
    if cleanup_task is None:
        cleanup_task = asyncio.create_task(cleanup_stale_calls())
        logger.info("✅ Telephony cleanup task started")

def stop_cleanup_task():
    """Stop the cleanup task"""
    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()
        cleanup_task = None
        logger.info("✅ Telephony cleanup task stopped")
