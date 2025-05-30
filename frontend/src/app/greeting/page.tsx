// frontend/src/app/greeting/page.tsx
'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'

export default function Profile() {
  const { user, organization } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!user) {
      router.push('/login')
    }
  }, [user, router])

  if (!user) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="bg-gray-100 py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back to Conversations link */}
        <div className="mb-4">
          <Link
            href="/conversations"
            className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
          >
            <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Conversations
          </Link>
        </div>

        {/* Profile Card */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="text-center">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                Your Profile
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                {getGreeting()}, {user.first_name || user.username}! 👋
              </p>
            </div>

            {/* User Info Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
              <div className="bg-gray-50 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Personal Information</h3>
                <dl className="space-y-2">
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600">Name:</dt>
                    <dd className="text-sm text-gray-900">
                      {user.first_name && user.last_name 
                        ? `${user.first_name} ${user.last_name}` 
                        : user.username}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600">Email:</dt>
                    <dd className="text-sm text-gray-900">{user.email}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600">Username:</dt>
                    <dd className="text-sm text-gray-900">{user.username}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600">Role:</dt>
                    <dd className="text-sm text-gray-900 capitalize">{user.role}</dd>
                  </div>
                </dl>
              </div>

              <div className="bg-gray-50 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Account Status</h3>
                <dl className="space-y-2">
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600">Status:</dt>
                    <dd>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        user.is_active 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600">Verified:</dt>
                    <dd>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        user.is_verified 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {user.is_verified ? 'Verified' : 'Unverified'}
                      </span>
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600">Tenant:</dt>
                    <dd className="text-sm text-gray-900">{organization}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600">Member Since:</dt>
                    <dd className="text-sm text-gray-900">
                      {new Date(user.created_at).toLocaleDateString()}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
              <button className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition duration-300">
                Edit Profile
              </button>
              <button className="px-6 py-2 bg-gray-200 text-gray-800 font-medium rounded-md hover:bg-gray-300 transition duration-300">
                Change Password
              </button>
            </div>

            {/* Info Message */}
            <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-md">
              <p className="text-sm text-blue-800">
                <span className="font-semibold">Note:</span> This is your profile page where you can view and manage your account information. 
                Profile editing features will be added in a future update.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <div className="text-blue-600 mb-3">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h4 className="font-semibold text-gray-900 mb-1">Conversations</h4>
            <p className="text-sm text-gray-600">View your chat history</p>
            <Link href="/conversations" className="mt-2 inline-block text-blue-600 hover:text-blue-700 text-sm font-medium">
              Go to Conversations →
            </Link>
          </div>

          <div className="bg-white rounded-lg shadow p-6 text-center">
            <div className="text-green-600 mb-3">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <h4 className="font-semibold text-gray-900 mb-1">Activity Log</h4>
            <p className="text-sm text-gray-600">Coming soon</p>
          </div>

          <div className="bg-white rounded-lg shadow p-6 text-center">
            <div className="text-purple-600 mb-3">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h4 className="font-semibold text-gray-900 mb-1">Settings</h4>
            <p className="text-sm text-gray-600">Manage preferences</p>
          </div>
        </div>
      </div>
    </div>
  )
}
