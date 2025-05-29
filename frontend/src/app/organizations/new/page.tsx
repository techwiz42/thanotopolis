
// frontend/src/app/organizations/new/page.tsx
'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function NewOrganization() {
  const [formData, setFormData] = useState({
    name: '',
    subdomain: ''
  })
  const [accessCode, setAccessCode] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const router = useRouter()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const response = await fetch('/api/organizations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create organization')
      }

      const org = await response.json()
      setAccessCode(org.access_code)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create organization')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (accessCode) {
    return (
      <div className="flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 min-h-[calc(100vh-8rem)]">
        <div className="max-w-md w-full space-y-8">
          <div className="bg-green-50 border border-green-200 rounded-lg p-6">
            <h2 className="text-2xl font-bold text-green-900 mb-4">
              Organization Created Successfully!
            </h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium text-gray-700">Organization Name:</p>
                <p className="text-lg font-semibold text-gray-900">{formData.name}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700">Subdomain:</p>
                <p className="text-lg font-semibold text-gray-900">{formData.subdomain}</p>
              </div>
              <div className="bg-yellow-100 border border-yellow-300 rounded-md p-4">
                <p className="text-sm font-medium text-yellow-800 mb-2">
                  Important: Save this access code!
                </p>
                <p className="text-2xl font-bold text-yellow-900 font-mono">
                  {accessCode}
                </p>
                <p className="text-xs text-yellow-700 mt-2">
                  Share this code only with authorized members who should join your organization.
                </p>
              </div>
            </div>
            <div className="mt-6 flex gap-4">
              <button
                onClick={() => router.push('/register')}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition duration-300"
              >
                Register First User
              </button>
              <button
                onClick={() => router.push('/')}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium transition duration-300"
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 min-h-[calc(100vh-8rem)]">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create New Organization
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Set up your organization to start inviting members
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
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Organization Name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                required
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., Acme Corporation"
              />
            </div>

            <div>
              <label htmlFor="subdomain" className="block text-sm font-medium text-gray-700">
                Subdomain
              </label>
              <div className="mt-1 flex rounded-md shadow-sm">
                <input
                  id="subdomain"
                  name="subdomain"
                  type="text"
                  required
                  pattern="[a-z0-9-]+"
                  className="flex-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-l-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.subdomain}
                  onChange={handleChange}
                  placeholder="acme"
                />
                <span className="inline-flex items-center px-3 rounded-r-md border border-l-0 border-gray-300 bg-gray-50 text-gray-500 sm:text-sm">
                  .thanotopolis.com
                </span>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Lowercase letters, numbers, and hyphens only
              </p>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating organization...' : 'Create Organization'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
