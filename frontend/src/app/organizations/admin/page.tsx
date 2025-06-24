'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useRouter } from 'next/navigation'

interface UsageStats {
  period: string
  start_date: string
  end_date: string
  total_tokens: number
  total_tts_words: number
  total_stt_words: number
  total_cost_cents: number
}

interface SystemMetric {
  id: string
  metric_type: string
  value: number
  additional_data: any
  created_at: string
}

interface TenantStat {
  tenant_id: string
  name: string
  subdomain: string
  user_count: number
  conversation_count: number
}

interface OrganizationUsage {
  tenant_id: string
  tenant_name: string
  subdomain: string
  total_tokens: number
  total_tts_words: number
  total_stt_words: number
  total_cost_cents: number
  record_count: number
}

interface AdminDashboard {
  total_users: number
  total_conversations: number
  active_ws_connections: number
  db_connection_pool_size: number
  recent_usage: any[]
  system_metrics: SystemMetric[]
  tenant_stats: TenantStat[]
  overall_usage_stats?: UsageStats
  usage_by_organization?: OrganizationUsage[]
}

const AdminMonitoringPage = () => {
  const { user, tokens, organization } = useAuth()
  const router = useRouter()
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null)
  const [isGeneratingToken, setIsGeneratingToken] = useState(false)
  const [tokenMessage, setTokenMessage] = useState('')
  const [generatedToken, setGeneratedToken] = useState('')

  const fetchDashboardData = useCallback(async () => {
    if (!tokens?.access_token || !organization) return

    try {
      const headers = {
        'Authorization': `Bearer ${tokens.access_token}`,
        'X-Tenant-ID': organization,
        'Content-Type': 'application/json'
      }

      // Fetch dashboard data
      const dashboardResponse = await fetch('/api/admin/dashboard', { headers })
      if (!dashboardResponse.ok) throw new Error('Failed to fetch dashboard data')
      const dashboardData = await dashboardResponse.json()
      setDashboard(dashboardData)

      // Fetch usage stats
      const usageResponse = await fetch('/api/admin/usage/stats?period=month', { headers })
      if (!usageResponse.ok) throw new Error('Failed to fetch usage stats')
      const usageData = await usageResponse.json()
      setUsageStats(usageData)

      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }, [tokens, organization])

  const generateNewToken = async () => {
    if (!tokens?.access_token || !organization) return

    setIsGeneratingToken(true)
    setTokenMessage('')
    setGeneratedToken('')

    try {
      const response = await fetch('/api/organizations/current/regenerate-access-code', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to generate new token')
      }

      const updatedOrg = await response.json()
      setGeneratedToken(updatedOrg.access_code)
      setTokenMessage('New access token generated successfully! Share this with new members.')

      // Clear the token display after 30 seconds for security
      setTimeout(() => {
        setGeneratedToken('')
        setTokenMessage('')
      }, 30000)

    } catch (err) {
      setTokenMessage(err instanceof Error ? err.message : 'Failed to generate new token')
    } finally {
      setIsGeneratingToken(false)
    }
  }

  // Check admin access
  useEffect(() => {
    if (user && user.role !== 'admin' && user.role !== 'super_admin') {
      router.push('/conversations')
      return
    }
  }, [user, router])

  useEffect(() => {
    fetchDashboardData()
    
    // Set up auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000)
    setRefreshInterval(interval)

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [tokens, organization, fetchDashboardData])

  // Early return for non-admin users to prevent flash
  if (!user) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Admin Monitoring Dashboard</h1>
        <div>Loading user data...</div>
      </div>
    )
  }

  if (user.role !== 'admin' && user.role !== 'super_admin') {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Admin Monitoring Dashboard</h1>
        <div>Redirecting...</div>
      </div>
    )
  }

  const formatBytes = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`
  }

  const formatWords = (words: number) => {
    if (words >= 1000000) {
      return `${(words / 1000000).toFixed(1)}M words`
    } else if (words >= 1000) {
      return `${(words / 1000).toFixed(1)}K words`
    } else {
      return `${words} words`
    }
  }

  const formatCost = (cents: number) => {
    return `$${(cents / 100).toFixed(2)}`
  }


  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Admin Monitoring Dashboard</h1>
        <div>Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Admin Monitoring Dashboard</h1>
        <div className="text-red-600">Error: {error}</div>
        <Button onClick={fetchDashboardData} className="mt-4">Retry</Button>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Admin Monitoring Dashboard</h1>
        <div className="flex gap-2">
          <Button 
            onClick={() => router.push('/organizations/edit')}
            variant="outline"
          >
            Edit Organization
          </Button>
          <Button 
            onClick={generateNewToken}
            disabled={isGeneratingToken}
            variant="outline"
          >
            {isGeneratingToken ? 'Generating...' : 'Generate Token'}
          </Button>
          <Button onClick={fetchDashboardData}>Refresh</Button>
        </div>
      </div>

      {/* Token Generation Results */}
      {(tokenMessage || generatedToken) && (
        <Card className="p-4">
          <div className="space-y-3">
            {tokenMessage && (
              <p className={`text-sm ${generatedToken ? 'text-green-600' : 'text-red-600'}`}>
                {tokenMessage}
              </p>
            )}
            {generatedToken && (
              <div className="bg-gray-100 p-3 rounded-md">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-1">New Access Token:</h3>
                    <code className="text-lg font-mono text-blue-600 select-all">{generatedToken}</code>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(generatedToken)
                      setTokenMessage('Token copied to clipboard!')
                    }}
                  >
                    Copy
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  ⚠️ This token will be hidden after 30 seconds for security. Copy it now!
                </p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <h3 className="font-semibold text-sm text-gray-600 mb-2">Total Users</h3>
          <p className="text-2xl font-bold">{dashboard?.total_users || 0}</p>
        </Card>
        
        <Card className="p-4">
          <h3 className="font-semibold text-sm text-gray-600 mb-2">Total Conversations</h3>
          <p className="text-2xl font-bold">{dashboard?.total_conversations || 0}</p>
        </Card>
        
        <Card className="p-4">
          <h3 className="font-semibold text-sm text-gray-600 mb-2">Active WebSocket Connections</h3>
          <p className="text-2xl font-bold">{dashboard?.active_ws_connections || 0}</p>
        </Card>
        
        <Card className="p-4">
          <h3 className="font-semibold text-sm text-gray-600 mb-2">DB Connection Pool</h3>
          <p className="text-2xl font-bold">{dashboard?.db_connection_pool_size || 0}</p>
        </Card>
      </div>

      {/* Usage Statistics */}
      {usageStats && (
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">Usage Statistics (Last Month)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <h3 className="font-semibold text-sm text-gray-600 mb-1">Total Tokens</h3>
              <p className="text-lg font-bold">{usageStats.total_tokens.toLocaleString()}</p>
            </div>
            
            <div>
              <h3 className="font-semibold text-sm text-gray-600 mb-1">TTS Usage</h3>
              <p className="text-lg font-bold">{formatWords(usageStats.total_tts_words)}</p>
            </div>
            
            <div>
              <h3 className="font-semibold text-sm text-gray-600 mb-1">STT Usage</h3>
              <p className="text-lg font-bold">{formatWords(usageStats.total_stt_words)}</p>
            </div>
            
            <div>
              <h3 className="font-semibold text-sm text-gray-600 mb-1">Total Cost</h3>
              <p className="text-lg font-bold">{formatCost(usageStats.total_cost_cents)}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Organization Usage Statistics - Only show for super_admin or current org */}
      {dashboard?.usage_by_organization && dashboard.usage_by_organization.length > 0 && (
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">
            {user?.role === 'super_admin' ? 'Usage by Organization (Last Month)' : 'Organization Usage (Last Month)'}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Organization</th>
                  <th className="text-left py-2">Subdomain</th>
                  <th className="text-right py-2">Tokens</th>
                  <th className="text-right py-2">TTS Words</th>
                  <th className="text-right py-2">STT Words</th>
                  <th className="text-right py-2">Cost</th>
                </tr>
              </thead>
              <tbody>
                {(dashboard?.usage_by_organization && Array.isArray(dashboard.usage_by_organization) 
                  ? dashboard.usage_by_organization.filter(org => user?.role === 'super_admin' || org.tenant_id === user?.tenant_id) 
                  : [])
                  .map((org) => (
                    <tr key={org.tenant_id} className="border-b">
                      <td className="py-2">{org.tenant_name}</td>
                      <td className="py-2 text-gray-600">{org.subdomain}</td>
                      <td className="py-2 text-right">{org.total_tokens.toLocaleString()}</td>
                      <td className="py-2 text-right">{formatWords(org.total_tts_words)}</td>
                      <td className="py-2 text-right">{formatWords(org.total_stt_words)}</td>
                      <td className="py-2 text-right">{formatCost(org.total_cost_cents)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Tenant Statistics - Only show for super_admin or current org */}
      {dashboard?.tenant_stats && dashboard.tenant_stats.length > 0 && (
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">
            {user?.role === 'super_admin' ? 'Tenant Statistics' : 'Organization Statistics'}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Organization</th>
                  <th className="text-left py-2">Subdomain</th>
                  <th className="text-right py-2">Users</th>
                  <th className="text-right py-2">Conversations</th>
                </tr>
              </thead>
              <tbody>
                {(dashboard?.tenant_stats && Array.isArray(dashboard.tenant_stats) 
                  ? dashboard.tenant_stats.filter(tenant => user?.role === 'super_admin' || tenant.tenant_id === user?.tenant_id) 
                  : [])
                  .map((tenant) => (
                    <tr key={tenant.tenant_id} className="border-b">
                      <td className="py-2">{tenant.name}</td>
                      <td className="py-2 text-gray-600">{tenant.subdomain}</td>
                      <td className="py-2 text-right">{tenant.user_count}</td>
                      <td className="py-2 text-right">{tenant.conversation_count}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* System Metrics */}
      {dashboard?.system_metrics && dashboard.system_metrics.length > 0 && (
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">Recent System Metrics</h2>
          <div className="space-y-2">
            {(dashboard?.system_metrics && Array.isArray(dashboard.system_metrics) ? dashboard.system_metrics : []).slice(0, 10).map((metric) => (
              <div key={metric.id} className="flex justify-between items-center py-2 border-b last:border-b-0">
                <div>
                  <span className="font-medium">{metric.metric_type}</span>
                  <span className="text-sm text-gray-500 ml-2">
                    {new Date(metric.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="text-right">
                  <span className="font-bold">{metric.value}</span>
                  {metric.metric_type.includes('usage') && <span className="text-sm text-gray-500">%</span>}
                  {metric.metric_type.includes('connections') && <span className="text-sm text-gray-500"> conn</span>}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

export default AdminMonitoringPage