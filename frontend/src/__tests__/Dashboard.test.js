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