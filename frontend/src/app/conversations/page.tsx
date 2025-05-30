// frontend/src/app/conversations/page.tsx
'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  last_message?: {
    content: string
    created_at: string
  }
  participant_count: number
  agent_count: number
}

export default function Conversations() {
  const { user, tokens, organization } = useAuth()
  const router = useRouter()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) {
      router.push('/login')
      return
    }

    fetchConversations()
  }, [user, router])

  const fetchConversations = async () => {
    if (!tokens || !organization) return

    try {
      const response = await fetch('/api/conversations', {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization
        }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch conversations')
      }

      const data = await response.json()
      // Sort by created_at in reverse chronological order (newest first)
      const sortedData = data.sort((a: Conversation, b: Conversation) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
      setConversations(sortedData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations')
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    
    return date.toLocaleDateString()
  }

  const truncateMessage = (message: string, maxLength: number = 100) => {
    if (message.length <= maxLength) return message
    return message.substring(0, maxLength) + '...'
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="bg-gray-50 min-h-[calc(100vh-8rem)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Conversations</h1>
              <p className="mt-1 text-sm text-gray-600">
                Your conversations with AI agents
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/greeting"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                My Profile
              </Link>
              <Link
                href="/conversations/new"
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition duration-300 flex items-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Conversation
              </Link>
            </div>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : error ? (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        ) : conversations.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No conversations</h3>
            <p className="mt-1 text-sm text-gray-500">Get started by creating a new conversation.</p>
            <div className="mt-6">
              <Link
                href="/conversations/new"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Conversation
              </Link>
            </div>
          </div>
        ) : (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {conversations.map((conversation) => (
                <li key={conversation.id}>
                  <Link
                    href={`/conversations/${conversation.id}`}
                    className="block hover:bg-gray-50 px-4 py-4 sm:px-6 transition duration-150"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-blue-600 truncate">
                            {conversation.title || 'Untitled Conversation'}
                          </p>
                          <div className="ml-2 flex-shrink-0 flex">
                            <p className="text-sm text-gray-500">
                              {formatDate(conversation.updated_at || conversation.created_at)}
                            </p>
                          </div>
                        </div>
                        {conversation.last_message && (
                          <p className="mt-1 text-sm text-gray-600">
                            {truncateMessage(conversation.last_message.content)}
                          </p>
                        )}
                        <div className="mt-2 flex items-center text-sm text-gray-500">
                          <svg className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                          </svg>
                          <span>{conversation.participant_count || 1} participant{(conversation.participant_count || 1) !== 1 ? 's' : ''}</span>
                          {conversation.agent_count > 0 && (
                            <>
                              <span className="mx-1">•</span>
                              <svg className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                              </svg>
                              <span>{conversation.agent_count} agent{conversation.agent_count !== 1 ? 's' : ''}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <div className="ml-5 flex-shrink-0">
                        <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
