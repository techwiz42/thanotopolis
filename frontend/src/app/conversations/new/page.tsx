// frontend/src/app/conversations/new/page.tsx
'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

export default function NewConversation() {
  const { user } = useAuth()
  const router = useRouter()
  const [title, setTitle] = useState('')

  if (!user) {
    router.push('/login')
    return null
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Dummy action - in real implementation would create conversation
    alert('This is a dummy page. In production, this would create a new conversation.')
  }

  return (
    <div className="bg-gray-50 min-h-[calc(100vh-8rem)]">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
          <h1 className="mt-2 text-3xl font-bold text-gray-900">New Conversation</h1>
          <p className="mt-1 text-sm text-gray-600">
            Start a new conversation with AI agents
          </p>
        </div>

        {/* Form */}
        <div className="bg-white shadow rounded-lg p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                Conversation Title
              </label>
              <input
                type="text"
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Enter a title for your conversation (optional)"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Agents
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    disabled
                  />
                  <span className="ml-2 text-sm text-gray-700">General Assistant</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    disabled
                  />
                  <span className="ml-2 text-sm text-gray-700">Web Search Agent</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    disabled
                  />
                  <span className="ml-2 text-sm text-gray-700">Regulatory Agent</span>
                </label>
              </div>
            </div>

            <div>
              <label htmlFor="firstMessage" className="block text-sm font-medium text-gray-700">
                First Message (Optional)
              </label>
              <textarea
                id="firstMessage"
                rows={4}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Type your first message to start the conversation..."
                disabled
              />
            </div>

            <div className="pt-5">
              <div className="flex justify-end space-x-3">
                <Link
                  href="/conversations"
                  className="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Cancel
                </Link>
                <button
                  type="submit"
                  className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Create Conversation
                </button>
              </div>
            </div>
          </form>

          {/* Placeholder message */}
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
            <p className="text-sm text-yellow-800">
              <span className="font-semibold">Note:</span> This is a dummy page for demonstration purposes. 
              In the production version, this form would create a new conversation and allow you to select 
              AI agents and start chatting.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
