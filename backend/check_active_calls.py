#!/usr/bin/env python3
"""
Check active calls that are blocking new calls
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

async def check_active_calls():
    """Check and clean up active calls"""
    
    async with get_db_context() as db:
        print("🔍 CHECKING ACTIVE CALLS")
        print("=" * 60)
        
        # Get telephony configuration
        config_query = select(TelephonyConfiguration)
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if not config:
            print("❌ No telephony configuration found!")
            return
            
        print(f"Max concurrent calls allowed: {config.max_concurrent_calls}")
        print()
        
        # Check for active calls
        active_statuses = [
            CallStatus.INCOMING.value,
            CallStatus.RINGING.value,
            CallStatus.ANSWERED.value,
            CallStatus.IN_PROGRESS.value
        ]
        
        active_calls_query = select(PhoneCall).where(
            and_(
                PhoneCall.telephony_config_id == config.id,
                PhoneCall.status.in_(active_statuses)
            )
        ).order_by(PhoneCall.created_at)
        
        active_calls_result = await db.execute(active_calls_query)
        active_calls = active_calls_result.scalars().all()
        
        print(f"Found {len(active_calls)} active calls:")
        print("-" * 40)
        
        stale_calls = []
        
        for call in active_calls:
            age = datetime.now(timezone.utc) - call.created_at.replace(tzinfo=timezone.utc)
            print(f"\nCall ID: {call.id}")
            print(f"Call SID: {call.call_sid}")
            print(f"Status: {call.status}")
            print(f"Created: {call.created_at} ({age.total_seconds():.0f}s ago)")
            print(f"Customer: {call.customer_phone_number}")
            
            # Check if this call is stale (older than 30 minutes)
            if age.total_seconds() > 1800:  # 30 minutes
                print(f"⚠️  This call is STALE (over 30 minutes old)")
                stale_calls.append(call)
                
        if stale_calls:
            print(f"\n\n🧹 CLEANING UP {len(stale_calls)} STALE CALLS")
            print("-" * 40)
            
            for call in stale_calls:
                # Update the call to completed status
                call.status = CallStatus.FAILED.value
                call.end_time = datetime.now(timezone.utc)
                
                # Add metadata about the cleanup
                if call.call_metadata is None:
                    call.call_metadata = {}
                call.call_metadata['cleanup_reason'] = 'Stale call cleaned up after 30 minutes'
                call.call_metadata['cleanup_time'] = datetime.now(timezone.utc).isoformat()
                
                print(f"✅ Cleaned up call: {call.call_sid}")
                
            await db.commit()
            print("\n✅ All stale calls have been cleaned up")
            
            # Re-check active calls
            active_calls_result = await db.execute(active_calls_query)
            active_calls = active_calls_result.scalars().all()
            print(f"\nActive calls after cleanup: {len(active_calls)}")
        else:
            print("\n✅ No stale calls found")
            
        # Check if we're at the limit
        if len(active_calls) >= config.max_concurrent_calls:
            print(f"\n⚠️  WARNING: At or above concurrent call limit ({len(active_calls)}/{config.max_concurrent_calls})")
            print("New calls will be rejected until some calls complete")
        else:
            print(f"\n✅ Below concurrent call limit ({len(active_calls)}/{config.max_concurrent_calls})")
            print("New calls can be accepted")

if __name__ == "__main__":
    asyncio.run(check_active_calls())