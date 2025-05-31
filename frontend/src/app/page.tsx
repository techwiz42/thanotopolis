'use client'

import Link from 'next/link'
import WingedSolarIcon from '@/components/WingedSolarIcon'

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl w-full text-center space-y-8">
        <div className="flex justify-center">
          <WingedSolarIcon width={150} height={75} className="text-yellow-500" />
        </div>
        
        <h1 className="text-5xl font-extrabold text-gray-900 tracking-tight">
          Thanotopolis
        </h1>
        
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6">
          <Link 
            href="/login"
            className="px-8 py-3 rounded-md bg-green-600 text-white font-medium hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
          >
            Login
          </Link>
          
          <Link 
            href="/register"
            className="px-8 py-3 rounded-md bg-blue-600 text-white font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Register User
          </Link>
          
          <Link 
            href="/organizations/new"
            className="px-8 py-3 rounded-md bg-gray-200 text-gray-900 font-medium hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors"
          >
            Create Organization
          </Link>
        </div>
      </div>
    </div>
  )
}