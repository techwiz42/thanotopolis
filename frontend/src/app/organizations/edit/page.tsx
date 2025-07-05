'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface OrganizationData {
  id: string
  name: string
  subdomain: string
  description?: string
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  address?: string
  city?: string
  state?: string
  country?: string
  postal_code?: string
  created_at: string
  updated_at: string
}

export default function EditOrganization() {
  const { user, tokens, organization } = useAuth()
  const router = useRouter()
  const [formData, setFormData] = useState<OrganizationData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Allow all authenticated users to edit their organization
  useEffect(() => {
    if (user && !user.tenant_id) {
      router.push('/conversations')
      return
    }
  }, [user, router])

  // Fetch current organization data
  useEffect(() => {
    const fetchOrganizationData = async () => {
      if (!tokens?.access_token || !organization || !user) {
        setIsLoading(false)
        return
      }

      try {
        // Get the current user's organization
        const response = await fetch(`/api/organizations/current`, {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`,
            'X-Tenant-ID': organization,
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          throw new Error('Failed to fetch organization data')
        }

        const orgData = await response.json()
        
        // Transform backend data to frontend format
        const transformedData: OrganizationData = {
          id: orgData.id,
          name: orgData.name,
          subdomain: orgData.subdomain,
          description: orgData.description,
          contact_name: orgData.full_name || '',
          contact_email: orgData.organization_email || '',
          contact_phone: orgData.phone || '',
          // Extract address fields from the address object
          address: orgData.address?.street || '',
          city: orgData.address?.city || '',
          state: orgData.address?.state || '',
          country: orgData.address?.country || 'US',
          postal_code: orgData.address?.postal_code || '',
          created_at: orgData.created_at,
          updated_at: orgData.updated_at
        }
        
        setFormData(transformedData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load organization data')
      } finally {
        setIsLoading(false)
      }
    }

    fetchOrganizationData()
  }, [tokens, organization, user])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    if (!formData) return
    
    setFormData(prev => prev ? {
      ...prev,
      [e.target.name]: e.target.value
    } : null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData || !tokens?.access_token || !organization) return

    setError('')
    setSuccess('')
    setIsSubmitting(true)

    try {
      const { id, created_at, updated_at, subdomain, ...baseData } = formData
      
      // Transform address fields into a single object
      const addressObject = baseData.address ? {
        street: baseData.address,
        city: baseData.city,
        state: baseData.state,
        postal_code: baseData.postal_code,
        country: baseData.country
      } : undefined
      
      // Remove individual address fields and add the combined object
      const { address, city, state, postal_code, country, ...otherData } = baseData
      
      // Map frontend fields to backend fields
      const updateData = {
        ...otherData,
        ...(addressObject && { address: addressObject }),
        ...(baseData.contact_name && { full_name: baseData.contact_name }),
        ...(baseData.contact_email && { organization_email: baseData.contact_email }),
        ...(baseData.contact_phone && { phone: baseData.contact_phone })
      }
      
      // Update the current organization
      const response = await fetch(`/api/organizations/current`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update organization')
      }

      const updatedOrg = await response.json()
      
      // Transform backend response to frontend format
      const transformedData: OrganizationData = {
        id: updatedOrg.id,
        name: updatedOrg.name,
        subdomain: updatedOrg.subdomain,
        description: updatedOrg.description,
        contact_name: updatedOrg.full_name || '',
        contact_email: updatedOrg.organization_email || '',
        contact_phone: updatedOrg.phone || '',
        // Extract address fields from the address object
        address: updatedOrg.address?.street || '',
        city: updatedOrg.address?.city || '',
        state: updatedOrg.address?.state || '',
        country: updatedOrg.address?.country || 'US',
        postal_code: updatedOrg.address?.postal_code || '',
        created_at: updatedOrg.created_at,
        updated_at: updatedOrg.updated_at
      }
      
      setFormData(transformedData)
      setSuccess('Organization updated successfully!')
      
      // Redirect to admin page after 2 seconds
      setTimeout(() => {
        router.push('/organizations/admin')
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update organization')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Early return for non-admin users
  if (!user) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Edit Organization</h1>
        <div>Loading user data...</div>
      </div>
    )
  }

  if (!user.tenant_id) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Edit Organization</h1>
        <div>You must be a member of an organization to edit its settings.</div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Edit Organization</h1>
        <div>Loading organization data...</div>
      </div>
    )
  }

  if (!formData) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Edit Organization</h1>
        <div className="text-red-600">Failed to load organization data.</div>
        <Button onClick={() => router.push('/organizations/admin')} className="mt-4">
          Back to Admin
        </Button>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Edit Organization</h1>
        <div className="flex gap-2">
          <Button 
            onClick={() => router.push('/organizations/members')}
            variant="outline"
          >
            Manage Members
          </Button>
          <Button 
            onClick={() => router.push('/organizations/admin')}
            variant="outline"
          >
            Back to Admin
          </Button>
        </div>
      </div>

      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {success && (
            <div className="rounded-md bg-green-50 p-4">
              <p className="text-sm text-green-800">{success}</p>
            </div>
          )}

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
              />
            </div>

            <div>
              <label htmlFor="subdomain" className="block text-sm font-medium text-gray-700">
                Subdomain (Read Only)
              </label>
              <div className="mt-1 flex rounded-md shadow-sm">
                <input
                  id="subdomain"
                  name="subdomain"
                  type="text"
                  disabled
                  className="flex-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-500 bg-gray-50 rounded-l-md focus:outline-none sm:text-sm"
                  value={formData.subdomain}
                />
                <span className="inline-flex items-center px-3 rounded-r-md border border-l-0 border-gray-300 bg-gray-50 text-gray-500 sm:text-sm">
                  .thanotopolis.com
                </span>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Subdomain cannot be changed after creation
              </p>
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                Additional instructions for agent
              </label>
              <textarea
                id="description"
                name="description"
                rows={10}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                value={formData.description || ''}
                onChange={handleChange}
                placeholder="Additional instructions for the AI agent when handling calls and conversations"
              />
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
                value={formData.contact_name || ''}
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
                  value={formData.contact_email || ''}
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
                  value={formData.contact_phone || ''}
                  onChange={handleChange}
                  placeholder="+1 (555) 123-4567"
                />
              </div>
            </div>
          </div>

          {/* Address Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900 border-b pb-2">Address</h3>
            
            <div>
              <label htmlFor="address" className="block text-sm font-medium text-gray-700">
                Street Address
              </label>
              <input
                id="address"
                name="address"
                type="text"
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                value={formData.address || ''}
                onChange={handleChange}
                placeholder="123 Main Street"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label htmlFor="city" className="block text-sm font-medium text-gray-700">
                  City
                </label>
                <input
                  id="city"
                  name="city"
                  type="text"
                  className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.city || ''}
                  onChange={handleChange}
                  placeholder="New York"
                />
              </div>

              <div>
                <label htmlFor="state" className="block text-sm font-medium text-gray-700">
                  State/Province
                </label>
                <input
                  id="state"
                  name="state"
                  type="text"
                  className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.state || ''}
                  onChange={handleChange}
                  placeholder="NY"
                />
              </div>

              <div>
                <label htmlFor="postal_code" className="block text-sm font-medium text-gray-700">
                  Postal Code
                </label>
                <input
                  id="postal_code"
                  name="postal_code"
                  type="text"
                  className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  value={formData.postal_code || ''}
                  onChange={handleChange}
                  placeholder="10001"
                />
              </div>
            </div>

            <div>
              <label htmlFor="country" className="block text-sm font-medium text-gray-700">
                Country
              </label>
              <select
                id="country"
                name="country"
                className="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={formData.country || 'US'}
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

          {/* Organization Metadata */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900 border-b pb-2">Information</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
              <div>
                <span className="font-medium">Created:</span> {new Date(formData.created_at).toLocaleDateString()}
              </div>
              <div>
                <span className="font-medium">Last Updated:</span> {new Date(formData.updated_at).toLocaleDateString()}
              </div>
            </div>
          </div>

          <div className="flex justify-end space-x-4">
            <Button
              type="button"
              onClick={() => router.push('/organizations/admin')}
              variant="outline"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isSubmitting ? 'Updating...' : 'Update Organization'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}