'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'

// Types
interface User {
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

interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

interface AuthContextType {
  user: User | null
  tokens: AuthTokens | null
  tenant: string | null
  login: (email: string, password: string, tenant: string) => Promise<void>
  register: (data: RegisterData, tenant: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

interface RegisterData {
  email: string
  username: string
  password: string
  first_name?: string
  last_name?: string
}

// Auth Context
const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

// API Configuration - using relative URL so Next.js proxy handles it
const API_BASE_URL = ''

// Auth Provider
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [tokens, setTokens] = useState<AuthTokens | null>(null)
  const [tenant, setTenant] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadStoredAuth = () => {
      const storedTokens = localStorage.getItem('tokens')
      const storedTenant = localStorage.getItem('tenant')
      
      if (storedTokens && storedTenant) {
        const parsedTokens = JSON.parse(storedTokens)
        setTokens(parsedTokens)
        setTenant(storedTenant)
        fetchUser(parsedTokens.access_token, storedTenant)
      } else {
        setIsLoading(false)
      }
    }

    loadStoredAuth()
  }, [])

  const fetchUser = async (accessToken: string, tenantSubdomain: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'X-Tenant-ID': tenantSubdomain
        }
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      } else {
        throw new Error('Failed to fetch user')
      }
    } catch (error) {
      console.error('Error fetching user:', error)
      logout()
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string, tenantSubdomain: string) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        tenant_subdomain: tenantSubdomain
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Login failed')
    }

    const authTokens = await response.json()
    setTokens(authTokens)
    setTenant(tenantSubdomain)
    
    localStorage.setItem('tokens', JSON.stringify(authTokens))
    localStorage.setItem('tenant', tenantSubdomain)
    
    await fetchUser(authTokens.access_token, tenantSubdomain)
  }

  const register = async (data: RegisterData, tenantSubdomain: string) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': tenantSubdomain
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Registration failed')
    }

    // Auto-login after registration
    await login(data.email, data.password, tenantSubdomain)
  }

  const logout = () => {
    if (tokens) {
      fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': tenant || ''
        }
      }).catch(console.error)
    }

    setUser(null)
    setTokens(null)
    setTenant(null)
    localStorage.removeItem('tokens')
    localStorage.removeItem('tenant')
  }

  return (
    <AuthContext.Provider value={{ user, tokens, tenant, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}
