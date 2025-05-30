// frontend/src/__tests__/Login.integration.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { mockUser, mockTokens } from '../test-utils/mockData';

describe('Login Integration', () => {
  beforeEach(() => {
    localStorage.clear();
    fetch.mockClear();
  });

  test('complete login flow', async () => {
    // Mock successful login
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => []  // Empty conversations list
      });

    render(<App />);
    const user = userEvent.setup();

    // Fill login form
    await user.type(screen.getByPlaceholderText('Tenant subdomain'), 'test-tenant');
    await user.type(screen.getByPlaceholderText('Email address'), 'test@example.com');
    await user.type(screen.getByPlaceholderText('Password'), 'password123');
    
    // Submit
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    // Should show loading state
    expect(screen.getByText('Signing in...')).toBeInTheDocument();

    // Should redirect to conversations page
    await waitFor(() => {
      expect(screen.getByText('Conversations')).toBeInTheDocument();
      expect(screen.getByText('Your conversations with AI agents')).toBeInTheDocument();
    });

    // Verify API calls
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch).toHaveBeenNthCalledWith(1, 
      'http://localhost:8000/api/auth/login',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'password123',
          tenant_subdomain: 'test-tenant'
        })
      })
    );
  });
});
