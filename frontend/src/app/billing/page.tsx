'use client';

import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import BillingDashboard from '@/components/BillingDashboard';

const BillingPage: React.FC = () => {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-600">Please log in to view billing information.</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <BillingDashboard />
    </div>
  );
};

export default BillingPage;