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

## 📋 Pending Production Updates

### Database Migrations Required
1. **Billing Exemption** (`is_demo` column on tenants table)
2. **Cemetery CRM Fields** (20+ new fields on contacts table)

### When Ready for Production
1. Update production environment with live Stripe keys
2. Run database migrations
3. Mark demo/cyberiad organizations as exempt
4. Deploy voice integration features

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

---

**Last Updated**: July 11, 2025
**Status**: Development environment fully operational with voice-to-CRM-to-calendar integration complete