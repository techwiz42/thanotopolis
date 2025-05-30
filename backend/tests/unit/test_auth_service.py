# backend/tests/unit/test_auth_service.py
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import HTTPException

from app.auth.auth import AuthService
from app.core.config import settings
from app.models.models import User, RefreshToken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

class TestAuthService:
    """Test suite for AuthService utility functions."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "secure_password123"
        
        # Test hashing
        hashed = AuthService.get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 20
        
        # Test verification with correct password
        assert AuthService.verify_password(password, hashed) is True
        
        # Test verification with incorrect password
        assert AuthService.verify_password("wrong_password", hashed) is False
        
        # Test that same password produces different hashes
        hashed2 = AuthService.get_password_hash(password)
        assert hashed != hashed2
        assert AuthService.verify_password(password, hashed2) is True
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {
            "sub": "user123",
            "tenant_id": "tenant456",
            "email": "test@example.com",
            "role": "user"
        }
        
        # Create token with default expiration
        token = AuthService.create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert decoded["sub"] == data["sub"]
        assert decoded["tenant_id"] == data["tenant_id"]
        assert decoded["email"] == data["email"]
        assert decoded["role"] == data["role"]
        assert "exp" in decoded
        
        # Create token with custom expiration
        custom_delta = timedelta(hours=1)
        token2 = AuthService.create_access_token(data, expires_delta=custom_delta)
        decoded2 = jwt.decode(token2, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # Verify custom expiration is approximately correct (within 5 seconds)
        expected_exp = datetime.now(timezone.utc) + custom_delta
        actual_exp = datetime.fromtimestamp(decoded2["exp"], tz=timezone.utc)
        assert abs((expected_exp - actual_exp).total_seconds()) < 5
    
    def test_decode_token(self):
        """Test token verification."""
        data = {
            "sub": "user123", 
            "tenant_id": "tenant456",
            "email": "test@example.com",
            "role": "user"
        }
        token = AuthService.create_access_token(data)
        
        # Test valid token
        payload = AuthService.decode_token(token)
        assert payload.sub == data["sub"]
        assert payload.tenant_id == data["tenant_id"]
        assert payload.email == data["email"]
        assert payload.role == data["role"]
        
        # Test invalid token
        with pytest.raises(HTTPException) as exc_info:
            AuthService.decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401
        
        # Test expired token
        expired_token = AuthService.create_access_token(
            data, 
            expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(HTTPException) as exc_info:
            AuthService.decode_token(expired_token)
        assert exc_info.value.status_code == 401
    
    async def test_create_refresh_token(self, db_session: AsyncSession, test_user: User):
        """Test refresh token creation."""
        # Create refresh token
        token = await AuthService.create_refresh_token(str(test_user.id), db_session)
        
        assert isinstance(token, str)
        assert len(token) > 20
        
        # Verify token was saved to database
        result = await db_session.execute(
            select(RefreshToken).filter(RefreshToken.token == token)
        )
        refresh_token = result.scalars().first()
        
        assert refresh_token is not None
        assert refresh_token.user_id == test_user.id
        assert refresh_token.expires_at > datetime.now(timezone.utc)
        
        # Verify expiration is approximately 7 days
        expected_exp = datetime.now(timezone.utc) + timedelta(days=7)
        actual_exp = refresh_token.expires_at
        assert abs((expected_exp - actual_exp).total_seconds()) < 60  # Within 1 minute
    
    def test_token_payload_structure(self):
        """Test that tokens contain all required fields."""
        data = {
            "sub": "user123",
            "tenant_id": "tenant456",
            "email": "test@example.com",
            "role": "admin",
            "extra_field": "should_be_included"
        }
        
        token = AuthService.create_access_token(data)
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # Check all fields are present
        assert decoded["sub"] == data["sub"]
        assert decoded["tenant_id"] == data["tenant_id"]
        assert decoded["email"] == data["email"]
        assert decoded["role"] == data["role"]
        assert decoded["extra_field"] == data["extra_field"]
        assert "exp" in decoded
    
    def test_token_tampering(self):
        """Test that tampered tokens are rejected."""
        data = {
            "sub": "user123", 
            "tenant_id": "tenant456", 
            "email": "test@example.com", 
            "role": "user"
        }
        token = AuthService.create_access_token(data)
        
        # Tamper with token
        parts = token.split('.')
        tampered_token = f"{parts[0]}.tampered.{parts[2]}"
        
        with pytest.raises(Exception) as exc_info:
            AuthService.decode_token(tampered_token)
        assert exc_info.value.status_code == 401
