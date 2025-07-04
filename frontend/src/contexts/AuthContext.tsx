// frontend/src/contexts/AuthContext.tsx
'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { User, AuthTokens } from '@/types/user.types'

// Re-export AuthTokens for backward compatibility
export type { AuthTokens }

interface AuthContextType {
  user: User | null
  tokens: AuthTokens | null
  token: string | null // Added for backward compatibility with conversation feature
  organization: string | null
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  switchOrganization?: (tenantId: string) => Promise<void>
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
      
      // Redirect based on user role
      const userResponse = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${access_token}`,
          'X-Tenant-ID': organization_subdomain
        }
      })
      
      if (userResponse.ok) {
        const userData = await userResponse.json()
        if (userData.role === 'super_admin') {
          router.push('/admin/organizations')
        } else {
          router.push('/conversations')
        }
      } else {
        router.push('/conversations')
      }
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

  const switchOrganization = async (tenantId: string) => {
    if (!tokens || !user) {
      throw new Error('Not authenticated')
    }

    if (user.role !== 'super_admin') {
      throw new Error('Only super admins can switch organizations')
    }

    try {
      // Get organization details to get subdomain
      const orgResponse = await fetch(`${API_BASE_URL}/api/organizations/${tenantId}`, {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization || '',
        }
      })

      if (!orgResponse.ok) {
        throw new Error('Failed to get organization details')
      }

      const orgData = await orgResponse.json()
      const newOrganization = orgData.subdomain

      // Update local state
      setOrganization(newOrganization)
      localStorage.setItem('organization', newOrganization)

      // Fetch user data with new organization context
      await fetchUser(tokens.access_token, newOrganization)
    } catch (error) {
      console.error('Error switching organization:', error)
      throw error
    }
  }


  return (
    <AuthContext.Provider value={{ user, tokens, token, organization, login, register, logout, switchOrganization, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}
