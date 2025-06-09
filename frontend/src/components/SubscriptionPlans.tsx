'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';

interface Plan {
  id: string;
  name: string;
  price_id: string;
  amount_cents: number;
  currency: string;
  interval: string;
  features: string[];
}

interface SubscriptionPlansProps {
  onSubscriptionStarted?: () => void;
}

const SubscriptionPlans: React.FC<SubscriptionPlansProps> = ({ onSubscriptionStarted }) => {
  const { tokens, organization } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingSubscription, setStartingSubscription] = useState<string | null>(null);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await fetch('/api/billing/subscription-plans', {
        headers: {
          'Authorization': `Bearer ${tokens?.access_token}`,
          'X-Tenant-ID': organization || '',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPlans(data.plans || []);
      }
    } catch (error) {
      console.error('Error fetching plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const startSubscription = async (planId: string) => {
    setStartingSubscription(planId);
    
    try {
      const response = await fetch('/api/billing/start-subscription', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens?.access_token}`,
          'X-Tenant-ID': organization || '',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ plan_id: planId }),
      });

      if (response.ok) {
        const data = await response.json();
        // Redirect to Stripe checkout
        window.location.href = data.checkout_url;
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to start subscription'}`);
      }
    } catch (error) {
      console.error('Error starting subscription:', error);
      alert('Failed to start subscription. Please try again.');
    } finally {
      setStartingSubscription(null);
    }
  };

  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(cents / 100);
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="text-lg">Loading subscription plans...</div>
      </div>
    );
  }

  if (plans.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No Subscription Plans Available</CardTitle>
          <CardDescription>
            Subscription plans are not configured yet. Please contact support.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">Choose Your Plan</h2>
        <p className="text-gray-600">
          Select a subscription plan to get started with Thanotopolis
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {plans.map((plan) => (
          <Card key={plan.id} className="relative">
            <CardHeader>
              <CardTitle className="text-xl">{plan.name}</CardTitle>
              <CardDescription>
                <div className="text-3xl font-bold text-blue-600 mt-2">
                  {formatCurrency(plan.amount_cents)}
                  <span className="text-sm font-normal text-gray-600">/{plan.interval}</span>
                </div>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-center">
                    <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>

              <div className="pt-4">
                <Button
                  onClick={() => startSubscription(plan.id)}
                  disabled={startingSubscription === plan.id}
                  className="w-full"
                >
                  {startingSubscription === plan.id ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Starting...
                    </>
                  ) : (
                    `Start ${plan.name}`
                  )}
                </Button>
              </div>
            </CardContent>

            {plan.id === 'pro' && (
              <div className="absolute top-0 right-0 bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-bl-lg">
                POPULAR
              </div>
            )}
          </Card>
        ))}
      </div>

      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold mb-2">Additional Usage Charges</h3>
        <p className="text-sm text-gray-600">
          Voice services (Speech-to-Text and Text-to-Speech) are billed separately at{' '}
          <span className="font-semibold">$1.00 per 1,000 words</span> used each month.
          This usage is automatically calculated and billed monthly.
        </p>
      </div>
    </div>
  );
};

export default SubscriptionPlans;