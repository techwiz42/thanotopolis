# backend/app/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import uvicorn
import time
import logging
import traceback

from app.db.database import init_db
from app.api.auth import router as auth_router
from app.api.voice_streaming import router as voice_streaming_router
from app.api.streaming_stt import router as streaming_stt_router
from app.api.websockets import router as websockets_router
from app.api.conversations import router as conversations_router
from app.api.admin import router as admin_router
from app.api.billing import router as billing_router
from app.api.organizations import router as organizations_router
from app.api.agents import router as agents_router
# NEW: Telephony routers
from app.api.telephony import router as telephony_router
from app.api.telephony_websocket import router as telephony_ws_router
# CRM router
from app.api.crm import router as crm_router
# Calendar router
from app.api.calendar import router as calendar_router
from app.core.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Silence noisy third-party loggers
logging.getLogger('multipart.multipart').setLevel(logging.WARNING)
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('websockets').setLevel(logging.WARNING)

# Keep our app loggers at DEBUG for detailed debugging
logging.getLogger('app').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting up Thanotopolis API with Telephony Support...")
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Initialize telephony services if enabled
    telephony_cleanup_task = None
    if getattr(settings, 'TELEPHONY_ENABLED', False):
        logger.info("📞 Telephony services enabled")
        if not getattr(settings, 'TWILIO_ACCOUNT_SID', None):
            logger.warning("⚠️  Twilio credentials not configured - running in mock mode")
        
        # Start telephony cleanup task
        try:
            from app.tasks.telephony_cleanup import start_cleanup_task
            start_cleanup_task()
            logger.info("✅ Telephony cleanup task started")
        except Exception as e:
            logger.error(f"⚠️  Failed to start telephony cleanup task: {e}")
    else:
        logger.info("📞 Telephony services disabled")
    
    # Start background task for websocket cleanup
    import asyncio
    cleanup_task = asyncio.create_task(websocket_cleanup_task())
    logger.info("✅ WebSocket cleanup task started")
    
    logger.info("✅ Application startup complete")
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down application...")
    
    # Cancel background tasks
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("✅ WebSocket cleanup task cancelled")
    
    # Clean up voice streaming handlers if any are active
    try:
        from app.api.voice_streaming import shutdown_all_handlers
        await shutdown_all_handlers()
        logger.info("✅ Voice handlers shut down successfully")
    except Exception as e:
        logger.error(f"⚠️  Error shutting down voice handlers: {e}")
    
    # Clean up STT handlers if any are active
    try:
        from app.api.streaming_stt import shutdown_stt_handlers
        await shutdown_stt_handlers()
        logger.info("✅ STT handlers shut down successfully")
    except Exception as e:
        logger.error(f"⚠️  Error shutting down STT handlers: {e}")
    
    # Clean up telephony connections
    try:
        from app.api.telephony_websocket import telephony_stream_handler
        telephony_stream_handler.active_connections.clear()
        telephony_stream_handler.call_sessions.clear()
        logger.info("✅ Telephony connections cleaned up")
    except Exception as e:
        logger.error(f"⚠️  Error cleaning up telephony connections: {e}")
    
    # Stop telephony cleanup task
    try:
        from app.tasks.telephony_cleanup import stop_cleanup_task
        stop_cleanup_task()
        logger.info("✅ Telephony cleanup task stopped")
    except Exception as e:
        logger.error(f"⚠️  Error stopping telephony cleanup task: {e}")
    
    logger.info("✅ Application shutdown complete")

# Background task for websocket cleanup
async def websocket_cleanup_task():
    """Background task to periodically clean up stale websocket connections"""
    import asyncio
    from app.api.websockets import connection_manager
    
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            await connection_manager.cleanup_stale_connections()
        except asyncio.CancelledError:
            logger.info("🧹 WebSocket cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"⚠️  Error in websocket cleanup: {e}")
            await asyncio.sleep(10)  # Wait before retrying

# Create FastAPI app
app = FastAPI(
    title="Thanotopolis AI Platform with Telephony",
    version="1.1.0",
    description="AI conversation platform with telephony support",
    lifespan=lifespan
)

# CORS middleware
cors_origins = getattr(settings, 'CORS_ORIGINS', ["http://localhost:3000"])
logger.info(f"🌐 CORS origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug middleware to track requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    start_time = time.time()
    
    # Get client info
    client_host = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
    
    # Log request details (but not too verbose for WebSocket upgrades)
    if request.url.path.startswith("/api/ws/"):
        logger.info(f"🔌 WebSocket: {request.method} {request.url.path} from {client_host}")
    elif request.url.path in ["/favicon.ico", "/robots.txt"]:
        logger.debug(f"📄 Static: {request.method} {request.url.path} from {client_host}")
    else:
        logger.info(f"📨 HTTP: {request.method} {request.url.path} from {client_host}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"   Headers: {dict(request.headers)}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        if request.url.path.startswith("/api/ws/"):
            logger.info(f"✅ WebSocket response: {response.status_code} ({process_time:.3f}s)")
        elif request.url.path in ["/favicon.ico", "/robots.txt"]:
            logger.debug(f"✅ Static response: {response.status_code} ({process_time:.3f}s)")
        else:
            logger.info(f"✅ HTTP response: {response.status_code} ({process_time:.3f}s)")
            
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"❌ Error processing {request.url.path}: {e} ({process_time:.3f}s)")
        logger.error(f"   Traceback: {traceback.format_exc()}")
        raise

# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logger.warning(f"🔍 404 Not Found: {request.method} {request.url.path}")
    
    # Check if this is a custom HTTP exception with a detail
    if hasattr(exc, "detail"):
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc.detail)}
        )
    
    # Pattern match for user endpoints
    if "/api/users/" in request.url.path:
        return JSONResponse(
            status_code=404,
            content={"detail": "User not found"}
        )
    
    # Default response for path not found
    return JSONResponse(
        status_code=404,
        content={
            "detail": f"Path {request.url.path} not found",
            "method": request.method,
            "available_endpoints": {
                "health": "/health",
                "docs": "/docs",
                "api_docs": "/api/docs",
                "auth": "/api/auth",
                "conversations": "/api/conversations",
                "telephony": "/api/telephony"
            }
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"💥 500 Internal Server Error: {request.method} {request.url.path}")
    logger.error(f"   Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_error"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"⚠️  Validation Error: {request.method} {request.url.path}")
    logger.warning(f"   Errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

# Common static file handlers
@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to prevent 404s"""
    logger.debug("📄 Serving favicon.ico")
    return Response(status_code=204)

@app.get("/robots.txt")
async def robots():
    """Return robots.txt"""
    logger.debug("📄 Serving robots.txt")
    return Response(
        content="User-agent: *\nDisallow: /api/\nAllow: /health\nAllow: /docs\n",
        media_type="text/plain"
    )

# Health and status endpoints
@app.get("/health")
async def health_check():
    """Primary health check endpoint"""
    return {
        "status": "healthy", 
        "service": "thanotopolis-ai-platform",
        "version": "1.1.0",
        "features": {
            "telephony": getattr(settings, 'TELEPHONY_ENABLED', False),
            "voice_streaming": True,
            "websockets": True
        },
        "timestamp": time.time()
    }

@app.get("/status")
async def status():
    """Alternative health check endpoint"""
    return {
        "status": "ok", 
        "service": "thanotopolis",
        "uptime": time.time()
    }

@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"ping": "pong", "timestamp": time.time()}

# Root endpoint
@app.get("/")
async def root():
    """API root with endpoint information"""
    return {
        "message": "Thanotopolis AI Platform with Telephony",
        "version": "1.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "auth": {
                "base": "/api/auth",
                "login": "/api/auth/login",
                "register": "/api/auth/register",
                "me": "/api/auth/me"
            },
            "conversations": {
                "base": "/api/conversations",
                "list": "/api/conversations",
                "create": "/api/conversations"
            },
            "telephony": {
                "base": "/api/telephony",
                "setup": "/api/telephony/setup",
                "verify": "/api/telephony/verify/initiate",
                "calls": "/api/telephony/calls",
                "webhook": "/api/telephony/webhook/incoming-call"
            },
            "voice": {
                "streaming_stt": "ws://localhost:8000/api/ws/voice/streaming-stt",
                "status": "/api/voice/stt/status"
            },
            "websockets": {
                "conversations": "ws://localhost:8000/api/ws/conversations/{conversation_id}",
                "notifications": "ws://localhost:8000/api/ws/notifications",
                "telephony": "ws://localhost:8000/api/ws/telephony/stream/{call_id}"
            }
        },
        "cors_origins": cors_origins,
        "timestamp": time.time()
    }

# API Info endpoint
@app.get("/api")
async def api_info():
    """API information"""
    return {
        "name": "Thanotopolis AI Platform",
        "version": "1.1.0",
        "description": "AI conversation platform with telephony support",
        "docs": "/docs",
        "health": "/health",
        "features": {
            "telephony": getattr(settings, 'TELEPHONY_ENABLED', False),
            "voice_streaming": True,
            "websockets": True,
            "multi_tenant": True
        }
    }

# Include routers with logging
logger.info("📋 Registering API routers...")

try:
    app.include_router(auth_router, prefix="/api", tags=["Authentication"])
    logger.info("✅ Auth router registered")
except Exception as e:
    logger.error(f"❌ Failed to register auth router: {e}")

try:
    app.include_router(voice_streaming_router, prefix="/api", tags=["Voice Streaming"])
    logger.info("✅ Voice streaming router registered")
except Exception as e:
    logger.error(f"❌ Failed to register voice streaming router: {e}")

try:
    app.include_router(streaming_stt_router, prefix="/api", tags=["Streaming STT"])
    logger.info("✅ Streaming STT router registered")
except Exception as e:
    logger.error(f"❌ Failed to register streaming STT router: {e}")

try:
    app.include_router(websockets_router, prefix="/api", tags=["WebSockets"])
    logger.info("✅ WebSocket router registered")
except Exception as e:
    logger.error(f"❌ Failed to register websocket router: {e}")

try:
    app.include_router(conversations_router, prefix="/api", tags=["Conversations"])
    logger.info("✅ Conversations router registered")
except Exception as e:
    logger.error(f"❌ Failed to register conversations router: {e}")

try:
    app.include_router(admin_router, prefix="/api", tags=["Admin"])
    logger.info("✅ Admin router registered")
except Exception as e:
    logger.error(f"❌ Failed to register admin router: {e}")

try:
    app.include_router(billing_router, tags=["Billing"])
    logger.info("✅ Billing router registered")
except Exception as e:
    logger.error(f"❌ Failed to register billing router: {e}")

try:
    app.include_router(organizations_router, tags=["Organizations"])
    logger.info("✅ Organizations router registered")
except Exception as e:
    logger.error(f"❌ Failed to register organizations router: {e}")

try:
    app.include_router(agents_router, tags=["Agents"])
    logger.info("✅ Agents router registered")
except Exception as e:
    logger.error(f"❌ Failed to register agents router: {e}")

# CRM router
try:
    app.include_router(crm_router, prefix="/api", tags=["CRM"])
    logger.info("✅ CRM router registered")
except Exception as e:
    logger.error(f"❌ Failed to register CRM router: {e}")

# Calendar router
try:
    app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar"])
    logger.info("✅ Calendar router registered")
except Exception as e:
    logger.error(f"❌ Failed to register calendar router: {e}")

# NEW: Add telephony routers
try:
    app.include_router(telephony_router, prefix="/api", tags=["Telephony"])
    logger.info("✅ Telephony router registered")
except Exception as e:
    logger.error(f"❌ Failed to register telephony router: {e}")

try:
    # Register the appropriate telephony WebSocket router based on feature flag
    if getattr(settings, 'USE_VOICE_AGENT', False):
        from app.api.telephony_voice_agent import telephony_voice_agent_websocket
        from fastapi import APIRouter
        
        voice_agent_router = APIRouter()
        voice_agent_router.add_websocket_route("/ws/telephony/voice-agent/stream", telephony_voice_agent_websocket)
        app.include_router(voice_agent_router, prefix="/api", tags=["Telephony Voice Agent"])
        logger.info("✅ Telephony Voice Agent router registered")
    else:
        app.include_router(telephony_ws_router, prefix="/api", tags=["Telephony WebSocket"])
        logger.info("✅ Telephony WebSocket router registered")
except Exception as e:
    logger.error(f"❌ Failed to register telephony WebSocket router: {e}")

logger.info("✅ All routers registered successfully")

# Debug endpoint to check router registration
@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, 'name', 'unnamed')
            })
    return {
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x['path'])
    }

# Startup event (alternative to lifespan for debugging)
@app.on_event("startup")
async def startup_event():
    """Additional startup logging"""
    logger.info("🎯 FastAPI startup event triggered")
    logger.info(f"🌐 Server will be available at: http://0.0.0.0:8000")
    logger.info(f"📚 API docs available at: http://0.0.0.0:8000/docs")

if __name__ == "__main__":
    logger.info("🚀 Starting server directly...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
