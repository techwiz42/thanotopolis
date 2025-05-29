// frontend/src/test-utils/test-utils.js
import React from 'react';
import { render } from '@testing-library/react';
import { AuthProvider } from '../App';

// Mock user data
export const mockUser = {
  id: 'user123',
  email: 'test@example.com',
  username: 'testuser',
  first_name: 'Test',
  last_name: 'User',
  role: 'user',
  is_active: true,
  is_verified: true,
  tenant_id: 'tenant123',
  created_at: '2024-01-01T00:00:00Z'
};

export const mockAdminUser = {
  ...mockUser,
  id: 'admin123',
  email: 'admin@example.com',
  username: 'adminuser',
  role: 'admin'
};

export const mockTokens = {
  access_token: 'mock_access_token',
  refresh_token: 'mock_refresh_token',
  token_type: 'bearer'
};

export const mockTenant = 'test-tenant';

// Custom render function with providers
export const renderWithAuth = (ui, { user = null, tokens = null, tenant = null } = {}) => {
  // Mock localStorage
  if (tokens) {
    localStorage.getItem.mockImplementation((key) => {
      if (key === 'tokens') return JSON.stringify(tokens);
      if (key === 'tenant') return tenant;
      return null;
    });
  }

  // Mock initial fetch for user data
  if (user && tokens) {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => user
    });
  }

  return render(
    <AuthProvider>
      {ui}
    </AuthProvider>
  );
};

// API response mocks
export const mockApiResponses = {
  login: {
    success: {
      ok: true,
      json: async () => mockTokens
    },
    failure: {
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid credentials' })
    }
  },
  register: {
    success: {
      ok: true,
      json: async () => mockUser
    },
    failure: {
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Email already registered' })
    }
  },
  getCurrentUser: {
    success: {
      ok: true,
      json: async () => mockUser
    },
    failure: {
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' })
    }
  },
  logout: {
    success: {
      ok: true,
      json: async () => ({ message: 'Logged out' })
    }
  }
};

// Wait for async updates
export const waitForLoadingToFinish = () => {
  return new Promise(resolve => setTimeout(resolve, 0));
};

// frontend/src/test-utils/mockData.js
export const createMockUser = (overrides = {}) => ({
  id: 'user123',
  email: 'test@example.com',
  username: 'testuser',
  first_name: 'Test',
  last_name: 'User',
  role: 'user',
  is_active: true,
  is_verified: true,
  tenant_id: 'tenant123',
  created_at: '2024-01-01T00:00:00Z',
  ...overrides
});

export const createMockTenant = (overrides = {}) => ({
  id: 'tenant123',
  name: 'Test Company',
  subdomain: 'test',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  ...overrides
});

export const createMockTokens = (overrides = {}) => ({
  access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock',
  refresh_token: 'mock_refresh_token_123',
  token_type: 'bearer',
  ...overrides
});

// API mock helpers
export const mockFetchSuccess = (data) => {
  global.fetch = jest.fn().mockResolvedValueOnce({
    ok: true,
    json: async () => data
  });
};

export const mockFetchError = (status, errorMessage) => {
  global.fetch = jest.fn().mockResolvedValueOnce({
    ok: false,
    status,
    json: async () => ({ detail: errorMessage })
  });
};
