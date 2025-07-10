# Thanotopolis Development Environment Setup

## Project Overview
Setting up a complete development installation of thanotopolis alongside the existing production instance. The development environment will mirror the production setup but use separate databases, ports, and eventually a dev subdomain.

## Goals
- **Separate Development Environment**: Complete isolation from production
- **CRM Branch Deployment**: Using the `origin/CRM` branch for development
- **Database Isolation**: `thanotopolis_dev` database separate from production
- **Port Separation**: Backend on 8001, Frontend on 3001 (vs prod 8000/3000)
- **Subdomain Access**: Eventually serve via `dev.thanotopolis.com`

## Current Status

### ✅ Completed Tasks

#### 1. Repository Setup
- **Source**: Cloned from `git@github.com:techwiz42/thanotopolis.git`
- **Branch**: `origin/CRM` branch checked out
- **Location**: `/home/peter/thanotopolis_dev/`
- **Virtual Environment**: Using existing `~/.virtualenvs/thanos`

#### 2. Database Setup
- **Database Created**: `thanotopolis_dev` with UTF8 encoding
- **Extensions**: `vector` extension installed (pgvector for RAG features)
- **Connection**: `postgresql+asyncpg://postgres:postgres@localhost:5432/thanotopolis_dev`
- **Schema**: All tables created using `init_dev_db.py` script
- **Migration Status**: Marked as current with latest revision `122b7567de22`
- **Status**: ✅ **CONFIRMED ISOLATED** - Dev database is empty and separate from production

#### 3. Backend Configuration
- **Environment File**: `/home/peter/thanotopolis_dev/backend/.env`
- **Port**: API server configured for port 8001
- **Database URL**: Points to `thanotopolis_dev` database
- **URLs**: Configured for `dev.thanotopolis.com` subdomain
- **CORS**: Set up for dev subdomain access
- **Status**: ✅ **FULLY OPERATIONAL** on port 8001

#### 4. Frontend Configuration
- **Environment File**: `/home/peter/thanotopolis_dev/frontend/.env.local`
- **URLs**: Fixed to point to `http://localhost:8001` for API calls
- **Authentication**: Google and Microsoft client IDs copied from production
- **Status**: ✅ **BUILT AND DEPLOYED** with correct API routing

#### 5. DNS and SSL Setup
- **DNS Record**: ✅ **CONFIGURED** - `dev.thanotopolis.com` resolves correctly
- **SSL Certificate**: ✅ **GENERATED** - Let's Encrypt certificate installed
- **Status**: ✅ **OPERATIONAL** - HTTPS access working

#### 6. Nginx Configuration
- **File**: `/etc/nginx/sites-available/thanotopolis-dev`
- **Subdomain**: `dev.thanotopolis.com`
- **Backend Proxy**: Port 8001 for API routes
- **Frontend Proxy**: Port 3001 for web interface
- **WebSocket Support**: Configured for real-time features
- **Status**: ✅ **DEPLOYED AND ACTIVE**

#### 7. Systemd Services
- **Backend Service**: `thanotopolis-backend-dev.service`
- **Frontend Service**: `thanotopolis-frontend-dev.service`
- **Auto-start**: Services configured to start on boot
- **Status**: ✅ **INSTALLED AND RUNNING**

#### 8. Critical Database Connection Fix
- **Problem**: Backend was loading production .env file due to hardcoded path
- **Root Cause**: `app/core/config.py` line 11 had `env_path = '/home/peter/thanotopolis/backend/.env'`
- **Solution**: Changed to dynamic path resolution: `env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')`
- **Result**: Dev backend now correctly loads dev environment and uses `thanotopolis_dev` database
- **Status**: ✅ **FIXED AND VERIFIED**

#### 9. Frontend API Routing Fix
- **Problem**: Frontend .env.local had incorrect API URLs pointing to dev.thanotopolis.com
- **Issue**: Next.js rewrites were routing API calls through nginx instead of directly to backend
- **Solution**: Updated `NEXT_PUBLIC_API_URL=http://localhost:8001` in `.env.local`
- **Result**: Frontend now makes direct API calls to dev backend on port 8001
- **Status**: ✅ **FIXED AND REBUILT**

#### 10. Complete Billing System Implementation
- **Dynamic Subscription Plans**: Added `/api/billing/subscription-plans` endpoint
- **Flexible Pricing**: No code changes needed to switch pricing tiers
- **Test Environment**: Complete Stripe test products and pricing
- **Live Environment**: Complete Stripe live products and pricing  
- **Usage-Based Billing**: Configurable rates via environment variables
- **Combined Billing**: Usage charges automatically added to subscription invoices
- **Status**: ✅ **FULLY IMPLEMENTED AND PRODUCTION READY**

**Test Products (Fake Money):**
- Beta: $99/month - `price_1RjOxWP1Wkv1gIa2p48ZcWNR`
- Full: $299/month - `price_1RjP1JP1Wkv1gIa2q6HSeSWE`

**Live Products (Real Money):**
- Beta: $99/month - `price_1RjPgwP1Wkv1gIa2UJkNXr3J`  
- Full: $299/month - `price_1RjPhfP1Wkv1gIa2hxe0JJjF`

**Usage Pricing (Configurable):**
- Voice: `VOICE_USAGE_PRICE_PER_1000_WORDS=100` ($1.00 per 1000 words)
- Calls: `CALL_BASE_PRICE_CENTS=100` ($1.00 per call)

#### 11. Billing Exemption System
- **Demo Account Support**: Organizations can be marked as `is_demo=True` for billing exemption
- **Automatic Exemption**: Demo accounts excluded from all billing processes
- **Dashboard Integration**: Demo accounts see "exempt from billing charges" message
- **Dev Database**: `is_demo` column added via direct database modification
- **Production Ready**: Scripts created for production database updates
- **Status**: ✅ **DEV IMPLEMENTED** - Production update pending

**Exemption Points:**
- ✅ Billing dashboard shows exemption message
- ✅ Billing automation excludes demo accounts  
- ✅ Usage tracking continues but no charges generated
- ✅ Invoice generation skipped for demo accounts

**Organizations Requiring Exemption:**
- `demo` - Demo organization (production)
- `cyberiad` - Company organization (production)

#### 12. Cemetery CRM Enhancement
- **Cemetery Customer Tracking**: Enhanced CRM to support cemetery-specific customer management
- **Cultural Preferences**: Added ethnic orientation and language preference fields
- **Deceased Information**: Added deceased name, dates, and service details
- **Cemetery Operations**: Plot numbers, service types, religious preferences, veteran status
- **Financial Tracking**: Contract amounts, payments, and balance due (stored in cents)
- **Special Requests**: Notes for flowers, music preferences, special arrangements
- **Family Relationships**: Track relationship to deceased and family name
- **Status**: ✅ **DEV IMPLEMENTED** - Production migration pending

**Cemetery-Specific Fields Added:**
- **Cultural/Language**: `ethnic_orientation`, `preferred_language`, `secondary_language`
- **Family Info**: `family_name`, `relationship_to_deceased`
- **Deceased Details**: `deceased_name`, `date_of_death`, `date_of_birth`
- **Service Info**: `service_type`, `service_date`, `service_location`
- **Plot Details**: `plot_number`, `plot_type`
- **Financial**: `contract_amount_cents`, `amount_paid_cents`, `balance_due_cents`, `payment_plan`, `payment_status`
- **Special Needs**: `special_requests`, `religious_preferences`, `veteran_status`

**Implementation Notes:**
- All new fields are optional (`nullable=True`) to maintain flexibility
- Financial amounts stored in cents for precision
- Supports both B2B (cemetery operations) and B2C (family customers) workflows
- Existing CRM functionality preserved for non-cemetery organizations

### 🚀 Development Environment Status: FULLY OPERATIONAL

The development environment is now **100% complete and functional**:
- ✅ **Isolated Database**: Uses `thanotopolis_dev` database
- ✅ **Separate Ports**: Backend 8001, Frontend 3001
- ✅ **SSL/HTTPS**: Accessible via `https://dev.thanotopolis.com`
- ✅ **Service Management**: Systemd services for auto-start
- ✅ **Environment Isolation**: No interference with production
- ✅ **Dynamic Pricing**: Configurable via environment variables

### 🔄 Next Steps (Optional Enhancements)

#### Production Deployment Readiness
**Status**: ✅ **COMPLETE** - All billing components ready for production
- ✅ Test products created and working
- ✅ Live products created and ready  
- ✅ Configurable pricing system implemented
- ✅ Usage-based billing fully functional

**When Ready for Production:**
1. Get live Stripe API keys from Dashboard
2. Update production environment with live keys
3. Set initial pricing tier (beta $99 recommended)
4. Configure webhooks for live environment
5. **Deploy billing exemption to production**

#### Production Database Updates Required
**Billing Exemption Deployment:**
1. **Create Alembic migration** for `is_demo` column:
   ```sql
   ALTER TABLE tenants ADD COLUMN is_demo BOOLEAN DEFAULT FALSE NOT NULL;
   ```
2. **Run migration** on production database
3. **Update organizations** to exempt status:
   ```sql
   UPDATE tenants SET is_demo = TRUE WHERE name ILIKE '%demo%' OR name ILIKE '%cyberiad%';
   ```
4. **Verify exemptions** using production scripts

**Cemetery CRM Migration:**
1. **Create Alembic migration** for cemetery fields on Contact model:
   ```sql
   ALTER TABLE contacts ADD COLUMN ethnic_orientation VARCHAR;
   ALTER TABLE contacts ADD COLUMN preferred_language VARCHAR;
   ALTER TABLE contacts ADD COLUMN secondary_language VARCHAR;
   -- Plus 18 additional cemetery-specific fields
   ```
2. **Run migration** on production database
3. **Test CRM functionality** with cemetery-specific workflows

**Scripts Available:**
- `check_billing_exemptions.py` - Verify current exemption status
- `update_demo_status.py` - Mark organizations as exempt
- `add_is_demo_column.py` - Dev database column addition (completed)
- **Cemetery CRM Migration Script** - To be created for production deployment

#### Billing System Capabilities
**Subscription Management:**
- ✅ Dynamic pricing without code changes
- ✅ Easy switching between beta ($99) and full ($299) pricing
- ✅ Separate test/live environments

**Usage-Based Billing:**
- ✅ Configurable voice processing rates
- ✅ Configurable phone call rates  
- ✅ Automatic invoice combination
- ✅ Transparent usage breakdowns

**Administrative Features:**
- ✅ Customer portal integration
- ✅ Subscription cancellation/reactivation
- ✅ Usage tracking and reporting
- ✅ Demo account exemptions

## Directory Structure

```
/home/peter/thanotopolis_dev/
├── backend/
│   ├── .env                    # Dev environment variables
│   ├── alembic/               # Database migrations (copied from prod)
│   ├── app/                   # Application code
│   ├── init_dev_db.py        # Database initialization script
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── .env.local            # Frontend environment variables
│   ├── src/                  # React/Next.js source code
│   ├── package.json          # Node.js dependencies
│   └── next.config.js        # Next.js configuration
└── CLAUDE.md                 # This documentation file
```

## Environment Configuration

### Backend Environment (`.env`)
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/thanotopolis_dev
API_PORT=8001
FRONTEND_URL=https://dev.thanotopolis.com
API_URL=https://dev.thanotopolis.com/api
WS_URL=wss://dev.thanotopolis.com/api/ws
CORS_ORIGINS=["https://dev.thanotopolis.com"]
```

### Frontend Environment (`.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=wss://dev.thanotopolis.com/ws
FRONTEND_URL=https://dev.thanotopolis.com
```

### Stripe Billing Configuration

#### Test Environment Pricing (Current Dev Setup)
```bash
# Subscription products (test/fake money)
STRIPE_PRICE_BETA_SUB="price_1RjOxWP1Wkv1gIa2p48ZcWNR"    # $99/month
STRIPE_PRICE_FULL_SUB="price_1RjP1JP1Wkv1gIa2q6HSeSWE"    # $299/month

# Active pricing (currently beta)
STRIPE_MONTHLY_PRICE_ID="price_1RjOxWP1Wkv1gIa2p48ZcWNR"

# Usage rates (configurable)
VOICE_USAGE_PRICE_PER_1000_WORDS=100    # $1.00 per 1000 words
CALL_BASE_PRICE_CENTS=100               # $1.00 per call
```

#### Production Environment Pricing (Live/Real Money)
```bash
# Subscription products (live/real money)  
STRIPE_PRICE_BETA_SUB_LIVE="price_1RjPgwP1Wkv1gIa2UJkNXr3J"    # $99/month
STRIPE_PRICE_FULL_SUB_LIVE="price_1RjPhfP1Wkv1gIa2hxe0JJjF"    # $299/month

# For production deployment:
STRIPE_MONTHLY_PRICE_ID="price_1RjPgwP1Wkv1gIa2UJkNXr3J"  # Start with beta

# Usage rates (same logic, different rates possible)
VOICE_USAGE_PRICE_PER_1000_WORDS=100    # Configurable per environment
CALL_BASE_PRICE_CENTS=100               # Configurable per environment
```

#### Easy Pricing Switches
**To switch to full pricing ($299):**
- Test: `STRIPE_MONTHLY_PRICE_ID="price_1RjP1JP1Wkv1gIa2q6HSeSWE"`
- Live: `STRIPE_MONTHLY_PRICE_ID="price_1RjPhfP1Wkv1gIa2hxe0JJjF"`

**To adjust usage rates:**
- Lower rates: `VOICE_USAGE_PRICE_PER_1000_WORDS=50` (50¢ per 1000 words)
- Higher rates: `VOICE_USAGE_PRICE_PER_1000_WORDS=150` ($1.50 per 1000 words)

## Database Information

### Connection Details
- **Host**: localhost
- **Port**: 5432 (PostgreSQL default)
- **Database**: `thanotopolis_dev`
- **User**: postgres
- **Password**: postgres

### Key Features
- **pgvector Extension**: Enabled for RAG/embedding features
- **Schema**: Complete thanotopolis schema with all tables
- **Isolation**: Completely separate from production `thanotopolis` database

## Next Steps (Tomorrow)

### 1. DNS Setup
```bash
# Create DNS A record for dev.thanotopolis.com pointing to server IP
# This needs to be done in your domain registrar/DNS provider
```

### 2. SSL Certificate Generation
```bash
sudo certbot certonly --nginx -d dev.thanotopolis.com
```

### 3. Nginx Configuration Deployment
```bash
# Copy the nginx config to sites-available
sudo cp /path/to/thanotopolis-dev /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/thanotopolis-dev /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

### 4. Systemd Service Creation

#### Backend Service (`thanotopolis-backend-dev.service`)
```ini
[Unit]
Description=Thanotopolis Backend Development Server
After=network.target postgresql.service

[Service]
Type=exec
User=peter
Group=peter
WorkingDirectory=/home/peter/thanotopolis_dev/backend
Environment=PATH=/home/peter/.virtualenvs/thanos/bin
ExecStart=/home/peter/.virtualenvs/thanos/bin/gunicorn app.main:app -c gunicorn_config.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### Frontend Service (`thanotopolis-frontend-dev.service`)
```ini
[Unit]
Description=Thanotopolis Frontend Development Server
After=network.target

[Service]
Type=exec
User=peter
Group=peter
WorkingDirectory=/home/peter/thanotopolis_dev/frontend
Environment=NODE_ENV=production
Environment=PORT=3001
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 5. Service Deployment
```bash
# Install and enable services
sudo systemctl daemon-reload
sudo systemctl enable thanotopolis-backend-dev
sudo systemctl enable thanotopolis-frontend-dev
sudo systemctl start thanotopolis-backend-dev
sudo systemctl start thanotopolis-frontend-dev

# Check status
sudo systemctl status thanotopolis-backend-dev
sudo systemctl status thanotopolis-frontend-dev
```

## Testing Checklist

### After Complete Setup
- [ ] `dev.thanotopolis.com` resolves to server IP
- [ ] SSL certificate valid for dev subdomain
- [ ] Backend API accessible at `https://dev.thanotopolis.com/api/health`
- [ ] Frontend loads at `https://dev.thanotopolis.com`
- [ ] WebSocket connections work for real-time features
- [ ] Database operations work (user registration, conversations, etc.)
- [ ] CRM features function correctly
- [ ] Voice/telephony features work
- [ ] No interference with production `thanotopolis.com`

## Development Workflow

### Starting Services Manually (for testing)
```bash
# Backend
cd /home/peter/thanotopolis_dev/backend
~/.virtualenvs/thanos/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# Frontend  
cd /home/peter/thanotopolis_dev/frontend
npm run dev -- --port 3001
```

### Checking Logs
```bash
# Backend logs
sudo journalctl -u thanotopolis-backend-dev -f

# Frontend logs
sudo journalctl -u thanotopolis-frontend-dev -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Security Considerations

### Development Environment Security
- **Separate Secrets**: Dev environment uses different JWT secret keys
- **Database Isolation**: No access to production data
- **API Keys**: Consider using separate API keys for external services in dev
- **CORS Configuration**: Restricted to dev subdomain only

### Production Safety
- **Port Isolation**: Dev services on different ports (8001/3001 vs 8000/3000)
- **Domain Separation**: Different subdomains prevent conflicts
- **Database Separation**: Completely isolated database
- **Service Names**: Different systemd service names prevent conflicts

## Notes

### Migration Issues Resolved
- **Initial Problem**: Alembic migration conflicts due to complex branching history
- **Solution**: Used `init_dev_db.py` to create all tables directly from models
- **Result**: Database marked as current with latest migration revision

### Configuration Strategy
- **Environment Variables**: All URLs use `dev.thanotopolis.com` for consistency
- **SSL/TLS**: HTTPS/WSS everywhere for production-like environment
- **API Compatibility**: Same endpoints and features as production

### Future Considerations
- **Automated Deployment**: Consider CI/CD pipeline for dev environment
- **Data Seeding**: Scripts to populate dev database with test data
- **Feature Flags**: Different feature configurations for testing
- **Performance Monitoring**: Separate monitoring for dev environment

---

## Summary

The thanotopolis development environment is **95% complete**. All code is configured, databases are set up, and the application is ready to run. The only remaining step is setting up the DNS record for `dev.thanotopolis.com` and generating the SSL certificate, after which the development environment will be fully operational and accessible via the dev subdomain.