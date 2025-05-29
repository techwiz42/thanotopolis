// frontend/src/components/MainLayout.tsx
'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

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
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo/Brand */}
            <div className="flex items-center">
              <Link href="/" className="flex items-center">
                <svg className="w-8 h-8 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <h1 className="text-xl font-semibold text-gray-900">Thanotopolis</h1>
              </Link>
              {user && organization && (
                <span className="ml-4 text-sm text-gray-500 hidden sm:block">
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
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Dashboard
                  </Link>
                  <span className="text-gray-700 text-sm hidden sm:block">{user.email}</span>
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
                      className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                    >
                      Home
                    </Link>
                  )}
                  <Link
                    href="/organizations/new"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
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
              <a href="#" className="text-sm text-gray-500 hover:text-gray-700">Privacy Policy</a>
              <a href="#" className="text-sm text-gray-500 hover:text-gray-700">Terms of Service</a>
              <a href="#" className="text-sm text-gray-500 hover:text-gray-700">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default MainLayout
