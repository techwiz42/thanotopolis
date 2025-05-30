# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.db.database import init_db
from app.api.auth import router as auth_router
from app.api.voice_streaming import router as voice_streaming_router
from app.api.websockets import router as websockets_router
from app.api.conversations import router as conversations_router
from app.core.config import settings

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    # Clean up voice streaming handlers if any are active
    try:
        from app.api.voice_streaming import shutdown_all_handlers
        await shutdown_all_handlers()
    except Exception as e:
        print(f"Error shutting down voice handlers: {e}")

# Create FastAPI app
app = FastAPI(
    title="Thanotopolis Auth API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "thanotopolis-auth"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Thanotopolis Auth API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/auth",
            "voice": {
                "streaming_stt": "ws://localhost:8000/api/ws/voice/streaming-stt",
                "status": "/api/voice/stt/status"
            },
            "websockets": {
                "conversations": "ws://localhost:8000/api/ws/conversations/{conversation_id}",
                "notifications": "ws://localhost:8000/api/ws/notifications"
            }
        }
    }

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(voice_streaming_router, prefix="/api")
app.include_router(websockets_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
