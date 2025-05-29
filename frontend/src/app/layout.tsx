import './globals.css'
import React from 'react'
import { AuthProvider } from '@/contexts/AuthContext'
import MainLayout from '@/components/MainLayout'

export const metadata = {
  title: 'Thanatopolis',
  description: 'Manage your afterlife affairs',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <MainLayout>
            {children}
          </MainLayout>
        </AuthProvider>
      </body>
    </html>
  )
}