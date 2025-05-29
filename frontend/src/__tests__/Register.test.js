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

// This content has been moved to separate files
