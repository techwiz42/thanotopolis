// frontend/src/components/MainLayout.tsx
'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import WingedSolarIcon from './WingedSolarIcon'

interface MainLayoutProps {
  children: React.ReactNode
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { user, organization, logout } = useAuth()
  const pathname = usePathname()

  // Determine if we're on a public page
  const isPublicPage = ['/', '/login', '/register', '/organizations/new'].includes(pathname)

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header/Navigation */}
      <header className="bg-slate-600 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo/Brand */}
            <div className="flex items-center">
              <Link href="/" className="flex items-center">
                <WingedSolarIcon className="w-8 h-4 text-yellow-400 mr-2" />
                <h1 className="text-xl font-semibold text-gray-100">Thanotopolis</h1>
              </Link>
              {user && organization && (
                <span className="ml-4 text-sm text-gray-300 hidden sm:block">
                  Organization: {organization}
                </span>
              )}
            </div>

            {/* Navigation */}
            <nav className="flex items-center space-x-4">
              {user ? (
                // Authenticated Navigation
                <>
                  <Link 
                    href="/greeting" 
                    className="text-gray-200 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Dashboard
                  </Link>
                  {pathname !== '/conversations' && (
                    <Link 
                      href="/conversations" 
                      className="text-gray-200 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                    >
                      My Conversations
                    </Link>
                  )}
                  <Link 
                    href="/organizations" 
                    className="text-gray-200 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Organization
                  </Link>
                  {user.role === 'super_admin' && (
                    <Link 
                      href="/admin/organizations" 
                      className="text-gray-200 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                    >
                      All Organizations
                    </Link>
                  )}
                  {(user.role === 'admin' || user.role === 'super_admin') && (
                    <Link 
                      href="/billing" 
                      className="text-gray-200 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                    >
                      Billing
                    </Link>
                  )}
                  <span className="text-gray-200 text-sm hidden sm:block">{user.email}</span>
                  <button
                    onClick={logout}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium transition duration-300"
                  >
                    Logout
                  </button>
                </>
              ) : (
                // Public Navigation
                <>
                  {pathname !== '/' && (
                    <Link
                      href="/"
                      className="text-gray-200 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                    >
                      Home
                    </Link>
                  )}
                  <Link
                    href="/organizations/new"
                    className="text-gray-200 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Create Organization
                  </Link>
                  {pathname !== '/login' && (
                    <Link
                      href="/login"
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition duration-300"
                    >
                      Sign In
                    </Link>
                  )}
                  {pathname !== '/register' && (
                    <Link
                      href="/register"
                      className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium transition duration-300"
                    >
                      Register
                    </Link>
                  )}
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row justify-between items-center">
            <p className="text-sm text-gray-600">
              &copy; 2025 Thanotopolis. All rights reserved.
            </p>
            <div className="flex space-x-6 mt-2 sm:mt-0">
              <Link href="/privacy" className="text-sm text-blue-600 hover:text-blue-800 underline">Privacy Policy</Link>
              <Link href="/terms" className="text-sm text-blue-600 hover:text-blue-800 underline">Terms of Service</Link>
              <a href="https://github.com/anthropics/claude-code/issues" target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:text-blue-800 underline">Report Issue</a>
              <a href={`mailto:pete@cyberiad.ai${user ? `?from=${encodeURIComponent(user.email)}` : ''}`} className="text-sm text-blue-600 hover:text-blue-800 underline">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default MainLayout
