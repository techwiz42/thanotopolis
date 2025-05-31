// src/types/user.types.ts

export interface User {
  id: string
  email: string
  username: string
  first_name?: string
  last_name?: string
  role: string
  is_active: boolean
  is_verified: boolean
  tenant_id: string
  created_at: string
}

export interface TokenResponse {
  tokens_remaining: number;
  total_tokens: number;
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  organization_subdomain: string
  user: User
}
