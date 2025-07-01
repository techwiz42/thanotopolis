# Thanotopolis Billing System Setup

## Overview

The Thanotopolis platform uses Stripe for billing with the following pricing structure:
- **Monthly Subscription**: $299/month
- **Voice Usage (STT/TTS)**: $1.00 per 1,000 words
- **Phone Calls**: $1.00 per call (base fee) + voice usage charges

## Stripe Configuration

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Stripe API Keys (get from https://dashboard.stripe.com/apikeys)
STRIPE_SECRET_KEY=sk_live_YOUR_SECRET_KEY_HERE
STRIPE_PUBLIC_KEY=pk_live_YOUR_PUBLISHABLE_KEY_HERE

# Webhook Secret (get from webhook endpoint settings)
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE

# Monthly Subscription Price ID (create in Stripe Dashboard)
STRIPE_MONTHLY_PRICE_ID=price_YOUR_MONTHLY_PRICE_ID
```

### 2. Create Products in Stripe Dashboard

#### Required Products

1. **Monthly Subscription Product**:
   - Go to Stripe Dashboard → Products
   - Click "Add product"
   - **Product Information**:
     - Name: `Thanotopolis Platform Subscription`
     - Description: `Monthly subscription for Thanotopolis multi-agent platform with web and telephony access`
     - Image: (optional - upload your logo)
   - **Pricing**:
     - Pricing model: `Recurring`
     - Price: `$299.00`
     - Billing period: `Monthly`
     - Currency: `USD`
   - **Additional Options**:
     - Usage is metered: `No` (this is the flat monthly fee)
     - Price description: `Monthly platform access fee`
   - Click "Save product"
   - Copy the Price ID (starts with `price_`) and add it to `STRIPE_MONTHLY_PRICE_ID`

#### Note on Usage-Based Billing

The voice usage and call charges are handled differently:
- **Voice Usage (STT/TTS)**: $1.00 per 1,000 words
- **Phone Calls**: $1.00 per call

These are **NOT** created as separate products in Stripe. Instead, they are added as **Invoice Items** during the monthly billing cycle. This approach provides more flexibility and accurate usage tracking.

The billing automation service:
1. Tracks usage in the local database throughout the month
2. On the 1st of each month, calculates total usage
3. Creates invoice items for:
   - Voice usage: `Voice Usage: X,XXX words (STT: X,XXX, TTS: X,XXX)`
   - Call charges: `Phone Calls: X calls`
4. Automatically generates and sends the invoice

This method ensures:
- Accurate per-customer usage tracking
- Detailed invoice line items
- No need for complex metered billing setup
- Easy adjustment of usage rates if needed

### 3. Configure Webhook Endpoint

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://yourdomain.com/api/billing/webhook`
3. Select these events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the signing secret to `STRIPE_WEBHOOK_SECRET`

### 4. Configure Customer Portal

1. Go to Stripe Dashboard → Settings → Billing → Customer portal
2. **Functionality**:
   - ✅ Enable "Allow customers to update their payment methods"
   - ✅ Enable "Allow customers to update their billing address"
   - ✅ Enable "Allow customers to update their email address"
   - ✅ Enable "Allow customers to view their billing history"
   - ✅ Enable "Allow customers to download invoices"
3. **Subscriptions**:
   - ✅ Enable "Allow customers to cancel subscriptions"
   - ⚠️ Cancellation behavior: "Cancel at end of billing period" (recommended)
   - Optional: Add cancellation reason collection
4. **Products**:
   - Show: "Thanotopolis Platform Subscription"
5. **Business Information**:
   - Add your company name, support email, and privacy policy URL
6. Save changes

### 5. Payment Methods Configuration

1. Go to Stripe Dashboard → Settings → Payment methods
2. Enable the following payment methods:
   - ✅ **Card payments** (Required)
   - ✅ **ACH Direct Debit** (Recommended for B2B)
   - ✅ **SEPA Direct Debit** (If you have EU customers)
3. For each payment method:
   - Configure statement descriptors
   - Set up appropriate fraud prevention rules

## Database Setup

Run the existing migration to create Stripe tables:

```bash
cd backend
alembic upgrade head
```

This creates:
- `stripe_customers` - Links tenants to Stripe customers
- `stripe_subscriptions` - Tracks active subscriptions
- `stripe_invoices` - Stores invoice history

## Usage Tracking

The system automatically tracks:
- **STT Words**: Through Deepgram Voice Agent events
- **TTS Words**: Through Voice Agent responses
- **Phone Calls**: Through telephony call records

Usage is recorded in the `usage_records` table and aggregated for billing.

## Customer Workflow

### 1. New Customer Signup

```javascript
// Frontend - Create checkout session
const response = await fetch('/api/billing/create-checkout-session', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    success_url: 'https://yourdomain.com/billing/success',
    cancel_url: 'https://yourdomain.com/billing/cancel',
    trial_days: 14  // Optional trial period
  })
});

const { checkout_url } = await response.json();
window.location.href = checkout_url;  // Redirect to Stripe Checkout
```

### 2. Manage Subscription

```javascript
// Frontend - Access customer portal
const response = await fetch('/api/billing/customer-portal?return_url=' + 
  encodeURIComponent(window.location.href), {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const { portal_url } = await response.json();
window.location.href = portal_url;  // Redirect to Stripe Portal
```

### 3. View Billing Dashboard

```javascript
// Frontend - Get billing info
const response = await fetch('/api/billing/dashboard', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const dashboard = await response.json();
// Contains: current_subscription, recent_invoices, current_period_usage, upcoming_charges
```

## Monthly Billing Process

The billing automation service runs daily and processes charges on the 1st of each month:

1. **Automatic Usage Billing**:
   - Calculates voice usage (STT + TTS words)
   - Counts phone calls
   - Creates invoice items in Stripe
   - Finalizes and sends invoices

2. **Manual Trigger** (for testing):
   ```python
   from app.services.billing_automation import trigger_manual_billing
   await trigger_manual_billing()  # Bills for previous month
   ```

## Testing

### Test Mode
Use Stripe test keys for development:
- Test cards: https://stripe.com/docs/testing
- Common test card: `4242 4242 4242 4242`

### Webhook Testing
Use Stripe CLI for local webhook testing:
```bash
stripe listen --forward-to localhost:8000/api/billing/webhook
```

## Frontend Integration

The billing dashboard components are already created:
- `/frontend/src/components/BillingDashboard.tsx` - Main billing view
- `/frontend/src/components/SubscriptionPlans.tsx` - Plan selection
- `/frontend/src/components/SuperAdminBilling.tsx` - Admin overview

## Monitoring

### Key Metrics to Track:
1. **Subscription MRR**: Monthly recurring revenue
2. **Usage Revenue**: Voice and call charges
3. **Failed Payments**: Monitor webhook events
4. **Customer Churn**: Track cancellations

### Useful Queries:
```sql
-- Monthly revenue by organization
SELECT 
    t.name,
    COUNT(DISTINCT si.id) as invoices,
    SUM(si.amount_paid_cents) / 100.0 as revenue_usd
FROM stripe_invoices si
JOIN stripe_customers sc ON si.customer_id = sc.id
JOIN tenants t ON sc.tenant_id = t.id
WHERE si.status = 'paid'
  AND si.paid_at >= date_trunc('month', CURRENT_DATE)
GROUP BY t.name;

-- Current usage this month
SELECT 
    t.name,
    SUM(CASE WHEN ur.usage_type = 'stt_words' THEN ur.amount ELSE 0 END) as stt_words,
    SUM(CASE WHEN ur.usage_type = 'tts_words' THEN ur.amount ELSE 0 END) as tts_words,
    SUM(CASE WHEN ur.usage_type = 'phone_calls' THEN ur.amount ELSE 0 END) as calls
FROM usage_records ur
JOIN tenants t ON ur.tenant_id = t.id
WHERE ur.created_at >= date_trunc('month', CURRENT_DATE)
GROUP BY t.name;
```

## Troubleshooting

### Common Issues:

1. **"No Stripe customer found"**
   - Customer needs to complete checkout first
   - Check if `stripe_customers` record exists

2. **Webhook signature verification failed**
   - Ensure `STRIPE_WEBHOOK_SECRET` is correct
   - Check if payload is being modified by proxy

3. **Usage not being billed**
   - Verify usage records exist in database
   - Check billing automation logs
   - Ensure customer has active subscription

## Demo Account Management

### Setting Demo Status

Demo accounts are exempt from all billing charges and can be set by super admins:

```bash
# Mark an organization as demo (super admin only)
curl -X POST "/api/billing/set-demo-status/{tenant_id}?is_demo=true" \
  -H "Authorization: Bearer {super_admin_token}"

# Remove demo status
curl -X POST "/api/billing/set-demo-status/{tenant_id}?is_demo=false" \
  -H "Authorization: Bearer {super_admin_token}"
```

Demo accounts:
- Show "Demo Account" message in billing dashboard
- Are excluded from automated billing processes
- Have full platform access without charges
- Cannot create subscriptions or be billed

### Database Management

```sql
-- Mark organization as demo
UPDATE tenants SET is_demo = true WHERE subdomain = 'demo-org';

-- List all demo organizations
SELECT name, subdomain, is_demo FROM tenants WHERE is_demo = true;

-- Exclude demos from billing queries
SELECT * FROM tenants t 
JOIN stripe_customers sc ON t.id = sc.tenant_id 
WHERE t.is_demo = false;
```

## Subscription Management

### Customer Cancellation

Customers can manage their subscriptions through:

1. **Billing Dashboard**: Cancel/reactivate buttons
2. **Customer Portal**: Full Stripe-hosted management
3. **API Endpoints**:
   - `POST /api/billing/cancel-subscription` - Cancel at period end
   - `POST /api/billing/reactivate-subscription` - Reactivate cancelled subscription

### Cancellation Behavior

- Subscriptions are cancelled at the end of the current billing period
- Customers retain access until period end
- Can reactivate before period ends
- Usage charges still apply during cancellation period

## Updated Contact Information

### Support Contacts:
- Technical Support: pete@cyberiad.ai
- Phone Support: (617) 997-1844
- Stripe Support: https://support.stripe.com
- API Reference: https://stripe.com/docs/api