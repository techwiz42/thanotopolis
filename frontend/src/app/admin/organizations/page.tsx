'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface TelephonyConfig {
  business_phone_number?: string
  platform_phone_number?: string
  call_forwarding_number?: string
}

interface Organization {
  id: string
  name: string
  subdomain: string
  description?: string
  full_name?: string
  phone?: string
  organization_email?: string
  is_active: boolean
  is_demo: boolean
  created_at: string
  updated_at: string
  user_count?: number
  agent_instructions?: string
  telephony_config?: TelephonyConfig
}

export default function OrganizationManagement() {
  const { user, tokens, switchOrganization } = useAuth()
  const router = useRouter()
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedInstructions, setExpandedInstructions] = useState<Set<string>>(new Set())

  // Check if user is super admin
  useEffect(() => {
    if (user && user.role !== 'super_admin') {
      router.push('/conversations')
      return
    }
  }, [user, router])

  // Helper functions
  const toggleInstructionsExpanded = (orgId: string) => {
    setExpandedInstructions(prev => {
      const newSet = new Set(prev)
      if (newSet.has(orgId)) {
        newSet.delete(orgId)
      } else {
        newSet.add(orgId)
      }
      return newSet
    })
  }

  const truncateText = (text: string, maxLength: number = 150) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  // Fetch all organizations with enhanced data
  useEffect(() => {
    const fetchOrganizations = async () => {
      if (!tokens?.access_token || !user || user.role !== 'super_admin') {
        setIsLoading(false)
        return
      }

      try {
        // Fetch organizations with enhanced data
        const [orgsResponse, agentsResponse, telephonyResponse] = await Promise.all([
          fetch('/api/admin/organizations', {
            headers: {
              'Authorization': `Bearer ${tokens.access_token}`,
              'Content-Type': 'application/json',
            },
          }),
          fetch('/api/admin/agents', {
            headers: {
              'Authorization': `Bearer ${tokens.access_token}`,
              'Content-Type': 'application/json',
            },
          }).catch(() => null),
          fetch('/api/admin/telephony', {
            headers: {
              'Authorization': `Bearer ${tokens.access_token}`,
              'Content-Type': 'application/json',
            },
          }).catch(() => null)
        ])

        if (orgsResponse.ok) {
          const orgsData = await orgsResponse.json()
          
          // Enhance organizations with agent and telephony data
          const enhancedOrgs = await Promise.all(orgsData.map(async (org: Organization) => {
            const enhanced = { ...org }
            
            // Try to get agent instructions for this org
            try {
              const agentResponse = await fetch(`/api/admin/organizations/${org.id}/agent`, {
                headers: {
                  'Authorization': `Bearer ${tokens.access_token}`,
                  'Content-Type': 'application/json',
                },
              })
              if (agentResponse.ok) {
                const agentData = await agentResponse.json()
                enhanced.agent_instructions = agentData.instructions || agentData.system_prompt
              }
            } catch (err) {
              console.log(`No agent data for ${org.name}`)
            }
            
            // Try to get telephony config for this org
            try {
              const telResponse = await fetch(`/api/admin/organizations/${org.id}/telephony`, {
                headers: {
                  'Authorization': `Bearer ${tokens.access_token}`,
                  'Content-Type': 'application/json',
                },
              })
              if (telResponse.ok) {
                const telData = await telResponse.json()
                enhanced.telephony_config = telData
              }
            } catch (err) {
              console.log(`No telephony data for ${org.name}`)
            }
            
            return enhanced
          }))
          
          setOrganizations(enhancedOrgs)
        } else {
          const errorData = await orgsResponse.text()
          setError(`Failed to fetch organizations: ${errorData}`)
        }
      } catch (err) {
        console.error('Error fetching organizations:', err)
        setError('Failed to fetch organizations')
      } finally {
        setIsLoading(false)
      }
    }

    fetchOrganizations()
  }, [tokens, user])

  const handleSwitchToOrganization = async (org: Organization) => {
    try {
      if (switchOrganization) {
        await switchOrganization(org.id)
        router.push('/conversations')
      }
    } catch (err) {
      console.error('Error switching organization:', err)
      setError('Failed to switch to organization')
    }
  }

  const toggleOrganizationStatus = async (orgId: string, currentStatus: boolean) => {
    if (!tokens?.access_token) return

    try {
      const response = await fetch(`/api/admin/organizations/${orgId}/toggle-status`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        setOrganizations(orgs => 
          orgs.map(org => 
            org.id === orgId ? { ...org, is_active: !currentStatus } : org
          )
        )
      } else {
        const errorData = await response.text()
        setError(`Failed to update organization status: ${errorData}`)
      }
    } catch (err) {
      console.error('Error toggling organization status:', err)
      setError('Failed to update organization status')
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading organizations...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="md:flex md:items-center md:justify-between mb-8">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
              Organization Management
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              Manage all organizations in the system
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <ul className="divide-y divide-gray-200">
            {organizations.map((org) => (
              <li key={org.id}>
                <div className="px-4 py-6 sm:px-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center">
                        <h3 className="text-lg font-medium text-gray-900 truncate">
                          {org.name}
                        </h3>
                        {org.is_demo && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Demo
                          </span>
                        )}
                        {!org.is_active && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            Inactive
                          </span>
                        )}
                      </div>
                      <div className="mt-2 flex items-center text-sm text-gray-500">
                        <span>Subdomain: {org.subdomain}</span>
                        {org.organization_email && (
                          <span className="ml-4">Email: {org.organization_email}</span>
                        )}
                        {org.phone && (
                          <span className="ml-4">Phone: {org.phone}</span>
                        )}
                      </div>
                      {org.description && (
                        <p className="mt-2 text-sm text-gray-600">{org.description}</p>
                      )}
                      
                      {/* Agent Instructions */}
                      {org.agent_instructions && (
                        <div className="mt-3">
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Agent Instructions:</h4>
                          <div className="text-sm text-gray-600">
                            {expandedInstructions.has(org.id) ? (
                              <div>
                                <p className="whitespace-pre-wrap">{org.agent_instructions}</p>
                                <button
                                  onClick={() => toggleInstructionsExpanded(org.id)}
                                  className="mt-1 text-blue-600 hover:text-blue-800 text-xs"
                                >
                                  Show less
                                </button>
                              </div>
                            ) : (
                              <div>
                                <p>{truncateText(org.agent_instructions)}</p>
                                {org.agent_instructions.length > 150 && (
                                  <button
                                    onClick={() => toggleInstructionsExpanded(org.id)}
                                    className="mt-1 text-blue-600 hover:text-blue-800 text-xs"
                                  >
                                    Show more
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {/* Telephony Information */}
                      {org.telephony_config && (
                        <div className="mt-3">
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Telephony:</h4>
                          <div className="text-sm text-gray-600 space-y-1">
                            {org.telephony_config.business_phone_number && (
                              <div>Business: {org.telephony_config.business_phone_number}</div>
                            )}
                            {org.telephony_config.platform_phone_number && (
                              <div>Platform: {org.telephony_config.platform_phone_number}</div>
                            )}
                            {org.telephony_config.call_forwarding_number && (
                              <div>Forwarding: {org.telephony_config.call_forwarding_number}</div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      <div className="mt-2 text-xs text-gray-400">
                        Created: {new Date(org.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-green-600 border-green-600 hover:bg-green-50"
                          onClick={() => {
                            // Navigate to organization-specific billing page
                            router.push(`/billing/organization?id=${org.id}`)
                          }}
                        >
                          Billing
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => toggleOrganizationStatus(org.id, org.is_active)}
                        >
                          {org.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                        <Button
                          onClick={() => handleSwitchToOrganization(org)}
                          className="bg-blue-600 hover:bg-blue-700 text-white"
                          size="sm"
                        >
                          Switch To Org
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {organizations.length === 0 && (
          <Card className="p-6 text-center">
            <p className="text-gray-500">No organizations found.</p>
          </Card>
        )}
      </div>
    </div>
  )
}