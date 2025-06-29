"""
Usage tracking service for monitoring token and voice usage
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.models.models import UsageRecord, SystemMetrics, User, Tenant
from app.schemas.schemas import UsageRecordCreate, UsageStats
from app.db.database import get_db


class UsageTrackingService:
    """Service for tracking and analyzing usage metrics"""
    
    def __init__(self):
        self.db: Optional[AsyncSession] = None
    
    async def record_usage(
        self, 
        db: AsyncSession,
        tenant_id: UUID,
        usage_type: str,  # 'tokens', 'tts_words', 'stt_words', 'phone_calls'
        amount: int,
        user_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        service_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        cost_cents: Optional[int] = 0,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """Record a usage event"""
        
        usage_record = UsageRecord(
            tenant_id=tenant_id,
            user_id=user_id,
            usage_type=usage_type,
            amount=amount,
            conversation_id=conversation_id,
            service_provider=service_provider,
            model_name=model_name,
            cost_cents=cost_cents or 0,
            additional_data=additional_data or {}
        )
        
        db.add(usage_record)
        await db.commit()
        await db.refresh(usage_record)
        
        return usage_record
    
    async def record_token_usage(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID],
        token_count: int,
        conversation_id: Optional[UUID] = None,
        service_provider: str = "openai",
        model_name: str = "gpt-4",
        cost_cents: Optional[int] = None
    ) -> UsageRecord:
        """Record token usage from AI model calls"""
        
        # Estimate cost if not provided (rough estimates in cents)
        if cost_cents is None:
            if "gpt-4" in model_name.lower():
                cost_cents = int(token_count * 0.003)  # ~$0.03 per 1K tokens
            elif "gpt-3.5" in model_name.lower():
                cost_cents = int(token_count * 0.0002)  # ~$0.002 per 1K tokens
            else:
                cost_cents = int(token_count * 0.001)  # default estimate
        
        return await self.record_usage(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            usage_type="tokens",
            amount=token_count,
            conversation_id=conversation_id,
            service_provider=service_provider,
            model_name=model_name,
            cost_cents=cost_cents
        )
    
    async def record_tts_usage(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID],
        word_count: int,
        conversation_id: Optional[UUID] = None,
        service_provider: str = "elevenlabs",
        model_name: str = "eleven_turbo_v2",
        duration_seconds: Optional[int] = None
    ) -> UsageRecord:
        """Record TTS usage in words"""
        
        # Estimate cost for ElevenLabs based on words (rough estimate)
        # ElevenLabs charges per character, approximately 5 chars per word
        cost_cents = int(word_count * 5 * 0.00003 * 100)  # ~$0.00003 per character
        
        additional_data = {}
        if duration_seconds:
            additional_data["duration_seconds"] = duration_seconds
        
        return await self.record_usage(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            usage_type="tts_words",
            amount=word_count,
            conversation_id=conversation_id,
            service_provider=service_provider,
            model_name=model_name,
            cost_cents=cost_cents,
            additional_data=additional_data
        )
    
    async def record_stt_usage(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID],
        word_count: int,
        conversation_id: Optional[UUID] = None,
        service_provider: str = "deepgram",
        model_name: str = "nova-2",
        duration_seconds: Optional[int] = None
    ) -> UsageRecord:
        """Record STT usage in words"""
        
        # Estimate cost for Deepgram based on duration (if provided) or word count
        # Deepgram charges per minute, roughly estimate from word count
        if duration_seconds:
            cost_cents = int(duration_seconds / 60 * 0.25 * 100)  # ~$0.0025 per minute
        else:
            # Estimate duration from word count (average 150 words per minute)
            estimated_minutes = word_count / 150
            cost_cents = int(estimated_minutes * 0.25 * 100)
        
        additional_data = {}
        if duration_seconds:
            additional_data["duration_seconds"] = duration_seconds
        
        return await self.record_usage(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            usage_type="stt_words",
            amount=word_count,
            conversation_id=conversation_id,
            service_provider=service_provider,
            model_name=model_name,
            cost_cents=cost_cents,
            additional_data=additional_data
        )
    
    async def record_phone_call(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: Optional[UUID],
        call_duration_seconds: int,
        call_id: Optional[UUID] = None,
        service_provider: str = "twilio",
        cost_cents: int = 100  # $1.00 base per call (actual cost calculated based on words)
    ) -> UsageRecord:
        """Record phone call usage"""
        
        additional_data = {
            "duration_seconds": call_duration_seconds,
            "call_id": str(call_id) if call_id else None
        }
        
        return await self.record_usage(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            usage_type="phone_calls",
            amount=1,  # 1 call
            service_provider=service_provider,
            cost_cents=cost_cents,
            additional_data=additional_data
        )
    
    async def get_usage_stats(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "month"
    ) -> UsageStats:
        """Get aggregated usage statistics"""
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            if period == "day":
                start_date = end_date - timedelta(days=1)
            elif period == "week":
                start_date = end_date - timedelta(weeks=1)
            else:  # month
                start_date = end_date - timedelta(days=30)
        
        # Build query conditions
        conditions = [UsageRecord.created_at >= start_date, UsageRecord.created_at <= end_date]
        
        if tenant_id:
            conditions.append(UsageRecord.tenant_id == tenant_id)
        if user_id:
            conditions.append(UsageRecord.user_id == user_id)
        
        # Get aggregated stats
        query = select(
            UsageRecord.usage_type,
            func.sum(UsageRecord.amount).label('total_amount'),
            func.count(UsageRecord.id).label('record_count'),
            func.sum(UsageRecord.cost_cents).label('total_cost')
        ).where(and_(*conditions)).group_by(UsageRecord.usage_type)
        
        result = await db.execute(query)
        stats = result.all()
        
        # Initialize totals
        total_tts_words = 0
        total_stt_words = 0
        total_phone_calls = 0
        total_cost_cents = 0
        
        # Process stats
        for stat in stats:
            if stat.usage_type == "tts_words":
                total_tts_words = stat.total_amount or 0
            elif stat.usage_type == "stt_words":
                total_stt_words = stat.total_amount or 0
            elif stat.usage_type == "phone_calls":
                total_phone_calls = stat.total_amount or 0
            elif stat.usage_type == "telephony_minutes":
                # Each telephony_minutes record represents one call
                total_phone_calls += stat.record_count or 0
            
            total_cost_cents += stat.total_cost or 0
        
        return UsageStats(
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_tts_words=total_tts_words,
            total_stt_words=total_stt_words,
            total_phone_calls=total_phone_calls,
            total_cost_cents=total_cost_cents
        )
    
    async def record_system_metric(
        self,
        db: AsyncSession,
        metric_type: str,
        value: int,
        tenant_id: Optional[UUID] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> SystemMetrics:
        """Record system-level metrics"""
        
        metric = SystemMetrics(
            metric_type=metric_type,
            value=value,
            tenant_id=tenant_id,
            additional_data=additional_data or {}
        )
        
        db.add(metric)
        await db.commit()
        await db.refresh(metric)
        
        return metric
    
    async def get_recent_usage(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[UsageRecord]:
        """Get recent usage records"""
        
        query = select(UsageRecord).order_by(desc(UsageRecord.created_at)).limit(limit)
        
        if tenant_id:
            query = query.where(UsageRecord.tenant_id == tenant_id)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_system_metrics(
        self,
        db: AsyncSession,
        metric_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[SystemMetrics]:
        """Get recent system metrics"""
        
        since = datetime.utcnow() - timedelta(hours=hours)
        query = select(SystemMetrics).where(
            SystemMetrics.created_at >= since
        ).order_by(desc(SystemMetrics.created_at)).limit(limit)
        
        if metric_type:
            query = query.where(SystemMetrics.metric_type == metric_type)
        
        result = await db.execute(query)
        return result.scalars().all()


# Global instance
usage_service = UsageTrackingService()