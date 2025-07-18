'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import SuperAdminBilling from './SuperAdminBilling';
import SubscriptionPlans from './SubscriptionPlans';
// import { format } from 'date-fns';

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

interface BillingDashboard {
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

const BillingDashboard: React.FC = () => {
  const { tokens, organization, user } = useAuth();
  const [dashboard, setDashboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [reactivating, setReactivating] = useState(false);

  useEffect(() => {
    if (tokens?.access_token && organization) {
      fetchBillingDashboard();
    }
  }, [tokens, organization]);

  const fetchBillingDashboard = async () => {
    if (!tokens?.access_token || !organization) return;
    
    try {
      setLoading(true);
      const response = await fetch('/api/billing/dashboard', {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch billing dashboard');
      }

      const data = await response.json();
      setDashboard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!tokens?.access_token || !organization) return;
    
    setCancelling(true);
    try {
      const response = await fetch('/api/billing/cancel-subscription', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to cancel subscription');
      }

      const result = await response.json();
      alert(result.message);
      await fetchBillingDashboard(); // Refresh data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel subscription');
    } finally {
      setCancelling(false);
    }
  };

  const handleReactivateSubscription = async () => {
    if (!tokens?.access_token || !organization) return;
    
    setReactivating(true);
    try {
      const response = await fetch('/api/billing/reactivate-subscription', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'X-Tenant-ID': organization,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to reactivate subscription');
      }

      const result = await response.json();
      alert(result.message);
      await fetchBillingDashboard(); // Refresh data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reactivate subscription');
    } finally {
      setReactivating(false);
    }
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(cents / 100);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'text-green-600';
      case 'past_due':
        return 'text-red-600';
      case 'canceled':
        return 'text-gray-600';
      case 'paid':
        return 'text-green-600';
      case 'open':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-lg">Loading billing information...</div>
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

  if (!dashboard) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-600">No billing information available</div>
      </div>
    );
  }

  // Check if this is super admin view
  if (dashboard.view_type === 'super_admin') {
    return <SuperAdminBilling data={dashboard} onRefresh={fetchBillingDashboard} />;
  }

  // Check if this is a demo account
  if (dashboard.is_demo) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Billing Dashboard</h1>
          <Button onClick={fetchBillingDashboard} variant="outline">
            Refresh
          </Button>
        </div>

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
              <p className="text-gray-600 mb-4">{dashboard.demo_message}</p>
              <p className="text-sm text-gray-500">
                This account has full access to all platform features without any billing charges.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Billing Dashboard</h1>
        <Button onClick={fetchBillingDashboard} variant="outline">
          Refresh
        </Button>
      </div>

      {/* Current Subscription */}
      <Card>
        <CardHeader>
          <CardTitle>Current Subscription</CardTitle>
          <CardDescription>Your monthly subscription details</CardDescription>
        </CardHeader>
        <CardContent>
          {dashboard.current_subscription ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="font-medium">Status:</span>
                <span className={`capitalize ${getStatusColor(dashboard.current_subscription.status)}`}>
                  {dashboard.current_subscription.status}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-medium">Monthly Cost:</span>
                <span className="text-lg font-semibold">
                  {formatCurrency(dashboard.current_subscription.amount_cents)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-medium">Current Period:</span>
                <span>
                  {formatDate(dashboard.current_subscription.current_period_start)} - {' '}
                  {formatDate(dashboard.current_subscription.current_period_end)}
                </span>
              </div>
              {dashboard.current_subscription.cancel_at_period_end && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-yellow-800 text-sm">
                    Your subscription will be cancelled at the end of the current period.
                  </p>
                </div>
              )}
              
              {/* Subscription Management Buttons */}
              <div className="flex gap-3 pt-4 border-t">
                {dashboard.current_subscription.cancel_at_period_end ? (
                  <Button 
                    onClick={handleReactivateSubscription}
                    disabled={reactivating}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {reactivating ? 'Reactivating...' : 'Reactivate Subscription'}
                  </Button>
                ) : (
                  <Button 
                    onClick={handleCancelSubscription}
                    disabled={cancelling}
                    variant="outline"
                    className="border-red-300 text-red-700 hover:bg-red-50"
                  >
                    {cancelling ? 'Cancelling...' : 'Cancel Subscription'}
                  </Button>
                )}
                
                <Button 
                  variant="outline"
                  onClick={() => {
                    const portalUrl = `/api/billing/customer-portal?return_url=${encodeURIComponent(window.location.href)}`;
                    window.open(portalUrl, '_blank', 'noopener,noreferrer');
                  }}
                >
                  Manage Payment Methods
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">No active subscription found</p>
              <div className="mt-6">
                <SubscriptionPlans onSubscriptionStarted={fetchBillingDashboard} />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Current Usage */}
      <Card>
        <CardHeader>
          <CardTitle>Current Period Usage</CardTitle>
          <CardDescription>
            Usage for {formatDate(dashboard.current_period_usage.start_date)} - {' '}
            {formatDate(dashboard.current_period_usage.end_date)}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {dashboard.current_period_usage.total_stt_words.toLocaleString()}
              </div>
              <div className="text-sm text-blue-600">STT Words Used</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {dashboard.current_period_usage.total_tts_words.toLocaleString()}
              </div>
              <div className="text-sm text-green-600">TTS Words Used</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">
                {dashboard.upcoming_charges.call_count}
              </div>
              <div className="text-sm text-yellow-600">Phone Calls</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {formatCurrency(dashboard.upcoming_charges.total_charges_cents)}
              </div>
              <div className="text-sm text-purple-600">Total Charges</div>
            </div>
          </div>
          
          <div className="mt-4 space-y-2">
            <div className="p-3 bg-gray-50 rounded-md">
              <p className="text-sm text-gray-600">
                <strong>Voice Usage:</strong> $1.00 per 1,000 words (STT + TTS) • {' '}
                {dashboard.upcoming_charges.voice_words_count.toLocaleString()} words = {' '}
                {formatCurrency(dashboard.upcoming_charges.voice_usage_cents)}
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-md">
              <p className="text-sm text-gray-600">
                <strong>Phone Calls:</strong> $1.00 base + word charges per call • {' '}
                {dashboard.upcoming_charges.call_count} calls = {' '}
                {formatCurrency(dashboard.upcoming_charges.call_charges_cents)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Invoices */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Invoices</CardTitle>
          <CardDescription>Your billing history</CardDescription>
        </CardHeader>
        <CardContent>
          {dashboard.recent_invoices.length > 0 ? (
            <div className="space-y-4">
              {dashboard.recent_invoices.map((invoice: StripeInvoice) => (
                <div key={invoice.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="space-y-1">
                    <div className="font-medium">
                      {formatDate(invoice.period_start)} - {formatDate(invoice.period_end)}
                    </div>
                    <div className="text-sm text-gray-600">
                      {invoice.voice_words_count.toLocaleString()} voice words
                    </div>
                    <div className={`text-sm capitalize ${getStatusColor(invoice.status)}`}>
                      {invoice.status}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">{formatCurrency(invoice.amount_due_cents)}</div>
                    {invoice.paid_at && (
                      <div className="text-sm text-gray-600">
                        Paid {formatDate(invoice.paid_at)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-600">
              No invoices found
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default BillingDashboard;