// frontend/src/__tests__/App.integration.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { mockUser, mockTokens } from '../test-utils/mockData';

describe('App Integration Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    fetch.mockClear();
  });

  test('loads user from localStorage on app start', async () => {
    // Setup localStorage with existing auth
    localStorage.getItem.mockImplementation((key) => {
      if (key === 'tokens') return JSON.stringify(mockTokens);
      if (key === 'tenant') return 'test-tenant';
      return null;
    });

    // Mock successful user fetch and conversations fetch
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => []  // Empty conversations list
      });

    render(<App />);

    // Should show loading state initially
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();

    // Should load user and show conversations page
    await waitFor(() => {
      expect(screen.getByText('Conversations')).toBeInTheDocument();
      expect(screen.getByText('Your conversations with AI agents')).toBeInTheDocument();
    });
  });

  test('redirects to login when no auth present', () => {
    render(<App />);

    expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
  });

  test('complete auth flow: register -> auto-login -> conversations -> logout', async () => {
    render(<App />);
    const user = userEvent.setup();

    // Navigate to register
    await user.click(screen.getByText("Don't have an account? Register"));

    // Fill registration form
    await user.type(screen.getByLabelText('Tenant Subdomain'), 'new-tenant');
    await user.type(screen.getByLabelText('First Name'), 'New');
    await user.type(screen.getByLabelText('Last Name'), 'User');
    await user.type(screen.getByLabelText('Username'), 'newuser');
    await user.type(screen.getByLabelText('Email Address'), 'new@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'password123');

    // Mock successful registration and auto-login
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockUser, email: 'new@example.com' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockUser, email: 'new@example.com' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => []  // Empty conversations list
      });

    // Submit registration
    await user.click(screen.getByRole('button', { name: 'Register' }));

    // Should show conversations page
    await waitFor(() => {
      expect(screen.getByText('Conversations')).toBeInTheDocument();
    });

    // Mock logout
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'Logged out' })
    });

    // Logout
    await user.click(screen.getByText('Logout'));

    // Should return to login
    await waitFor(() => {
      expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
    });
  });
});
