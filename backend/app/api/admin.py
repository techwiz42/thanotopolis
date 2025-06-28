"""
Admin API endpoints for usage monitoring and system management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
import logging

from app.db.database import get_db
from app.auth.auth import get_current_user, require_admin_user
from app.models.models import User, Tenant, UsageRecord, SystemMetrics, Conversation, PhoneCall, TelephonyConfiguration, PhoneVerificationStatus
from app.schemas.schemas import (
    UserResponse, 
    UsageRecordResponse, 
    UsageStats, 
    SystemMetricsResponse,
    AdminDashboardResponse,
    AdminUserUpdate,
    PaginationParams,
    PaginatedResponse
)
from app.services.usage_service import usage_service

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard data with system overview"""
    
    # Get basic counts - filtered by current user's tenant
    total_users = await db.scalar(
        select(func.count(User.id)).where(User.tenant_id == current_user.tenant_id)
    )
    total_conversations = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.tenant_id == current_user.tenant_id)
    )
    
    # For phone calls, need to join with telephony_configurations
    phone_calls_query = select(func.count(PhoneCall.id)).select_from(PhoneCall).join(
        TelephonyConfiguration,
        PhoneCall.telephony_config_id == TelephonyConfiguration.id
    ).where(TelephonyConfiguration.tenant_id == current_user.tenant_id)
    
    total_phone_calls = await db.scalar(phone_calls_query)
    
    # Get recent usage (last 50 records) - filtered by current user's tenant
    recent_usage = await usage_service.get_recent_usage(
        db, 
        tenant_id=current_user.tenant_id,
        limit=50
    )
    
    # Get system metrics from last 24 hours
    system_metrics = await usage_service.get_system_metrics(db, hours=24)
    
    # Get overall usage stats for last 30 days - filtered by current user's tenant
    overall_usage_stats = await usage_service.get_usage_stats(
        db=db,
        tenant_id=current_user.tenant_id,
        period="month"
    )
    
    # Get usage breakdown by organization for last 30 days
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    usage_by_org_query = select(
        Tenant.id.label('tenant_id'),
        Tenant.name.label('tenant_name'),
        Tenant.subdomain.label('subdomain'),
        UsageRecord.usage_type,
        func.sum(UsageRecord.amount).label('total_amount'),
        func.sum(UsageRecord.cost_cents).label('total_cost'),
        func.count(UsageRecord.id).label('record_count')
    ).select_from(
        Tenant
    ).outerjoin(
        UsageRecord,
        and_(
            UsageRecord.tenant_id == Tenant.id,
            UsageRecord.created_at >= start_date,
            UsageRecord.created_at <= end_date
        )
    ).group_by(
        Tenant.id, Tenant.name, Tenant.subdomain, UsageRecord.usage_type
    ).order_by(Tenant.name)
    
    org_usage_result = await db.execute(usage_by_org_query)
    org_usage_data = org_usage_result.all()
    
    # Organize usage data by tenant
    usage_by_organization = {}
    for row in org_usage_data:
        tenant_id = str(row.tenant_id)
        if tenant_id not in usage_by_organization:
            usage_by_organization[tenant_id] = {
                "tenant_id": tenant_id,
                "tenant_name": row.tenant_name,
                "subdomain": row.subdomain,
                "total_tts_words": 0,
                "total_stt_words": 0,
                "total_cost_cents": 0,
                "record_count": 0
            }
        
        if row.usage_type:  # Only process if there's actual usage
            if row.usage_type == "tts_words":
                usage_by_organization[tenant_id]["total_tts_words"] = row.total_amount or 0
            elif row.usage_type == "stt_words":
                usage_by_organization[tenant_id]["total_stt_words"] = row.total_amount or 0
            
            usage_by_organization[tenant_id]["total_cost_cents"] += row.total_cost or 0
            usage_by_organization[tenant_id]["record_count"] += row.record_count or 0
    
    # Get tenant stats with phone calls
    tenant_stats_query = select(
        Tenant.id,
        Tenant.name,
        Tenant.subdomain,
        func.count(User.id.distinct()).label('user_count'),
        func.count(Conversation.id.distinct()).label('conversation_count'),
        func.count(PhoneCall.id.distinct()).label('phone_call_count')
    ).select_from(
        Tenant
    ).outerjoin(User, User.tenant_id == Tenant.id
    ).outerjoin(Conversation, Conversation.tenant_id == Tenant.id
    ).outerjoin(TelephonyConfiguration, TelephonyConfiguration.tenant_id == Tenant.id
    ).outerjoin(PhoneCall, PhoneCall.telephony_config_id == TelephonyConfiguration.id
    ).group_by(
        Tenant.id, Tenant.name, Tenant.subdomain
    )
    
    tenant_stats_result = await db.execute(tenant_stats_query)
    tenant_stats = [
        {
            "tenant_id": str(row.id),
            "name": row.name,
            "subdomain": row.subdomain,
            "user_count": row.user_count or 0,
            "conversation_count": row.conversation_count or 0,
            "phone_call_count": row.phone_call_count or 0
        }
        for row in tenant_stats_result.all()
    ]
    
    # Get real WebSocket connection counts
    try:
        from app.api.websockets import connection_manager, connection_stats, active_connections, connection_lock
        
        # Get stats from our connection manager
        cm_stats = connection_manager.get_stats()
        
        # Get stats from the global active_connections dict
        async with connection_lock:
            total_active = sum(len(sockets) for sockets in active_connections.values())
        
        active_ws_connections = max(cm_stats.get("total_connections", 0), total_active)
        
    except Exception as e:
        # Fallback to 0 if there's an error
        active_ws_connections = 0
    
    # Get real database connection pool info
    try:
        from app.db.database import engine
        db_connection_pool_size = engine.pool.size() + engine.pool.overflow()
    except:
        db_connection_pool_size = 10
    
    return AdminDashboardResponse(
        total_users=total_users or 0,
        total_conversations=total_conversations or 0,
        total_phone_calls=total_phone_calls or 0,
        active_ws_connections=active_ws_connections,
        db_connection_pool_size=db_connection_pool_size,
        recent_usage=[UsageRecordResponse.model_validate(usage) for usage in recent_usage],
        system_metrics=[SystemMetricsResponse.model_validate(metric) for metric in system_metrics],
        tenant_stats=tenant_stats,
        overall_usage_stats=overall_usage_stats,
        usage_by_organization=list(usage_by_organization.values())
    )


@router.get("/users", response_model=PaginatedResponse)
async def list_all_users(
    current_user: User = Depends(require_admin_user),
    pagination: PaginationParams = Depends(),
    tenant_id: Optional[UUID] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List all users with filtering options"""
    
    # Build query
    query = select(User)
    conditions = []
    
    if tenant_id:
        conditions.append(User.tenant_id == tenant_id)
    if role:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return PaginatedResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total or 0,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=((total or 0) + pagination.page_size - 1) // pagination.page_size
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: UUID,
    user_update: AdminUserUpdate,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user (admin only)"""
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    if user_update.role is not None:
        if user_update.role not in ["user", "admin", "super_admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = user_update.role
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    if user_update.is_verified is not None:
        user.is_verified = user_update.is_verified
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.get("/usage/stats", response_model=UsageStats)
async def get_usage_statistics(
    current_user: User = Depends(require_admin_user),
    tenant_id: Optional[UUID] = Query(None),
    user_id: Optional[UUID] = Query(None),
    period: str = Query("month", pattern="^(day|week|month)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics"""
    
    return await usage_service.get_usage_stats(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        period=period
    )


@router.get("/usage/records", response_model=PaginatedResponse)
async def list_usage_records(
    current_user: User = Depends(require_admin_user),
    pagination: PaginationParams = Depends(),
    tenant_id: Optional[UUID] = Query(None),
    user_id: Optional[UUID] = Query(None),
    usage_type: Optional[str] = Query(None),
    service_provider: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List usage records with filtering"""
    
    # Build query
    query = select(UsageRecord)
    conditions = []
    
    if tenant_id:
        conditions.append(UsageRecord.tenant_id == tenant_id)
    if user_id:
        conditions.append(UsageRecord.user_id == user_id)
    if usage_type:
        conditions.append(UsageRecord.usage_type == usage_type)
    if service_provider:
        conditions.append(UsageRecord.service_provider == service_provider)
    if start_date:
        conditions.append(UsageRecord.created_at >= start_date)
    if end_date:
        conditions.append(UsageRecord.created_at <= end_date)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size).order_by(desc(UsageRecord.created_at))
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return PaginatedResponse(
        items=[UsageRecordResponse.model_validate(record) for record in records],
        total=total or 0,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=((total or 0) + pagination.page_size - 1) // pagination.page_size
    )


@router.get("/system/metrics", response_model=List[SystemMetricsResponse])
async def get_system_metrics(
    current_user: User = Depends(require_admin_user),
    metric_type: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),  # Max 1 week
    db: AsyncSession = Depends(get_db)
):
    """Get system metrics"""
    
    metrics = await usage_service.get_system_metrics(
        db=db,
        metric_type=metric_type,
        hours=hours
    )
    
    return [SystemMetricsResponse.model_validate(metric) for metric in metrics]


@router.post("/system/metrics")
async def record_system_metric(
    metric_type: str,
    value: int,
    current_user: User = Depends(require_admin_user),
    tenant_id: Optional[UUID] = None,
    additional_data: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    """Record a system metric (admin only)"""
    
    metric = await usage_service.record_system_metric(
        db=db,
        metric_type=metric_type,
        value=value,
        tenant_id=tenant_id,
        additional_data=additional_data
    )
    
    return {"message": "Metric recorded", "id": str(metric.id)}


@router.get("/usage/by-organization")
async def get_usage_by_organization(
    current_user: User = Depends(require_admin_user),
    period: str = Query("month", pattern="^(day|week|month)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics broken down by organization/tenant"""
    
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        if period == "day":
            start_date = end_date - timedelta(days=1)
        elif period == "week":
            start_date = end_date - timedelta(weeks=1)
        else:  # month
            start_date = end_date - timedelta(days=30)
    
    # Query for usage by tenant
    usage_query = select(
        Tenant.id.label('tenant_id'),
        Tenant.name.label('tenant_name'),
        Tenant.subdomain.label('subdomain'),
        UsageRecord.usage_type,
        func.sum(UsageRecord.amount).label('total_amount'),
        func.sum(UsageRecord.cost_cents).label('total_cost'),
        func.count(UsageRecord.id).label('record_count')
    ).select_from(
        Tenant
    ).outerjoin(
        UsageRecord,
        and_(
            UsageRecord.tenant_id == Tenant.id,
            UsageRecord.created_at >= start_date,
            UsageRecord.created_at <= end_date
        )
    ).group_by(
        Tenant.id, Tenant.name, Tenant.subdomain, UsageRecord.usage_type
    ).order_by(Tenant.name)
    
    result = await db.execute(usage_query)
    usage_data = result.all()
    
    # Organize data by tenant
    tenant_usage = {}
    for row in usage_data:
        tenant_id = str(row.tenant_id)
        if tenant_id not in tenant_usage:
            tenant_usage[tenant_id] = {
                "tenant_id": tenant_id,
                "tenant_name": row.tenant_name,
                "subdomain": row.subdomain,
                "total_tokens": 0,
                "total_tts_words": 0,
                "total_stt_words": 0,
                "total_cost_cents": 0,
                "record_count": 0
            }
        
        if row.usage_type:  # Only process if there's actual usage
            if row.usage_type == "tokens":
                tenant_usage[tenant_id]["total_tokens"] = row.total_amount or 0
            elif row.usage_type == "tts_words":
                tenant_usage[tenant_id]["total_tts_words"] = row.total_amount or 0
            elif row.usage_type == "stt_words":
                tenant_usage[tenant_id]["total_stt_words"] = row.total_amount or 0
            
            tenant_usage[tenant_id]["total_cost_cents"] += row.total_cost or 0
            tenant_usage[tenant_id]["record_count"] += row.record_count or 0
    
    return {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "organizations": list(tenant_usage.values())
    }


@router.get("/tenants")
async def list_tenants(
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all tenants (super admin only)"""
    
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    
    return [
        {
            "id": str(tenant.id),
            "name": tenant.name,
            "subdomain": tenant.subdomain,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at,
            "access_code": tenant.access_code
        }
        for tenant in tenants
    ]


@router.get("/websocket/stats")
async def get_admin_websocket_stats(
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed WebSocket connection statistics (admin only)"""
    
    try:
        from app.api.websockets import connection_manager, connection_stats, active_connections, connection_lock
        
        # Get stats from connection manager
        cm_stats = connection_manager.get_stats()
        
        # Get stats from global active_connections
        async with connection_lock:
            total_active = sum(len(sockets) for sockets in active_connections.values())
            conversations_with_connections = len(active_connections)
            
            # Update connection_stats
            connection_stats["total"] = total_active
            connection_stats["by_conversation"] = {
                str(conv_id): len(sockets) 
                for conv_id, sockets in active_connections.items()
            }
        
        # Get cleanup task status
        from app.api.websockets import cleanup_task
        cleanup_running = cleanup_task is not None and not cleanup_task.done()
        
        return {
            "connection_manager": cm_stats,
            "global_connections": {
                "total": total_active,
                "conversations": conversations_with_connections,
                "by_conversation": connection_stats["by_conversation"],
                "last_cleanup": connection_stats.get("last_cleanup")
            },
            "limits": {
                "max_total": 500,  # MAX_TOTAL_CONNECTIONS
                "max_per_conversation": 50  # MAX_CONNECTIONS_PER_CONVERSATION
            },
            "cleanup_task": {
                "running": cleanup_running,
                "last_run": connection_stats.get("last_cleanup")
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting WebSocket stats: {str(e)}"
        )


@router.get("/telephony/configs")
async def list_telephony_configs(
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all telephony configurations (admin only)"""
    
    query = select(TelephonyConfiguration).join(Tenant)
    result = await db.execute(query)
    configs = result.scalars().all()
    
    config_list = []
    for config in configs:
        # Get tenant info
        tenant_query = select(Tenant).where(Tenant.id == config.tenant_id)
        tenant_result = await db.execute(tenant_query)
        tenant = tenant_result.scalar_one_or_none()
        
        config_list.append({
            "id": str(config.id),
            "tenant_id": str(config.tenant_id),
            "tenant_name": tenant.name if tenant else "Unknown",
            "organization_phone_number": config.organization_phone_number,
            "formatted_phone_number": config.formatted_phone_number,
            "platform_phone_number": config.platform_phone_number,
            "verification_status": config.verification_status,
            "call_forwarding_enabled": config.call_forwarding_enabled,
            "is_enabled": config.is_enabled,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        })
    
    return {
        "configs": config_list,
        "total": len(config_list)
    }


@router.post("/telephony/manual-verify/{config_id}")
async def manual_verify_phone(
    config_id: UUID,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually verify a phone number (admin only)"""
    
    # Only super admins can perform manual verification
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403, 
            detail="Super admin access required for manual verification"
        )
    
    # Get telephony configuration
    config_query = select(TelephonyConfiguration).where(
        TelephonyConfiguration.id == config_id
    )
    config_result = await db.execute(config_query)
    config = config_result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Telephony configuration not found")
    
    # Get tenant info for logging
    tenant_query = select(Tenant).where(Tenant.id == config.tenant_id)
    tenant_result = await db.execute(tenant_query)
    tenant = tenant_result.scalar_one_or_none()
    
    # Update verification status
    config.verification_status = PhoneVerificationStatus.VERIFIED.value
    config.call_forwarding_enabled = True
    
    await db.commit()
    await db.refresh(config)
    
    logger.info(f"🔧 Admin {current_user.email} manually verified phone {config.organization_phone_number} for tenant {tenant.name if tenant else config.tenant_id}")
    
    return {
        "success": True,
        "message": f"Phone number {config.organization_phone_number} manually verified",
        "config_id": str(config.id),
        "tenant_name": tenant.name if tenant else "Unknown",
        "verification_status": config.verification_status,
        "call_forwarding_enabled": config.call_forwarding_enabled
    }


@router.post("/telephony/manual-unverify/{config_id}")
async def manual_unverify_phone(
    config_id: UUID,
    current_user: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually unverify a phone number (admin only)"""
    
    # Only super admins can perform manual unverification
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403, 
            detail="Super admin access required for manual unverification"
        )
    
    # Get telephony configuration
    config_query = select(TelephonyConfiguration).where(
        TelephonyConfiguration.id == config_id
    )
    config_result = await db.execute(config_query)
    config = config_result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Telephony configuration not found")
    
    # Get tenant info for logging
    tenant_query = select(Tenant).where(Tenant.id == config.tenant_id)
    tenant_result = await db.execute(tenant_query)
    tenant = tenant_result.scalar_one_or_none()
    
    # Update verification status
    config.verification_status = PhoneVerificationStatus.PENDING.value
    config.call_forwarding_enabled = False
    
    await db.commit()
    await db.refresh(config)
    
    logger.info(f"🔧 Admin {current_user.email} manually unverified phone {config.organization_phone_number} for tenant {tenant.name if tenant else config.tenant_id}")
    
    return {
        "success": True,
        "message": f"Phone number {config.organization_phone_number} manually unverified",
        "config_id": str(config.id),
        "tenant_name": tenant.name if tenant else "Unknown",
        "verification_status": config.verification_status,
        "call_forwarding_enabled": config.call_forwarding_enabled
    }