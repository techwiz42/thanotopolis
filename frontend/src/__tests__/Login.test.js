// frontend/src/__tests__/Login.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Login } from '../App';
import { renderWithAuth, mockApiResponses } from '../test-utils/test-utils';

// Mock the useAuth hook
const mockLogin = jest.fn();
jest.mock('../App', () => ({
  ...jest.requireActual('../App'),
  useAuth: () => ({
    login: mockLogin,
    user: null,
    tokens: null,
    tenant: null,
    isLoading: false
  })
}));

describe('Login Component', () => {
  const mockOnViewChange = jest.fn();

  beforeEach(() => {
    mockLogin.mockClear();
    mockOnViewChange.mockClear();
  });

  test('renders login form correctly', () => {
    render(<Login onViewChange={mockOnViewChange} />);

    expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Tenant subdomain')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Email address')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.getByText("Don't have an account? Register")).toBeInTheDocument();
  });

  test('handles form input changes', async () => {
    render(<Login onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    const tenantInput = screen.getByPlaceholderText('Tenant subdomain');
    const emailInput = screen.getByPlaceholderText('Email address');
    const passwordInput = screen.getByPlaceholderText('Password');

    await user.type(tenantInput, 'test-tenant');
    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');

    expect(tenantInput).toHaveValue('test-tenant');
    expect(emailInput).toHaveValue('test@example.com');
    expect(passwordInput).toHaveValue('password123');
  });

  test('submits form with correct data', async () => {
    mockLogin.mockResolvedValueOnce();
    render(<Login onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText('Tenant subdomain'), 'test-tenant');
    await user.type(screen.getByPlaceholderText('Email address'), 'test@example.com');
    await user.type(screen.getByPlaceholderText('Password'), 'password123');
    
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123', 'test-tenant');
  });

  test('displays error message on login failure', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));
    render(<Login onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText('Tenant subdomain'), 'test-tenant');
    await user.type(screen.getByPlaceholderText('Email address'), 'test@example.com');
    await user.type(screen.getByPlaceholderText('Password'), 'wrongpassword');
    
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  test('disables submit button while submitting', async () => {
    mockLogin.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
    render(<Login onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText('Tenant subdomain'), 'test-tenant');
    await user.type(screen.getByPlaceholderText('Email address'), 'test@example.com');
    await user.type(screen.getByPlaceholderText('Password'), 'password123');
    
    const submitButton = screen.getByRole('button', { name: 'Sign in' });
    await user.click(submitButton);

    expect(submitButton).toBeDisabled();
    expect(submitButton).toHaveTextContent('Signing in...');

    await waitFor(() => {
      expect(submitButton).not.toBeDisabled();
      expect(submitButton).toHaveTextContent('Sign in');
    });
  });

  test('navigates to register view when register link clicked', async () => {
    render(<Login onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    await user.click(screen.getByText("Don't have an account? Register"));

    expect(mockOnViewChange).toHaveBeenCalledWith('register');
  });

  test('validates required fields', async () => {
    render(<Login onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    // Try to submit empty form
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    // Check that HTML5 validation prevents submission
    expect(mockLogin).not.toHaveBeenCalled();
  });

  test('clears error when user starts typing', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));
    render(<Login onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    // Submit with wrong credentials
    await user.type(screen.getByPlaceholderText('Tenant subdomain'), 'test-tenant');
    await user.type(screen.getByPlaceholderText('Email address'), 'test@example.com');
    await user.type(screen.getByPlaceholderText('Password'), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });

    // Start typing in email field
    await user.type(screen.getByPlaceholderText('Email address'), '2');

    // Error should be cleared
    expect(screen.queryByText('Invalid credentials')).not.toBeInTheDocument();
  });
});

// This content has been moved to a separate file
