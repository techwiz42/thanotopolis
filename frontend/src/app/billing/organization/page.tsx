'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface StripeSubscription {
  id: string;
  stripe_subscription_id: string;
  stripe_price_id: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  amount_cents: number;
  currency: string;
  created_at: string;
}

interface StripeInvoice {
  id: string;
  stripe_invoice_id: string;
  status: string;
  amount_due_cents: number;
  amount_paid_cents: number;
  currency: string;
  period_start: string;
  period_end: string;
  voice_words_count: number;
  voice_usage_cents: number;
  created_at: string;
  due_date?: string;
  paid_at?: string;
}

interface UsageStats {
  period: string;
  start_date: string;
  end_date: string;
  total_tokens: number;
  total_tts_words: number;
  total_stt_words: number;
  total_cost_cents: number;
}

interface OrganizationBilling {
  organization_id: string;
  organization_name: string;
  subdomain: string;
  is_demo?: boolean;
  demo_message?: string;
  current_subscription?: StripeSubscription;
  recent_invoices: StripeInvoice[];
  current_period_usage?: UsageStats;
  upcoming_charges: {
    voice_usage_cents: number;
    voice_words_count: number;
    call_count: number;
    call_charges_cents: number;
    total_charges_cents: number;
  };
}

const OrganizationBillingPage: React.FC = () => {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { tokens, user } = useAuth();
  const [billing, setBilling] = useState<OrganizationBilling | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const orgId = searchParams?.get('id') as string;

  useEffect(() => {
    if (tokens?.access_token && orgId && user?.role === 'super_admin') {
      fetchOrganizationBilling();
    } else if (user && user.role !== 'super_admin') {
      // Redirect non-super admins to regular billing
      router.push('/billing');
    }
  }, [tokens, orgId, user, router]);

  const fetchOrganizationBilling = async () => {
    if (!tokens?.access_token || !orgId) return;
    
    try {
      setLoading(true);
      const response = await fetch(`/api/admin/organizations/${orgId}/billing`, {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch organization billing');
      }

      const data = await response.json();
      setBilling(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (cents: number): string => {
    return `$${(cents / 100).toFixed(2)}`;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-red-600">Error: {error}</div>
      </div>
    );
  }

  if (!billing) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-600">No billing information available</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Billing Dashboard</h1>
            <p className="text-gray-600 mt-1">
              {billing.organization_name} ({billing.subdomain})
            </p>
          </div>
          <div className="flex space-x-2">
            <Button 
              onClick={() => router.push('/admin/organizations')} 
              variant="outline"
            >
              Back to Organizations
            </Button>
            <Button onClick={fetchOrganizationBilling} variant="outline">
              Refresh
            </Button>
          </div>
        </div>

        {/* Demo Account Notice */}
        {billing.is_demo && (
          <Card>
            <CardHeader>
              <CardTitle>Demo Account</CardTitle>
              <CardDescription>This account is exempt from billing charges</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 mb-4">
                  <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Demo Account</h3>
                <p className="text-gray-600 mb-4">{billing.demo_message}</p>
                <p className="text-sm text-gray-500">
                  This account has full access to all platform features without any billing charges.
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Current Usage & Charges */}
        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Current Period Usage</CardTitle>
              <CardDescription>Usage for the current billing period</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {billing.current_period_usage ? (
                <>
                  <div className="flex justify-between">
                    <span>Text-to-Speech Words:</span>
                    <span className="font-medium">{billing.current_period_usage.total_tts_words.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Speech-to-Text Words:</span>
                    <span className="font-medium">{billing.current_period_usage.total_stt_words.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Phone Calls:</span>
                    <span className="font-medium">{billing.upcoming_charges.call_count}</span>
                  </div>
                  <div className="border-t pt-4 flex justify-between font-semibold">
                    <span>Total Usage Cost:</span>
                    <span>{formatCurrency(billing.current_period_usage.total_cost_cents)}</span>
                  </div>
                </>
              ) : (
                <p className="text-gray-500">No usage data available</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Upcoming Charges</CardTitle>
              <CardDescription>Estimated charges for current period</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between">
                <span>Voice Usage:</span>
                <span className="font-medium">{formatCurrency(billing.upcoming_charges.voice_usage_cents)}</span>
              </div>
              <div className="flex justify-between">
                <span>Phone Calls:</span>
                <span className="font-medium">{formatCurrency(billing.upcoming_charges.call_charges_cents)}</span>
              </div>
              <div className="border-t pt-4 flex justify-between font-semibold">
                <span>Total Estimated:</span>
                <span>{formatCurrency(billing.upcoming_charges.total_charges_cents)}</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Subscription Status */}
        {billing.current_subscription && (
          <Card>
            <CardHeader>
              <CardTitle>Subscription Status</CardTitle>
              <CardDescription>Current subscription details</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className={`font-medium ${
                      billing.current_subscription.status === 'active' ? 'text-green-600' : 'text-yellow-600'
                    }`}>
                      {billing.current_subscription.status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Amount:</span>
                    <span className="font-medium">{formatCurrency(billing.current_subscription.amount_cents)}</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Current Period:</span>
                    <span className="font-medium">
                      {formatDate(billing.current_subscription.current_period_start)} - {formatDate(billing.current_subscription.current_period_end)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cancel at Period End:</span>
                    <span className="font-medium">
                      {billing.current_subscription.cancel_at_period_end ? 'Yes' : 'No'}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recent Invoices */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Invoices</CardTitle>
            <CardDescription>Payment history and invoice details</CardDescription>
          </CardHeader>
          <CardContent>
            {billing.recent_invoices.length > 0 ? (
              <div className="space-y-4">
                {billing.recent_invoices.map((invoice) => (
                  <div key={invoice.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium">Invoice #{invoice.stripe_invoice_id}</p>
                        <p className="text-sm text-gray-600">
                          Period: {formatDate(invoice.period_start)} - {formatDate(invoice.period_end)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{formatCurrency(invoice.amount_due_cents)}</p>
                        <p className={`text-sm ${
                          invoice.status === 'paid' ? 'text-green-600' : 'text-yellow-600'
                        }`}>
                          {invoice.status}
                        </p>
                      </div>
                    </div>
                    {invoice.voice_words_count && (
                      <div className="mt-2 text-sm text-gray-600">
                        Voice usage: {invoice.voice_words_count.toLocaleString()} words ({formatCurrency(invoice.voice_usage_cents || 0)})
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No invoices found</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default function BillingPageWrapper() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <OrganizationBillingPage />
    </Suspense>
  );
}