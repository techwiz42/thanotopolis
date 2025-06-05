"""
System monitoring service for tracking connections and performance metrics
"""
import asyncio
import psutil
import time
from typing import Dict, Any, Set
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.services.usage_service import usage_service


class MonitoringService:
    """Service for monitoring system resources and connections"""
    
    def __init__(self):
        self.active_websocket_connections: Set[str] = set()
        self.connection_metrics: Dict[str, Any] = {}
        self.last_metrics_update = time.time()
        
    def add_websocket_connection(self, connection_id: str, user_id: str = None, tenant_id: str = None):
        """Track a new WebSocket connection"""
        self.active_websocket_connections.add(connection_id)
        self.connection_metrics[connection_id] = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
    
    def remove_websocket_connection(self, connection_id: str):
        """Remove a WebSocket connection from tracking"""
        self.active_websocket_connections.discard(connection_id)
        self.connection_metrics.pop(connection_id, None)
    
    def update_websocket_activity(self, connection_id: str):
        """Update last activity time for a WebSocket connection"""
        if connection_id in self.connection_metrics:
            self.connection_metrics[connection_id]["last_activity"] = datetime.utcnow()
    
    def get_websocket_count(self) -> int:
        """Get current number of active WebSocket connections"""
        return len(self.active_websocket_connections)
    
    def get_websocket_connections_by_tenant(self) -> Dict[str, int]:
        """Get WebSocket connection count by tenant"""
        tenant_counts = {}
        for conn_id, metrics in self.connection_metrics.items():
            tenant_id = metrics.get("tenant_id")
            if tenant_id:
                tenant_counts[tenant_id] = tenant_counts.get(tenant_id, 0) + 1
        return tenant_counts
    
    async def get_database_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get database connection pool and performance metrics"""
        metrics = {}
        
        try:
            # Get database connection info
            result = await db.execute(text("SELECT count(*) as connection_count FROM pg_stat_activity WHERE state = 'active'"))
            active_connections = result.scalar()
            
            # Get database size
            result = await db.execute(text("SELECT pg_database_size(current_database()) as db_size"))
            db_size = result.scalar()
            
            # Get table counts
            result = await db.execute(text("SELECT schemaname, tablename, n_tup_ins + n_tup_upd + n_tup_del as total_changes FROM pg_stat_user_tables ORDER BY total_changes DESC LIMIT 10"))
            table_stats = result.fetchall()
            
            metrics = {
                "active_connections": active_connections,
                "database_size_bytes": db_size,
                "table_activity": [
                    {
                        "schema": row.schemaname,
                        "table": row.tablename,
                        "total_changes": row.total_changes
                    }
                    for row in table_stats
                ]
            }
            
        except Exception as e:
            metrics = {"error": str(e), "active_connections": 0}
        
        return metrics
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "timestamp": datetime.utcnow()
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.utcnow()}
    
    async def record_periodic_metrics(self, db: AsyncSession):
        """Record system metrics to database"""
        try:
            # Record WebSocket connections
            ws_count = self.get_websocket_count()
            await usage_service.record_system_metric(
                db=db,
                metric_type="ws_connections",
                value=ws_count,
                additional_data={"tenant_breakdown": self.get_websocket_connections_by_tenant()}
            )
            
            # Record database metrics
            db_metrics = await self.get_database_metrics(db)
            if "active_connections" in db_metrics:
                await usage_service.record_system_metric(
                    db=db,
                    metric_type="db_connections",
                    value=db_metrics["active_connections"],
                    additional_data=db_metrics
                )
            
            # Record system metrics
            sys_metrics = self.get_system_metrics()
            if "cpu_percent" in sys_metrics:
                await usage_service.record_system_metric(
                    db=db,
                    metric_type="cpu_usage",
                    value=int(sys_metrics["cpu_percent"]),
                    additional_data=sys_metrics
                )
                
                await usage_service.record_system_metric(
                    db=db,
                    metric_type="memory_usage",
                    value=int(sys_metrics["memory_percent"]),
                    additional_data=sys_metrics
                )
            
        except Exception as e:
            print(f"Error recording metrics: {e}")
    
    async def start_monitoring_loop(self, db_session_factory, interval_seconds: int = 60):
        """Start background monitoring loop"""
        while True:
            try:
                async with db_session_factory() as db:
                    await self.record_periodic_metrics(db)
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)


# Global monitoring instance
monitoring_service = MonitoringService()


# Decorator to track WebSocket connections
def track_websocket_connection(user_id: str = None, tenant_id: str = None):
    """Decorator to automatically track WebSocket connections"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import uuid
            connection_id = str(uuid.uuid4())
            
            monitoring_service.add_websocket_connection(
                connection_id=connection_id,
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            try:
                # Add connection_id to kwargs for the function to use
                kwargs['connection_id'] = connection_id
                result = await func(*args, **kwargs)
                return result
            finally:
                monitoring_service.remove_websocket_connection(connection_id)
        
        return wrapper
    return decorator