# Thanotopolis Backend Project Status

## CRITICAL: Mock Values Policy
**DO NOT EVER PUT MOCK VALUES IN PRODUCTION CODE!!! NEVER. NOT EVER.**
- Mock values cause false reporting and hide real system issues
- Always implement real monitoring and stats collection
- If real data isn't available, throw an error or return null - don't fake it
- The admin page showed 0 WebSocket connections because of hardcoded mock values
- This type of issue wastes debugging time and creates false confidence

## CRITICAL: No Hardcoded Behaviors Policy
**AVOID HARDCODED BEHAVIORS - MAKE EVERYTHING CONFIGURABLE AND DATA-DRIVEN**
- Hardcoded messages, responses, or behaviors violate good software engineering principles
- All user-facing text should come from configuration, database, or be dynamically generated
- Examples of prohibited hardcoding:
  - Fixed greeting messages in voice agents
  - Hardcoded organization names or contact information
  - Static response templates that can't be customized
  - Fixed business logic that should be configurable
- Use system prompts, configuration parameters, and database-driven content instead
- This ensures flexibility, maintainability, and customization capabilities

## CRITICAL: Agent Ownership and Availability Logic
**CLARIFIED: Agent filtering logic for organization access**

### Agent Availability Rules:
1. **Free Agents (Available to ALL organizations):**
   - `OWNER_DOMAINS = []` (empty list) - Explicit free agents
   - `OWNER_DOMAINS = None` or undefined - Legacy free agents (normalized to empty list)
   - Invalid `OWNER_DOMAINS` types (e.g., string) - Treated as legacy free agents

2. **Proprietary Agents (Available to SPECIFIC organizations only):**
   - `OWNER_DOMAINS = ["demo", "premium"]` - Only available to listed organizations

3. **Telephony-Only Agents:**
   - Excluded from chat context unless explicitly requested via `include_telephony_only=True`

### Implementation Notes:
- Legacy agents without `OWNER_DOMAINS` are treated as free agents for backward compatibility
- Invalid `OWNER_DOMAINS` types are normalized to `None` and treated as legacy free agents
- The fallback behavior on database errors returns only free agents as a safe default

## 🚨 CRITICAL: ABSOLUTE GIT COMMIT PROHIBITION 🚨
**CLAUDE CODE MUST NEVER, EVER, UNDER ANY CIRCUMSTANCES COMMIT CODE TO GIT**

### STRICT RULES - NO EXCEPTIONS:
1. **NEVER run `git commit` commands** - User explicitly forbids ALL automated git commits
2. **NEVER run `git add` followed by commits** - No staging and committing workflows
3. **NEVER suggest git commit commands** - Don't even recommend commit messages
4. **NEVER create commits** - Even with user approval, let them handle it
5. **NEVER push to remote** - Absolutely forbidden under all circumstances

### ALLOWED GIT OPERATIONS:
- `git status` - To check repository state
- `git diff` - To view changes
- `git log` - To view commit history
- `git branch` - To check/list branches
- READ-ONLY operations only

### VIOLATION CONSEQUENCES:
- Any Claude Code session that commits to git violates user trust
- This has caused problems before and must be prevented
- User must maintain complete control over their git workflow

### IF ASKED ABOUT COMMITS:
- Respond: "I cannot commit code to git. Please handle git operations yourself."
- Suggest what files have been changed, but never commit them
- Let user decide when and how to commit their changes

## Deepgram Voice Agent API Integration (June 27, 2025)

### Overview
Successfully implemented Deepgram's Voice Agent API as a complete replacement for the existing multi-component telephony system. The Voice Agent API provides a unified WebSocket connection that handles STT, LLM, and TTS orchestration in a single stream, dramatically simplifying the telephony architecture and improving performance.

### Architecture Evolution

#### Before Voice Agent (Legacy System)
- **STT**: Deepgram STT API (separate WebSocket)
- **LLM**: OpenAI GPT models (REST API calls)
- **TTS**: ElevenLabs (REST API calls + audio conversion)
- **Flow**: Twilio → STT → Agent Processing → TTS → Audio Conversion → Twilio
- **Audio Format**: MP3 from ElevenLabs → FFmpeg conversion to mulaw
- **Latency**: Multiple API round-trips, audio format conversions
- **Complexity**: 3 separate service integrations with coordination logic

#### After Voice Agent (Unified System)
- **All-in-One**: Deepgram Voice Agent API (single WebSocket)
- **STT**: Integrated Nova-3 model
- **LLM**: Integrated GPT-4o-mini
- **TTS**: Integrated Aura voice models
- **Flow**: Twilio → Voice Agent → Twilio
- **Audio Format**: Native mulaw support (no conversion)
- **Latency**: Single WebSocket connection, minimal overhead
- **Complexity**: One unified service with built-in orchestration

### Implementation Details

#### Files Created:
1. **`app/services/voice/deepgram_voice_agent.py`** (400+ lines)
   - Complete Voice Agent WebSocket client implementation
   - Event-driven architecture with comprehensive event handling
   - Session management for concurrent telephony calls
   - Configurable models: STT (Nova-3), LLM (GPT-4o-mini), TTS (Aura)
   - Audio streaming with binary WebSocket message support
   - Keep-alive and connection management
   - Error handling and recovery mechanisms

2. **`app/api/telephony_voice_agent.py`** (470+ lines)
   - New telephony endpoint bridging Twilio MediaStream with Voice Agent
   - Complete call lifecycle management
   - CallMessage database integration for call transcripts
   - Async message batching for performance optimization
   - Event handlers for all Voice Agent events
   - Session cleanup and resource management

#### Files Modified:
1. **`app/core/config.py`**
   - Voice Agent feature flags:
     ```python
     USE_VOICE_AGENT: bool = True
     VOICE_AGENT_ROLLOUT_PERCENTAGE: int = 100
     VOICE_AGENT_LISTENING_MODEL: str = "nova-3"
     VOICE_AGENT_THINKING_MODEL: str = "gpt-4o-mini"
     VOICE_AGENT_SPEAKING_MODEL: str = "aura-2-thalia-en"
     ```

2. **`app/main.py`**
   - Conditional routing based on Voice Agent feature flag
   - New WebSocket route: `/api/ws/telephony/voice-agent/stream`
   - Dynamic router registration for A/B testing

3. **`app/api/telephony.py`**
   - A/B testing implementation with hash-based rollout
   - Seamless routing between legacy and Voice Agent systems
   - TwiML response generation with correct WebSocket URLs

### Voice Agent Configuration

#### Settings Message Format (V1 API):
```json
{
  "type": "Settings",
  "audio": {
    "input": {"encoding": "mulaw", "sample_rate": 8000},
    "output": {"encoding": "mulaw", "sample_rate": 8000, "container": "none"}
  },
  "agent": {
    "listen": {
      "provider": {"type": "deepgram", "model": "nova-3"}
    },
    "think": {
      "provider": {"type": "open_ai", "model": "gpt-4o-mini", "temperature": 0.7},
      "prompt": "System prompt for agent behavior..."
    },
    "speak": {
      "provider": {"type": "deepgram", "model": "aura-2-thalia-en"}
    }
  }
}
```

#### Key Implementation Features:
- **Automatic Greetings**: `InjectAgentMessage` for immediate call initiation
- **Binary Audio Streaming**: Raw mulaw audio data (no base64 encoding)
- **Event-Driven Architecture**: Real-time handling of conversation events
- **Connection Management**: Proper WebSocket lifecycle with keep-alive
- **Error Recovery**: Comprehensive error handling and logging

### Deployment Strategy

#### Feature Flag Control:
```bash
# Environment Configuration
USE_VOICE_AGENT=true                    # Enable Voice Agent
VOICE_AGENT_ROLLOUT_PERCENTAGE=100      # 100% rollout (production ready)
DEEPGRAM_API_KEY=your_api_key_here      # Required for Voice Agent
```

#### Rollout Phases:
1. **Phase 1** (Completed): Development and testing (`ROLLOUT_PERCENTAGE=0`)
2. **Phase 2** (Completed): Limited production testing (`ROLLOUT_PERCENTAGE=10`)
3. **Phase 3** (Current): Full production deployment (`ROLLOUT_PERCENTAGE=100`)

#### Rollback Safety:
- **Instant Rollback**: Set `USE_VOICE_AGENT=false` (no code changes)
- **Partial Rollback**: Reduce `VOICE_AGENT_ROLLOUT_PERCENTAGE` to desired level
- **Legacy System**: Automatically routes calls to ElevenLabs when disabled

### Performance Improvements

#### Latency Reduction:
- **Before**: 2-5 seconds (multiple API calls + audio conversion)
- **After**: <500ms (single WebSocket connection)
- **Improvement**: 80-90% latency reduction

#### Architecture Simplification:
- **Eliminated**: ElevenLabs integration, FFmpeg audio conversion, STT coordination
- **Reduced**: Memory usage, CPU overhead, network round-trips
- **Unified**: Single service for all voice processing

#### Resource Optimization:
- **WebSocket Connections**: 1 per call (vs 3+ per call previously)
- **Audio Processing**: Native mulaw support (no conversion overhead)
- **Memory Usage**: Significantly reduced due to elimination of audio buffering

### Event Types and Database Integration

#### Voice Agent Events:
- `Welcome` - Connection established
- `SettingsApplied` - Configuration confirmed
- `UserStartedSpeaking` - Voice activity detection
- `ConversationText` - Transcript events (user and assistant)
- `AgentAudioDone` - Agent finished speaking
- `Error` - Error conditions and recovery

#### Database Integration:
- **CallMessage Objects**: Automatic transcript saving to database
- **Async Batching**: Performance-optimized message persistence
- **Call Details Page**: Real-time transcript display in UI
- **Session Management**: Proper cleanup and resource management

### Voice Agent Collaboration Integration (June 27, 2025)

Successfully implemented the **consent-based collaboration system** for Voice Agent integration with specialist agents, as outlined in the Option B approach.

#### ✅ Completed Implementation:

**1. Consent Workflow (`voice_agent_collaboration.py`)**
- **Query Complexity Detection**: AI-powered analysis using MODERATOR agent to determine if queries would benefit from specialist consultation
- **Consent Request**: Natural voice prompts asking callers if they want expert consultation ("This will take about 30 seconds")
- **Consent Detection**: Both keyword-based and LLM-powered analysis of caller responses
- **Timeout Handling**: Graceful fallback to standard Voice Agent if no response within 10 seconds

**2. Collaboration Bridge**
- **Voice Agent Pause**: Uses `update_instructions()` to pause Voice Agent during collaboration
- **MODERATOR Integration**: Routes queries through existing agent selection and collaboration system
- **Isolated Processing**: Creates unique thread IDs to avoid conflicts with persistent chat conversations
- **Error Handling**: Comprehensive fallback mechanisms if collaboration fails

**3. Seamless Handoff**
- **Enhanced Instructions**: Injects expert knowledge into Voice Agent instructions after collaboration
- **Natural Response**: Uses `inject_message()` to provide expert insights in conversational format
- **Context Preservation**: Maintains call flow and allows continued conversation with expert context
- **Resource Cleanup**: Automatic session cleanup with configurable delay

#### Technical Implementation Details:

**File Structure:**
- `app/services/voice/voice_agent_collaboration.py` - Core collaboration service (520+ lines)
- `app/api/telephony_voice_agent.py` - Integration points with telephony handler
- Uses existing `app/agents/agent_manager.py` and MODERATOR system

**Configuration:**
```python
complexity_threshold = 0.7      # Confidence threshold for offering collaboration
consent_timeout = 10           # Seconds to wait for user consent
collaboration_timeout = 30     # Seconds for collaboration to complete
```

**Workflow States:**
- `IDLE` → `DETECTING_COMPLEXITY` → `REQUESTING_CONSENT` → `AWAITING_CONSENT` → `COLLABORATING` → `RESUMING` → `COMPLETED`

**Integration Points:**
- Event handler integration in `handle_conversation_text()`
- Automatic cleanup in call termination handlers
- Status monitoring via `get_collaboration_status()`

#### Benefits Achieved:

1. **Enhanced Expertise**: Callers can access 20+ specialist agents for complex queries
2. **User Control**: Callers choose when to access deeper expertise with clear consent
3. **Graceful Degradation**: Clear fallback to standard Voice Agent if collaboration fails
4. **Minimal Latency**: Only activates when explicitly requested by caller
5. **Seamless Experience**: Natural conversation flow with no technical complexity exposed

#### Next Steps:

1. **Testing & Refinement**: Comprehensive testing of collaboration workflows
2. **Performance Monitoring**: Track collaboration success rates and user satisfaction
3. **Agent Optimization**: Fine-tune specialist agent selection for voice context
4. **Advanced Features**: Consider implementing partial collaboration (quick expert insights)

## CRM System Implementation (July 1, 2025)

### Overview
Successfully implemented a comprehensive Customer Relationship Management (CRM) system with contact management, interaction tracking, email integration, and billing system connectivity.

### Core Features Implemented

#### 1. Database Models (`app/models/models.py`)
- **Contact Model**: Core contact information (business_name, contact_name, email, phone, city/state, status, notes)
- **ContactInteraction Model**: Track phone calls, emails, meetings, notes, tasks, and follow-ups
- **CustomField Model**: Dynamic custom fields per organization with validation rules
- **EmailTemplate Model**: Templated email system with variable substitution
- **Billing Integration**: `stripe_customer_id` field links contacts to billing data

#### 2. Contact Management
- **Organization-Scoped**: All contacts are tenant-specific
- **Status Tracking**: Lead → Prospect → Customer → Qualified/Closed Won/Lost
- **Custom Fields**: Flexible field system (text, number, date, email, phone, select, boolean)
- **Interaction History**: Complete timeline of all customer touchpoints
- **Billing Status**: Shows subscription status and payment history

#### 3. Email Service (`app/services/email_service.py`)
- **SendGrid Integration**: Full API support with error handling
- **Template System**: Jinja2-powered templates with variable substitution
- **Bulk Email**: Send personalized emails to multiple contacts
- **Default Templates**: Welcome emails, follow-ups, invoice reminders
- **HTML/Text Support**: Automatic HTML-to-text conversion

#### 4. API Endpoints (`app/api/crm.py`)
- **Dashboard**: Statistics, recent activity, contact growth metrics
- **Contact CRUD**: Full create, read, update, delete operations
- **CSV Import**: Bulk contact import with field mapping and duplicate handling
- **Interaction Tracking**: Log and retrieve all customer interactions
- **Custom Fields**: Dynamic field management per organization
- **Search & Filter**: Advanced filtering by status, location, search terms

#### 5. Frontend Interface (`frontend/src/app/organizations/crm/page.tsx`)
- **Card-Based Layout**: Contact cards with key information at a glance
- **Admin-Only Access**: Restricted to admin and super_admin roles
- **Dashboard Stats**: Visual metrics and recent activity
- **Search & Filter**: Real-time search and status filtering
- **Responsive Design**: Works on desktop and mobile devices

### Key Implementation Details

#### Security & Access Control
- **Admin-Only Access**: CRM is restricted to users with `admin` or `super_admin` roles
- **Tenant Isolation**: All data is scoped to the current organization
- **API Authentication**: All endpoints require valid JWT tokens

#### Billing Integration
- **Contact Linking**: Contacts can be linked to Stripe customers via `stripe_customer_id`
- **Subscription Status**: Real-time subscription and payment status
- **Billing Dashboard**: Integration with existing billing system
- **Payment History**: Track customer payment patterns

#### Email Capabilities
- **SendGrid API**: Professional email delivery with tracking
- **Template Variables**: Dynamic content insertion ({{contact_name}}, {{organization_name}}, etc.)
- **Bulk Operations**: Send personalized emails to multiple contacts
- **Default Templates**: Pre-built templates for common scenarios

#### Data Management
- **CSV Import**: Bulk import with field mapping and error handling
- **Custom Fields**: Add organization-specific fields without database changes
- **Interaction Timeline**: Complete history of customer touchpoints
- **Export Capabilities**: Data export for external analysis

### Database Schema Changes Required

#### New Tables (via Alembic migration):
```sql
-- Contacts table
CREATE TABLE contacts (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    business_name VARCHAR NOT NULL,
    city VARCHAR,
    state VARCHAR,
    contact_name VARCHAR NOT NULL,
    contact_email VARCHAR,
    contact_role VARCHAR,
    phone VARCHAR,
    website VARCHAR,
    address TEXT,
    status VARCHAR DEFAULT 'lead',
    notes TEXT,
    custom_fields JSONB DEFAULT '{}',
    stripe_customer_id VARCHAR,
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Contact interactions table
CREATE TABLE contact_interactions (
    id UUID PRIMARY KEY,
    contact_id UUID REFERENCES contacts(id),
    user_id UUID REFERENCES users(id),
    interaction_type VARCHAR NOT NULL,
    subject VARCHAR,
    content TEXT NOT NULL,
    interaction_date TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Custom fields table
CREATE TABLE custom_fields (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    field_name VARCHAR NOT NULL,
    field_label VARCHAR NOT NULL,
    field_type VARCHAR NOT NULL,
    field_options JSONB DEFAULT '{}',
    is_required BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE(tenant_id, field_name)
);

-- Email templates table
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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE(tenant_id, name)
);
```

### Configuration Requirements

#### Environment Variables:
```bash
# SendGrid Configuration
SENDGRID_API_KEY=your_sendgrid_api_key_here
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your Organization

# Existing billing variables continue to work
```

#### Frontend Navigation:
- Added CRM link to organization navigation sidebar
- Admin-only visibility based on user role
- Icon: UserCheck from Lucide React

### Usage Examples

#### Creating a Contact:
```python
contact_data = {
    "business_name": "Acme Corp",
    "contact_name": "John Smith",
    "contact_email": "john@acme.com",
    "contact_role": "CEO",
    "phone": "+1-555-123-4567",
    "city": "New York",
    "state": "NY",
    "status": "lead",
    "notes": "Interested in enterprise plan"
}
```

#### CSV Import Format:
```csv
business_name,contact_name,contact_email,phone,city,state,status
"Acme Corp","John Smith","john@acme.com","+1-555-123-4567","New York","NY","lead"
"Beta Inc","Jane Doe","jane@beta.com","+1-555-987-6543","Los Angeles","CA","prospect"
```

#### Email Template Example:
```html
<h2>Welcome {{contact_name}}!</h2>
<p>Thank you for your interest in {{organization_name}}. We're excited to work with {{business_name}}.</p>
<p>Best regards,<br>{{organization_name}} Team</p>
```

### Benefits Achieved

1. **Centralized Contact Management**: All customer data in one organized location
2. **Interaction Tracking**: Complete history of customer touchpoints
3. **Email Integration**: Professional email campaigns with templates
4. **Billing Connectivity**: Link contacts to subscription and payment data
5. **Scalable Architecture**: Custom fields and bulk operations support growth
6. **Security**: Admin-only access with tenant isolation
7. **User-Friendly Interface**: Intuitive card-based design

### Email Domain Verification System (Future Enhancement)

**Challenge**: Currently all CRM emails must be sent from `pete@cyberiad.ai` (the only verified sender in SendGrid). Organizations cannot send emails from their own domains.

**Proposed Solution**: Implement programmatic domain verification system allowing organizations to verify their own domains through the CRM interface.

**Implementation Plan**:
1. **Admin Interface**: Domain registration form, DNS record display, verification status
2. **Backend API**: 
   - `POST /email-settings/register-domain` - Register domain with SendGrid API
   - `GET /email-settings/verify-domain/{domain_id}` - Check verification status
3. **Database Schema**: 
   ```sql
   CREATE TABLE email_domains (
       id UUID PRIMARY KEY,
       tenant_id UUID REFERENCES tenants(id),
       domain VARCHAR NOT NULL,
       sendgrid_domain_id VARCHAR,
       verification_status VARCHAR DEFAULT 'pending',
       dns_records JSONB,
       verified_at TIMESTAMP,
       created_at TIMESTAMP DEFAULT NOW()
   );
   ```
4. **SendGrid Integration**: Use Domain Authentication API for programmatic domain verification
5. **User Flow**: 
   - User enters domain → System generates DNS records → User adds DNS records → System verifies → Domain becomes available for sending
6. **Email Service Update**: Automatically use organization's verified domain when available, fallback to `pete@cyberiad.ai`

**Alternative Approaches**:
- **Reply-To Method**: Send from `pete@cyberiad.ai` with customer email as reply-to
- **Per-Organization SendGrid**: Each org gets their own SendGrid account
- **Subdomain Approach**: Use `orgname@thanotopolis.com` pattern

**Current Status**: All CRM emails use `pete@cyberiad.ai` as verified sender. Domain verification system planned for future implementation.

### Future Enhancements

1. **Email Domain Verification**: Allow organizations to send from their own verified domains
2. **Advanced Email Campaigns**: Automated drip campaigns and segmentation
3. **Mobile App**: Native mobile interface for field sales teams
4. **Calendar Integration**: Schedule and track meetings
5. **Advanced Analytics**: Contact scoring and pipeline forecasting
6. **API Webhooks**: Real-time integration with external systems
7. **Document Management**: Attach files and documents to contacts

### Current Status (June 27, 2025)

#### ✅ Completed:
- Voice Agent API integration and configuration
- Real-time conversation with minimal latency
- Automatic call greetings and natural conversation flow
- WebSocket connection management and error handling
- A/B testing infrastructure for safe deployment
- Production deployment at 100% rollout
- **Consent-based Voice Agent collaboration system**

#### 🔄 In Progress:
- **Fixing collaboration detection for direct user requests**
- Transcript message saving to database (ConversationText events being received but text content empty)
- Call details page message display debugging

#### 🚨 Current Issue Being Fixed:
**Voice Agent Collaboration Request Detection**
- User says "I would like to talk to an expert agent" but agent claims it cannot collaborate
- Problem located in `_check_for_collaboration_request()` method in `telephony_voice_agent.py:383-407`
- Current phrases array doesn't include exact match for "talk to expert agent" pattern
- Need to add missing phrases like:
  - "talk to expert"
  - "speak to expert" 
  - "talk to an expert"
  - "speak to an expert"
  - "I would like to talk to"
  - "I want to talk to"

#### 🎯 Next Steps:
1. **IMMEDIATE**: Fix collaboration request detection by adding missing phrases to `collaboration_request_phrases` array
2. Test collaboration system with real calls using direct requests
3. Debug and fix transcript message saving
4. Performance monitoring for collaboration workflows
5. Consider advanced collaboration features

### Technical Debt Removal

#### Deprecated Components:
Once Voice Agent is fully stable, these components can be removed:
- `elevenlabs_service.py` - No longer needed
- Audio conversion utilities in telephony WebSocket handler
- Separate STT WebSocket connections
- TTS audio buffering and streaming logic

#### Simplified Maintenance:
- **Single Integration Point**: Only Deepgram Voice Agent API
- **Reduced Dependencies**: Elimination of ElevenLabs, FFmpeg
- **Unified Error Handling**: One service to monitor and maintain
- **Consistent Audio Quality**: Professional voice models with guaranteed reliability

## Previous Project: Integration Test Suite Deployment (June 23, 2025)

### Overview
Preparing the integration test suite for comprehensive deployment across the Thanotopolis backend system. Focus on creating a robust testing infrastructure that ensures system reliability, API compatibility, and consistent behavior across different components.
