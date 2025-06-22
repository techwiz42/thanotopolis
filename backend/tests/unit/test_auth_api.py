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


class TestAuthAPIErrorHandling:
    """Test error handling scenarios in auth API functions."""
    
    @pytest.mark.asyncio
    async def test_create_tenant_duplicate_subdomain(self):
        """Test creating tenant with duplicate subdomain."""
        from app.api.auth import create_tenant
        from app.schemas.auth import TenantCreate
        from sqlalchemy.exc import IntegrityError
        
        # Mock database session
        mock_db = AsyncMock()
        mock_db.add = Mock()
        mock_db.commit.side_effect = IntegrityError("duplicate key", None, None)
        mock_db.rollback = AsyncMock()
        
        tenant_data = TenantCreate(
            subdomain="duplicate",
            organization_name="Test Org"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_tenant(tenant_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in str(exc_info.value.detail).lower()
        mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self):
        """Test registering user with duplicate email."""
        from app.api.auth import register_user
        from app.schemas.auth import UserCreate
        from sqlalchemy.exc import IntegrityError
        
        # Mock dependencies
        mock_db = AsyncMock()
        mock_tenant = Mock()
        mock_tenant.id = "tenant-id-123"
        mock_tenant.is_active = True
        
        # Mock database session
        mock_db.add = Mock()
        mock_db.commit.side_effect = IntegrityError("duplicate key", None, None)
        mock_db.rollback = AsyncMock()
        
        user_data = UserCreate(
            email="duplicate@example.com",
            username="testuser",
            password="password123",
            first_name="Test",
            last_name="User"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await register_user(user_data, mock_tenant, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in str(exc_info.value.detail).lower()
        mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_inactive_tenant(self):
        """Test registering user with inactive tenant."""
        from app.api.auth import register_user
        from app.schemas.auth import UserCreate
        
        # Mock inactive tenant
        mock_tenant = Mock()
        mock_tenant.is_active = False
        mock_db = AsyncMock()
        
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="password123",
            first_name="Test",
            last_name="User"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await register_user(user_data, mock_tenant, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "inactive" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        """Test login with nonexistent user."""
        from app.api.auth import login_user
        from app.schemas.auth import LoginRequest
        
        # Mock database to return no user
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        login_data = LoginRequest(
            email="nonexistent@example.com",
            password="password123"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid credentials" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_login_user_incorrect_password(self):
        """Test login with incorrect password."""
        from app.api.auth import login_user
        from app.schemas.auth import LoginRequest
        
        # Mock user with different password
        mock_user = Mock()
        mock_user.password_hash = AuthService.get_password_hash("correct_password")
        mock_user.is_active = True
        mock_user.tenant.is_active = True
        
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        login_data = LoginRequest(
            email="user@example.com",
            password="wrong_password"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid credentials" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_login_user_inactive(self):
        """Test login with inactive user."""
        from app.api.auth import login_user
        from app.schemas.auth import LoginRequest
        
        # Mock inactive user
        mock_user = Mock()
        mock_user.password_hash = AuthService.get_password_hash("password123")
        mock_user.is_active = False
        mock_user.tenant.is_active = True
        
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        login_data = LoginRequest(
            email="inactive@example.com",
            password="password123"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "inactive" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_login_user_inactive_tenant(self):
        """Test login with inactive tenant."""
        from app.api.auth import login_user
        from app.schemas.auth import LoginRequest
        
        # Mock user with inactive tenant
        mock_user = Mock()
        mock_user.password_hash = AuthService.get_password_hash("password123")
        mock_user.is_active = True
        mock_user.tenant.is_active = False
        
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        login_data = LoginRequest(
            email="user@example.com",
            password="password123"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "organization" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self):
        """Test refresh with invalid refresh token."""
        from app.api.auth import refresh_access_token
        from app.schemas.auth import RefreshTokenRequest
        
        # Mock database to return no token
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        refresh_data = RefreshTokenRequest(refresh_token="invalid_token")
        
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(refresh_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_expired(self):
        """Test refresh with expired token."""
        from app.api.auth import refresh_access_token
        from app.schemas.auth import RefreshTokenRequest
        
        # Mock expired refresh token
        mock_token = Mock()
        mock_token.expires_at = datetime.now(timezone.utc) - timedelta(days=1)  # Expired
        mock_token.user.is_active = True
        mock_token.user.tenant.is_active = True
        
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_token
        
        refresh_data = RefreshTokenRequest(refresh_token="expired_token")
        
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(refresh_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_inactive_user(self):
        """Test refresh with inactive user."""
        from app.api.auth import refresh_access_token
        from app.schemas.auth import RefreshTokenRequest
        
        # Mock token with inactive user
        mock_token = Mock()
        mock_token.expires_at = datetime.now(timezone.utc) + timedelta(days=7)  # Valid
        mock_token.user.is_active = False  # Inactive user
        mock_token.user.tenant.is_active = True
        
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_token
        
        refresh_data = RefreshTokenRequest(refresh_token="valid_token")
        
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(refresh_data, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "inactive" in str(exc_info.value.detail).lower()


class TestAuthAPISecurityChecks:
    """Test security-critical functionality in auth API."""
    
    @pytest.mark.asyncio
    async def test_require_admin_permission(self):
        """Test admin permission requirement."""
        from app.api.auth import require_admin
        from app.models.models import User
        
        # Test with admin user
        admin_user = Mock(spec=User)
        admin_user.role = "admin"
        
        # Should not raise exception
        result = await require_admin(admin_user)
        assert result == admin_user
        
        # Test with super admin user
        super_admin_user = Mock(spec=User)
        super_admin_user.role = "super_admin"
        
        result = await require_admin(super_admin_user)
        assert result == super_admin_user
        
        # Test with regular user
        regular_user = Mock(spec=User)
        regular_user.role = "user"
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(regular_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_require_super_admin_permission(self):
        """Test super admin permission requirement."""
        from app.api.auth import require_super_admin
        from app.models.models import User
        
        # Test with super admin user
        super_admin_user = Mock(spec=User)
        super_admin_user.role = "super_admin"
        
        result = await require_super_admin(super_admin_user)
        assert result == super_admin_user
        
        # Test with regular admin
        admin_user = Mock(spec=User)
        admin_user.role = "admin"
        
        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin(admin_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "super admin" in str(exc_info.value.detail).lower()
        
        # Test with regular user
        regular_user = Mock(spec=User)
        regular_user.role = "user"
        
        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin(regular_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_update_user_role_permission_matrix(self):
        """Test role update permission matrix."""
        from app.api.auth import update_user_role
        from app.schemas.auth import UserRoleUpdate
        from uuid import uuid4
        
        # Mock database and users
        mock_db = AsyncMock()
        target_user = Mock()
        target_user.id = uuid4()
        target_user.role = "user"
        target_user.tenant_id = uuid4()
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = target_user
        mock_db.commit = AsyncMock()
        
        # Test cases: (current_user_role, target_role, should_succeed)
        test_cases = [
            ("admin", "admin", True),           # Admin can promote to admin
            ("admin", "super_admin", False),    # Admin cannot promote to super_admin
            ("super_admin", "super_admin", True), # Super admin can promote to super_admin
            ("user", "admin", False),           # User cannot promote anyone
        ]
        
        for current_role, target_role, should_succeed in test_cases:
            # Reset mock
            mock_db.commit.reset_mock()
            
            # Create current user
            current_user = Mock()
            current_user.role = current_role
            current_user.tenant_id = target_user.tenant_id  # Same tenant
            
            role_update = UserRoleUpdate(role=target_role)
            
            if should_succeed:
                # Should not raise exception
                result = await update_user_role(target_user.id, role_update, current_user, mock_db)
                assert result.role == target_role
                mock_db.commit.assert_called_once()
            else:
                # Should raise 403 exception
                with pytest.raises(HTTPException) as exc_info:
                    await update_user_role(target_user.id, role_update, current_user, mock_db)
                
                assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
                mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cross_tenant_access_prevention(self):
        """Test that users cannot access other tenants' data."""
        from app.api.auth import get_user_by_id, update_user_role
        from app.schemas.auth import UserRoleUpdate
        from uuid import uuid4
        
        # Create users from different tenants
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        
        current_user = Mock()
        current_user.role = "admin"
        current_user.tenant_id = tenant1_id
        
        target_user = Mock()
        target_user.id = uuid4()
        target_user.tenant_id = tenant2_id  # Different tenant
        
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = target_user
        
        # Test get_user_by_id cross-tenant access
        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_id(target_user.id, current_user, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        
        # Test update_user_role cross-tenant access
        role_update = UserRoleUpdate(role="admin")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_user_role(target_user.id, role_update, current_user, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_self_deletion_prevention(self):
        """Test that users cannot delete themselves."""
        from app.api.auth import delete_user
        from uuid import uuid4
        
        # Create user
        user_id = uuid4()
        current_user = Mock()
        current_user.id = user_id
        current_user.role = "admin"
        current_user.tenant_id = uuid4()
        
        mock_db = AsyncMock()
        
        # Test self-deletion
        with pytest.raises(HTTPException) as exc_info:
            await delete_user(user_id, current_user, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "yourself" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_token_cleanup_on_logout_all(self):
        """Test that logout_all properly cleans up all user tokens."""
        from app.api.auth import logout_all
        from uuid import uuid4
        
        # Mock current user
        current_user = Mock()
        current_user.id = uuid4()
        
        # Mock database
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.rowcount = 3  # 3 tokens deleted
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        result = await logout_all(current_user, mock_db)
        
        # Verify database operations
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Verify response
        assert "logout successful" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_organization_access_code_validation(self):
        """Test organization access code validation."""
        from app.api.auth import get_organization_by_access_code
        
        # Mock database
        mock_db = AsyncMock()
        
        # Test with invalid access code
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_organization_by_access_code("invalid_code", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "access code" in str(exc_info.value.detail).lower()
        
        # Test with valid access code
        mock_tenant = Mock()
        mock_tenant.subdomain = "valid-org"
        mock_tenant.organization_name = "Valid Organization"
        mock_tenant.is_active = True
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_tenant
        
        result = await get_organization_by_access_code("valid_code", mock_db)
        
        assert result.subdomain == "valid-org"
        assert result.organization_name == "Valid Organization"


class TestAuthAPIEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_get_users_empty_tenant(self):
        """Test getting users when tenant has no users."""
        from app.api.auth import get_users
        
        # Mock admin user
        current_user = Mock()
        current_user.role = "admin"
        current_user.tenant_id = "empty-tenant-id"
        
        # Mock empty result
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        result = await get_users(current_user, mock_db)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_tenant_by_subdomain_not_found(self):
        """Test getting tenant by nonexistent subdomain."""
        from app.api.auth import get_tenant_by_subdomain
        
        # Mock database to return None
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_by_subdomain("nonexistent", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "tenant" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_register_with_token_success(self):
        """Test successful registration with immediate token generation."""
        from app.api.auth import register_and_return_tokens
        from app.schemas.auth import UserCreate
        
        # Mock tenant
        mock_tenant = Mock()
        mock_tenant.id = "tenant-id-123"
        mock_tenant.is_active = True
        
        # Mock database
        mock_db = AsyncMock()
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock created user
        mock_user = Mock()
        mock_user.id = "user-id-123"
        mock_user.email = "test@example.com"
        mock_user.tenant_id = "tenant-id-123"
        mock_user.role = "user"
        
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="password123",
            first_name="Test",
            last_name="User"
        )
        
        # Mock token creation
        with patch('app.api.auth.AuthService.create_access_token') as mock_access_token, \
             patch('app.api.auth.AuthService.create_refresh_token') as mock_refresh_token:
            
            mock_access_token.return_value = "access_token_123"
            mock_refresh_token.return_value = "refresh_token_123"
            
            # Mock user creation side effect
            def create_user_effect(user):
                user.id = mock_user.id
                return user
            
            mock_db.refresh.side_effect = create_user_effect
            
            result = await register_and_return_tokens(user_data, mock_tenant, mock_db)
            
            # Verify token generation
            assert result.access_token == "access_token_123"
            assert result.refresh_token == "refresh_token_123"
            assert result.token_type == "bearer"
    
    @pytest.mark.asyncio
    async def test_me_endpoint_with_detailed_user_info(self):
        """Test the /me endpoint returns complete user information."""
        from app.api.auth import get_current_user_info
        
        # Mock current user with all fields
        current_user = Mock()
        current_user.id = "user-id-123"
        current_user.email = "test@example.com"
        current_user.username = "testuser"
        current_user.first_name = "Test"
        current_user.last_name = "User"
        current_user.role = "admin"
        current_user.is_active = True
        current_user.tenant_id = "tenant-id-123"
        current_user.created_at = datetime.now(timezone.utc)
        current_user.updated_at = datetime.now(timezone.utc)
        
        result = await get_current_user_info(current_user)
        
        # Verify all user information is returned
        assert result.id == current_user.id
        assert result.email == current_user.email
        assert result.username == current_user.username
        assert result.first_name == current_user.first_name
        assert result.last_name == current_user.last_name
        assert result.role == current_user.role
        assert result.is_active == current_user.is_active

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