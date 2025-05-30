// frontend/src/app/conversations/[id]/page.tsx
'use client'

import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

export default function ConversationDetail({ params }: { params: { id: string } }) {
  const { user } = useAuth()
  const router = useRouter()

  if (!user) {
    router.push('/login')
    return null
  }

  return (
    <div className="bg-gray-50 min-h-[calc(100vh-8rem)]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/conversations"
            className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
          >
            <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Conversations
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-gray-900">Conversation</h1>
          <p className="mt-1 text-sm text-gray-600">
            ID: {params.id}
          </p>
        </div>

        {/* Chat Interface Placeholder */}
        <div className="bg-white shadow rounded-lg">
          {/* Messages Area */}
          <div className="p-6 space-y-4 min-h-[400px]">
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">Conversation View</h3>
              <p className="mt-1 text-sm text-gray-500">
                This is where the conversation messages would appear.
              </p>
            </div>
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 px-4 py-4">
            <div className="flex space-x-4">
              <input
                type="text"
                className="flex-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Type your message..."
                disabled
              />
              <button
                type="button"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                disabled
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Placeholder message */}
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-800">
            <span className="font-semibold">Note:</span> This is a dummy page for demonstration purposes. 
            In the production version, this would display the full conversation history with messages from 
            users and AI agents, and allow you to continue the conversation.
          </p>
        </div>
      </div>
    </div>
  )
}
