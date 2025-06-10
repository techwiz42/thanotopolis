"""
Tests for the authentication service.
Tests actual authentication flows including password verification, JWT creation/validation,
and token refresh functionality.

NOTE: These tests are for a planned AuthService class that was never implemented.
The actual AuthService in app.auth.auth only has static methods for basic JWT operations.
All tests in this file are skipped until the full AuthService is implemented.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.auth import AuthService
from app.schemas.schemas import UserCreate, UserLogin
from app.models import User, RefreshToken, Tenant
from app.core.config import settings


@pytest.mark.skip(reason="AuthService with instance methods not implemented - only static methods exist")
class TestAuthService:
    """Test authentication service functionality."""

    async def test_create_user_with_valid_data(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test creating a new user with valid registration data."""
        auth_service = AuthService(db_session)
        
        user_data = UserCreate(
            email="test@example.com",
            password="SecurePass123!",
            name="Test User",
            tenant_id=sample_tenant.id
        )
        
        user = await auth_service.create_user(user_data)
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.tenant_id == sample_tenant.id
        assert user.role == "user"  # Default role
        assert user.is_active is True
        # Password should be hashed, not plaintext
        assert user.hashed_password != "SecurePass123!"
        assert len(user.hashed_password) > 50  # bcrypt hashes are long

    async def test_create_user_with_duplicate_email_fails(self, db_session: AsyncSession, sample_user: User):
        """Test that creating a user with duplicate email fails."""
        auth_service = AuthService(db_session)
        
        user_data = UserCreate(
            email=sample_user.email,  # Duplicate email
            password="AnotherPass123!",
            name="Another User",
            tenant_id=sample_user.tenant_id
        )
        
        with pytest.raises(ValueError, match="User with this email already exists"):
            await auth_service.create_user(user_data)

    async def test_authenticate_user_with_correct_credentials(self, db_session: AsyncSession, sample_user: User):
        """Test authenticating a user with correct email and password."""
        auth_service = AuthService(db_session)
        
        # Use the known password from the fixture
        login_data = UserLogin(
            email=sample_user.email,
            password="testpassword123"
        )
        
        authenticated_user = await auth_service.authenticate_user(login_data)
        
        assert authenticated_user is not None
        assert authenticated_user.id == sample_user.id
        assert authenticated_user.email == sample_user.email

    async def test_authenticate_user_with_wrong_password(self, db_session: AsyncSession, sample_user: User):
        """Test that authentication fails with wrong password."""
        auth_service = AuthService(db_session)
        
        login_data = UserLogin(
            email=sample_user.email,
            password="wrongpassword"
        )
        
        authenticated_user = await auth_service.authenticate_user(login_data)
        
        assert authenticated_user is None

    async def test_authenticate_user_with_nonexistent_email(self, db_session: AsyncSession):
        """Test that authentication fails with non-existent email."""
        auth_service = AuthService(db_session)
        
        login_data = UserLogin(
            email="nonexistent@example.com",
            password="anypassword"
        )
        
        authenticated_user = await auth_service.authenticate_user(login_data)
        
        assert authenticated_user is None

    async def test_authenticate_inactive_user_fails(self, db_session: AsyncSession, inactive_user: User):
        """Test that authentication fails for inactive users."""
        auth_service = AuthService(db_session)
        
        login_data = UserLogin(
            email=inactive_user.email,
            password="testpassword123"
        )
        
        authenticated_user = await auth_service.authenticate_user(login_data)
        
        assert authenticated_user is None

    async def test_create_access_token(self, db_session: AsyncSession, sample_user: User):
        """Test creating a valid JWT access token."""
        auth_service = AuthService(db_session)
        
        access_token = auth_service.create_access_token(sample_user)
        
        assert access_token is not None
        assert isinstance(access_token, str)
        
        # Decode and verify token content
        payload = jwt.decode(
            access_token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        assert payload["sub"] == str(sample_user.id)
        assert payload["tenant_id"] == str(sample_user.tenant_id)
        assert payload["email"] == sample_user.email
        assert payload["role"] == sample_user.role
        
        # Token should expire in 15 minutes
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        time_diff = exp_time - now
        assert 14 * 60 < time_diff.total_seconds() < 15 * 60

    async def test_create_refresh_token(self, db_session: AsyncSession, sample_user: User):
        """Test creating and storing a refresh token."""
        auth_service = AuthService(db_session)
        
        refresh_token = await auth_service.create_refresh_token(sample_user)
        
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 20  # Should be a substantial token
        
        # Verify token is stored in database
        stored_token = await auth_service.get_refresh_token(refresh_token)
        assert stored_token is not None
        assert stored_token.user_id == sample_user.id
        assert stored_token.is_active is True

    async def test_refresh_access_token_with_valid_token(self, db_session: AsyncSession, sample_user: User):
        """Test refreshing access token with valid refresh token."""
        auth_service = AuthService(db_session)
        
        # Create refresh token
        refresh_token = await auth_service.create_refresh_token(sample_user)
        
        # Use it to create new access token
        new_access_token = await auth_service.refresh_access_token(refresh_token)
        
        assert new_access_token is not None
        
        # Verify new token content
        payload = jwt.decode(
            new_access_token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == str(sample_user.id)

    async def test_refresh_access_token_with_invalid_token(self, db_session: AsyncSession):
        """Test that refresh fails with invalid token."""
        auth_service = AuthService(db_session)
        
        new_access_token = await auth_service.refresh_access_token("invalid_token")
        
        assert new_access_token is None

    async def test_refresh_access_token_with_inactive_token(self, db_session: AsyncSession, sample_user: User):
        """Test that refresh fails with inactive token."""
        auth_service = AuthService(db_session)
        
        # Create and then deactivate refresh token
        refresh_token = await auth_service.create_refresh_token(sample_user)
        await auth_service.revoke_refresh_token(refresh_token)
        
        new_access_token = await auth_service.refresh_access_token(refresh_token)
        
        assert new_access_token is None

    async def test_verify_access_token_with_valid_token(self, db_session: AsyncSession, sample_user: User):
        """Test verifying a valid access token."""
        auth_service = AuthService(db_session)
        
        access_token = auth_service.create_access_token(sample_user)
        payload = auth_service.verify_access_token(access_token)
        
        assert payload is not None
        assert payload["sub"] == str(sample_user.id)
        assert payload["email"] == sample_user.email

    async def test_verify_access_token_with_invalid_token(self, db_session: AsyncSession):
        """Test that verification fails with invalid token."""
        auth_service = AuthService(db_session)
        
        payload = auth_service.verify_access_token("invalid_token")
        
        assert payload is None

    async def test_verify_access_token_with_expired_token(self, db_session: AsyncSession, sample_user: User):
        """Test that verification fails with expired token."""
        auth_service = AuthService(db_session)
        
        # Create token with negative expiration (already expired)
        expired_payload = {
            "sub": str(sample_user.id),
            "tenant_id": str(sample_user.tenant_id),
            "email": sample_user.email,
            "role": sample_user.role,
            "exp": datetime.utcnow() - timedelta(minutes=1)  # Expired 1 minute ago
        }
        
        expired_token = jwt.encode(
            expired_payload, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        payload = auth_service.verify_access_token(expired_token)
        
        assert payload is None

    async def test_revoke_refresh_token(self, db_session: AsyncSession, sample_user: User):
        """Test revoking a refresh token."""
        auth_service = AuthService(db_session)
        
        refresh_token = await auth_service.create_refresh_token(sample_user)
        
        # Verify token exists and is active
        stored_token = await auth_service.get_refresh_token(refresh_token)
        assert stored_token.is_active is True
        
        # Revoke token
        success = await auth_service.revoke_refresh_token(refresh_token)
        assert success is True
        
        # Verify token is now inactive
        stored_token = await auth_service.get_refresh_token(refresh_token)
        assert stored_token.is_active is False

    async def test_revoke_all_user_tokens(self, db_session: AsyncSession, sample_user: User):
        """Test revoking all refresh tokens for a user."""
        auth_service = AuthService(db_session)
        
        # Create multiple refresh tokens
        token1 = await auth_service.create_refresh_token(sample_user)
        token2 = await auth_service.create_refresh_token(sample_user)
        
        # Verify both are active
        assert (await auth_service.get_refresh_token(token1)).is_active is True
        assert (await auth_service.get_refresh_token(token2)).is_active is True
        
        # Revoke all tokens for user
        count = await auth_service.revoke_all_user_tokens(sample_user.id)
        assert count == 2
        
        # Verify both are now inactive
        assert (await auth_service.get_refresh_token(token1)).is_active is False
        assert (await auth_service.get_refresh_token(token2)).is_active is False

    async def test_password_hashing_security(self, db_session: AsyncSession, sample_tenant: Tenant):
        """Test that passwords are properly hashed and salted."""
        auth_service = AuthService(db_session)
        
        password = "TestPassword123!"
        
        # Create two users with same password
        user1_data = UserCreate(
            email="user1@example.com",
            password=password,
            name="User 1",
            tenant_id=sample_tenant.id
        )
        
        user2_data = UserCreate(
            email="user2@example.com", 
            password=password,
            name="User 2",
            tenant_id=sample_tenant.id
        )
        
        user1 = await auth_service.create_user(user1_data)
        user2 = await auth_service.create_user(user2_data)
        
        # Hashed passwords should be different (due to salt)
        assert user1.hashed_password != user2.hashed_password
        assert user1.hashed_password != password
        assert user2.hashed_password != password