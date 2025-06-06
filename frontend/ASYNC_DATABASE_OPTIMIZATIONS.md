# Async Database Optimizations

## Good News: Backend is Already Fully Async! ✅

The backend is already using **async SQLAlchemy with asyncpg** throughout the application. This is excellent for performance and scalability.

## Current Async Architecture

### Database Layer
- ✅ `create_async_engine` with `asyncpg` driver
- ✅ `async_sessionmaker` for session management
- ✅ Proper async dependency injection
- ✅ All API endpoints use `AsyncSession = Depends(get_db)`
- ✅ WebSocket handlers are fully async
- ✅ No sync/async mixing detected

### Performance Features Already in Place
- ✅ Connection pooling with `create_async_engine`
- ✅ `expire_on_commit=False` to prevent unnecessary DB hits
- ✅ Proper relationship loading with `selectinload()` and `joinedload()`
- ✅ Strategic indexing on high-query columns
- ✅ Multi-tenant architecture with efficient isolation

## Specific Optimizations for Current Async Setup

### 1. Optimize Connection Pool Configuration

**Current Issue**: Default pool settings may not be optimal for high concurrency.

**Solution**: Tune async engine parameters in `/backend/app/db/database.py`:

```python
# Enhanced async engine configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    
    # Connection Pool Settings (Critical for async performance)
    pool_size=50,                    # Base connections (up from default 5)
    max_overflow=100,                # Additional connections (up from default 10)
    pool_timeout=30,                 # Max wait time for connection
    pool_recycle=3600,               # Recycle connections every hour
    pool_pre_ping=True,              # Test connections before use
    
    # Async-specific optimizations
    pool_reset_on_return='commit',   # Reset connections properly
    connect_args={
        "server_settings": {
            "jit": "off",            # Disable JIT for better connection times
            "application_name": "thanotopolis_async"
        },
        "command_timeout": 60,       # Command timeout
        "server_settings": {
            "tcp_keepalives_idle": "600",      # Keep connections alive
            "tcp_keepalives_interval": "30",
            "tcp_keepalives_count": "3"
        }
    }
)
```

### 2. Implement Async Connection Context Patterns

**Add connection health monitoring**:

```python
# In /backend/app/db/database.py
import asyncio
from typing import AsyncGenerator

class AsyncDBManager:
    def __init__(self, engine):
        self.engine = engine
        self._connection_count = 0
    
    async def get_pool_stats(self):
        """Get current connection pool statistics"""
        pool = self.engine.pool
        return {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin()
        }
    
    async def health_check(self) -> bool:
        """Quick async health check"""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

# Initialize manager
db_manager = AsyncDBManager(engine)
```

### 3. Optimize Query Patterns for Async

**Batch Operations** for better async performance:

```python
# In your service files - batch operations
async def batch_create_messages(
    db: AsyncSession,
    messages_data: List[MessageCreate]
) -> List[Message]:
    """Efficiently create multiple messages in a single transaction"""
    messages = [Message(**msg_data.dict()) for msg_data in messages_data]
    
    # Add all at once
    db.add_all(messages)
    
    # Single commit for all
    await db.commit()
    
    # Refresh all efficiently
    for msg in messages:
        await db.refresh(msg)
    
    return messages

async def batch_update_usage(
    db: AsyncSession,
    usage_updates: List[Dict]
) -> None:
    """Batch update usage records efficiently"""
    # Use bulk update for better performance
    await db.execute(
        update(UsageRecord)
        .where(UsageRecord.id == bindparam('record_id'))
        .values(
            tokens_used=bindparam('tokens'),
            cost_cents=bindparam('cost')
        ),
        usage_updates
    )
    await db.commit()
```

### 4. Implement Async Query Optimization

**Add query performance monitoring**:

```python
# In /backend/app/middleware/db_monitoring.py
import time
from contextvars import ContextVar
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

# Context variable to track query performance
query_time_ctx: ContextVar[float] = ContextVar('query_time', default=0.0)

@event.listens_for(AsyncSession.sync_session, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(AsyncSession.sync_session, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    
    # Log slow queries
    if total > 0.5:  # Queries taking more than 500ms
        logger.warning(f"Slow query detected: {total:.2f}s - {statement[:100]}...")
    
    # Update context
    current_time = query_time_ctx.get(0.0)
    query_time_ctx.set(current_time + total)
```

### 5. Async Transaction Management Patterns

**Implement nested transaction patterns**:

```python
# In your service files
from contextlib import asynccontextmanager

@asynccontextmanager
async def async_transaction(db: AsyncSession):
    """Async context manager for database transactions"""
    async with db.begin():
        try:
            yield db
        except Exception:
            await db.rollback()
            raise
        else:
            await db.commit()

# Usage example
async def complex_conversation_operation(
    db: AsyncSession,
    conversation_data: dict
) -> Conversation:
    async with async_transaction(db) as tx_db:
        # Create conversation
        conversation = Conversation(**conversation_data)
        tx_db.add(conversation)
        await tx_db.flush()  # Get ID without committing
        
        # Create initial message
        message = Message(
            conversation_id=conversation.id,
            content="Welcome to the conversation!"
        )
        tx_db.add(message)
        
        # Update usage
        usage = UsageRecord(
            tenant_id=conversation.tenant_id,
            conversation_id=conversation.id,
            tokens_used=10
        )
        tx_db.add(usage)
        
        # All committed together or rolled back on error
        return conversation
```

### 6. Async Caching Integration

**Add async caching for frequent queries**:

```python
# Install: pip install aioredis
import aioredis
import json
from typing import Optional

class AsyncCache:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = aioredis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[dict]:
        """Get cached data"""
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def set(self, key: str, value: dict, ttl: int = 300):
        """Cache data with TTL"""
        await self.redis.setex(key, ttl, json.dumps(value))
    
    async def delete(self, key: str):
        """Delete cached data"""
        await self.redis.delete(key)

# Usage in services
cache = AsyncCache()

async def get_dashboard_stats_cached(
    db: AsyncSession,
    tenant_id: str
) -> dict:
    cache_key = f"dashboard_stats:{tenant_id}"
    
    # Try cache first
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Fetch from database
    stats = await get_dashboard_stats_from_db(db, tenant_id)
    
    # Cache for 5 minutes
    await cache.set(cache_key, stats, ttl=300)
    
    return stats
```

### 7. WebSocket Async Optimizations

**Optimize WebSocket database operations**:

```python
# In WebSocket handlers
async def handle_message_async(
    websocket: WebSocket,
    message_data: dict,
    db: AsyncSession
):
    """Async message handling without blocking"""
    
    # Don't await database operations that don't need immediate response
    async def save_message_background():
        message = Message(**message_data)
        db.add(message)
        await db.commit()
    
    # Send immediate response
    await websocket.send_json({"status": "received"})
    
    # Save to database in background
    asyncio.create_task(save_message_background())
    
    # Process with AI (this can be long-running)
    response = await process_with_ai(message_data["content"])
    
    # Send AI response
    await websocket.send_json({"content": response})
```

### 8. Database Connection Monitoring

**Add async monitoring endpoint**:

```python
# Add to your API routes
@app.get("/api/admin/db-stats")
async def get_database_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """Get real-time database connection statistics"""
    
    pool_stats = await db_manager.get_pool_stats()
    health = await db_manager.health_check()
    
    return {
        "pool_stats": pool_stats,
        "healthy": health,
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Performance Testing for Async Setup

### 1. Connection Pool Load Test

```python
# Test script for async connection handling
import asyncio
import asyncpg
import time

async def test_connection_pool_performance():
    """Test async connection pool under load"""
    
    async def make_query(pool):
        async with pool.acquire() as conn:
            await conn.execute("SELECT COUNT(*) FROM users")
    
    # Create connection pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=10,
        max_size=50
    )
    
    # Test concurrent queries
    start_time = time.time()
    tasks = [make_query(pool) for _ in range(1000)]
    await asyncio.gather(*tasks)
    end_time = time.time()
    
    print(f"1000 concurrent queries completed in {end_time - start_time:.2f}s")
    await pool.close()

# Run test
asyncio.run(test_connection_pool_performance())
```

### 2. WebSocket Concurrent Connection Test

```python
# Test WebSocket async handling
import asyncio
import websockets

async def test_websocket_load():
    async def connect_and_send():
        uri = "ws://localhost:8000/api/ws/conversations/test"
        async with websockets.connect(uri) as websocket:
            await websocket.send('{"type": "message", "content": "test"}')
            response = await websocket.recv()
            print(f"Received: {response}")
    
    # Test 100 concurrent WebSocket connections
    tasks = [connect_and_send() for _ in range(100)]
    await asyncio.gather(*tasks, return_exceptions=True)

asyncio.run(test_websocket_load())
```

## Monitoring Async Performance

### 1. Add to your monitoring dashboard:

```python
# Metrics to track
async_metrics = {
    "connection_pool_size": pool.size(),
    "active_connections": pool.checkedout(),
    "avg_query_time": query_time_ctx.get(),
    "websocket_connections": len(active_websockets),
    "cache_hit_rate": cache.hit_rate(),
}
```

### 2. Set up alerts for:
- Connection pool exhaustion (>80% utilization)
- Slow queries (>500ms)
- High WebSocket connection count
- Cache miss rate (>50%)

## Summary

Your backend's async architecture is already excellent. Focus on:

1. **Connection pool tuning** (most important)
2. **Query optimization** with monitoring
3. **Async caching layer** for frequent queries
4. **Background task processing** for non-critical operations
5. **Connection health monitoring**

These optimizations will handle 1000+ concurrent users effectively while maintaining the clean async architecture you already have.