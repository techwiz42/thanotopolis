// frontend/src/__tests__/Register.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Register } from '../App';

// Mock the useAuth hook
const mockRegister = jest.fn();
jest.mock('../App', () => ({
  ...jest.requireActual('../App'),
  useAuth: () => ({
    register: mockRegister,
    user: null,
    tokens: null,
    tenant: null,
    isLoading: false
  })
}));

describe('Register Component', () => {
  const mockOnViewChange = jest.fn();

  beforeEach(() => {
    mockRegister.mockClear();
    mockOnViewChange.mockClear();
  });

  test('renders registration form correctly', () => {
    render(<Register onViewChange={mockOnViewChange} />);

    expect(screen.getByText('Create your account')).toBeInTheDocument();
    expect(screen.getByLabelText('Tenant Subdomain')).toBeInTheDocument();
    expect(screen.getByLabelText('First Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Last Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Register' })).toBeInTheDocument();
  });

  test('handles form submission with valid data', async () => {
    mockRegister.mockResolvedValueOnce();
    render(<Register onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    // Fill form
    await user.type(screen.getByLabelText('Tenant Subdomain'), 'test-tenant');
    await user.type(screen.getByLabelText('First Name'), 'John');
    await user.type(screen.getByLabelText('Last Name'), 'Doe');
    await user.type(screen.getByLabelText('Username'), 'johndoe');
    await user.type(screen.getByLabelText('Email Address'), 'john@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'password123');

    // Submit
    await user.click(screen.getByRole('button', { name: 'Register' }));

    expect(mockRegister).toHaveBeenCalledWith(
      {
        email: 'john@example.com',
        username: 'johndoe',
        password: 'password123',
        first_name: 'John',
        last_name: 'Doe'
      },
      'test-tenant'
    );
  });

  test('validates password match', async () => {
    render(<Register onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Tenant Subdomain'), 'test-tenant');
    await user.type(screen.getByLabelText('Username'), 'johndoe');
    await user.type(screen.getByLabelText('Email Address'), 'john@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'different123');

    await user.click(screen.getByRole('button', { name: 'Register' }));

    await waitFor(() => {
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
    });
    expect(mockRegister).not.toHaveBeenCalled();
  });

  test('validates password length', async () => {
    render(<Register onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Tenant Subdomain'), 'test-tenant');
    await user.type(screen.getByLabelText('Username'), 'johndoe');
    await user.type(screen.getByLabelText('Email Address'), 'john@example.com');
    await user.type(screen.getByLabelText('Password'), 'short');
    await user.type(screen.getByLabelText('Confirm Password'), 'short');

    await user.click(screen.getByRole('button', { name: 'Register' }));

    await waitFor(() => {
      expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument();
    });
    expect(mockRegister).not.toHaveBeenCalled();
  });

  test('displays registration error', async () => {
    mockRegister.mockRejectedValueOnce(new Error('Email already registered'));
    render(<Register onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Tenant Subdomain'), 'test-tenant');
    await user.type(screen.getByLabelText('Username'), 'johndoe');
    await user.type(screen.getByLabelText('Email Address'), 'existing@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText('Confirm Password'), 'password123');

    await user.click(screen.getByRole('button', { name: 'Register' }));

    await waitFor(() => {
      expect(screen.getByText('Email already registered')).toBeInTheDocument();
    });
  });

  test('navigates to login view', async () => {
    render(<Register onViewChange={mockOnViewChange} />);
    const user = userEvent.setup();

    await user.click(screen.getByText('Already have an account? Sign in'));

    expect(mockOnViewChange).toHaveBeenCalledWith('login');
  });
});

// frontend/src/__tests__/Dashboard.test.js
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Dashboard } from '../App';
import { mockUser, mockAdminUser } from '../test-utils/mockData';

// Mock the useAuth hook
const mockLogout = jest.fn();
const mockAuthState = {
  user: mockUser,
  tenant: 'test-tenant',
  logout: mockLogout
};

jest.mock('../App', () => ({
  ...jest.requireActual('../App'),
  useAuth: () => mockAuthState
}));

describe('Dashboard Component', () => {
  beforeEach(() => {
    mockLogout.mockClear();
  });

  test('renders user information correctly', () => {
    render(<Dashboard />);

    expect(screen.getByText(`Welcome, ${mockUser.first_name || mockUser.username}!`)).toBeInTheDocument();
    expect(screen.getByText('User Information')).toBeInTheDocument();
    expect(screen.getByText(mockUser.username)).toBeInTheDocument();
    expect(screen.getByText(mockUser.email)).toBeInTheDocument();
    expect(screen.getByText(mockUser.role)).toBeInTheDocument();
    expect(screen.getByText('Tenant: test-tenant')).toBeInTheDocument();
  });

  test('displays account status correctly', () => {
    render(<Dashboard />);

    expect(screen.getByText('Account Status')).toBeInTheDocument();
    
    // Check active status
    const activeStatus = screen.getByText('Yes').closest('span');
    expect(activeStatus).toHaveClass('bg-green-100', 'text-green-800');
    
    // Check member since date
    expect(screen.getByText(new Date(mockUser.created_at).toLocaleDateString())).toBeInTheDocument();
  });

  test('displays inactive user status', () => {
    mockAuthState.user = { ...mockUser, is_active: false };
    render(<Dashboard />);

    const inactiveStatus = screen.getByText('No').closest('span');
    expect(inactiveStatus).toHaveClass('bg-red-100', 'text-red-800');
  });

  test('displays unverified user status', () => {
    mockAuthState.user = { ...mockUser, is_verified: false };
    render(<Dashboard />);

    const unverifiedStatus = screen.getByText('No');
    expect(unverifiedStatus.closest('span')).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  test('handles logout', async () => {
    render(<Dashboard />);
    const user = userEvent.setup();

    await user.click(screen.getByText('Logout'));

    expect(mockLogout).toHaveBeenCalled();
  });

  test('displays admin role correctly', () => {
    mockAuthState.user = mockAdminUser;
    render(<Dashboard />);

    expect(screen.getByText('admin')).toBeInTheDocument();
  });

  test('displays username when first name is not available', () => {
    mockAuthState.user = { ...mockUser, first_name: null };
    render(<Dashboard />);

    expect(screen.getByText(`Welcome, ${mockUser.username}!`)).toBeInTheDocument();
  });
});

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

    // Mock successful user fetch
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockUser
    });

    render(<App />);

    // Should show loading state initially
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();

    // Should load user and show dashboard
    await waitFor(() => {
      expect(screen.getByText(`Welcome, ${mockUser.first_name}!`)).toBeInTheDocument();
    });
  });

  test('redirects to login when no auth present', () => {
    render(<App />);

    expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
  });

  test('complete auth flow: register -> auto-login -> dashboard -> logout', async () => {
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
      });

    // Submit registration
    await user.click(screen.getByRole('button', { name: 'Register' }));

    // Should show dashboard
    await waitFor(() => {
      expect(screen.getByText('Welcome, New!')).toBeInTheDocument();
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
