'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function BillingSignup() {
  const [organizationData, setOrganizationData] = useState<any>(null)
  const [isCreatingCheckout, setIsCreatingCheckout] = useState(false)
  const [error, setError] = useState('')
  const router = useRouter()

  useEffect(() => {
    // Retrieve organization data from sessionStorage
    const pendingOrgData = sessionStorage.getItem('pendingOrganization')
    if (pendingOrgData) {
      setOrganizationData(JSON.parse(pendingOrgData))
    } else {
      // If no pending organization data, redirect back to creation form
      router.push('/organizations/new')
    }
  }, [router])

  const handleStartSubscription = async () => {
    if (!organizationData) return
    
    setIsCreatingCheckout(true)
    setError('')

    try {
      // Create checkout session for new organization signup
      const response = await fetch('/api/billing/organization-signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          success_url: `${window.location.origin}/billing/success`,
          cancel_url: `${window.location.origin}/billing/signup`,
          trial_days: 0,
          customer_email: organizationData.organization_email || 'noreply@example.com',
          organization_name: organizationData.name
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create checkout session')
      }

      const { checkout_url } = await response.json()
      
      // Redirect to Stripe Checkout
      window.location.href = checkout_url
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start subscription process')
    } finally {
      setIsCreatingCheckout(false)
    }
  }

  if (!organizationData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 min-h-[calc(100vh-8rem)]">
      <div className="max-w-2xl w-full space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900">
            Complete Your Organization Setup
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Choose your subscription plan to activate your organization
          </p>
        </div>

        {/* Organization Summary */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Organization Summary</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-700">Organization Name:</span>
              <span className="text-sm text-gray-900">{organizationData.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-700">Subdomain:</span>
              <span className="text-sm text-gray-900">{organizationData.subdomain}.thanotopolis.com</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-700">Contact Email:</span>
              <span className="text-sm text-gray-900">{organizationData.organization_email || 'Not provided'}</span>
            </div>
          </div>
        </div>

        {/* Subscription Plan */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="text-center">
            <h3 className="text-xl font-semibold text-gray-900">Thanotopolis Platform</h3>
            <div className="mt-4">
              <span className="text-4xl font-bold text-gray-900">$299</span>
              <span className="text-lg text-gray-600">/month</span>
            </div>
            
            <div className="mt-6 space-y-3 text-left">
              <h4 className="font-medium text-gray-900">What's included:</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Complete multi-agent platform access
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Web chat interface with AI agents
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Full telephony system integration
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Custom agent instructions
                </li>
                <li className="flex items-center">
                  <svg className="h-4 w-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Unlimited team members
                </li>
              </ul>
            </div>

          </div>
        </div>

        {/* Usage-based pricing info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h4 className="font-medium text-blue-900 mb-3">Usage-Based Pricing</h4>
          <div className="space-y-2 text-sm text-blue-800">
            <div className="flex justify-between">
              <span>Voice Usage (STT/TTS):</span>
              <span className="font-medium">$1.00 per 1,000 words</span>
            </div>
            <div className="flex justify-between">
              <span>Phone Calls:</span>
              <span className="font-medium">$1.00 per call + voice usage</span>
            </div>
          </div>
          <p className="mt-3 text-xs text-blue-700">
            Usage charges are billed monthly based on actual consumption. Most organizations use 2,000-5,000 words per month.
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <button
            onClick={handleStartSubscription}
            disabled={isCreatingCheckout}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
{isCreatingCheckout ? 'Preparing checkout...' : 'Subscribe Now'}
          </button>

          <button
            onClick={() => router.push('/organizations/new')}
            className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            ← Back to Organization Details
          </button>
        </div>

        <div className="text-center">
          <p className="text-xs text-gray-500">
            By continuing, you agree to our Terms of Service and Privacy Policy. 
            You can cancel your subscription anytime from your billing dashboard.
          </p>
        </div>
      </div>
    </div>
  )
}