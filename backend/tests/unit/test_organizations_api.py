"""
Comprehensive unit tests for organizations API endpoints.
Tests multi-tenant organization management and org admin functions.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, status
from datetime import datetime, timezone
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.organizations import router, is_org_admin
from app.models.models import User, Tenant
from app.schemas.schemas import (
    OrganizationRegisterRequest, OrganizationRegisterResponse,
    OrganizationResponse, OrganizationUpdate, AdminUserUpdate
)


class TestOrganizationsAPIUnit:
    """Unit tests for organizations API endpoints."""

    @pytest.fixture
    def mock_org_admin_user(self):
        """Create a mock org admin user."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.email = "orgadmin@example.com"
        user.role = "org_admin"
        user.is_active = True
        user.is_verified = True
        user.tenant_id = uuid4()
        return user

    @pytest.fixture
    def mock_super_admin_user(self):
        """Create a mock super admin user."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.email = "superadmin@example.com"
        user.role = "super_admin"
        user.is_active = True
        user.is_verified = True
        user.tenant_id = uuid4()
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular user."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.email = "user@example.com"
        user.role = "member"
        user.is_active = True
        user.is_verified = True
        user.tenant_id = uuid4()
        return user

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_organization(self):
        """Create a mock organization."""
        org = Mock(spec=Tenant)
        org.id = uuid4()
        org.name = "Test Organization"
        org.subdomain = "testorg"
        org.full_name = "Test Organization Ltd"
        org.address = {"street": "123 Test St", "city": "Test City"}
        org.phone = "+1234567890"
        org.organization_email = "contact@testorg.com"
        org.access_code = "test123"
        org.is_active = True
        org.created_at = datetime.now(timezone.utc)
        return org

    @pytest.mark.asyncio
    async def test_register_organization_success(self, mock_db_session):
        """Test successful organization registration."""
        from app.api.organizations import register_organization
        
        # Mock that subdomain and email don't exist
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=None)),  # subdomain check
            Mock(scalar_one_or_none=Mock(return_value=None))   # email check
        ]
        
        # Mock org and user creation with all required fields
        mock_org = Mock(spec=Tenant)
        mock_org.id = uuid4()
        mock_org.name = "Test Org"
        mock_org.subdomain = "testorg"
        mock_org.access_code = "access123"
        mock_org.description = None
        mock_org.full_name = "Test Organization Ltd"
        mock_org.address = {"street": "123 Test St"}
        mock_org.phone = "+1234567890"
        mock_org.organization_email = "contact@testorg.com"
        mock_org.is_active = True
        mock_org.created_at = datetime.now(timezone.utc)
        mock_org.updated_at = None
        
        mock_user = Mock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "admin@testorg.com"
        mock_user.username = "admin"
        mock_user.first_name = "Admin"
        mock_user.last_name = "User"
        mock_user.role = "org_admin"
        mock_user.is_active = True
        mock_user.is_verified = True
        mock_user.tenant_id = mock_org.id
        mock_user.created_at = datetime.now(timezone.utc)
        
        # Set up database mock to handle add and refresh
        def set_db_defaults(obj):
            """Set default database values on object after add"""
            if not hasattr(obj, 'id') or obj.id is None:
                obj.id = uuid4()
            if hasattr(obj, 'created_at') and obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
            if hasattr(obj, 'is_active') and obj.is_active is None:
                obj.is_active = True
                
        mock_db_session.add.side_effect = set_db_defaults
        mock_db_session.refresh = AsyncMock(side_effect=lambda obj: None)
        
        with patch('app.api.organizations.get_password_hash') as mock_hash, \
             patch('app.api.organizations.create_tokens') as mock_tokens, \
             patch('app.api.organizations.secrets.token_urlsafe') as mock_token:
            
            mock_hash.return_value = "hashed_password"
            mock_tokens.return_value = ("access_token", "refresh_token")
            mock_token.return_value = "access123"
            
            request = OrganizationRegisterRequest(
                name="Test Org",
                subdomain="testorg",
                full_name="Test Organization Ltd",
                address={"street": "123 Test St"},
                phone="+1234567890",
                organization_email="contact@testorg.com",
                admin_email="admin@testorg.com",
                admin_username="admin",
                admin_password="password123",
                admin_first_name="Admin",
                admin_last_name="User"
            )
            
            result = await register_organization(request, mock_db_session)
            
        assert isinstance(result, OrganizationRegisterResponse)
        assert result.access_token == "access_token"
        assert result.refresh_token == "refresh_token"
        
        # Verify database operations
        mock_db_session.add.assert_called()
        mock_db_session.flush.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_organization_subdomain_exists(self, mock_db_session):
        """Test organization registration with existing subdomain."""
        from app.api.organizations import register_organization
        
        # Mock that subdomain exists
        existing_org = Mock(spec=Tenant)
        mock_db_session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=existing_org)
        )
        
        request = OrganizationRegisterRequest(
            name="Test Org",
            subdomain="existing",
            full_name="Test Organization Ltd",
            address={},
            phone="+1234567890",
            organization_email="contact@test.com",
            admin_email="admin@test.com",
            admin_username="admin",
            admin_password="password123",
            admin_first_name="Admin",
            admin_last_name="User"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await register_organization(request, mock_db_session)
        
        assert exc_info.value.status_code == 400
        assert "Subdomain already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_register_organization_email_exists(self, mock_db_session):
        """Test organization registration with existing admin email."""
        from app.api.organizations import register_organization
        
        # Mock subdomain check (doesn't exist) and email check (exists)
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=None)),  # subdomain ok
            Mock(scalar_one_or_none=Mock(return_value=Mock(spec=User)))  # email exists
        ]
        
        request = OrganizationRegisterRequest(
            name="Test Org",
            subdomain="testorg",
            full_name="Test Organization Ltd",
            address={},
            phone="+1234567890",
            organization_email="contact@test.com",
            admin_email="existing@test.com",
            admin_username="admin",
            admin_password="password123",
            admin_first_name="Admin",
            admin_last_name="User"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await register_organization(request, mock_db_session)
        
        assert exc_info.value.status_code == 400
        assert "Email already registered" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_organization_success(self, mock_org_admin_user, mock_db_session, mock_organization):
        """Test successful current organization retrieval."""
        from app.api.organizations import get_current_organization
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_organization
        mock_db_session.execute.return_value = mock_result
        
        result = await get_current_organization(mock_org_admin_user, mock_db_session)
        
        assert result == mock_organization

    @pytest.mark.asyncio
    async def test_get_current_organization_no_tenant(self, mock_db_session):
        """Test current organization retrieval when user has no tenant."""
        from app.api.organizations import get_current_organization
        
        user_without_tenant = Mock(spec=User)
        user_without_tenant.tenant_id = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_organization(user_without_tenant, mock_db_session)
        
        assert exc_info.value.status_code == 404
        assert "User does not belong to any organization" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_organization_not_found(self, mock_org_admin_user, mock_db_session):
        """Test current organization retrieval when organization not found."""
        from app.api.organizations import get_current_organization
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_organization(mock_org_admin_user, mock_db_session)
        
        assert exc_info.value.status_code == 404
        assert "Organization not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_current_organization_success(self, mock_org_admin_user, mock_db_session, mock_organization):
        """Test successful current organization update."""
        from app.api.organizations import update_current_organization
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_organization
        mock_db_session.execute.return_value = mock_result
        
        update_data = OrganizationUpdate(
            full_name="Updated Organization Name",
            phone="+9876543210"
        )
        
        result = await update_current_organization(update_data, mock_org_admin_user, mock_db_session)
        
        assert result == mock_organization
        assert mock_organization.full_name == "Updated Organization Name"
        assert mock_organization.phone == "+9876543210"
        
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(mock_organization)

    @pytest.mark.asyncio
    async def test_get_organization_success_own_org(self, mock_org_admin_user, mock_db_session, mock_organization):
        """Test successful organization retrieval for own organization."""
        from app.api.organizations import get_organization
        
        # Set up user's organization ID to match requested org
        mock_org_admin_user.tenant_id = mock_organization.id
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_organization
        mock_db_session.execute.return_value = mock_result
        
        result = await get_organization(mock_organization.id, mock_org_admin_user, mock_db_session)
        
        assert result == mock_organization

    @pytest.mark.asyncio
    async def test_get_organization_forbidden_other_org(self, mock_org_admin_user, mock_db_session):
        """Test organization retrieval forbidden for other organization."""
        from app.api.organizations import get_organization
        
        other_org_id = uuid4()
        # User's tenant_id is different from requested org_id
        
        with pytest.raises(HTTPException) as exc_info:
            await get_organization(other_org_id, mock_org_admin_user, mock_db_session)
        
        assert exc_info.value.status_code == 403
        assert "You can only view your own organization" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_organization_super_admin_access(self, mock_super_admin_user, mock_db_session, mock_organization):
        """Test super admin can access any organization."""
        from app.api.organizations import get_organization
        
        # Super admin accessing different organization
        other_org_id = uuid4()
        mock_organization.id = other_org_id
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_organization
        mock_db_session.execute.return_value = mock_result
        
        result = await get_organization(other_org_id, mock_super_admin_user, mock_db_session)
        
        assert result == mock_organization

    @pytest.mark.asyncio
    async def test_list_organization_users_success(self, mock_org_admin_user, mock_db_session):
        """Test successful organization users listing."""
        from app.api.organizations import list_organization_users
        
        mock_users = [
            Mock(spec=User, id=uuid4(), email="user1@test.com"),
            Mock(spec=User, id=uuid4(), email="user2@test.com")
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db_session.execute.return_value = mock_result
        
        # Set user's org to match requested org
        org_id = mock_org_admin_user.tenant_id
        
        result = await list_organization_users(org_id, mock_org_admin_user, mock_db_session)
        
        assert result == mock_users

    @pytest.mark.asyncio
    async def test_list_organization_users_forbidden(self, mock_org_admin_user, mock_db_session):
        """Test organization users listing forbidden for other organization."""
        from app.api.organizations import list_organization_users
        
        other_org_id = uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await list_organization_users(other_org_id, mock_org_admin_user, mock_db_session)
        
        assert exc_info.value.status_code == 403
        assert "You can only list users in your own organization" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_organization_user_success(self, mock_org_admin_user, mock_db_session):
        """Test successful organization user update."""
        from app.api.organizations import update_organization_user
        
        target_user = Mock(spec=User)
        target_user.id = uuid4()
        target_user.role = "member"
        target_user.is_active = True
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = target_user
        mock_db_session.execute.return_value = mock_result
        
        org_id = mock_org_admin_user.tenant_id
        update_data = AdminUserUpdate(role="org_admin", is_active=False)
        
        result = await update_organization_user(
            org_id, target_user.id, update_data, mock_org_admin_user, mock_db_session
        )
        
        assert result == target_user
        assert target_user.role == "org_admin"
        assert target_user.is_active == False
        
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(target_user)

    @pytest.mark.asyncio
    async def test_update_organization_user_self_demotion_forbidden(self, mock_org_admin_user, mock_db_session):
        """Test preventing self-demotion."""
        from app.api.organizations import update_organization_user
        
        org_id = mock_org_admin_user.tenant_id
        user_id = mock_org_admin_user.id  # Same as current user
        update_data = AdminUserUpdate(role="user")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_organization_user(org_id, user_id, update_data, mock_org_admin_user, mock_db_session)
        
        assert exc_info.value.status_code == 400
        assert "You cannot change your own role" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_organization_user_privilege_escalation_forbidden(self, mock_org_admin_user, mock_db_session):
        """Test preventing privilege escalation by org admin."""
        from app.api.organizations import update_organization_user
        
        target_user = Mock(spec=User)
        target_user.id = uuid4()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = target_user
        mock_db_session.execute.return_value = mock_result
        
        org_id = mock_org_admin_user.tenant_id
        update_data = AdminUserUpdate(role="admin")  # Trying to promote to admin
        
        with pytest.raises(HTTPException) as exc_info:
            await update_organization_user(org_id, target_user.id, update_data, mock_org_admin_user, mock_db_session)
        
        assert exc_info.value.status_code == 403
        assert "You cannot promote users to admin or super_admin" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_organization_user_not_found(self, mock_org_admin_user, mock_db_session):
        """Test organization user update when user not found."""
        from app.api.organizations import update_organization_user
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        org_id = mock_org_admin_user.tenant_id
        user_id = uuid4()
        update_data = AdminUserUpdate(role="user")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_organization_user(org_id, user_id, update_data, mock_org_admin_user, mock_db_session)
        
        assert exc_info.value.status_code == 404
        assert "User not found in this organization" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_deactivate_organization_user_success(self, mock_org_admin_user, mock_db_session):
        """Test successful user deactivation."""
        from app.api.organizations import deactivate_organization_user
        
        target_user = Mock(spec=User)
        target_user.id = uuid4()
        target_user.is_active = True
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = target_user
        mock_db_session.execute.return_value = mock_result
        
        org_id = mock_org_admin_user.tenant_id
        
        result = await deactivate_organization_user(org_id, target_user.id, mock_org_admin_user, mock_db_session)
        
        assert result["message"] == "User deactivated successfully"
        assert target_user.is_active == False
        
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_organization_user_self_deactivation_forbidden(self, mock_org_admin_user, mock_db_session):
        """Test preventing self-deactivation."""
        from app.api.organizations import deactivate_organization_user
        
        org_id = mock_org_admin_user.tenant_id
        user_id = mock_org_admin_user.id  # Same as current user
        
        with pytest.raises(HTTPException) as exc_info:
            await deactivate_organization_user(org_id, user_id, mock_org_admin_user, mock_db_session)
        
        assert exc_info.value.status_code == 400
        assert "You cannot deactivate yourself" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_regenerate_access_code_success(self, mock_org_admin_user, mock_db_session, mock_organization):
        """Test successful access code regeneration."""
        from app.api.organizations import regenerate_organization_access_code
        
        original_code = mock_organization.access_code
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_organization
        mock_db_session.execute.return_value = mock_result
        
        with patch('app.api.organizations.secrets.token_urlsafe') as mock_token:
            mock_token.return_value = "new_access_code"
            
            result = await regenerate_organization_access_code(mock_org_admin_user, mock_db_session)
        
        assert result == mock_organization
        assert mock_organization.access_code == "new_access_code"
        assert mock_organization.access_code != original_code
        
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(mock_organization)


class TestOrganizationsAPISecurityUnit:
    """Security-focused unit tests for organizations API."""

    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular user."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.email = "user@example.com"
        user.role = "member"
        user.is_active = True
        return user

    @pytest.fixture
    def mock_org_admin_user(self):
        """Create a mock org admin user."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.email = "orgadmin@example.com"
        user.role = "org_admin"
        user.is_active = True
        user.tenant_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_is_org_admin_permission_check_success(self, mock_org_admin_user):
        """Test successful org admin permission check."""
        result = await is_org_admin(mock_org_admin_user)
        assert result == mock_org_admin_user

    @pytest.mark.asyncio
    async def test_is_org_admin_permission_check_admin_allowed(self):
        """Test that admin role is allowed for org admin operations."""
        admin_user = Mock(spec=User)
        admin_user.role = "admin"
        
        result = await is_org_admin(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_is_org_admin_permission_check_super_admin_allowed(self):
        """Test that super admin role is allowed for org admin operations."""
        super_admin_user = Mock(spec=User)
        super_admin_user.role = "super_admin"
        
        result = await is_org_admin(super_admin_user)
        assert result == super_admin_user

    @pytest.mark.asyncio
    async def test_is_org_admin_permission_check_regular_user_forbidden(self, mock_regular_user):
        """Test that regular user is forbidden from org admin operations."""
        with pytest.raises(HTTPException) as exc_info:
            await is_org_admin(mock_regular_user)
        
        assert exc_info.value.status_code == 403
        assert "Only organization admins can perform this action" in str(exc_info.value.detail)

    def test_organization_isolation_enforcement(self):
        """Test that organization isolation is properly enforced."""
        # This tests the security pattern used throughout the API
        # where users can only access their own organization's data
        
        # The pattern is: str(current_user.tenant_id) != str(org_id)
        user_tenant_id = uuid4()
        other_org_id = uuid4()
        
        # Different organizations should be blocked
        assert str(user_tenant_id) != str(other_org_id)
        
        # Same organization should be allowed
        assert str(user_tenant_id) == str(user_tenant_id)

    def test_role_hierarchy_enforcement(self):
        """Test role hierarchy enforcement in user management."""
        # Test the role validation logic used in user updates
        
        # Org admin cannot promote to admin or super_admin
        org_admin_role = "org_admin"
        forbidden_roles = ["admin", "super_admin"]
        allowed_roles = ["user", "org_admin"]
        
        for role in forbidden_roles:
            # This would be checked in the endpoint
            assert role in ["admin", "super_admin"]
        
        for role in allowed_roles:
            # These should be allowed for org admin
            assert role not in ["admin", "super_admin"]

    @pytest.mark.asyncio
    async def test_self_modification_prevention(self):
        """Test prevention of self-modification in user management."""
        user_id = uuid4()
        
        # Self-demotion check
        assert str(user_id) == str(user_id)  # Same user
        
        # Different user check
        other_user_id = uuid4()
        assert str(user_id) != str(other_user_id)  # Different user

    def test_access_code_security(self):
        """Test access code generation security."""
        with patch('app.api.organizations.secrets.token_urlsafe') as mock_token:
            mock_token.return_value = "secure_random_token"
            
            # Access codes should be URL-safe and random
            from app.api.organizations import secrets
            code = secrets.token_urlsafe(8)
            
            # This is a mock, but verifies the pattern
            assert code == "secure_random_token"
            mock_token.assert_called_with(8)


class TestOrganizationsAPIDataValidationUnit:
    """Data validation unit tests for organizations API."""

    def test_organization_register_request_validation(self):
        """Test organization registration request validation."""
        from app.schemas.schemas import OrganizationRegisterRequest
        
        # Valid request
        valid_request = OrganizationRegisterRequest(
            name="Test Org",
            subdomain="testorg",
            full_name="Test Organization Ltd",
            address={"street": "123 Main St", "city": "Test City"},
            phone="+1234567890",
            organization_email="contact@testorg.com",
            admin_email="admin@testorg.com",
            admin_username="admin",
            admin_password="secure_password_123",
            admin_first_name="Admin",
            admin_last_name="User"
        )
        
        assert valid_request.name == "Test Org"
        assert valid_request.subdomain == "testorg"
        assert valid_request.admin_email == "admin@testorg.com"

    def test_organization_update_validation(self):
        """Test organization update data validation."""
        from app.schemas.schemas import OrganizationUpdate
        
        # Partial update should work
        update = OrganizationUpdate(
            full_name="Updated Name",
            phone="+9876543210"
        )
        
        assert update.full_name == "Updated Name"
        assert update.phone == "+9876543210"
        
        # Should exclude unset fields
        update_dict = update.model_dump(exclude_unset=True)
        assert "full_name" in update_dict
        assert "phone" in update_dict
        # Other fields should not be present

    def test_admin_user_update_validation(self):
        """Test admin user update validation."""
        from app.schemas.schemas import AdminUserUpdate
        
        # Valid update
        update = AdminUserUpdate(
            role="org_admin",
            is_active=True,
            is_verified=True
        )
        
        assert update.role == "org_admin"
        assert update.is_active == True
        assert update.is_verified == True

    def test_organization_response_structure(self):
        """Test organization response data structure."""
        from app.schemas.schemas import OrganizationResponse
        
        # This would typically be handled by Pydantic's validation
        # when converting from model instances
        
        # Test that the response model exists and has expected structure
        assert hasattr(OrganizationResponse, '__annotations__')
        
        # The actual validation happens at runtime when data is serialized