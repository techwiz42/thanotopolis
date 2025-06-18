"""
Tests for the authentication service.
Tests password verification, JWT creation/validation, and token operations.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from unittest.mock import Mock, AsyncMock

from app.auth.auth import AuthService
from app.schemas.schemas import TokenPayload
from app.models.models import User, RefreshToken, Tenant
from app.core.config import settings


class TestAuthService:
    """Test authentication service functionality."""

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePass123!"
        hashed = AuthService.get_password_hash(password)
        
        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePass123!"
        wrong_password = "WrongPassword!"
        hashed = AuthService.get_password_hash(password)
        
        assert AuthService.verify_password(wrong_password, hashed) is False

    def test_get_password_hash_generates_different_hashes(self):
        """Test that password hashing generates different hashes for same password."""
        password = "SecurePass123!"
        hash1 = AuthService.get_password_hash(password)
        hash2 = AuthService.get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify the original password
        assert AuthService.verify_password(password, hash1) is True
        assert AuthService.verify_password(password, hash2) is True

    def test_password_hash_length_and_format(self):
        """Test that password hashes have expected format."""
        password = "TestPassword123!"
        hashed = AuthService.get_password_hash(password)
        
        # bcrypt hashes start with $2b$ and are typically 60 characters
        assert hashed.startswith("$2b$")
        assert len(hashed) >= 50  # bcrypt hashes are substantial

    def test_create_access_token_with_default_expiry(self):
        """Test creating access token with default expiry."""
        user_data = {"sub": "user123", "email": "test@example.com"}
        token = AuthService.create_access_token(user_data)
        
        assert isinstance(token, str)
        # Decode to verify content
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_create_access_token_with_custom_expiry(self):
        """Test creating access token with custom expiry."""
        user_data = {"sub": "user123"}
        custom_expiry = timedelta(hours=1)
        token = AuthService.create_access_token(user_data, custom_expiry)
        
        assert isinstance(token, str)
        # Decode to verify expiry
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        exp_timestamp = payload["exp"]
        
        # Should expire in about 1 hour (allowing some tolerance)
        exp_time = datetime.fromtimestamp(exp_timestamp)
        expected_time = datetime.utcnow() + custom_expiry
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 10  # Within 10 seconds tolerance

    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        user_data = {
            "sub": "user123", 
            "email": "test@example.com", 
            "tenant_id": "tenant456",
            "role": "user"
        }
        token = AuthService.create_access_token(user_data)
        
        decoded = AuthService.decode_token(token)
        
        assert isinstance(decoded, TokenPayload)
        assert decoded.sub == "user123"
        assert decoded.email == "test@example.com"
        assert decoded.tenant_id == "tenant456"
        assert decoded.role == "user"

    def test_decode_token_invalid_raises_exception(self):
        """Test that decoding invalid token raises HTTPException."""
        invalid_token = "invalid.jwt.token"
        
        with pytest.raises(Exception):  # Should raise HTTPException
            AuthService.decode_token(invalid_token)

    def test_decode_token_expired_raises_exception(self):
        """Test that decoding expired token raises HTTPException."""
        # Create token that expires immediately
        user_data = {"sub": "user123"}
        expired_expiry = timedelta(seconds=-1)  # Negative = already expired
        expired_token = AuthService.create_access_token(user_data, expired_expiry)
        
        with pytest.raises(Exception):  # Should raise HTTPException
            AuthService.decode_token(expired_token)

    @pytest.mark.asyncio
    async def test_create_refresh_token(self):
        """Test creating refresh token."""
        mock_db = AsyncMock()
        user_id = "user123"
        
        # Mock the database operations
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        
        token = await AuthService.create_refresh_token(user_id, mock_db)
        
        assert isinstance(token, str)
        assert len(token) > 20  # Should be a substantial random string
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()