'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { 
  Mail, 
  ArrowLeft, 
  BarChart,
  Eye,
  MousePointer,
  Send,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  Search,
  Calendar,
  Filter,
  UserMinus
} from 'lucide-react'

interface EmailCampaign {
  id: string
  name: string
  subject: string
  status: 'draft' | 'sending' | 'sent' | 'partial'
  recipient_count: number
  sent_count: number
  opened_count: number
  clicked_count: number
  bounced_count: number
  unsubscribed_count: number
  created_at: string
  sent_at?: string
  open_rate: number
  click_rate: number
}

interface CampaignsResponse {
  campaigns: EmailCampaign[]
  total: number
  skip: number
  limit: number
}

export default function CampaignsPage() {
  const { token, user, organization, isLoading } = useAuth()
  const router = useRouter()
  
  const [campaigns, setCampaigns] = useState<EmailCampaign[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCampaigns, setTotalCampaigns] = useState(0)
  const [pageSize] = useState(10)
  
  // Aggregate statistics
  const [totalStats, setTotalStats] = useState({
    totalCampaigns: 0,
    totalSent: 0,
    avgOpenRate: 0,
    avgClickRate: 0
  })

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
    }
  }, [user, isLoading, router])

  useEffect(() => {
    const fetchCampaigns = async () => {
      if (!token || !organization) return
      
      setLoading(true)
      try {
        const params = new URLSearchParams({
          skip: ((currentPage - 1) * pageSize).toString(),
          limit: pageSize.toString()
        })
        
        if (searchTerm) {
          params.append('search', searchTerm)
        }
        
        console.log('Fetching campaigns with:', {
          url: `/api/crm/email-campaigns?${params}`,
          user: user?.email,
          role: user?.role,
          organization: organization
        })
        
        const response = await fetch(`/api/crm/email-campaigns?${params}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-ID': organization,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const data: CampaignsResponse = await response.json()
          setCampaigns(data.campaigns)
          setTotalCampaigns(data.total)
          
          // Calculate aggregate stats
          if (data.campaigns.length > 0) {
            const sentCampaigns = data.campaigns.filter(c => c.sent_count > 0)
            const totalSent = sentCampaigns.reduce((sum, c) => sum + c.sent_count, 0)
            const avgOpenRate = sentCampaigns.length > 0 
              ? sentCampaigns.reduce((sum, c) => sum + c.open_rate, 0) / sentCampaigns.length 
              : 0
            const avgClickRate = sentCampaigns.length > 0 
              ? sentCampaigns.reduce((sum, c) => sum + c.click_rate, 0) / sentCampaigns.length 
              : 0
            
            setTotalStats({
              totalCampaigns: data.total,
              totalSent,
              avgOpenRate: Math.round(avgOpenRate * 10) / 10,
              avgClickRate: Math.round(avgClickRate * 10) / 10
            })
          }
        } else {
          console.error('Failed to fetch campaigns', response.status, response.statusText)
          const errorData = await response.text()
          console.error('Response body:', errorData)
        }
      } catch (error) {
        console.error('Error fetching campaigns:', error)
      } finally {
        setLoading(false)
      }
    }

    if (token && organization) {
      fetchCampaigns()
    }
  }, [token, organization, currentPage, searchTerm])

  if (isLoading) {
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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const totalPages = Math.ceil(totalCampaigns / pageSize)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button variant="outline" onClick={() => router.push('/organizations/crm')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to CRM
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                <Mail className="h-8 w-8 mr-3 text-blue-600" />
                Email Campaigns
              </h1>
              <p className="text-gray-600 mt-1">
                Track and analyze your email campaign performance
              </p>
            </div>
          </div>
          <Button onClick={() => router.push('/organizations/crm/bulk-email')}>
            <Send className="h-4 w-4 mr-2" />
            New Campaign
          </Button>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Campaigns</p>
                  <p className="text-2xl font-bold">{totalStats.totalCampaigns}</p>
                </div>
                <Mail className="h-8 w-8 text-blue-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Emails Sent</p>
                  <p className="text-2xl font-bold">{totalStats.totalSent.toLocaleString()}</p>
                </div>
                <Send className="h-8 w-8 text-green-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Avg Open Rate</p>
                  <p className="text-2xl font-bold">{totalStats.avgOpenRate}%</p>
                </div>
                <Eye className="h-8 w-8 text-purple-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Avg Click Rate</p>
                  <p className="text-2xl font-bold">{totalStats.avgClickRate}%</p>
                </div>
                <MousePointer className="h-8 w-8 text-orange-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search and Filters */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search campaigns by name or subject..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value)
                    setCurrentPage(1)
                  }}
                  className="pl-10"
                />
              </div>
              <Button variant="outline" disabled>
                <Filter className="h-4 w-4 mr-2" />
                Filters
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Campaigns List */}
        <Card>
          <CardHeader>
            <CardTitle>All Campaigns</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-pulse">Loading campaigns...</div>
              </div>
            ) : campaigns.length === 0 ? (
              <div className="text-center py-8">
                <Mail className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Campaigns Yet</h3>
                <p className="text-gray-600 mb-4">Create your first email campaign to see analytics here.</p>
                <Button onClick={() => router.push('/organizations/crm/bulk-email')}>
                  Create Campaign
                </Button>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b">
                      <tr>
                        <th className="text-left p-3 font-medium text-gray-700">Campaign</th>
                        <th className="text-left p-3 font-medium text-gray-700">Status</th>
                        <th className="text-center p-3 font-medium text-gray-700">Recipients</th>
                        <th className="text-center p-3 font-medium text-gray-700">Sent</th>
                        <th className="text-center p-3 font-medium text-gray-700">Open Rate</th>
                        <th className="text-center p-3 font-medium text-gray-700">Click Rate</th>
                        <th className="text-center p-3 font-medium text-gray-700">Unsubscribed</th>
                        <th className="text-left p-3 font-medium text-gray-700">Date</th>
                        <th className="text-center p-3 font-medium text-gray-700">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {campaigns.map((campaign) => (
                        <tr key={campaign.id} className="hover:bg-gray-50">
                          <td className="p-3">
                            <div>
                              <p className="font-medium text-gray-900">{campaign.name}</p>
                              <p className="text-sm text-gray-600 truncate max-w-xs">{campaign.subject}</p>
                            </div>
                          </td>
                          <td className="p-3">
                            {getStatusBadge(campaign.status)}
                          </td>
                          <td className="p-3 text-center">
                            <span className="text-gray-900">{campaign.recipient_count}</span>
                          </td>
                          <td className="p-3 text-center">
                            <span className="text-gray-900">{campaign.sent_count}</span>
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              <Eye className="h-4 w-4 text-gray-400" />
                              <span className={campaign.open_rate > 25 ? 'text-green-600 font-medium' : 'text-gray-900'}>
                                {campaign.open_rate}%
                              </span>
                            </div>
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              <MousePointer className="h-4 w-4 text-gray-400" />
                              <span className={campaign.click_rate > 5 ? 'text-green-600 font-medium' : 'text-gray-900'}>
                                {campaign.click_rate}%
                              </span>
                            </div>
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              <UserMinus className="h-4 w-4 text-gray-400" />
                              <span className={campaign.unsubscribed_count > 0 ? 'text-red-600 font-medium' : 'text-gray-900'}>
                                {campaign.unsubscribed_count || 0}
                              </span>
                            </div>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1 text-sm text-gray-600">
                              <Calendar className="h-3 w-3" />
                              {formatDate(campaign.sent_at || campaign.created_at)}
                            </div>
                          </td>
                          <td className="p-3 text-center">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => router.push(`/organizations/crm/campaigns/${campaign.id}`)}
                            >
                              <BarChart className="h-4 w-4 mr-1" />
                              Analytics
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-6 pt-4 border-t">
                    <div className="text-sm text-gray-600">
                      Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalCampaigns)} of {totalCampaigns} campaigns
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage - 1)}
                        disabled={currentPage <= 1}
                      >
                        Previous
                      </Button>
                      
                      <div className="flex items-center gap-1">
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum: number
                          if (totalPages <= 5) {
                            pageNum = i + 1
                          } else if (currentPage <= 3) {
                            pageNum = i + 1
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i
                          } else {
                            pageNum = currentPage - 2 + i
                          }
                          
                          return (
                            <Button
                              key={pageNum}
                              variant={pageNum === currentPage ? "default" : "outline"}
                              size="sm"
                              onClick={() => setCurrentPage(pageNum)}
                              className="w-8 h-8 p-0"
                            >
                              {pageNum}
                            </Button>
                          )
                        })}
                      </div>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage + 1)}
                        disabled={currentPage >= totalPages}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}