
// frontend/src/app/organizations/new/page.tsx
'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function NewOrganization() {
  const [formData, setFormData] = useState({
    name: '',
    subdomain: '',
    description: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    address: '',
    city: '',
    state: '',
    country: 'US',
    postal_code: ''
  })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const router = useRouter()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
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
      // Transform the form data to match backend schema
      const { address, city, state, country, postal_code, contact_name, contact_email, contact_phone, description, ...baseData } = formData
      
      // Create address object only if address fields are provided
      const addressObject = address ? {
        street: address,
        city: city,
        state: state,
        postal_code: postal_code,
        country: country
      } : undefined
      
      // Map frontend fields to backend fields
      const organizationData = {
        ...baseData,
        ...(addressObject && { address: addressObject }),
        ...(contact_name && { full_name: contact_name }),
        ...(contact_email && { organization_email: contact_email }),
        ...(contact_phone && { phone: contact_phone })
      }
      
      // Store organization data in sessionStorage for payment process
      sessionStorage.setItem('pendingOrganization', JSON.stringify(organizationData))
      
      // Redirect to billing page instead of creating organization immediately
      router.push('/billing/signup')
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to prepare organization data')
    } finally {
      setIsSubmitting(false)
    }
  }


  return (
    <div className="flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 min-h-[calc(100vh-8rem)]">
      <div className="max-w-2xl w-full space-y-8">
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
          <div className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900 border-b pb-2">Basic Information</h3>
              
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                  Organization Name *
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
                  Subdomain *
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

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                  Custom Instructions for Agent
                </label>
                <textarea
                  id="description"
                  name="description"
                  rows={5}
                  className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Example: 'You are a customer service representative for Acme Healthcare. Always introduce yourself as Sarah from Acme Healthcare. Our main services include primary care, cardiology, and telehealth consultations. If customers ask about appointments, direct them to call our scheduling line at (555) 123-4567. Always be professional, empathetic, and helpful. For medical emergencies, immediately direct callers to call 911.'"
                />
                <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-sm text-blue-800">
                    Our team is standing by to help you craft the perfect agent instructions for your organization's specific needs. This is a free service included with your subscription to Thanotopolis.com 
                    <br />
                    <span className="font-medium">Contact us at pete@cyberiad.ai or (617) 997-1844 for personalized agent setup assistance.</span>
                  </p>
                </div>
              </div>
            </div>


            {/* Contact Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900 border-b pb-2">Contact Information</h3>
              
              <div>
                <label htmlFor="contact_name" className="block text-sm font-medium text-gray-700">
                  Contact Name
                </label>
                <input
                  id="contact_name"
                  name="contact_name"
                  type="text"
                  className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.contact_name}
                  onChange={handleChange}
                  placeholder="John Doe"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="contact_email" className="block text-sm font-medium text-gray-700">
                    Contact Email
                  </label>
                  <input
                    id="contact_email"
                    name="contact_email"
                    type="email"
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                    value={formData.contact_email}
                    onChange={handleChange}
                    placeholder="contact@example.com"
                  />
                </div>

                <div>
                  <label htmlFor="contact_phone" className="block text-sm font-medium text-gray-700">
                    Contact Phone
                  </label>
                  <input
                    id="contact_phone"
                    name="contact_phone"
                    type="tel"
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                    value={formData.contact_phone}
                    onChange={handleChange}
                    placeholder="+1 (555) 123-4567"
                  />
                </div>
              </div>
            </div>

            {/* Address Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900 border-b pb-2">Address *</h3>
              
              <div>
                <label htmlFor="address" className="block text-sm font-medium text-gray-700">
                  Street Address *
                </label>
                <input
                  id="address"
                  name="address"
                  type="text"
                  required
                  className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.address}
                  onChange={handleChange}
                  placeholder="123 Main Street"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="city" className="block text-sm font-medium text-gray-700">
                    City *
                  </label>
                  <input
                    id="city"
                    name="city"
                    type="text"
                    required
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                    value={formData.city}
                    onChange={handleChange}
                    placeholder="New York"
                  />
                </div>

                <div>
                  <label htmlFor="state" className="block text-sm font-medium text-gray-700">
                    State/Province *
                  </label>
                  <input
                    id="state"
                    name="state"
                    type="text"
                    required
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                    value={formData.state}
                    onChange={handleChange}
                    placeholder="NY"
                  />
                </div>

                <div>
                  <label htmlFor="postal_code" className="block text-sm font-medium text-gray-700">
                    Postal Code *
                  </label>
                  <input
                    id="postal_code"
                    name="postal_code"
                    type="text"
                    required
                    className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                    value={formData.postal_code}
                    onChange={handleChange}
                    placeholder="10001"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="country" className="block text-sm font-medium text-gray-700">
                  Country *
                </label>
                <select
                  id="country"
                  name="country"
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={formData.country}
                  onChange={handleChange}
                >
                  <option value="US">United States</option>
                  <option value="CA">Canada</option>
                  <option value="GB">United Kingdom</option>
                  <option value="AU">Australia</option>
                  <option value="DE">Germany</option>
                  <option value="FR">France</option>
                  <option value="IN">India</option>
                  <option value="JP">Japan</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Preparing billing...' : 'Continue to Billing'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
