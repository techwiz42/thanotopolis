// frontend/src/app/layout.tsx
import './globals.css'
import React from 'react'
import { AuthProvider } from '@/contexts/AuthContext'
import MainLayout from '@/components/MainLayout'
import { ToastProvider } from '@/components/ui/use-toast'
import ChunkErrorBoundary from '@/components/common/ChunkErrorBoundary'
import '@/utils/chunkErrorHandler'

export const metadata = {
  title: 'Thanotopolis',
  description: 'Manage your afterlife affairs',
  icons: {
    icon: '/favicon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <ChunkErrorBoundary>
          <AuthProvider>
            <ToastProvider>
              <MainLayout>
                {children}
              </MainLayout>
            </ToastProvider>
          </AuthProvider>
        </ChunkErrorBoundary>
      </body>
    </html>
  )
}
