"""
True unit tests for authentication API functions.
Tests isolated functions without database dependencies.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone

from app.auth.auth import AuthService


class TestAuthServiceUnit:
    """Unit tests for AuthService class methods."""

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = AuthService.get_password_hash(password)
        
        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = AuthService.get_password_hash(password)
        
        assert AuthService.verify_password(wrong_password, hashed) is False

    def test_get_password_hash_generates_hash(self):
        """Test that password hashing generates a hash."""
        password = "test_password_123"
        hashed = AuthService.get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 20  # BCrypt hashes are long
        assert hashed.startswith("$2b$")  # BCrypt prefix

    def test_get_password_hash_different_for_same_password(self):
        """Test that same password generates different hashes (salt)."""
        password = "test_password_123"
        hash1 = AuthService.get_password_hash(password)
        hash2 = AuthService.get_password_hash(password)
        
        assert hash1 != hash2
        # But both should verify correctly
        assert AuthService.verify_password(password, hash1)
        assert AuthService.verify_password(password, hash2)

    def test_create_access_token_default_expiry(self):
        """Test access token creation with default expiry."""
        data = {"sub": "test_user_id", "email": "test@example.com"}
        
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
            mock_settings.JWT_SECRET_KEY = "test_secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            token = AuthService.create_access_token(data)
            
            assert isinstance(token, str)
            assert len(token) > 50  # JWT tokens are long

    def test_create_access_token_custom_expiry(self):
        """Test access token creation with custom expiry."""
        data = {"sub": "test_user_id"}
        expires_delta = timedelta(minutes=30)
        
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test_secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            token = AuthService.create_access_token(data, expires_delta)
            
            assert isinstance(token, str)
            assert len(token) > 50

    @pytest.mark.asyncio
    async def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "test_user_id"
        mock_db = AsyncMock()
        
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
            
            token = await AuthService.create_refresh_token(user_id, mock_db)
            
            assert isinstance(token, str)
            assert len(token) > 20  # URL-safe tokens are reasonably long
            
            # Verify database operations were called
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_decode_token_valid(self):
        """Test token decoding with valid token."""
        data = {
            "sub": "test_user_id", 
            "email": "test@example.com",
            "tenant_id": "test_tenant_id",
            "role": "user"
        }
        
        with patch('app.auth.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test_secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
            
            # Create token first
            token = AuthService.create_access_token(data)
            
            # Then decode it
            decoded = AuthService.decode_token(token)
            
            assert decoded.sub == "test_user_id"

    def test_decode_token_invalid(self):
        """Test token decoding with invalid token."""
        invalid_token = "invalid.jwt.token"
        
        with patch('app.auth.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test_secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            with pytest.raises(HTTPException) as exc_info:
                AuthService.decode_token(invalid_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_decode_token_wrong_secret(self):
        """Test token decoding with wrong secret."""
        data = {
            "sub": "test_user_id",
            "email": "test@example.com", 
            "tenant_id": "test_tenant_id",
            "role": "user"
        }
        
        # Create token with one secret
        with patch('app.auth.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "secret1"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
            token = AuthService.create_access_token(data)
        
        # Try to decode with different secret
        with patch('app.auth.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "secret2"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            with pytest.raises(HTTPException) as exc_info:
                AuthService.decode_token(token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthDependencies:
    """Unit tests for auth dependency functions."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test get_current_user with valid token."""
        from app.auth.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid_token"
        
        # Mock database and user
        mock_db = AsyncMock()
        mock_user = Mock()
        mock_user.id = "test_user_id"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Mock token decoding
        mock_token_data = Mock()
        mock_token_data.sub = "test_user_id"
        
        with patch.object(AuthService, 'decode_token', return_value=mock_token_data):
            user = await get_current_user(mock_credentials, mock_db)
            
            assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self):
        """Test get_current_user when user not found in database."""
        from app.auth.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock credentials
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid_token"
        
        # Mock database with no user found
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Mock token decoding
        mock_token_data = Mock()
        mock_token_data.sub = "nonexistent_user_id"
        
        with patch.object(AuthService, 'decode_token', return_value=mock_token_data):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_active_user_active(self):
        """Test get_current_active_user with active user."""
        from app.auth.auth import get_current_active_user
        
        mock_user = Mock()
        mock_user.is_active = True
        
        result = await get_current_active_user(mock_user)
        
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self):
        """Test get_current_active_user with inactive user."""
        from app.auth.auth import get_current_active_user
        
        mock_user = Mock()
        mock_user.is_active = False
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(mock_user)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Inactive user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_tenant_from_request_header(self):
        """Test get_tenant_from_request with tenant header."""
        from app.auth.auth import get_tenant_from_request
        
        # Mock request with tenant header
        mock_request = Mock()
        mock_request.headers = {"X-Tenant-ID": "test_subdomain"}
        
        # Mock database
        mock_db = AsyncMock()
        mock_tenant = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        tenant = await get_tenant_from_request(mock_request, mock_db)
        
        assert tenant == mock_tenant

    @pytest.mark.asyncio
    async def test_get_tenant_from_request_host(self):
        """Test get_tenant_from_request with host header."""
        from app.auth.auth import get_tenant_from_request
        
        # Mock request with host header
        mock_request = Mock()
        mock_request.headers = {"host": "tenant.example.com"}
        
        # Mock database
        mock_db = AsyncMock()
        mock_tenant = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute.return_value = mock_result
        
        tenant = await get_tenant_from_request(mock_request, mock_db)
        
        assert tenant == mock_tenant

    @pytest.mark.asyncio
    async def test_get_tenant_from_request_not_found(self):
        """Test get_tenant_from_request when tenant not found."""
        from app.auth.auth import get_tenant_from_request
        
        # Mock request
        mock_request = Mock()
        mock_request.headers = {}
        
        # Mock database with no tenant found
        mock_db = AsyncMock()
        
        tenant = await get_tenant_from_request(mock_request, mock_db)
        
        assert tenant is None


class TestAuthRoleDependencies:
    """Unit tests for role-based auth dependencies."""

    @pytest.mark.asyncio
    async def test_require_role_correct_role(self):
        """Test require_role with correct role."""
        from app.auth.auth import require_role
        
        # Create role checker for 'admin'
        role_checker = require_role('admin')
        
        # Mock user with admin role
        mock_user = Mock()
        mock_user.role = 'admin'
        
        result = await role_checker(mock_user)
        
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_role_super_admin_always_allowed(self):
        """Test require_role allows super_admin for any role."""
        from app.auth.auth import require_role
        
        # Create role checker for 'admin'
        role_checker = require_role('admin')
        
        # Mock user with super_admin role
        mock_user = Mock()
        mock_user.role = 'super_admin'
        
        result = await role_checker(mock_user)
        
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_role_insufficient_permissions(self):
        """Test require_role with insufficient permissions."""
        from app.auth.auth import require_role
        
        # Create role checker for 'admin'
        role_checker = require_role('admin')
        
        # Mock user with user role
        mock_user = Mock()
        mock_user.role = 'user'
        
        with pytest.raises(HTTPException) as exc_info:
            await role_checker(mock_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_admin_user_admin(self):
        """Test require_admin_user with admin user."""
        from app.auth.auth import require_admin_user
        
        mock_user = Mock()
        mock_user.role = 'admin'
        
        result = await require_admin_user(mock_user)
        
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_admin_user_super_admin(self):
        """Test require_admin_user with super admin."""
        from app.auth.auth import require_admin_user
        
        mock_user = Mock()
        mock_user.role = 'super_admin'
        
        result = await require_admin_user(mock_user)
        
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_admin_user_regular_user(self):
        """Test require_admin_user with regular user."""
        from app.auth.auth import require_admin_user
        
        mock_user = Mock()
        mock_user.role = 'user'
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_user(mock_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_require_super_admin_user_super_admin(self):
        """Test require_super_admin_user with super admin."""
        from app.auth.auth import require_super_admin_user
        
        mock_user = Mock()
        mock_user.role = 'super_admin'
        
        result = await require_super_admin_user(mock_user)
        
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_super_admin_user_admin(self):
        """Test require_super_admin_user with regular admin."""
        from app.auth.auth import require_super_admin_user
        
        mock_user = Mock()
        mock_user.role = 'admin'
        
        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin_user(mock_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN