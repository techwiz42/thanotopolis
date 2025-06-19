#!/usr/bin/env python3
"""
Test to verify integration fixtures work with a simple auth test.
"""
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Use simple integration fixtures
pytest_plugins = ["tests.conftest_integration_simple"]


@pytest.mark.asyncio
async def test_auth_integration_simple(client: AsyncClient, sample_tenant, sample_user):
    """Test that auth registration works with real fixtures."""
    # Test registration with tenant header
    registration_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "SecurePassword123!",
        "first_name": "New",
        "last_name": "User"
    }
    
    response = await client.post(
        "/api/auth/register", 
        json=registration_data, 
        headers={"X-Tenant-ID": sample_tenant.subdomain}
    )
    
    print(f"Registration response: {response.status_code}")
    if response.status_code != 200:
        print(f"Response body: {response.json()}")
    
    # Should succeed now that tenant exists in database
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_auth_login_simple(client: AsyncClient, sample_user):
    """Test that login works with real fixtures."""
    login_data = {
        "email": sample_user.email,
        "password": "testpassword123"
    }
    
    response = await client.post("/api/auth/login", json=login_data)
    
    print(f"Login response: {response.status_code}")
    if response.status_code != 200:
        print(f"Response body: {response.json()}")
    
    # Should succeed with real user
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data