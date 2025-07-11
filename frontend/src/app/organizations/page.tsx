'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

export default function OrganizationsPage() {
  const router = useRouter()
  const { user } = useAuth()

  useEffect(() => {
    if (user) {
      if (user.role === 'admin' || user.role === 'super_admin') {
        // Admin users see the overview page with stats
        router.push('/organizations/overview')
      } else {
        // Non-admin users stay on the base organization page
        // This page will show basic organization info without admin stats
      }
    }
  }, [user, router])

  // Show basic organization info for non-admin users
  if (user && user.role !== 'admin' && user.role !== 'super_admin') {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Organization</h1>
            <p className="text-gray-600 mt-1">
              Welcome to your organization dashboard
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-3">Conversations</h3>
            <p className="text-gray-600 mb-4">
              Chat with AI agents and access your conversation history
            </p>
            <button 
              onClick={() => router.push('/conversations')}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Open Conversations
            </button>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-3">Call History</h3>
            <p className="text-gray-600 mb-4">
              View your phone call history and transcripts
            </p>
            <button 
              onClick={() => router.push('/organizations/telephony/calls')}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              View Call History
            </button>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-3">CRM</h3>
            <p className="text-gray-600 mb-4">
              Access customer relationship management tools
            </p>
            <button 
              onClick={() => router.push('/organizations/crm')}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Open CRM
            </button>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-3">Calendar</h3>
            <p className="text-gray-600 mb-4">
              Schedule appointments and manage events
            </p>
            <button 
              onClick={() => router.push('/organizations/calendar')}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Open Calendar
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Loading state for admin users while redirecting
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  )
}