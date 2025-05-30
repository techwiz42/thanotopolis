// frontend/src/app/register/page.tsx
'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

export default function Register() {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    access_code: ''
  })
  const [organizationInfo, setOrganizationInfo] = useState<{
    name: string;
    subdomain: string;
  } | null>(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isValidatingCode, setIsValidatingCode] = useState(false)
  
  const { register } = useAuth()
  const router = useRouter()

  // Validate access code when it changes
  useEffect(() => {
    const validateAccessCode = async () => {
      if (formData.access_code.length < 6) {
        setOrganizationInfo(null)
        return
      }

      setIsValidatingCode(true)
      try {
        const response = await fetch(`/api/organizations/${formData.access_code}/info`)
        if (response.ok) {
          const orgInfo = await response.json()
          setOrganizationInfo(orgInfo)
        } else {
          setOrganizationInfo(null)
        }
      } catch (error) {
        console.error('Failed to validate access code:', error)
        setOrganizationInfo(null)
      } finally {
        setIsValidatingCode(false)
      }
    }

    const debounceTimer = setTimeout(validateAccessCode, 500)
    return () => clearTimeout(debounceTimer)
  }, [formData.access_code])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    if (!formData.access_code) {
      setError('Please enter the organization access code')
      return
    }

    setIsSubmitting(true)

    try {
      const { confirmPassword, ...registerData } = formData
      await register(registerData)
      router.push('/conversations')  // Changed from '/greeting' to '/conversations'
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 min-h-[calc(100vh-8rem)]">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Or{' '}
            <Link href="/login" className="font-medium text-blue-600 hover:text-blue-500">
              sign in to existing account
            </Link>
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label htmlFor="access_code" className="block text-sm font-medium text-gray-700">
                Organization Access Code
              </label>
              <input
                id="access_code"
                name="access_code"
                type="text"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                value={formData.access_code}
                onChange={handleChange}
                placeholder="Enter the code provided by your organization"
              />
              {isValidatingCode && (
                <p className="mt-1 text-xs text-gray-500">Validating code...</p>
              )}
              {organizationInfo && (
                <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-md">
                  <p className="text-xs text-green-800">
                    You're joining: <strong>{organizationInfo.name}</strong> ({organizationInfo.subdomain})
                  </p>
                </div>
              )}
              {!organizationInfo && formData.access_code.length >= 6 && !isValidatingCode && (
                <p className="mt-1 text-xs text-red-600">
                  Invalid access code. Please check with your organization admin.
                </p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Don't have an access code?{' '}
                <Link href="/organizations/new" className="text-blue-600 hover:text-blue-500">
                  Create an organization
                </Link>
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">
                  First Name
                </label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.first_name}
                  onChange={handleChange}
                />
              </div>
              <div>
                <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">
                  Last Name
                </label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.last_name}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                value={formData.username}
                onChange={handleChange}
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                value={formData.email}
                onChange={handleChange}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                value={formData.password}
                onChange={handleChange}
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                value={formData.confirmPassword}
                onChange={handleChange}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting || !organizationInfo}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating account...' : 'Register'}
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link href="/login" className="font-medium text-blue-600 hover:text-blue-500">
                Sign in here
              </Link>
            </p>
          </div>
        </form>

        {/* Demo credentials reminder */}
        <div className="mt-6 p-4 bg-blue-50 rounded-md">
          <p className="text-sm text-blue-800 font-medium">Demo Access Code:</p>
          <p className="text-xs text-blue-700 mt-1">
            Use access code: <strong>DEMO123</strong>
          </p>
          <p className="text-xs text-blue-600 mt-2">
            This will register you in the demo organization.
          </p>
        </div>
      </div>
    </div>
  )
}
