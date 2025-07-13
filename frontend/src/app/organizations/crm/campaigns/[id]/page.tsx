'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { 
  Mail, 
  ArrowLeft, 
  Eye,
  MousePointer,
  Send,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Users,
  Calendar,
  BarChart3,
  Activity,
  Target,
  AlertCircle,
  ExternalLink
} from 'lucide-react'

interface CampaignAnalytics {
  campaign_id: string
  campaign_name: string
  status: string
  created_at: string
  sent_at?: string
  metrics: {
    total_recipients: number
    sent_count: number
    opened_count: number
    clicked_count: number
    bounced_count: number
    unsubscribed_count: number
    open_rate: number
    click_rate: number
    click_through_rate: number
    bounce_rate: number
    unsubscribe_rate: number
  }
}

interface RecipientDetail {
  recipient_id: string
  email: string
  name?: string
  contact_id?: string
  status: string
  sent_at?: string
  opened_at?: string
  clicked_at?: string
  open_count: number
  click_count: number
  events: Array<{
    event_type: string
    timestamp: string
    user_agent?: string
    ip_address?: string
    url?: string
  }>
}

export default function CampaignAnalyticsPage({ params }: { params: Promise<{ id: string }> }) {
  const { token, user, organization, isLoading } = useAuth()
  const router = useRouter()
  
  const [analytics, setAnalytics] = useState<CampaignAnalytics | null>(null)
  const [recipients, setRecipients] = useState<RecipientDetail[]>([])
  const [loading, setLoading] = useState(true)
  const [recipientsLoading, setRecipientsLoading] = useState(false)
  const [selectedTab, setSelectedTab] = useState<'overview' | 'recipients'>('overview')
  const [error, setError] = useState<string | null>(null)
  const [campaignId, setCampaignId] = useState<string | null>(null)

  useEffect(() => {
    params.then(resolvedParams => {
      setCampaignId(resolvedParams.id)
    })
  }, [params])

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
    }
  }, [user, isLoading, router])

  const fetchAnalytics = async () => {
    if (!token || !organization || !campaignId) return
    
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/api/crm/email-campaigns/${campaignId}/analytics`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Analytics data received:', data)
        console.log('Analytics metrics:', data.metrics)
        
        // Validate the structure
        if (!data) {
          console.error('Empty analytics data received')
          setError('Received empty analytics data')
          return
        }
        
        if (!data.metrics) {
          console.error('Analytics data missing metrics:', data)
          setError('Analytics data is missing metrics information')
          return
        }
        
        setAnalytics(data)
      } else if (response.status === 404) {
        console.error('Campaign not found, redirecting to campaigns list')
        router.push('/organizations/crm/campaigns')
      } else {
        console.error('Failed to fetch analytics:', response.status, response.statusText)
        const errorText = await response.text()
        console.error('Error response:', errorText)
        setError(`Failed to load analytics: ${response.status} ${response.statusText}`)
      }
    } catch (error) {
      console.error('Error fetching analytics:', error)
      setError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (token && organization) {
      fetchAnalytics()
    }
  }, [token, organization, campaignId, router])

  const fetchRecipients = async () => {
    if (!token || !organization || !campaignId) return
    
    setRecipientsLoading(true)
    try {
      // Note: This endpoint would need to be implemented in the backend
      // For now, we'll just show a placeholder
      console.log('Recipients endpoint not yet implemented')
    } catch (error) {
      console.error('Error fetching recipients:', error)
    } finally {
      setRecipientsLoading(false)
    }
  }

  useEffect(() => {
    if (selectedTab === 'recipients' && recipients.length === 0) {
      fetchRecipients()
    }
  }, [selectedTab])

  if (isLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Analytics</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="flex gap-2 justify-center">
            <Button onClick={fetchAnalytics}>
              Try Again
            </Button>
            <Button variant="outline" onClick={() => router.push('/organizations/crm/campaigns')}>
              Back to Campaigns
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (!analytics || !analytics.metrics) {
    console.log('Analytics validation failed:', { analytics, hasMetrics: analytics?.metrics })
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">No Analytics Data</h2>
          <p className="text-gray-600 mb-4">
            {!analytics ? 'No analytics data found' : 'Analytics data missing metrics'}
          </p>
          <div className="flex gap-2 justify-center">
            <Button onClick={fetchAnalytics}>
              Retry
            </Button>
            <Button variant="outline" onClick={() => router.push('/organizations/crm/campaigns')}>
              Back to Campaigns
            </Button>
          </div>
        </div>
      </div>
    )
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      draft: { variant: "secondary" as const, icon: Clock, className: "" },
      sending: { variant: "default" as const, icon: Send, className: "" },
      sent: { variant: "default" as const, icon: CheckCircle, className: "bg-green-500 text-white hover:bg-green-600 border-green-500" },
      partial: { variant: "destructive" as const, icon: XCircle, className: "" }
    }
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.draft
    const Icon = config.icon
    
    return (
      <Badge variant={config.variant} className={cn("flex items-center gap-1", config.className)}>
        <Icon className="h-3 w-3" />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    )
  }

  const MetricCard = ({ 
    title, 
    value, 
    icon: Icon, 
    color, 
    trend, 
    suffix = '' 
  }: { 
    title: string
    value: number | string
    icon: any
    color: string
    trend?: 'up' | 'down' | 'neutral'
    suffix?: string
  }) => {
    const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : null
    
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <Icon className={`h-8 w-8 ${color}`} />
            {TrendIcon && <TrendIcon className={`h-4 w-4 ${trend === 'up' ? 'text-green-500' : 'text-red-500'}`} />}
          </div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-bold mt-1">
            {typeof value === 'number' ? value.toLocaleString() : value}{suffix}
          </p>
        </CardContent>
      </Card>
    )
  }

  const { metrics } = analytics
  
  // Add defensive checks with defaults
  if (!metrics) {
    console.error('Analytics metrics are undefined:', analytics)
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Analytics Data Error</h2>
          <p className="text-gray-600 mb-4">Analytics data is missing metrics information</p>
          <div className="flex gap-2 justify-center">
            <Button onClick={fetchAnalytics}>
              Retry
            </Button>
            <Button variant="outline" onClick={() => router.push('/organizations/crm/campaigns')}>
              Back to Campaigns
            </Button>
          </div>
        </div>
      </div>
    )
  }
  
  // Ensure all metrics have default values
  const safeMetrics = {
    total_recipients: metrics.total_recipients || 0,
    sent_count: metrics.sent_count || 0,
    opened_count: metrics.opened_count || 0,
    clicked_count: metrics.clicked_count || 0,
    bounced_count: metrics.bounced_count || 0,
    unsubscribed_count: metrics.unsubscribed_count || 0,
    open_rate: metrics.open_rate || 0,
    click_rate: metrics.click_rate || 0,
    click_through_rate: metrics.click_through_rate || 0,
    bounce_rate: metrics.bounce_rate || 0,
    unsubscribe_rate: metrics.unsubscribe_rate || 0,
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button variant="outline" onClick={() => router.push('/organizations/crm/campaigns')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Campaigns
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{analytics.campaign_name}</h1>
              <div className="flex items-center gap-3 mt-2">
                {getStatusBadge(analytics.status)}
                <span className="text-gray-600 flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  Sent: {formatDate(analytics.sent_at)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <Button
            variant={selectedTab === 'overview' ? 'default' : 'outline'}
            onClick={() => setSelectedTab('overview')}
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            Overview
          </Button>
          <Button
            variant={selectedTab === 'recipients' ? 'default' : 'outline'}
            onClick={() => setSelectedTab('recipients')}
            disabled
          >
            <Users className="h-4 w-4 mr-2" />
            Recipients
          </Button>
        </div>

        {selectedTab === 'overview' && (
          <>
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <MetricCard
                title="Total Recipients"
                value={safeMetrics.total_recipients}
                icon={Users}
                color="text-blue-500"
              />
              <MetricCard
                title="Successfully Sent"
                value={safeMetrics.sent_count}
                icon={Send}
                color="text-green-500"
              />
              <MetricCard
                title="Total Opens"
                value={safeMetrics.opened_count}
                icon={Eye}
                color="text-purple-500"
              />
              <MetricCard
                title="Total Clicks"
                value={safeMetrics.clicked_count}
                icon={MousePointer}
                color="text-orange-500"
              />
            </div>

            {/* Performance Metrics */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5" />
                    Engagement Rates
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm font-medium">Open Rate</span>
                      <span className="text-sm font-bold">{safeMetrics.open_rate}%</span>
                    </div>
                    <Progress value={safeMetrics.open_rate} className="h-2" />
                    <p className="text-xs text-gray-500 mt-1">
                      Industry average: 21.5%
                    </p>
                  </div>
                  
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm font-medium">Click Rate</span>
                      <span className="text-sm font-bold">{safeMetrics.click_rate}%</span>
                    </div>
                    <Progress value={safeMetrics.click_rate} className="h-2" />
                    <p className="text-xs text-gray-500 mt-1">
                      Industry average: 2.6%
                    </p>
                  </div>
                  
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm font-medium">Click-Through Rate</span>
                      <span className="text-sm font-bold">{safeMetrics.click_through_rate}%</span>
                    </div>
                    <Progress value={safeMetrics.click_through_rate} className="h-2" />
                    <p className="text-xs text-gray-500 mt-1">
                      Clicks as % of opens
                    </p>
                  </div>
                  
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm font-medium">Unsubscribe Rate</span>
                      <span className="text-sm font-bold">{safeMetrics.unsubscribe_rate}%</span>
                    </div>
                    <Progress value={safeMetrics.unsubscribe_rate} className="h-2" />
                    <p className="text-xs text-gray-500 mt-1">
                      Industry average: &lt;0.5%
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-5 w-5" />
                    Campaign Performance
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-5 w-5 text-green-500" />
                        <span className="font-medium">Delivered</span>
                      </div>
                      <span className="font-bold">{safeMetrics.sent_count - safeMetrics.bounced_count}</span>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <Eye className="h-5 w-5 text-purple-500" />
                        <span className="font-medium">Unique Opens</span>
                      </div>
                      <span className="font-bold">{safeMetrics.opened_count}</span>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <MousePointer className="h-5 w-5 text-orange-500" />
                        <span className="font-medium">Unique Clicks</span>
                      </div>
                      <span className="font-bold">{safeMetrics.clicked_count}</span>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <XCircle className="h-5 w-5 text-red-500" />
                        <span className="font-medium">Bounced</span>
                      </div>
                      <span className="font-bold">{safeMetrics.bounced_count}</span>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <ExternalLink className="h-5 w-5 text-yellow-500" />
                        <span className="font-medium">Unsubscribed</span>
                      </div>
                      <span className="font-bold">{safeMetrics.unsubscribed_count}</span>
                    </div>
                  </div>
                  
                  {safeMetrics.bounce_rate > 5 && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5" />
                        <div className="text-sm">
                          <p className="font-medium text-yellow-800">High Bounce Rate</p>
                          <p className="text-yellow-700">
                            Your bounce rate ({safeMetrics.bounce_rate}%) is above the recommended threshold. 
                            Consider cleaning your email list.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {safeMetrics.unsubscribe_rate > 0.5 && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
                        <div className="text-sm">
                          <p className="font-medium text-red-800">High Unsubscribe Rate</p>
                          <p className="text-red-700">
                            Your unsubscribe rate ({safeMetrics.unsubscribe_rate}%) is above the recommended threshold (&lt;0.5%). 
                            Consider reviewing your email frequency and content relevance.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Success Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Campaign Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <CheckCircle className="h-8 w-8 mx-auto text-green-600 mb-2" />
                    <p className="text-lg font-bold text-green-700">
                      {safeMetrics.total_recipients > 0 ? Math.round((safeMetrics.sent_count / safeMetrics.total_recipients) * 100) : 0}%
                    </p>
                    <p className="text-sm text-gray-600">Delivery Rate</p>
                  </div>
                  
                  <div className="text-center p-4 bg-purple-50 rounded-lg">
                    <Activity className="h-8 w-8 mx-auto text-purple-600 mb-2" />
                    <p className="text-lg font-bold text-purple-700">
                      {safeMetrics.open_rate > 20 ? 'Above' : 'Below'} Average
                    </p>
                    <p className="text-sm text-gray-600">Open Performance</p>
                  </div>
                  
                  <div className="text-center p-4 bg-orange-50 rounded-lg">
                    <Target className="h-8 w-8 mx-auto text-orange-600 mb-2" />
                    <p className="text-lg font-bold text-orange-700">
                      {safeMetrics.click_rate > 2.5 ? 'Above' : 'Below'} Average
                    </p>
                    <p className="text-sm text-gray-600">Click Performance</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {selectedTab === 'recipients' && (
          <Card>
            <CardHeader>
              <CardTitle>Recipient Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-600">
                <Users className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p>Recipient details view coming soon</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}