'use client'

import React from 'react'
import { usePathname } from 'next/navigation'
import OrganizationNavigation from '@/components/navigation/OrganizationNavigation'
import TelephonySystemInitializer from '@/components/telephony/TelephonySystemInitializer'

interface OrganizationLayoutProps {
  children: React.ReactNode
}

export default function OrganizationLayout({ children }: OrganizationLayoutProps) {
  const pathname = usePathname()
  
  // Don't show navigation on the new organization creation page
  if (pathname === '/organizations/new') {
    return <>{children}</>
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Initialize telephony system */}
      <TelephonySystemInitializer />
      
      <div className="flex">
        {/* Sidebar Navigation */}
        <aside className="w-64 min-h-screen bg-white shadow-sm border-r border-gray-200">
          <div className="p-4">
            <OrganizationNavigation />
          </div>
        </aside>
        
        {/* Main Content */}
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  )
}