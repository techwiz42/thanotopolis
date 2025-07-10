'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function BillingSuccess() {
  const [organizationData, setOrganizationData] = useState<any>(null)
  const [accessCode, setAccessCode] = useState('')
  const [isCreatingOrg, setIsCreatingOrg] = useState(true)
  const [error, setError] = useState('')
  const router = useRouter()

  useEffect(() => {
    // Retrieve organization data from sessionStorage
    const pendingOrgData = sessionStorage.getItem('pendingOrganization')
    if (pendingOrgData) {
      const orgData = JSON.parse(pendingOrgData)
      setOrganizationData(orgData)
      createOrganization(orgData)
    } else {
      // If no pending organization data, redirect to creation form
      router.push('/organizations/new')
    }
  }, [router])

  const createOrganization = async (orgData: any) => {
    try {
      const response = await fetch('/api/organizations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(orgData)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create organization')
      }

      const org = await response.json()
      setAccessCode(org.access_code)
      
      // Clear the pending organization data
      sessionStorage.removeItem('pendingOrganization')
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create organization')
    } finally {
      setIsCreatingOrg(false)
    }
  }

  if (isCreatingOrg) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <h2 className="mt-4 text-xl font-semibold text-gray-900">Creating Your Organization...</h2>
          <p className="mt-2 text-gray-600">Please wait while we set up your account</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="max-w-md w-full">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-900 mb-4">
              Organization Creation Failed
            </h2>
            <p className="text-red-800 mb-4">{error}</p>
            <div className="space-y-2">
              <button
                onClick={() => router.push('/organizations/new')}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Try Again
              </button>
              <button
                onClick={() => router.push('/billing')}
                className="w-full bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Go to Billing
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 min-h-[calc(100vh-8rem)]">
      <div className="max-w-2xl w-full space-y-8">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="text-center mb-6">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
              <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold text-green-900">
              Welcome to Thanotopolis!
            </h2>
            <p className="mt-2 text-green-800">
              Your organization has been created successfully and your subscription is active.
            </p>
          </div>

          <div className="space-y-4">
            <div className="bg-white rounded-lg p-4">
              <h3 className="font-medium text-gray-900 mb-3">Organization Details</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Organization Name:</span>
                  <span className="font-medium text-gray-900">{organizationData?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Subdomain:</span>
                  <span className="font-medium text-gray-900">{organizationData?.subdomain}.thanotopolis.com</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Subscription:</span>
                  <span className="font-medium text-green-600">Active</span>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 border border-purple-200 rounded-md p-4 mb-4">
              <h4 className="text-sm font-medium text-purple-800 mb-2">
                📞 We're Here to Help!
              </h4>
              <p className="text-sm text-purple-700">
                <strong>We will guide you through the setup process.</strong> Contact us at{' '}
                <a href="tel:+16179971844" className="font-semibold text-purple-800 hover:text-purple-600">(617) 997-1844</a>{' '}
                or{' '}
                <a href="mailto:pete@cyberiad.ai" className="font-semibold text-purple-800 hover:text-purple-600">pete@cyberiad.ai</a>{' '}
                to continue the setup process with personalized assistance.
              </p>
            </div>

            <div className="bg-yellow-100 border border-yellow-300 rounded-md p-4">
              <h4 className="text-sm font-medium text-yellow-800 mb-2">
                🔑 Your Organization Access Code
              </h4>
              <p className="text-2xl font-bold text-yellow-900 font-mono mb-2">
                {accessCode}
              </p>
              <p className="text-xs text-yellow-700">
                <strong>Important:</strong> Save this code securely! Share it only with team members who should join your organization.
                You can regenerate this code later from your admin dashboard if needed.
              </p>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <h4 className="text-sm font-medium text-blue-800 mb-2">
                🚀 Next Steps
              </h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Create your first user account with the access code</li>
                <li>• Set up your telephony system in the admin dashboard</li>
                <li>• Customize your agent instructions</li>
                <li>• Invite team members to join your organization</li>
              </ul>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            <button
              onClick={() => router.push('/register')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-md text-sm font-medium transition duration-300"
            >
              Create Your User Account
            </button>
            
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => router.push('/billing')}
                className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-4 py-2 rounded-md text-sm font-medium transition duration-300"
              >
                View Billing
              </button>
              <button
                onClick={() => router.push('/')}
                className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-4 py-2 rounded-md text-sm font-medium transition duration-300"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Need help getting started? Contact our support team at{' '}
            <a href="mailto:pete@cyberiad.ai" className="text-blue-600 hover:text-blue-500">
              pete@cyberiad.ai
            </a>{' '}
            or call <a href="tel:+16179971844" className="text-blue-600 hover:text-blue-500">(617) 997-1844</a>
          </p>
        </div>
      </div>
    </div>
  )
}