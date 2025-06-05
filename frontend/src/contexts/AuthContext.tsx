// frontend/src/contexts/AuthContext.tsx
'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'

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
  token: string | null // Added for backward compatibility with conversation feature
  organization: string | null
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  isLoading: boolean
}

interface RegisterData {
  email: string
  username: string
  password: string
  first_name?: string
  last_name?: string
  access_code: string  // Only access code needed - org derived from this
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
  const [organization, setOrganization] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  // Computed property for backward compatibility
  const token = tokens?.access_token || null

  const logout = useCallback(() => {
    if (tokens) {
      fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization || '',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: tokens.refresh_token
        })
      }).catch(console.error)
    }

    setUser(null)
    setTokens(null)
    setOrganization(null)
    localStorage.removeItem('tokens')
    localStorage.removeItem('organization')
    
    // Redirect to login page
    router.push('/login')
  }, [tokens, organization, router])

  const fetchUser = useCallback(async (accessToken: string, organizationSubdomain: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'X-Tenant-ID': organizationSubdomain
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
      // Don't call logout here to avoid circular dependency
      setUser(null)
      setTokens(null)
      setOrganization(null)
      localStorage.removeItem('tokens')
      localStorage.removeItem('organization')
      router.push('/login')
    } finally {
      setIsLoading(false)
    }
  }, [router])

  useEffect(() => {
    const loadStoredAuth = () => {
      const storedTokens = localStorage.getItem('tokens')
      const storedOrganization = localStorage.getItem('organization')
      
      if (storedTokens && storedOrganization) {
        const parsedTokens = JSON.parse(storedTokens)
        setTokens(parsedTokens)
        setOrganization(storedOrganization)
        fetchUser(parsedTokens.access_token, storedOrganization)
      } else {
        setIsLoading(false)
      }
    }

    loadStoredAuth()
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Login failed')
      }

      const authResponse = await response.json()
      const { access_token, refresh_token, token_type, organization_subdomain } = authResponse
      
      const authTokens = { access_token, refresh_token, token_type }
      setTokens(authTokens)
      setOrganization(organization_subdomain)
      
      localStorage.setItem('tokens', JSON.stringify(authTokens))
      localStorage.setItem('organization', organization_subdomain)
      
      await fetchUser(access_token, organization_subdomain)
      
      // Redirect to conversations after successful login
      router.push('/conversations')
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  }

  const register = async (data: RegisterData) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Registration failed')
    }

    const authResponse = await response.json()
    const { access_token, refresh_token, token_type, organization_subdomain } = authResponse
    
    const authTokens = { access_token, refresh_token, token_type }
    setTokens(authTokens)
    setOrganization(organization_subdomain)
    
    localStorage.setItem('tokens', JSON.stringify(authTokens))
    localStorage.setItem('organization', organization_subdomain)
    
    await fetchUser(access_token, organization_subdomain)
  }


  return (
    <AuthContext.Provider value={{ user, tokens, token, organization, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}
