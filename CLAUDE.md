# Thanotopolis Development Environment

## 🚀 Current Status: FULLY OPERATIONAL

**Environment**: Complete development instance isolated from production
- **URL**: https://dev.thanotopolis.com
- **Database**: `thanotopolis_dev` (PostgreSQL with pgvector)
- **Backend**: Port 8001 | **Frontend**: Port 3001
- **Branch**: `calendar` (based on CRM branch)

## 🏗️ Infrastructure

### Core Services
- **Backend**: `thanotopolis-backend-dev.service` (FastAPI on port 8001)
- **Frontend**: `thanotopolis-frontend-dev.service` (Next.js on port 3001)
- **Database**: PostgreSQL with `thanotopolis_dev` database
- **SSL**: Let's Encrypt certificate for HTTPS
- **Nginx**: Reverse proxy configuration active

### Environment Configuration
```bash
# Backend (.env)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/thanotopolis_dev
API_PORT=8001
FRONTEND_URL=https://dev.thanotopolis.com

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=wss://dev.thanotopolis.com/ws
```

## ✅ Completed Features

### 1. Billing System
- **Dynamic Pricing**: Beta ($99/mo) and Full ($299/mo) tiers
- **Usage-Based**: Configurable voice/call rates
- **Exemptions**: Demo accounts excluded from billing
- **Stripe Integration**: Test and live products configured

### 2. Cemetery CRM
- **Specialized Fields**: Deceased info, family relationships, cultural preferences
- **Financial Tracking**: Contracts, payments, balances
- **Service Management**: Plot numbers, service types, veteran status

### 3. Calendar System
- **Multi-View**: Month, week, day views
- **CRM Integration**: Link events to contacts
- **Event Types**: Appointments, services, meetings
- **Statistics**: Dashboard with event analytics

### 4. Voice-to-CRM-to-Calendar Integration 🎯
**Status**: PRODUCTION READY (Completed July 11, 2025)

Revolutionary AI voice agent that automatically:
- Extracts customer information from conversations
- Creates CRM contacts with cemetery-specific data
- Schedules appointments in real-time
- Provides natural language confirmations

**Key Files**:
- `/app/services/voice/customer_extraction.py` - Data extraction
- `/app/services/voice/scheduling_intent.py` - Intent detection
- `/app/services/voice/voice_calendar.py` - Calendar integration
- Modified `/app/api/telephony_voice_agent.py` - Voice agent enhancement

### 5. Security Upgrades 🔒
**Status**: COMPLETED (July 13, 2025)

Critical security vulnerability fixes:
- **Next.js Upgrade**: 13.5.11 → 15.4.0 (eliminates CVE vulnerabilities)
- **React Upgrade**: 18.2.0 → 19.0.0 (latest stable)
- **Breaking Changes Handled**: Async route params, Suspense boundaries
- **Build Process**: All 33 pages compile successfully

### 6. Issue Tracker System 🐛
**Status**: COMPLETED (July 15, 2025)

Complete internal issue tracking system replacing GitHub dependency:
- **Anonymous Reporting**: Users can report issues without GitHub accounts
- **Full Lifecycle Management**: Open → In Progress → Resolved → Closed
- **Priority & Type System**: Critical/High/Medium/Low priority, Bug/Feature/Improvement/Question types
- **Comments & Discussion**: Threaded conversations with anonymous support
- **Search & Filtering**: Real-time filtering by status, priority, type with pagination
- **Statistics Dashboard**: Issue counts, trends, and recent activity overview
- **Responsive Design**: Mobile-friendly interface with proper status icons
- **Footer Integration**: Updated footer link points to internal tracker (/issues)

## 📋 Pending Production Updates

### Database Migrations Required
1. **Billing Exemption** (`is_demo` column on tenants table)
2. **Cemetery CRM Fields** (20+ new fields on contacts table)
3. **Issue Tracker Tables** (issues and issue_comments tables) - COMPLETED in dev

### When Ready for Production
1. Update production environment with live Stripe keys
2. Run database migrations
3. Mark demo/cyberiad organizations as exempt
4. Deploy voice integration features
5. **Deploy Next.js 15 upgrade** (security fixes included)

## 🛠️ Quick Commands

```bash
# Service Management
sudo systemctl status thanotopolis-backend-dev
sudo systemctl status thanotopolis-frontend-dev

# Logs
sudo journalctl -u thanotopolis-backend-dev -f
sudo journalctl -u thanotopolis-frontend-dev -f

# Manual Testing
cd /home/peter/thanotopolis_dev/backend
~/.virtualenvs/thanos/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

cd /home/peter/thanotopolis_dev/frontend
npm run dev -- --port 3001

# Next.js Upgrade Commands (if needed)
npm install next@15.4.0 react@19.0.0 react-dom@19.0.0
npm run build  # Test build process
```

## 🔧 Next.js 15 Upgrade Details

### Breaking Changes Handled
- **Async Route Parameters**: Dynamic routes now use `Promise<{ param: string }>` 
  - Updated: `/organizations/crm/campaigns/[id]/page.tsx`
  - Updated: `/organizations/telephony/calls/[id]/page.tsx`
- **Suspense Boundaries**: Added for `useSearchParams()` hook usage
  - Updated: `/billing/organization/page.tsx`

### Migration Process
```bash
# 1. Upgrade packages
npm install next@15.4.0 react@19.0.0 react-dom@19.0.0

# 2. Fix dynamic route components
# Change: { params }: { params: { id: string } }
# To: { params }: { params: Promise<{ id: string }> }

# 3. Add async param resolution
useEffect(() => {
  params.then(resolvedParams => {
    setParamId(resolvedParams.id)
  })
}, [params])

# 4. Wrap useSearchParams in Suspense
<Suspense fallback={<div>Loading...</div>}>
  <ComponentUsingSearchParams />
</Suspense>

# 5. Test build
npm run build
```

## 📁 Directory Structure
```
/home/peter/thanotopolis_dev/
├── backend/
│   ├── .env                    # Dev environment variables
│   ├── app/                    # Application code
│   └── alembic/                # Database migrations
├── frontend/
│   ├── .env.local              # Frontend environment
│   └── src/                    # React/Next.js code
└── CLAUDE.md                   # This file
```

## 🔄 Active Development

Currently on `calendar` branch with all features integrated:
- ✅ Basic calendar functionality
- ✅ CRM contact linking
- ✅ Voice agent integration
- ✅ Real-time scheduling

## 📝 Notes

- Virtual environment: `~/.virtualenvs/thanos`
- All new database fields are nullable for flexibility
- Financial amounts stored in cents for precision
- Voice integration handles multiple concurrent sessions
- Complete conversation history linked to contacts/events

## Issue Tracker Implementation Details (July 15, 2025)

### Database Schema
```sql
-- Issues table
CREATE TABLE issues (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    type issuetype NOT NULL,
    status issuestatus NOT NULL,
    priority issuepriority NOT NULL,
    reporter_email VARCHAR(255),
    reporter_name VARCHAR(255),
    reporter_user_id UUID REFERENCES users(id),
    assigned_to_id UUID REFERENCES users(id),
    resolved_by_id UUID REFERENCES users(id),
    resolution TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP
);

-- Issue comments table
CREATE TABLE issue_comments (
    id UUID PRIMARY KEY,
    issue_id UUID REFERENCES issues(id) NOT NULL,
    content TEXT NOT NULL,
    user_id UUID REFERENCES users(id),
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### API Endpoints
- **POST /api/issues** - Create new issues (anonymous or authenticated)
- **GET /api/issues** - List/search/filter issues with pagination
- **GET /api/issues/{id}** - Get specific issue details
- **PUT /api/issues/{id}** - Update issue status/priority (admin only)
- **POST /api/issues/{id}/comments** - Add comments to issues
- **GET /api/issues/stats/summary** - Dashboard statistics

### Frontend Routes
- **/issues** - Main issue listing with search and filters
- **/issues/new** - Issue submission form
- **/issues/[id]** - Issue detail view with comments

### Key Features
- **Anonymous Support**: No authentication required for reporting
- **Tenant Isolation**: Organization-specific issues for authenticated users
- **Public Issues**: Anonymous issues visible to all users
- **Role-Based Updates**: Only admins can update issue status/priority
- **Real-time Stats**: Dashboard with issue counts by status, priority, type
- **Rich UI**: Status icons, priority colors, responsive design

### Files Created
- `backend/app/models/issues.py` - Database models
- `backend/app/schemas/issues.py` - Pydantic schemas
- `backend/app/api/issues.py` - API endpoints
- `frontend/src/app/issues/page.tsx` - Main listing page
- `frontend/src/app/issues/new/page.tsx` - Issue submission form
- `frontend/src/app/issues/[id]/page.tsx` - Issue detail view

### Footer Integration
- Updated `frontend/src/components/MainLayout.tsx` to point "Report Issue" link to `/issues`
- Removed dependency on GitHub accounts for issue reporting

---

**Last Updated**: July 15, 2025
**Status**: Development environment fully operational with voice-to-CRM-to-calendar integration complete, Next.js 15 security upgrade, and internal issue tracker system