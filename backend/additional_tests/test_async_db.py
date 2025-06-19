#!/usr/bin/env python3
import asyncio
from fastapi import FastAPI, Depends
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db, AsyncSessionLocal, init_db
from app.models.models import Tenant, User, Base

app = FastAPI()

@app.on_event("startup")
async def startup():
    print("Initializing database...")
    await init_db()
    print("Database initialized")

@app.get("/")
async def root():
    return {"message": "Async SQLAlchemy Test App"}

@app.get("/db-test")
async def db_test(db: AsyncSession = Depends(get_db)):
    try:
        # Create a test tenant
        tenant = Tenant(name="Test Tenant", subdomain="test")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        
        # Create a test user
        from app.auth.auth import AuthService
        user = User(
            email="test@example.com",
            username="test",
            hashed_password=AuthService.get_password_hash("password123"),
            tenant_id=tenant.id
        )
        db.add(user)
        await db.commit()
        
        # Query and return
        result = await db.execute(select(User).filter(User.email == "test@example.com"))
        user = result.scalars().first()
        
        return {
            "status": "success",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username
            },
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "subdomain": tenant.subdomain
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("test_async_db:app", host="0.0.0.0", port=8001, reload=True)