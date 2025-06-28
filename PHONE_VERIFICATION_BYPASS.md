# Phone Verification Bypass Guide

This guide explains how to bypass or manually override phone number verification in the Thanotopolis telephony system.

## Overview

The phone verification system requires organizations to verify ownership of their business phone numbers before enabling AI call handling. However, for testing, development, or administrative purposes, you may need to bypass this verification process.

## Verification Process Components

### 1. Database Models

The verification system uses these key database fields:

**TelephonyConfiguration Table:**
- `verification_status`: `pending` | `verified` | `failed` | `expired`
- `call_forwarding_enabled`: Boolean flag controlling call forwarding
- `organization_phone_number`: The business phone number being verified
- `platform_phone_number`: The assigned Twilio number for forwarding

**PhoneVerificationAttempt Table:**
- Tracks individual verification attempts with codes
- Status tracking and expiration timestamps
- Maximum attempts limiting

### 2. Backend API Endpoints

**Regular Verification Flow:**
- `POST /api/telephony/verify/initiate` - Send verification code
- `POST /api/telephony/verify/confirm` - Confirm with code
- `GET /api/telephony/config` - Check verification status

**Admin Override Endpoints:**
- `GET /api/admin/telephony/configs` - List all configurations (admin only)
- `POST /api/admin/telephony/manual-verify/{config_id}` - Manual verify (super admin only)
- `POST /api/admin/telephony/manual-unverify/{config_id}` - Manual unverify (super admin only)

### 3. Frontend Components

**Main Telephony Service:** `/frontend/src/services/telephony.ts`
- `initiateVerification()` - Trigger verification process
- `confirmVerification()` - Submit verification code
- `getTelephonyConfig()` - Check verification status
- Status checking utilities and UI state management

## Bypass Methods

### Method 1: Manual Script (Recommended)

Use the provided manual verification script:

```bash
# Navigate to backend directory
cd /home/peter/thanotopolis/backend

# List all telephony configurations
python manual_verify_phone.py list

# Verify by tenant ID
python manual_verify_phone.py verify c7156bfd-4fb1-4588-b217-817a159c65d0

# Verify by phone number
python manual_verify_phone.py verify +14243584857

# Unverify (for testing)
python manual_verify_phone.py unverify +14243584857

# Interactive mode
python manual_verify_phone.py
```

**Current Database State (as of search):**
```
1. Tenant ID: c7156bfd-4fb1-4588-b217-817a159c65d0
   Organization Phone: +14245330093
   Status: verified ✅
   Call Forwarding: True

2. Tenant ID: 10d695f2-9223-47ef-b2bd-25eb8a66f10f
   Organization Phone: +14243584857
   Status: pending ❌
   Call Forwarding: False
```

### Method 2: Admin API Endpoints

If you have super admin access, use the API endpoints:

```bash
# Get authentication token first
TOKEN="your_super_admin_jwt_token"

# List all telephony configs
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/admin/telephony/configs

# Manual verify by config ID
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/admin/telephony/manual-verify/{config_id}

# Manual unverify by config ID
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/admin/telephony/manual-unverify/{config_id}
```

### Method 3: Direct Database Manipulation

**⚠️ Use with caution - for emergency situations only**

```sql
-- Check current verification status
SELECT 
    tc.tenant_id,
    tc.organization_phone_number,
    tc.verification_status,
    tc.call_forwarding_enabled,
    t.name as tenant_name
FROM telephony_configurations tc
JOIN tenants t ON tc.tenant_id = t.id;

-- Manually verify a phone number
UPDATE telephony_configurations 
SET 
    verification_status = 'verified',
    call_forwarding_enabled = true
WHERE organization_phone_number = '+14243584857';

-- Manually unverify (for testing)
UPDATE telephony_configurations 
SET 
    verification_status = 'pending',
    call_forwarding_enabled = false
WHERE organization_phone_number = '+14243584857';
```

## Configuration Requirements

### Environment Variables
Ensure these are set in `/backend/.env`:
```
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890
```

### User Permissions
- **Manual script**: No authentication required (direct DB access)
- **Admin API**: Requires `super_admin` role
- **Regular verification**: Requires `org_admin` or higher

## Verification Status Flow

```
[Setup] → [Pending] → [Verified] → [Call Forwarding Enabled]
              ↓            ↑
         [Failed/Expired] ← (retry)
```

**Status Values:**
- `pending`: Initial state, verification required
- `verified`: Phone ownership confirmed
- `failed`: Verification attempts failed
- `expired`: Verification code expired

## Troubleshooting

### Common Issues

1. **"No telephony configuration found"**
   - Run setup first: `POST /api/telephony/setup`
   - Check tenant ID is correct

2. **"Telephony is disabled for this organization"**
   - Check `is_enabled` field in database
   - Update via: `PATCH /api/telephony/config`

3. **"Organization phone number not verified"**
   - Use manual bypass methods above
   - Check verification status in database

4. **Frontend shows "verification required"**
   - Clear browser cache
   - Check API responses for updated status
   - Verify JWT token is valid

### Verification Checking

```bash
# Check via script
python manual_verify_phone.py list

# Check via API (requires auth)
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/telephony/config

# Check database directly
psql -d thanotopolis -c "
SELECT organization_phone_number, verification_status, call_forwarding_enabled 
FROM telephony_configurations;"
```

## Security Notes

- Manual bypass bypasses all security checks
- Only use for testing/development environments  
- Production systems should use proper verification
- Admin API endpoints require super admin role
- All bypass actions are logged for audit trails

## Files Involved

**Backend:**
- `/backend/manual_verify_phone.py` - Manual bypass script
- `/backend/app/api/admin.py` - Admin override endpoints
- `/backend/app/api/telephony.py` - Regular verification endpoints
- `/backend/app/services/telephony_service.py` - Verification business logic
- `/backend/app/models/models.py` - Database models

**Frontend:**
- `/frontend/src/services/telephony.ts` - Verification service
- Telephony setup components (referenced but not detailed)

**Database:**
- `telephony_configurations` table
- `phone_verification_attempts` table

Use these methods to bypass phone verification when needed for testing or administrative purposes.