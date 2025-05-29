# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.db.database import init_db, get_db_context
from app.auth.auth import get_tenant_from_request
from app.api.auth import router as auth_router
from app.core.config import settings

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown

# Create FastAPI app
app = FastAPI(
    title="Multi-Tenant Auth API",
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

# Middleware to set tenant context
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # Skip tenant check for certain paths
    if request.url.path in ["/", "/docs", "/openapi.json", "/health", "/api/tenants"]:
        return await call_next(request)
    
    # For auth endpoints, we'll handle tenant differently
    if request.url.path.startswith("/api/auth"):
        return await call_next(request)
    
    # For other endpoints, require tenant context
    async with get_db_context() as db:
        tenant = await get_tenant_from_request(request, db)
        if not tenant and not request.url.path.startswith("/api/tenants"):
            return JSONResponse(
                status_code=400,
                content={"detail": "Tenant not found"}
            )
    
    response = await call_next(request)
    return response

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "multi-tenant-auth"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Multi-Tenant Auth API",
        "version": "0.0.1",
        "docs": "/docs"
    }

# Include routers
app.include_router(auth_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
