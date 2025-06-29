'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface Organization {
  organization_id: string;
  organization_name: string;
  subdomain: string;
  subscription: any;
  subscription_revenue_cents: number;
  voice_words_count: number;
  voice_charges_cents: number;
  call_count: number;
  call_charges_cents: number;
  total_charges_cents: number;
  recent_invoices: any[];
  usage_stats: any;
}

interface SuperAdminBillingData {
  view_type: 'super_admin';
  total_organizations: number;
  total_revenue_cents: number;
  total_voice_words: number;
  total_phone_calls: number;
  organizations: Organization[];
  summary: {
    period_start: string;
    period_end: string;
    total_subscription_revenue: number;
    total_voice_revenue: number;
    total_call_revenue: number;
    total_usage_revenue: number;
  };
}

interface SuperAdminBillingProps {
  data: SuperAdminBillingData;
  onRefresh: () => void;
}

const SuperAdminBilling: React.FC<SuperAdminBillingProps> = ({ data, onRefresh }) => {
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Super Admin Billing Dashboard</h1>
        <button 
          onClick={onRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Total Organizations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.total_organizations}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Total Revenue (Month)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(data.total_revenue_cents)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Subscription Revenue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {formatCurrency(data.summary.total_subscription_revenue)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Usage Revenue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">
              {formatCurrency(data.summary.total_usage_revenue)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Period Info */}
      <Card>
        <CardHeader>
          <CardTitle>Billing Period</CardTitle>
          <CardDescription>
            {formatDate(data.summary.period_start)} - {formatDate(data.summary.period_end)}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-lg font-semibold">{data.total_voice_words.toLocaleString()}</div>
              <div className="text-sm text-gray-600">Total Voice Words</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-lg font-semibold">{data.total_phone_calls.toLocaleString()}</div>
              <div className="text-sm text-gray-600">Total Phone Calls</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-lg font-semibold">
                {formatCurrency(data.summary.total_voice_revenue)}
              </div>
              <div className="text-sm text-gray-600">Voice Revenue</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-lg font-semibold">
                {formatCurrency(data.summary.total_call_revenue)}
              </div>
              <div className="text-sm text-gray-600">Call Revenue</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-lg font-semibold">
                {formatCurrency(data.summary.total_usage_revenue)}
              </div>
              <div className="text-sm text-gray-600">Total Usage Revenue</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Organizations Table */}
      <Card>
        <CardHeader>
          <CardTitle>Organizations Billing Breakdown</CardTitle>
          <CardDescription>Revenue and usage by organization</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-2">Organization</th>
                  <th className="text-left py-3 px-2">Subdomain</th>
                  <th className="text-right py-3 px-2">Subscription</th>
                  <th className="text-right py-3 px-2">Voice Words</th>
                  <th className="text-right py-3 px-2">Phone Calls</th>
                  <th className="text-right py-3 px-2">Voice Charges</th>
                  <th className="text-right py-3 px-2">Call Charges</th>
                  <th className="text-right py-3 px-2">Total Revenue</th>
                  <th className="text-center py-3 px-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.organizations.map((org) => (
                  <tr key={org.organization_id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-2 font-medium">{org.organization_name}</td>
                    <td className="py-3 px-2 text-gray-600">{org.subdomain}</td>
                    <td className="py-3 px-2 text-right">
                      {formatCurrency(org.subscription_revenue_cents)}
                    </td>
                    <td className="py-3 px-2 text-right">
                      {org.voice_words_count.toLocaleString()}
                    </td>
                    <td className="py-3 px-2 text-right">
                      {org.call_count}
                    </td>
                    <td className="py-3 px-2 text-right">
                      {formatCurrency(org.voice_charges_cents)}
                    </td>
                    <td className="py-3 px-2 text-right">
                      {formatCurrency(org.call_charges_cents)}
                    </td>
                    <td className="py-3 px-2 text-right font-semibold">
                      {formatCurrency(org.total_charges_cents)}
                    </td>
                    <td className="py-3 px-2 text-center">
                      {org.subscription ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          {org.subscription.status}
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          No subscription
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 font-semibold">
                  <td className="py-3 px-2" colSpan={7}>Total</td>
                  <td className="py-3 px-2 text-right text-lg">
                    {formatCurrency(data.total_revenue_cents)}
                  </td>
                  <td className="py-3 px-2"></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SuperAdminBilling;