# Claude Development Context

## Deepgram Voice Agent Integration

### Current Implementation Status

The telephony application has successfully integrated **Deepgram Voice Agent** as the primary conversational AI solution for phone calls. This replaces the traditional STT → LLM → TTS pipeline with a unified WebSocket-based service.

#### Key Components:
- **VoiceAgentService** (`app/services/voice/deepgram_voice_agent.py`): Core WebSocket client managing real-time conversational AI
- **TelephonyVoiceAgentHandler** (`app/api/telephony_voice_agent.py`): Bridges Twilio MediaStream with Deepgram Voice Agent
- **Feature Flag Integration**: Controlled rollout with `USE_VOICE_AGENT` and `VOICE_AGENT_ROLLOUT_PERCENTAGE`

#### Technical Details:
- **Audio Format**: mulaw 8kHz for telephony compatibility
- **Models**: nova-3 (STT), gpt-4o-mini (LLM), aura-2-thalia-en (TTS)
- **Real-time Processing**: Bidirectional audio streaming via WebSocket
- **Usage Tracking**: STT/TTS word counts and call duration metrics
- **Auto-summarization**: Post-call summary generation

### Agent Collaboration System Analysis

The chat application implements a sophisticated agent collaboration system:

#### Core Architecture:
- **MODERATOR Agent**: Central orchestrator for routing user queries to specialist agents
- **AgentManager**: Dynamic agent discovery and conversation processing
- **CollaborationManager**: Multi-agent collaboration with parallel execution and response synthesis
- **20+ Specialist Agents**: Cultural, regulatory, service-specific expertise

#### Key Features:
- Dynamic agent selection based on query analysis
- Parallel agent execution with 30s individual / 90s total timeouts
- LLM-powered response synthesis from multiple agent perspectives
- Real-time WebSocket streaming with typing indicators

## Proposed Voice Agent Collaboration Integration

### Option B: Hybrid Implementation with Caller Consent

**Estimated Effort: 4-6 weeks** (reduced from 8-12 weeks due to consent-based approach)

#### Phase 1: Consent Workflow (1-2 weeks)
Implement caller consent mechanism for accessing specialist expertise:

```python
# Voice Agent detects complex query requiring specialist knowledge
await voice_agent.inject_message(
    "I can give you a quick response, or consult with my specialist team "
    "for a more comprehensive answer. Would you like me to check with the "
    "experts? This will take about 30 seconds."
)
```

**Technical Implementation:**
- Query complexity detection logic
- Consent detection from caller response
- Graceful fallback for declined collaboration

#### Phase 2: Collaboration Bridge (2-3 weeks)
Bridge Voice Agent with existing collaboration system:

```python
# Pause Voice Agent and route to collaboration system
await voice_agent.update_instructions("Please hold while I consult with specialists...")
collaborative_response = await collaboration_manager.process_query(
    user_message, selected_agents
)
```

**Key Components:**
- Voice Agent pause/resume state management
- Message routing to MODERATOR system
- Collaboration trigger without real-time streaming requirements
- Response adaptation for voice delivery

#### Phase 3: Seamless Handoff (1 week)
Integrate collaborative responses back into voice conversation:

```python
# Resume Voice Agent with expert knowledge
await voice_agent.update_instructions(
    f"Based on expert consultation: {collaborative_response}. "
    f"Continue the conversation naturally with this enhanced context."
)
```

**Features:**
- Smooth transition back to Voice Agent
- Context preservation across collaboration
- Natural conversation flow resumption

### Technical Advantages

#### Leverages Existing Capabilities:
- **Real-time Instruction Updates**: `update_instructions()` and `inject_message()` methods already implemented
- **Collaboration Infrastructure**: Complete MODERATOR + specialist agent system available
- **Session Management**: Robust Voice Agent session handling in place

#### Simplified Architecture:
- **No Real-time Streaming Integration**: Collaboration happens during explicit pause
- **Clear Error Handling**: Defined fallback paths when collaboration fails
- **User-Controlled Complexity**: Only activates when caller explicitly requests it
- **Manageable Latency**: Caller expects wait time after consenting to specialist consultation

### Benefits

1. **Enhanced Expertise**: Access to 20+ specialist agents for complex queries
2. **User Choice**: Callers control when to access deeper expertise
3. **Reduced Complexity**: Consent-based approach eliminates real-time streaming challenges
4. **Graceful Degradation**: Clear fallback to standard Voice Agent responses
5. **Scalable Implementation**: Incremental rollout using existing feature flag system

### Next Steps

1. **Implement Consent Detection**: Add logic to identify when collaboration would be beneficial
2. **Create Collaboration Bridge**: Develop service to pause Voice Agent and route to MODERATOR
3. **Test Integration**: Validate seamless handoff between Voice Agent and collaboration system
4. **Performance Optimization**: Ensure sub-30s collaboration response times for telephony use
5. **Deployment Strategy**: Gradual rollout with monitoring and fallback mechanisms

---

## Stripe Billing System

### Implementation Overview

The platform features a comprehensive Stripe-based billing system with subscription management, usage-based pricing, and automated monthly billing.

#### Core Architecture:
- **Stripe Integration**: Full customer, subscription, and invoice management
- **Usage Tracking**: Real-time monitoring of voice services and phone calls
- **Automated Billing**: Monthly invoice generation with detailed usage breakdown
- **Demo Account Support**: Billing exemption for demo organizations

#### Database Models (`backend/app/models/stripe_models.py`):
- **StripeCustomer**: Links tenants to Stripe customers
- **StripeSubscription**: Tracks subscription lifecycle and billing periods
- **StripeInvoice**: Stores invoice history with usage tracking

#### Pricing Structure:
- **Monthly Subscription**: $299/month for platform access
- **Voice Usage**: $1.00 per 1,000 words (STT/TTS)
- **Phone Calls**: $1.00 per call + voice usage charges

### Key Features

#### Subscription Management:
- Stripe Checkout integration for new signups
- Cancel at period end with reactivation option
- Customer portal for payment method management
- Automatic trial period support

#### Billing API (`backend/app/api/billing.py`):
- Customer workflow endpoints (checkout, signup, portal)
- Subscription management (cancel, reactivate)
- Admin features (demo status, billing dashboard)
- Webhook event handling

#### Frontend Components:
- **BillingDashboard**: Subscription status, usage stats, invoice history
- **Organization Signup**: New customer onboarding flow
- **Admin Dashboard**: Platform-wide revenue and usage metrics

#### Automated Billing (`backend/app/services/billing_automation.py`):
- Monthly billing runs on 1st of each month
- Usage calculation for previous month
- Automated invoice generation and delivery
- Demo account exclusion

#### Configuration:
- Stripe API keys and webhook secrets
- Monthly subscription price ID
- Demo account flags in tenant model

### Usage

#### Manual Billing Trigger:
```python
from app.services.billing_automation import trigger_manual_billing
await trigger_manual_billing()  # Bills for previous month
```

#### Demo Account Management:
```python
# Mark organization as demo (exempt from billing)
POST /api/billing/set-demo-status/{tenant_id}
```

---

## CRM System Implementation (July 1, 2025)

### Overview
Successfully implemented a comprehensive Customer Relationship Management (CRM) system with contact management, interaction tracking, email integration, and billing system connectivity.

#### Core Features Implemented

##### 1. Database Models (`backend/app/models/models.py`)
- **Contact Model**: Core contact information with business details, contact person, and status tracking
- **ContactInteraction Model**: Track all customer touchpoints (calls, emails, meetings, notes, tasks)
- **CustomField Model**: Dynamic custom fields per organization with validation rules
- **EmailTemplate Model**: Templated email system with Jinja2 variable substitution
- **Billing Integration**: Links contacts to Stripe customers for subscription status

##### 2. API Implementation (`backend/app/api/crm.py`)
- **Dashboard Endpoint**: Statistics, recent activity, contact growth metrics
- **Contact CRUD**: Full create, read, update, delete operations with search/filtering
- **CSV Import**: Bulk contact import with field mapping and duplicate handling
- **Interaction Tracking**: Log and retrieve all customer interactions with timeline view
- **Custom Fields Management**: Dynamic field creation and validation per organization
- **Billing Status Integration**: Shows subscription status and payment history

##### 3. Email Service (`backend/app/services/email_service.py`)
- **SendGrid Integration**: Professional email delivery with error handling
- **Template System**: Jinja2-powered templates with variable substitution
- **Bulk Email**: Send personalized emails to multiple contacts
- **Default Templates**: Welcome emails, follow-ups, invoice reminders
- **HTML/Text Support**: Automatic HTML-to-text conversion

##### 4. Frontend Interface (`frontend/src/app/organizations/crm/page.tsx`)
- **Card-Based Layout**: Contact cards with key information at a glance
- **Admin-Only Access**: Restricted to admin and super_admin roles
- **Dashboard Stats**: Visual metrics and recent activity display
- **Search & Filter**: Real-time search by name/email and status filtering
- **CSV Import UI**: Complete import workflow with field mapping interface
- **Responsive Design**: Works on desktop and mobile devices

#### Key Implementation Details

##### Database Schema:
```sql
-- Contacts table with full business and contact information
CREATE TABLE contacts (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    business_name VARCHAR NOT NULL,
    city VARCHAR, state VARCHAR,
    contact_name VARCHAR NOT NULL,
    contact_email VARCHAR,
    contact_role VARCHAR,
    phone VARCHAR, website VARCHAR,
    address TEXT, notes TEXT,
    status VARCHAR DEFAULT 'lead',
    custom_fields JSONB DEFAULT '{}',
    stripe_customer_id VARCHAR,  -- Billing integration
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Interaction tracking for complete customer timeline
CREATE TABLE contact_interactions (
    id UUID PRIMARY KEY,
    contact_id UUID REFERENCES contacts(id),
    user_id UUID REFERENCES users(id),
    interaction_type VARCHAR NOT NULL,  -- phone_call, email, meeting, note, task, follow_up
    subject VARCHAR,
    content TEXT NOT NULL,
    interaction_date TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Dynamic custom fields per organization
CREATE TABLE custom_fields (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    field_name VARCHAR NOT NULL,
    field_label VARCHAR NOT NULL,
    field_type VARCHAR NOT NULL,  -- text, number, date, email, phone, select, boolean
    field_options JSONB DEFAULT '{}',
    is_required BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by_user_id UUID REFERENCES users(id),
    UNIQUE(tenant_id, field_name)
);

-- Email templates with variable substitution
CREATE TABLE email_templates (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    name VARCHAR NOT NULL,
    subject VARCHAR NOT NULL,
    html_content TEXT NOT NULL,
    text_content TEXT,
    variables JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_by_user_id UUID REFERENCES users(id),
    UNIQUE(tenant_id, name)
);
```

##### Contact Status Workflow:
- **Lead**: Initial prospect, not yet qualified
- **Prospect**: Qualified lead, actively pursuing
- **Customer**: Active paying customer
- **Qualified**: Ready to close
- **Closed Won**: Successfully closed deal
- **Closed Lost**: Unsuccessful pursuit
- **Inactive**: No longer pursuing

##### Security & Access Control:
- **Admin-Only Access**: CRM restricted to users with `admin` or `super_admin` roles
- **Tenant Isolation**: All data scoped to current organization
- **API Authentication**: All endpoints require valid JWT tokens
- **Email Validation**: Prevents duplicate contacts within organization

##### Email Integration Features:
- **Template Variables**: Dynamic content insertion (`{{contact_name}}`, `{{business_name}}`, `{{organization_name}}`)
- **Bulk Operations**: Send personalized emails to filtered contact lists
- **Default Templates**: Pre-built templates for common scenarios
- **SendGrid API**: Professional delivery with tracking and analytics

##### CSV Import Capabilities:
- **Field Mapping**: Map CSV columns to contact fields via drag-and-drop interface
- **Duplicate Handling**: Option to update existing contacts or skip duplicates
- **Error Reporting**: Detailed validation errors with row-by-row feedback
- **Preview System**: Preview mapped data before import
- **Batch Processing**: Handles large CSV files efficiently

#### Configuration Requirements

##### Environment Variables:
```bash
# SendGrid Configuration
SENDGRID_API_KEY=your_sendgrid_api_key_here
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your Organization Name

# Existing billing and database configurations continue to work
```

##### Frontend Navigation:
- Added CRM link to organization navigation sidebar
- Admin-only visibility based on user role
- Icon: UserCheck from Lucide React
- Located at `/organizations/crm`

#### Usage Examples

##### Creating a Contact:
```python
contact_data = {
    "business_name": "Acme Corporation",
    "contact_name": "John Smith",
    "contact_email": "john.smith@acme.com",
    "contact_role": "CEO",
    "phone": "+1-555-123-4567",
    "city": "New York",
    "state": "NY",
    "status": "lead",
    "notes": "Interested in enterprise plan, has 500+ employees"
}
```

##### CSV Import Format:
```csv
business_name,contact_name,contact_email,phone,city,state,status,notes
"Acme Corp","John Smith","john@acme.com","+1-555-123-4567","New York","NY","lead","Enterprise prospect"
"Beta Inc","Jane Doe","jane@beta.com","+1-555-987-6543","Los Angeles","CA","prospect","Follow up in 2 weeks"
```

##### Email Template Example:
```html
<h2>Welcome {{contact_name}}!</h2>
<p>Thank you for your interest in {{organization_name}}. We're excited to potentially work with {{business_name}}.</p>
<p>Based on our conversation, I understand you're looking for solutions that can help with your specific needs.</p>
<p>Best regards,<br>{{organization_name}} Team</p>
```

#### Benefits Achieved

1. **Centralized Contact Management**: All customer data organized in one location
2. **Complete Interaction History**: Timeline view of all customer touchpoints
3. **Professional Email Campaigns**: Templated emails with personalization
4. **Billing Integration**: Direct connection to subscription and payment data
5. **Scalable Architecture**: Custom fields support unique business requirements
6. **Security First**: Admin-only access with tenant isolation
7. **User-Friendly Interface**: Intuitive card-based design with search/filter
8. **Bulk Operations**: CSV import and bulk email capabilities for efficiency

#### Current Status:
- ✅ **Complete Implementation**: All core CRM features implemented and tested
- ✅ **Database Models**: Full schema with indexes for performance
- ✅ **API Endpoints**: Complete CRUD operations with advanced filtering
- ✅ **Frontend Interface**: Professional UI with admin access controls
- ✅ **Email Integration**: SendGrid service with template system
- ✅ **CSV Import**: Full import workflow with validation and error handling
- ✅ **Billing Integration**: Links contacts to subscription status

### Email Campaign Analytics (July 8, 2025)

#### Overview
Enhanced the CRM system with comprehensive email campaign tracking and analytics capabilities, providing detailed insights into campaign performance with open rates, click rates, and engagement metrics.

#### Core Components Implemented

##### 1. Email Tracking Service (`backend/app/services/email_tracking_service.py`)
- **Campaign Management**: Create, send, and track email campaigns
- **Real-time Tracking**: Track opens, clicks, and bounces
- **Analytics Calculation**: Compute open rates, click rates, CTR, and bounce rates
- **Event Logging**: Detailed event timeline for each recipient

##### 2. Database Models for Email Tracking
```sql
-- Email campaigns table
CREATE TABLE email_campaigns (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    name VARCHAR NOT NULL,
    subject VARCHAR NOT NULL,
    html_content TEXT NOT NULL,
    text_content TEXT,
    status VARCHAR DEFAULT 'draft',  -- draft, sending, sent, partial
    recipient_count INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    opened_count INTEGER DEFAULT 0,
    clicked_count INTEGER DEFAULT 0,
    bounced_count INTEGER DEFAULT 0,
    track_opens BOOLEAN DEFAULT TRUE,
    track_clicks BOOLEAN DEFAULT TRUE,
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Email recipients tracking
CREATE TABLE email_recipients (
    id UUID PRIMARY KEY,
    campaign_id UUID REFERENCES email_campaigns(id),
    contact_id UUID REFERENCES contacts(id),
    email_address VARCHAR NOT NULL,
    name VARCHAR,
    tracking_id UUID UNIQUE NOT NULL,
    status VARCHAR DEFAULT 'pending',  -- pending, sent, bounced, failed
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    first_opened_at TIMESTAMP,
    first_clicked_at TIMESTAMP,
    last_opened_at TIMESTAMP,
    last_clicked_at TIMESTAMP,
    open_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    sendgrid_message_id VARCHAR,
    error_message TEXT
);

-- Email events tracking
CREATE TABLE email_events (
    id UUID PRIMARY KEY,
    recipient_id UUID REFERENCES email_recipients(id),
    event_type VARCHAR NOT NULL,  -- opened, clicked, bounced, dropped, deferred
    timestamp TIMESTAMP DEFAULT NOW(),
    user_agent TEXT,
    ip_address VARCHAR,
    url TEXT,  -- For click events
    metadata JSONB DEFAULT '{}'
);
```

##### 3. API Endpoints (`backend/app/api/crm.py`)
- `GET /api/crm/email-campaigns` - List all campaigns with metrics
- `GET /api/crm/email-campaigns/{campaign_id}/analytics` - Detailed campaign analytics
- `GET /api/crm/email-recipients/{recipient_id}/analytics` - Individual recipient analytics
- `GET /api/crm/email-tracking/open/{tracking_id}` - Track email opens
- `GET /api/crm/email-tracking/click/{tracking_id}` - Track link clicks

##### 4. Frontend Campaign Analytics (`frontend/src/app/organizations/crm/campaigns/`)

###### Campaigns List Page (`page.tsx`)
- **Overview Dashboard**: Aggregate statistics across all campaigns
- **Campaign Table**: Sortable list with key metrics
- **Visual Indicators**: Color-coded performance metrics
- **Search & Filter**: Find campaigns by name or subject
- **Pagination**: Handle large campaign lists
- **Quick Actions**: Direct links to detailed analytics

###### Individual Campaign Analytics (`[id]/page.tsx`)
- **Key Metrics Cards**: Recipients, sends, opens, clicks
- **Engagement Rates**: Visual progress bars with industry comparisons
- **Performance Breakdown**: Detailed delivery statistics
- **Visual Alerts**: Warnings for high bounce rates
- **Campaign Timeline**: Created and sent dates
- **Export Options**: (Future enhancement)

#### Analytics Metrics Provided

##### Campaign Level:
- **Total Recipients**: Number of contacts targeted
- **Sent Count**: Successfully delivered emails
- **Open Rate**: Percentage of recipients who opened
- **Click Rate**: Percentage of recipients who clicked
- **Click-Through Rate (CTR)**: Clicks as percentage of opens
- **Bounce Rate**: Failed delivery percentage

##### Aggregate Statistics:
- **Total Campaigns**: All-time campaign count
- **Total Emails Sent**: Cumulative sends
- **Average Open Rate**: Cross-campaign average
- **Average Click Rate**: Cross-campaign average

#### UI/UX Features

##### Navigation:
- Added "View Campaigns" button in CRM Quick Actions
- Located between "Send Email Campaign" and "Export Contacts"
- Uses BarChart3 icon for visual consistency

##### Design Patterns:
- **Responsive Layout**: Works on desktop and mobile
- **Loading States**: Skeleton loaders and progress indicators
- **Error Handling**: Graceful fallbacks and user-friendly messages
- **Access Control**: Admin-only viewing permissions
- **Visual Hierarchy**: Important metrics highlighted

##### Performance Indicators:
- **Green highlighting**: Above-average performance (>25% open rate, >5% click rate)
- **Industry benchmarks**: 21.5% average open rate, 2.6% average click rate
- **Status badges**: Visual campaign status indicators

#### Integration Points

##### With Email Service:
- Automatic tracking pixel insertion for opens
- Link wrapping for click tracking
- SendGrid webhook integration for real-time updates

##### With CRM Contacts:
- Links email recipients to contact records
- Tracks engagement history per contact
- Enables targeted follow-ups based on engagement

#### Current Status:
- ✅ **Backend Implementation**: Complete tracking service and API
- ✅ **Database Schema**: Full tracking tables with indexes
- ✅ **Frontend UI**: Campaign list and analytics pages
- ✅ **Navigation Integration**: Quick access from CRM dashboard
- ✅ **Real-time Tracking**: Open and click event logging
- ✅ **Analytics Calculation**: All key metrics computed

#### Future Enhancement Opportunities:
1. **Advanced Email Campaigns**: Automated drip campaigns and segmentation
2. **A/B Testing**: Compare campaign variations
3. **Recipient Timeline**: Individual engagement history view
4. **Export Analytics**: PDF/CSV reports for campaigns
5. **Real-time Updates**: WebSocket for live metric updates
6. **Heatmap Analysis**: Click location tracking
7. **Mobile App**: Native mobile interface for field sales teams
8. **Calendar Integration**: Schedule and track meetings directly in CRM
9. **Advanced Analytics**: Contact scoring, pipeline forecasting, and conversion metrics
10. **API Webhooks**: Real-time integration with external CRM and marketing systems
11. **Document Management**: Attach files, contracts, and documents to contacts
12. **Task Management**: Advanced task scheduling and reminder system
13. **Integration Hub**: Connect with popular tools like Slack, Salesforce, HubSpot

---

## Development Commands

### Testing
- `pytest` - Run test suite
- `npm run test` - Frontend tests (if applicable)

### Voice Agent Testing
- `python test_voice_agent.py` - Voice Agent connection testing
- `python debug_voice_agent_events.py` - Real-time event monitoring
- Frontend test: `telephony/test/simulate-call`

### Linting
- `ruff check` - Python linting
- `ruff format` - Python formatting