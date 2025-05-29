// frontend/src/__tests__/AuthContext.test.js
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from '../App';
import { mockUser, mockTokens, mockTenant, mockFetchSuccess, mockFetchError } from '../test-utils/mockData';

// Test component to access auth context
const TestComponent = () => {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="user">{auth.user ? auth.user.email : 'No user'}</div>
      <div data-testid="tenant">{auth.tenant || 'No tenant'}</div>
      <div data-testid="loading">{auth.isLoading ? 'Loading' : 'Not loading'}</div>
      <button onClick={() => auth.logout()}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    fetch.mockClear();
  });

  test('provides auth context to children', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('user')).toHaveTextContent('No user');
    expect(screen.getByTestId('tenant')).toHaveTextContent('No tenant');
    expect(screen.getByTestId('loading')).toHaveTextContent('Not loading');
  });

  test('throws error when useAuth is used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAuth must be used within AuthProvider');
    
    consoleSpy.mockRestore();
  });

  test('loads stored auth on mount', async () => {
    localStorage.getItem.mockImplementation((key) => {
      if (key === 'tokens') return JSON.stringify(mockTokens);
      if (key === 'tenant') return mockTenant;
      return null;
    });

    mockFetchSuccess(mockUser);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('loading')).toHaveTextContent('Loading');

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent(mockUser.email);
      expect(screen.getByTestId('tenant')).toHaveTextContent(mockTenant);
      expect(screen.getByTestId('loading')).toHaveTextContent('Not loading');
    });

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/me',
      expect.objectContaining({
        headers: {
          'Authorization': `Bearer ${mockTokens.access_token}`,
          'X-Tenant-ID': mockTenant
        }
      })
    );
  });

  test('handles failed user fetch on mount', async () => {
    localStorage.getItem.mockImplementation((key) => {
      if (key === 'tokens') return JSON.stringify(mockTokens);
      if (key === 'tenant') return mockTenant;
      return null;
    });

    mockFetchError(401, 'Unauthorized');

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('No user');
      expect(screen.getByTestId('loading')).toHaveTextContent('Not loading');
    });

    // Should clear localStorage on auth failure
    expect(localStorage.removeItem).toHaveBeenCalledWith('tokens');
    expect(localStorage.removeItem).toHaveBeenCalledWith('tenant');
  });

  test('login function works correctly', async () => {
    const LoginTest = () => {
      const { login, user } = useAuth();
      const handleLogin = async () => {
        await login('test@example.com', 'password123', 'test-tenant');
      };
      
      return (
        <div>
          <button onClick={handleLogin}>Login</button>
          <div data-testid="user">{user ? user.email : 'No user'}</div>
        </div>
      );
    };

    // Mock successful login
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      });

    render(
      <AuthProvider>
        <LoginTest />
      </AuthProvider>
    );

    const user = userEvent.setup();
    await user.click(screen.getByText('Login'));

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent(mockUser.email);
    });

    // Verify login API call
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/auth/login',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'password123',
          tenant_subdomain: 'test-tenant'
        })
      })
    );

    // Verify tokens stored
    expect(localStorage.setItem).toHaveBeenCalledWith('tokens', JSON.stringify(mockTokens));
    expect(localStorage.setItem).toHaveBeenCalledWith('tenant', 'test-tenant');
  });

  test('login handles errors correctly', async () => {
    const LoginTest = () => {
      const { login } = useAuth();
      const [error, setError] = React.useState(null);
      
      const handleLogin = async () => {
        try {
          await login('test@example.com', 'wrong-password', 'test-tenant');
        } catch (err) {
          setError(err.message);
        }
      };
      
      return (
        <div>
          <button onClick={handleLogin}>Login</button>
          <div data-testid="error">{error || 'No error'}</div>
        </div>
      );
    };

    mockFetchError(401, 'Invalid credentials');

    render(
      <AuthProvider>
        <LoginTest />
      </AuthProvider>
    );

    const user = userEvent.setup();
    await user.click(screen.getByText('Login'));

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent('Invalid credentials');
    });
  });

  test('register function works correctly', async () => {
    const RegisterTest = () => {
      const { register, user } = useAuth();
      const handleRegister = async () => {
        await register({
          email: 'new@example.com',
          username: 'newuser',
          password: 'password123',
          first_name: 'New',
          last_name: 'User'
        }, 'test-tenant');
      };
      
      return (
        <div>
          <button onClick={handleRegister}>Register</button>
          <div data-testid="user">{user ? user.email : 'No user'}</div>
        </div>
      );
    };

    // Mock successful registration and auto-login
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      });

    render(
      <AuthProvider>
        <RegisterTest />
      </AuthProvider>
    );

    const user = userEvent.setup();
    await user.click(screen.getByText('Register'));

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent(mockUser.email);
    });

    // Verify register API call
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/auth/register',
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': 'test-tenant'
        }
      })
    );
  });

  test('logout function works correctly', async () => {
    localStorage.getItem.mockImplementation((key) => {
      if (key === 'tokens') return JSON.stringify(mockTokens);
      if (key === 'tenant') return mockTenant;
      return null;
    });

    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Logged out' })
      });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent(mockUser.email);
    });

    const user = userEvent.setup();
    await user.click(screen.getByText('Logout'));

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('No user');
      expect(screen.getByTestId('tenant')).toHaveTextContent('No tenant');
    });

    // Verify logout API call
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/auth/logout',
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${mockTokens.access_token}`,
          'X-Tenant-ID': mockTenant
        }
      })
    );

    // Verify localStorage cleared
    expect(localStorage.removeItem).toHaveBeenCalledWith('tokens');
    expect(localStorage.removeItem).toHaveBeenCalledWith('tenant');
  });
});
