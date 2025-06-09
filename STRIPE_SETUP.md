# Stripe Billing Setup Guide

## 1. Stripe Dashboard Setup

### Create Stripe Account (Sandbox)
1. Go to [https://dashboard.stripe.com](https://dashboard.stripe.com)
2. Create account or log in
3. Make sure you're in **Test mode** (toggle in left sidebar)

### Get API Keys
1. Go to **Developers > API keys**
2. Copy your test keys:
   - **Publishable key**: `pk_test_...`
   - **Secret key**: `sk_test_...`

### Create Monthly Subscription Products
1. Go to **Products** in Stripe Dashboard
2. Click **+ Add product**
3. Create subscription products:

**Basic Plan Example:**
- Name: "Basic Monthly Subscription"
- Pricing: $29.00/month (or your chosen price)
- Billing period: Monthly
- Copy the **Price ID** (starts with `price_`)

**Pro Plan Example:**
- Name: "Pro Monthly Subscription"  
- Pricing: $99.00/month (or your chosen price)
- Billing period: Monthly
- Copy the **Price ID** (starts with `price_`)

### Set Up Webhooks
1. Go to **Developers > Webhooks**
2. Click **+ Add endpoint**
3. Endpoint URL: `https://your-domain.com/api/billing/webhook`
4. Select events to listen for:
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the **Webhook signing secret** (starts with `whsec_`)

## 2. Environment Configuration

Add to your `.env` file:

```bash
# Stripe Test Configuration
STRIPE_SECRET_KEY=sk_test_YOUR_ACTUAL_SECRET_KEY
STRIPE_PUBLIC_KEY=pk_test_YOUR_ACTUAL_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_ACTUAL_WEBHOOK_SECRET

# Monthly Subscription Price IDs
STRIPE_PRICE_BASIC_SUB=price_YOUR_BASIC_PRICE_ID
STRIPE_PRICE_PRO_SUB=price_YOUR_PRO_PRICE_ID
```

## 3. Database Migration

Run the database migration to create billing tables:

```bash
cd backend
alembic upgrade head
```

## 4. Test the Integration

### Backend API Testing

1. **Create a customer:**
```bash
curl -X POST http://localhost:8000/api/billing/customer \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test Organization"
  }'
```

2. **Create a subscription:**
```bash
curl -X POST http://localhost:8000/api/billing/subscription \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stripe_price_id": "price_YOUR_BASIC_PRICE_ID"
  }'
```

3. **Check billing dashboard:**
```bash
curl -X GET http://localhost:8000/api/billing/dashboard \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Frontend Testing

1. Navigate to `/billing` in your frontend
2. You should see the billing dashboard with:
   - Current subscription status
   - Usage statistics
   - Recent invoices

## 5. Usage-Based Billing

The system automatically tracks voice usage (STT + TTS words) and bills at $1.00 per 1,000 words.

### Manual Usage Invoice (Testing)
```bash
curl -X POST http://localhost:8000/api/billing/generate-usage-invoice \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Automated Monthly Billing
The system includes a background job that runs monthly to generate usage invoices automatically.

## 6. Stripe Test Cards

Use these test card numbers in Stripe sandbox:

- **Successful payment**: `4242424242424242`
- **Declined payment**: `4000000000000002`
- **Requires authentication**: `4000002500003155`

## 7. Production Deployment

When ready for production:

1. Switch to **Live mode** in Stripe Dashboard
2. Get live API keys (`sk_live_...` and `pk_live_...`)
3. Update environment variables
4. Set up production webhook endpoint
5. Test thoroughly with small amounts

## 8. Billing Architecture

```
Organization (Tenant)
├── StripeCustomer (1:1)
├── StripeSubscription (1:many) - Monthly recurring
└── StripeInvoice (1:many) - Usage-based billing

Usage Tracking:
├── STT Words (tracked per conversation)
├── TTS Words (tracked per conversation)
└── Monthly aggregation → Invoice
```

## 9. Key Features

- ✅ Monthly subscription billing
- ✅ Usage-based billing ($1.00/1000 words)
- ✅ Multi-tenant (per organization)
- ✅ Webhook integration
- ✅ Automated monthly billing
- ✅ Real-time usage dashboard
- ✅ Sandbox/Production ready

## 10. Troubleshooting

**Stripe not configured error:**
- Check that `STRIPE_SECRET_KEY` starts with `sk_test_` or `sk_live_`

**Webhook signature verification failed:**
- Ensure `STRIPE_WEBHOOK_SECRET` is correctly set
- For development, webhook verification can be disabled

**Database errors:**
- Run `alembic upgrade head` to create billing tables
- Check database connection

**No usage data:**
- Ensure voice services are properly tracking usage
- Check `UsageRecord` table for STT/TTS entries