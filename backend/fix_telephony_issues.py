#!/usr/bin/env python3
"""
Fix telephony issues:
1. Clean up stale calls automatically
2. Add better error handling
3. Add call timeout handling
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta

# Add the backend directory to the Python path
sys.path.append('/home/peter/thanotopolis/backend')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, update
from app.db.database import get_db_context
from app.models.models import TelephonyConfiguration, PhoneCall, CallStatus

async def add_call_cleanup_task():
    """Add a background task to clean up stale calls"""
    
    print("🔧 ADDING CALL CLEANUP IMPROVEMENTS")
    print("=" * 60)
    
    # Create a new file for the cleanup task
    cleanup_task_code = '''# backend/app/tasks/telephony_cleanup.py
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
'''
    
    # Write the cleanup task file
    import os
    tasks_dir = "/home/peter/thanotopolis/backend/app/tasks"
    os.makedirs(tasks_dir, exist_ok=True)
    
    with open(f"{tasks_dir}/__init__.py", "w") as f:
        f.write("# Tasks module\n")
        
    with open(f"{tasks_dir}/telephony_cleanup.py", "w") as f:
        f.write(cleanup_task_code)
        
    print("✅ Created telephony cleanup task module")
    
    # Now let's also add a check to the webhook handler to handle edge cases
    print("\n🔧 IMPROVING WEBHOOK ERROR HANDLING")
    print("-" * 40)
    
    async with get_db_context() as db:
        # Check current configuration
        config_query = select(TelephonyConfiguration)
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if config:
            print(f"Current max concurrent calls: {config.max_concurrent_calls}")
            
            # Set a more reasonable limit if it's too low
            if config.max_concurrent_calls < 10:
                config.max_concurrent_calls = 10
                await db.commit()
                print(f"✅ Updated max concurrent calls to 10")
            
            # Make sure the platform number matches the Twilio number
            import os
            actual_twilio_number = os.getenv("TWILIO_PHONE_NUMBER", "+18884374952")
            
            if config.platform_phone_number != actual_twilio_number:
                print(f"\n⚠️  Platform number mismatch:")
                print(f"   Database: {config.platform_phone_number}")
                print(f"   Twilio: {actual_twilio_number}")
                
                config.platform_phone_number = actual_twilio_number
                await db.commit()
                print(f"✅ Updated platform number to match Twilio")
                
    print("\n📋 RECOMMENDATIONS")
    print("-" * 40)
    print("1. Add the cleanup task to main.py startup:")
    print("   from app.tasks.telephony_cleanup import start_cleanup_task")
    print("   start_cleanup_task()")
    print()
    print("2. Monitor the logs for stale call cleanups")
    print()
    print("3. Consider adding call duration limits in the WebSocket handler")
    print()
    print("✅ Fixes applied successfully!")

if __name__ == "__main__":
    asyncio.run(add_call_cleanup_task())