// frontend/src/app/layout.tsx
import './globals.css'
import React from 'react'
import { AuthProvider } from '@/contexts/AuthContext'
import { ToastProvider } from '@/components/ui/use-toast'
import MainLayout from '@/components/MainLayout'

export const metadata = {
  title: 'Thanotopolis',
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
          <ToastProvider>
            <MainLayout>
              {children}
            </MainLayout>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
