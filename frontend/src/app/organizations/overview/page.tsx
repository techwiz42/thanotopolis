'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useRouter } from 'next/navigation'
import { Building2, Users, MessageSquare, UserCheck, Phone, Calendar, TrendingUp } from 'lucide-react'

interface OrganizationStats {
  total_users: number
  total_conversations: number
  total_contacts: number
  total_calls: number
  recent_activity: Array<{
    id: string
    type: 'conversation' | 'contact' | 'call'
    description: string
    timestamp: string
  }>
}

export default function OrganizationOverviewPage() {
  const { user, organization, tokens } = useAuth()
  const router = useRouter()
  const [stats, setStats] = useState<OrganizationStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Check if user has admin access
  const hasAdminAccess = user?.role === 'admin' || user?.role === 'super_admin'

  useEffect(() => {
    const fetchStats = async () => {
      if (!tokens?.access_token || !organization || !hasAdminAccess) return

      try {
        setLoading(true)
        const response = await fetch('/api/organizations/stats', {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`,
            'X-Tenant-ID': organization,
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          throw new Error('Failed to fetch organization statistics')
        }

        const data = await response.json()
        setStats(data)
      } catch (err) {
        console.error('Error fetching organization stats:', err)
        setError(err instanceof Error ? err.message : 'Failed to load statistics')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [tokens, organization, hasAdminAccess])

  if (!hasAdminAccess) {
    return (
      <div className="p-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h1>
          <p className="text-gray-600 mb-4">
            You need admin privileges to access the organization overview.
          </p>
          <Button onClick={() => router.push('/organizations')}>
            Back to Organizations
          </Button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Organization Overview</h1>
          <div className="text-red-600 mb-4">Error: {error}</div>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    )
  }

  const statCards = [
    {
      title: 'Total Users',
      value: stats?.total_users || 0,
      icon: Users,
      color: 'bg-blue-500',
      href: '/organizations/members'
    },
    {
      title: 'Conversations',
      value: stats?.total_conversations || 0,
      icon: MessageSquare,
      color: 'bg-green-500',
      href: '/conversations'
    },
    {
      title: 'Contacts',
      value: stats?.total_contacts || 0,
      icon: UserCheck,
      color: 'bg-purple-500',
      href: '/organizations/crm'
    },
    {
      title: 'Phone Calls',
      value: stats?.total_calls || 0,
      icon: Phone,
      color: 'bg-orange-500',
      href: '/organizations/telephony/calls'
    }
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <Building2 className="h-6 w-6 mr-2" />
            Organization Overview
          </h1>
          <p className="text-gray-600 mt-1">
            Welcome to your organization dashboard
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={() => router.push('/organizations/edit')}
            variant="outline"
          >
            Edit Organization
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((card) => (
          <Card key={card.title} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => router.push(card.href)}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{card.title}</p>
                  <p className="text-2xl font-bold text-gray-900">{card.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${card.color}`}>
                  <card.icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <MessageSquare className="h-5 w-5 mr-2" />
              Start a Conversation
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">
              Chat with AI agents or start a new conversation
            </p>
            <Button onClick={() => router.push('/conversations')} className="w-full">
              Go to Conversations
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <UserCheck className="h-5 w-5 mr-2" />
              Manage Contacts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">
              Add new contacts or manage existing customer relationships
            </p>
            <Button onClick={() => router.push('/organizations/crm')} className="w-full">
              Open CRM
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Phone className="h-5 w-5 mr-2" />
              Call History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">
              Review past phone calls and transcripts
            </p>
            <Button onClick={() => router.push('/organizations/telephony/calls')} className="w-full">
              View Call History
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      {stats?.recent_activity && stats.recent_activity.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <TrendingUp className="h-5 w-5 mr-2" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.recent_activity.slice(0, 5).map((activity) => (
                <div key={activity.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    {activity.type === 'conversation' && <MessageSquare className="h-4 w-4 mr-3 text-green-600" />}
                    {activity.type === 'contact' && <UserCheck className="h-4 w-4 mr-3 text-purple-600" />}
                    {activity.type === 'call' && <Phone className="h-4 w-4 mr-3 text-orange-600" />}
                    <span className="text-sm font-medium">{activity.description}</span>
                  </div>
                  <div className="flex items-center text-xs text-gray-500">
                    <Calendar className="h-3 w-3 mr-1" />
                    {new Date(activity.timestamp).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}