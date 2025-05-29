import React from 'react'
import Link from 'next/link'

export default function Home() {
  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-100 py-16">
      <div className="container mx-auto px-4">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Welcome to Thanatopolis
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Secure, scalable authentication for your organization
          </p>
          
          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/login"
              className="px-8 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition duration-300 shadow-md text-center"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-8 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition duration-300 shadow-md text-center"
            >
              Create Account
            </Link>
          </div>
        </div>

        {/* Main Content Card */}
        <div className="max-w-4xl mx-auto mb-16">
          <div className="bg-white rounded-lg shadow-xl p-8">
            <div className="text-center">
              <h2 className="text-3xl font-semibold text-gray-800 mb-4">
                Enterprise-Ready Authentication
              </h2>
              <p className="text-gray-600">
                Manage multiple tenants with isolated user bases, secure authentication,
                and role-based access control. Perfect for SaaS applications and multi-organization platforms.
              </p>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="max-w-6xl mx-auto">
          <h3 className="text-2xl font-semibold text-center text-gray-800 mb-8">
            Key Features
          </h3>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="text-blue-600 mb-4">
                <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h4 className="text-xl font-semibold mb-2">Secure Authentication</h4>
              <p className="text-gray-600">
                JWT-based authentication with refresh tokens for enhanced security.
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="text-green-600 mb-4">
                <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h4 className="text-xl font-semibold mb-2">Multi-Tenant Support</h4>
              <p className="text-gray-600">
                Isolate user data across different organizations with subdomain-based tenancy.
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="text-purple-600 mb-4">
                <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h4 className="text-xl font-semibold mb-2">Role-Based Access</h4>
              <p className="text-gray-600">
                Control user permissions with flexible role assignments and access levels.
              </p>
            </div>
          </div>
        </div>

        {/* Demo Info */}
        <div className="max-w-2xl mx-auto mt-16 text-center">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-blue-900 mb-2">Demo Credentials</h4>
            <p className="text-blue-800">
              <span className="font-medium">Tenant:</span> demo<br />
              <span className="font-medium">Email:</span> demo@example.com<br />
              <span className="font-medium">Password:</span> demo123
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
