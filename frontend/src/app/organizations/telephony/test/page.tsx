// src/app/organizations/telephony/test/page.tsx
'use client';

import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import TelephonyTestPanel from '@/components/telephony/TelephonyTestPanel';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle } from 'lucide-react';

export default function TelephonyTestPage() {
  const { user } = useAuth();

  // Only allow admin users to access the test panel
  if (user?.role !== 'admin' && user?.role !== 'org_admin' && user?.role !== 'super_admin') {
    return (
      <div className="container mx-auto py-8">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Access denied. This page is only available to administrators.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-7xl">
      <TelephonyTestPanel />
    </div>
  );
}