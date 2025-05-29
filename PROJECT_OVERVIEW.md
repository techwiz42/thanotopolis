# Thanotopolis Project Overview

## Project Structure
This is a full-stack web application with:
- **Backend**: Python FastAPI with SQLAlchemy ORM and async database operations
- **Frontend**: Next.js 13+ application with TypeScript, React, and Tailwind CSS

## Authentication System Architecture

### Backend Authentication
- **JWT-based authentication** with refresh token rotation for enhanced security
- **Multi-tenant system** with tenant isolation through subdomains and headers
- **Role-based access control** (user, admin, super_admin roles)

#### Authentication Flow
1. **Registration**:
   - User provides email, username, password, and optional name
   - System validates email/username uniqueness within tenant
   - Password is hashed using bcrypt via CryptContext
   - User record is created with default "user" role

2. **Login**:
   - User provides email, password, and tenant subdomain
   - System verifies tenant existence and active status
   - System authenticates user against stored hashed password
   - On success, system issues:
     - JWT access token (30-minute expiry)
     - Refresh token (7-day expiry stored in database)

3. **Request Authentication**:
   - HTTP Bearer token scheme with FastAPI's HTTPBearer dependency
   - Access token verified on each request
   - User and tenant information extracted from token
   - User existence and active status verified against database

4. **Token Refresh**:
   - Client sends refresh token to get new access token
   - System validates refresh token against database
   - Old refresh token is invalidated (deleted)
   - New access token and refresh token pair issued
   - This rotation pattern prevents token reuse attacks

5. **Logout**:
   - All refresh tokens for user are invalidated
   - Client discards access token

#### Security Components
- **JWT Structure**:
  - Contains user ID (sub), tenant ID, email, and role
  - HS256 algorithm with secret key
  - UUID values converted to strings for serialization
  - Includes 30-minute expiration timestamp

- **Password Handling**:
  - Passwords hashed with bcrypt (via passlib CryptContext)
  - Hash verification handled by CryptContext's verify method
  - No plain passwords stored or logged

- **Tenant Isolation**:
  - Users are scoped to specific tenants
  - DB constraints ensure email/username uniqueness within tenants
  - Tenant information extracted from subdomain or X-Tenant-ID header
  - All user operations verify tenant context

### Frontend Authentication

#### Authentication State Management
- **AuthContext Provider** (`frontend/src/contexts/AuthContext.tsx`):
  - Uses React Context API for global auth state
  - Maintains three key state elements:
    - `user`: Current authenticated user data
    - `tokens`: Access and refresh token pair
    - `tenant`: Current tenant subdomain

#### Authentication Methods
- **login(email, password, tenant)**:
  - Sends credentials to `/api/auth/login` endpoint
  - Stores tokens in localStorage and context state
  - Fetches user profile on successful login

- **register(userData, tenant)**:
  - Sends registration data to `/api/auth/register` endpoint
  - Auto-logs in user after successful registration

- **logout()**:
  - Calls `/api/auth/logout` to invalidate server-side tokens
  - Clears localStorage and auth context state

#### Token Management
- **Token Storage**:
  - Tokens stored in localStorage for persistence across page refreshes
  - Token and user state loaded on application start
  - Automatic user fetching using stored tokens

- **API Authentication**:
  - Requests include Bearer token in Authorization header
  - Tenant context provided via X-Tenant-ID header

#### Protected Routes
- **ProtectedRoute Component** (`frontend/src/components/ProtectedRoute.tsx`):
  - Wraps private routes to ensure authentication
  - Redirects unauthenticated users to login page
  - Handles loading states during auth checks

#### Login/Registration Forms
- **Login Page** (`frontend/src/app/login/page.tsx`):
  - Email, password, and tenant fields
  - Form validation and error handling
  - Demo tenant information provided

- **Registration Page** (`frontend/src/app/register/page.tsx`):
  - Complete user registration form
  - Validation for required fields and password strength

## Dashboard and Admin Features

### User Dashboard
- **Greeting Page** (`frontend/src/app/greeting/page.tsx`):
  - Personalized greeting based on time of day
  - User profile information display
  - Account status indicators (active/inactive, verified/unverified)
  - Links to dashboard functionality (in development)

### Admin Features
- **User Management** (backend implemented):
  - List users within tenant (admin+ only)
  - View specific user details
  - Update user roles (super_admin only)
  - Delete users (admin+ only, with restrictions)

- **Role-Based Access Control**:
  - Three role levels: user, admin, super_admin
  - Role-specific endpoint access:
    - Users: Limited to own profile
    - Admins: User management within tenant
    - Super Admins: Full control including role management

## Multi-Tenant System
- **Tenant Isolation**:
  - Each tenant has its own subdomain
  - User emails and usernames unique within tenant
  - Cross-tenant data access prevented

- **Tenant Identification**:
  - Extracted from subdomain in HTTP host
  - Fallback to X-Tenant-ID header
  - Required for authentication and data access

## Technology Stack
- **Backend**:
  - FastAPI framework
  - SQLAlchemy ORM with async operations
  - PostgreSQL database with UUID primary keys
  - Alembic for database migrations
  - Pydantic for data validation
  - JWT authentication with Python-jose
  - Bcrypt password hashing with passlib

- **Frontend**:
  - Next.js 13+ with App Router
  - TypeScript for type safety
  - React Context for state management
  - Tailwind CSS for styling
  - Jest for testing