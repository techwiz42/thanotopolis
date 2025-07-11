# Thanotopolis - Multi-Agent AI Platform

A comprehensive AI platform built by **Cyberiad.ai** that provides intelligent telephone answering services and web-based chat applications. Features **Deepgram Voice Agent** integration, advanced multi-agent collaboration, and multi-tenant architecture for organizations requiring sophisticated AI assistance.

## 🎙️ Voice Agent Technology

### **Deepgram Voice Agent Integration**

Thanotopolis integrates **Deepgram's Voice Agent API** - a unified technology that replaces traditional STT → LLM → TTS pipelines with a single, real-time conversational AI system.

#### **Architectural Comparison**

**Legacy Architecture** (Pre-Voice Agent):
```
Twilio → Deepgram STT → OpenAI GPT → ElevenLabs TTS → Audio Conversion → Twilio
Latency: 2-5 seconds | Complexity: 3 separate APIs | Format: MP3→mulaw conversion
```

**Voice Agent Architecture** (Current):
```
Twilio ↔ Deepgram Voice Agent (STT + LLM + TTS unified) ↔ Twilio
Latency: <500ms | Complexity: Single WebSocket | Format: Native mulaw
```

#### **Performance Improvements**
- **🚀 90% Latency Reduction**: From 2-5 seconds to <500ms response time
- **🎯 Native Audio**: Direct mulaw support eliminates conversion overhead
- **💡 Unified Processing**: Single WebSocket replaces multiple API calls
- **⚡ Real-time Streaming**: Continuous conversation flow with immediate responses

### **Consent-Based Agent Collaboration**

Integration combining Voice Agent's real-time capabilities with 20+ specialist agents:

#### **How It Works**
1. **Smart Detection**: AI analyzes query complexity in real-time
2. **User Consent**: "I can give you a quick response, or consult with my specialist team. This will take about 30 seconds."
3. **Expert Collaboration**: Routes to MODERATOR + specialist agents (Cultural, Compliance, Financial, etc.)
4. **Seamless Handoff**: Returns enhanced knowledge to voice conversation

#### **Specialist Agent Network**
- **Cultural Agents**: 17 culturally-sensitive agents (Mexican, Filipino, Vietnamese, Korean, Jewish, Persian, etc.)
- **Service Agents**: Financial, Compliance, Emergency, Inventory, Grief Support
- **Technical Agents**: Web Search, Regulatory, Documentation

## 📢 What's New

### **July 2025 Updates - Revolutionary Voice-to-CRM-to-Calendar Integration** 🎯
- **📅 Complete Calendar System**: Full calendar functionality with month/week/day views
- **🎙️ Voice-to-CRM Integration**: Automatic customer information extraction from voice calls
- **📞 Voice-to-Calendar Integration**: Real-time appointment scheduling during phone conversations
- **👥 Advanced Attendee Management**: Multi-type attendee selection with enhanced UI
- **🔗 Seamless CRM-Calendar Integration**: Events linked to CRM contacts with full context
- **📋 Organizations Dashboard**: Added Calendar section to main organizations page

### **Previous Updates**
- **📇 CRM System**: Complete Customer Relationship Management system with contact management
- **📧 Email Integration**: SendGrid-powered email campaigns with template system
- **📊 CSV Import**: Bulk contact import with field mapping and validation
- **💰 Billing Integration**: Direct connection between CRM contacts and Stripe customers
- **🎨 Custom Fields**: Dynamic field creation per organization with validation rules
- **📈 Interaction Tracking**: Complete customer touchpoint history and timeline

### **Voice Agent Infrastructure**
- **🎙️ Deepgram Voice Agent**: Complete telephony architecture update with 90% latency reduction
- **🤖 Voice-Agent Collaboration**: Consent-based specialist agent integration for complex queries
- **📊 Advanced Call Analytics**: Message-based call tracking with granular transcript analysis
- **🔄 A/B Testing Infrastructure**: Feature flag system for safe Voice Agent rollout
- **🎯 Production Ready**: 100% Voice Agent rollout with instant rollback capability

### **Enhanced Features**
- **Enhanced Call Message System**: Granular message tracking replacing monolithic transcripts
- **17 New Cultural Agents**: Culturally-sensitive funeral and memorial service agents
- **Improved Test Coverage**: From 63% to 72% with 98.4% test success rate
- **Voice Agent Testing Tools**: Comprehensive testing suite for Voice Agent connections

## 🏗️ Architecture Overview

### **Backend Technology Stack** (`/backend`)
- **🌐 Framework**: FastAPI with async/await architecture
- **🗄️ Database**: PostgreSQL 14+ with pgvector for RAG capabilities
- **🎙️ Voice Processing**: Deepgram Voice Agent API (STT + LLM + TTS unified)
- **🤖 AI Integration**: GPT-4o-mini with 20+ specialist agents
- **☎️ Telephony**: Twilio integration with WebSocket streaming
- **📅 Calendar System**: Full calendar with attendee management and RSVP tracking
- **📞 Voice-to-CRM-to-Calendar**: Revolutionary voice conversation automation
- **🔐 Authentication**: JWT-based with hierarchical role system
- **🧪 Testing**: Comprehensive unit and integration test suite (72% coverage)

### **Frontend Technology Stack** (`/frontend`)
- **⚛️ Framework**: Next.js 14 with TypeScript
- **🎨 UI/UX**: Tailwind CSS with custom component library
- **⚡ Real-time**: WebSocket connections for live conversations
- **🎤 Voice**: Browser-based audio recording and playbook
- **📅 Calendar UI**: Interactive calendar with multi-view support
- **👥 Attendee Management**: Advanced multi-type attendee selection interface
- **📊 State Management**: React Context with custom hooks
- **🧪 Testing**: Jest with React Testing Library

### **Database Schema & E/R Diagram**

```mermaid
erDiagram
    TENANTS ||--o{ USERS : owns
    TENANTS ||--o{ CONVERSATIONS : hosts
    TENANTS ||--o{ AGENTS : owns
    TENANTS ||--o{ CONTACTS : manages
    TENANTS ||--o{ CUSTOM_FIELDS : defines
    TENANTS ||--o{ EMAIL_TEMPLATES : stores
    TENANTS ||--o{ CALENDAR_EVENTS : schedules
    TENANTS ||--|| TELEPHONY_CONFIGURATIONS : has
    
    TELEPHONY_CONFIGURATIONS ||--o{ PHONE_CALLS : receives
    TELEPHONY_CONFIGURATIONS ||--o{ PHONE_VERIFICATION_ATTEMPTS : has
    
    PHONE_CALLS ||--o{ CALL_MESSAGES : contains
    PHONE_CALLS ||--o{ CALL_AGENTS : uses
    PHONE_CALLS }o--|| CONVERSATIONS : links_to
    
    CONVERSATIONS ||--o{ MESSAGES : contains
    CONVERSATIONS ||--o{ CONVERSATION_USERS : has
    CONVERSATIONS ||--o{ CONVERSATION_PARTICIPANTS : includes
    
    USERS ||--o{ MESSAGES : sends
    USERS ||--o{ CONVERSATIONS : creates
    USERS ||--o{ USAGE_RECORDS : generates
    USERS ||--o{ DOCUMENT_EMBEDDINGS : owns
    USERS ||--o{ CONTACTS : creates
    USERS ||--o{ CONTACT_INTERACTIONS : logs
    USERS ||--o{ CALENDAR_EVENTS : creates
    USERS ||--o{ CALENDAR_EVENT_ATTENDEES : invited_to
    
    AGENTS ||--o{ CALL_AGENTS : participates_in
    
    CONTACTS ||--o{ CONTACT_INTERACTIONS : has
    CONTACTS }o--|| STRIPE_CUSTOMERS : linked_to
    CONTACTS ||--o{ CALENDAR_EVENTS : linked_to
    CONTACTS ||--o{ CALENDAR_EVENT_ATTENDEES : invited_as
    
    CALENDAR_EVENTS ||--o{ CALENDAR_EVENT_ATTENDEES : has
    
    TENANTS {
        uuid id PK
        string name
        string subdomain UK
        string access_code
        string description
        string full_name
        json address
        string phone
        string organization_email
        boolean is_active
        boolean is_demo
        timestamp created_at
        timestamp updated_at
    }
    
    TELEPHONY_CONFIGURATIONS {
        uuid id PK
        uuid tenant_id FK
        string organization_phone_number
        string platform_phone_number
        string verification_status
        boolean call_forwarding_enabled
        text welcome_message
        json business_hours
        string timezone
        json voice_settings
        boolean record_calls
        timestamp created_at
        timestamp updated_at
    }
    
    PHONE_CALLS {
        uuid id PK
        uuid telephony_config_id FK
        uuid conversation_id FK
        string call_sid UK
        string customer_phone_number
        string organization_phone_number
        string platform_phone_number
        string direction
        string status
        timestamp start_time
        timestamp answer_time
        timestamp end_time
        integer duration_seconds
        integer cost_cents
        string recording_url
        text summary
        json call_metadata
    }
    
    CALL_MESSAGES {
        uuid id PK
        uuid call_id FK
        text content
        json sender
        timestamp timestamp
        string message_type
        jsonb message_metadata
        timestamp created_at
        timestamp updated_at
    }
    
    AGENTS {
        uuid id PK
        uuid owner_tenant_id FK
        string agent_type UK
        string name
        text description
        boolean is_enabled
        boolean is_free_agent
        string owner_domain
        json capabilities
        timestamp created_at
        timestamp updated_at
    }
    
    USERS {
        uuid id PK
        uuid tenant_id FK
        string email
        string username
        string hashed_password
        string first_name
        string last_name
        boolean is_active
        boolean is_verified
        string role
        timestamp created_at
        timestamp updated_at
    }
    
    CONVERSATIONS {
        uuid id PK
        uuid tenant_id FK
        uuid created_by_user_id FK
        string title
        text description
        string status
        timestamp created_at
        timestamp updated_at
    }
    
    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        uuid user_id FK
        uuid participant_id FK
        string message_type
        text content
        string agent_type
        json message_metadata
        timestamp created_at
        timestamp updated_at
    }
    
    USAGE_RECORDS {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        uuid conversation_id FK
        string usage_type
        numeric amount
        numeric cost_per_unit
        integer cost_cents
        string service_provider
        string model_name
        json usage_metadata
        timestamp usage_date
        timestamp created_at
    }
    
    CONTACTS {
        uuid id PK
        uuid tenant_id FK
        string business_name
        string city
        string state
        string contact_name
        string contact_email UK
        string contact_role
        string phone
        string website
        text address
        text notes
        string status
        jsonb custom_fields
        string stripe_customer_id FK
        uuid created_by_user_id FK
        string ethnic_orientation
        string preferred_language
        string secondary_language
        string family_name
        string relationship_to_deceased
        string deceased_name
        date date_of_death
        date date_of_birth
        string service_type
        date service_date
        string service_location
        string plot_number
        string plot_type
        integer contract_amount_cents
        integer amount_paid_cents
        integer balance_due_cents
        string payment_plan
        string payment_status
        text special_requests
        string religious_preferences
        boolean veteran_status
        timestamp created_at
        timestamp updated_at
    }
    
    CONTACT_INTERACTIONS {
        uuid id PK
        uuid contact_id FK
        uuid user_id FK
        string interaction_type
        string subject
        text content
        timestamp interaction_date
        jsonb metadata
        timestamp created_at
    }
    
    CUSTOM_FIELDS {
        uuid id PK
        uuid tenant_id FK
        string field_name UK
        string field_label
        string field_type
        jsonb field_options
        boolean is_required
        integer display_order
        boolean is_active
        uuid created_by_user_id FK
    }
    
    EMAIL_TEMPLATES {
        uuid id PK
        uuid tenant_id FK
        string name UK
        string subject
        text html_content
        text text_content
        jsonb variables
        boolean is_active
        uuid created_by_user_id FK
    }
    
    CALENDAR_EVENTS {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        uuid contact_id FK
        string title
        text description
        timestamp start_time
        timestamp end_time
        boolean all_day
        string location
        string event_type
        string status
        json event_metadata
        timestamp created_at
        timestamp updated_at
    }
    
    CALENDAR_EVENT_ATTENDEES {
        uuid id PK
        uuid event_id FK
        string attendee_type
        uuid user_id FK
        uuid contact_id FK
        string external_email
        string external_name
        string attendee_name
        string attendee_email
        string invitation_status
        string response_status
        string invitation_token UK
        timestamp invited_at
        timestamp responded_at
        text response_message
        timestamp created_at
        timestamp updated_at
    }
```

### **Backend Code Structure**

```
backend/
├── app/
│   ├── agents/                          # 🤖 AI Agent System
│   │   ├── base_agent.py               # Base agent interface
│   │   ├── moderator_agent.py          # Central routing agent
│   │   ├── collaboration_manager.py    # Multi-agent collaboration
│   │   ├── agent_manager.py            # Agent discovery & lifecycle
│   │   ├── tenant_aware_agent_manager.py # Multi-tenant agent filtering
│   │   │
│   │   ├── # 🌍 Cultural Specialist Agents (17 agents)
│   │   ├── mexican_cultural_agent.py   # Mexican traditions & Day of the Dead
│   │   ├── filipino_cultural_agent.py  # Filipino wake & burial customs
│   │   ├── vietnamese_cultural_agent.py # Vietnamese ancestor veneration
│   │   ├── korean_cultural_agent.py    # Korean funeral rites
│   │   ├── jewish_cultural_agent.py    # Jewish burial & shiva traditions
│   │   ├── persian_cultural_agent.py   # Persian/Iranian customs
│   │   ├── thai_cultural_agent.py      # Thai Buddhist practices
│   │   ├── cambodian_cultural_agent.py # Cambodian memorial traditions
│   │   ├── russian_cultural_agent.py   # Russian Orthodox customs
│   │   ├── ukrainian_cultural_agent.py # Ukrainian memorial services
│   │   ├── japanese_cultural_agent.py  # Japanese Buddhist & Shinto
│   │   ├── somali_cultural_agent.py    # Somali Islamic traditions
│   │   ├── ethiopian_cultural_agent.py # Ethiopian Orthodox customs
│   │   ├── chinese_cultural_agent.py   # Chinese ancestor worship
│   │   ├── polish_cultural_agent.py    # Polish Catholic traditions
│   │   ├── armenian_cultural_agent.py  # Armenian Apostolic customs
│   │   ├── salvadoran_cultural_agent.py # Salvadoran traditions
│   │   │
│   │   ├── # 🏢 Service Specialist Agents
│   │   ├── demo_answering_service_agent.py # Barney (Cyberiad.ai)
│   │   ├── financial_services_agent.py     # Payment plans & billing
│   │   ├── compliance_and_documentation_agent.py # Regulatory compliance
│   │   ├── emergency_and_crisis_agent.py   # Crisis & urgent situations
│   │   ├── inventory_and_facilities_agent.py # Facilities management
│   │   ├── grief_support_agent.py          # Emotional support
│   │   ├── regulatory_agent.py             # Legal & regulatory
│   │   ├── religious_agent.py              # Religious services
│   │   └── web_search_agent.py             # Real-time information
│   │
│   ├── api/                            # 🌐 REST API Endpoints
│   │   ├── auth.py                     # Authentication & user management
│   │   ├── conversations.py            # Chat & message handling
│   │   ├── agents.py                   # Agent discovery & configuration
│   │   ├── organizations.py            # Multi-tenant management
│   │   ├── billing.py                  # Usage tracking & payments
│   │   ├── crm.py                      # 📇 CRM endpoints & contact management
│   │   ├── calendar.py                 # 📅 Calendar & event management
│   │   ├── telephony.py                # Legacy telephony API
│   │   ├── telephony_voice_agent.py    # 🎙️ Voice Agent WebSocket handler
│   │   ├── telephony_websocket.py      # Legacy telephony WebSocket
│   │   ├── voice_streaming.py          # Voice chat API
│   │   ├── streaming_stt.py            # Legacy STT streaming
│   │   ├── websockets.py               # General WebSocket management
│   │   └── admin.py                    # Admin panel APIs
│   │
│   ├── services/                       # 🔧 Core Business Logic
│   │   ├── voice/                      # 🎙️ Voice Processing Services
│   │   │   ├── deepgram_voice_agent.py # Voice Agent WebSocket client
│   │   │   ├── voice_agent_collaboration.py # Specialist agent integration
│   │   │   ├── customer_extraction.py  # 🎯 Voice-to-CRM customer data extraction
│   │   │   ├── scheduling_intent.py    # 🎯 Voice scheduling intent detection
│   │   │   ├── voice_calendar.py       # 🎯 Voice-to-Calendar integration
│   │   │   ├── deepgram_service.py     # Legacy STT service
│   │   │   ├── elevenlabs_service.py   # Legacy TTS service
│   │   │   └── audio_converter.py      # Audio format utilities
│   │   │
│   │   ├── calendar/                   # 📅 Calendar Services
│   │   │   └── calendar_invitation_service.py # Event invitation system
│   │   │
│   │   ├── rag/                        # 📚 Retrieval Augmented Generation
│   │   │   ├── ingestion_service.py    # Document processing
│   │   │   ├── pgvector_storage_service.py # Vector storage
│   │   │   └── pgvector_query_service.py   # Semantic search
│   │   │
│   │   ├── memory/                     # 🧠 Conversation Memory
│   │   │   ├── conversation_buffer.py  # Message buffering
│   │   │   └── conversation_context_manager.py # Context management
│   │   │
│   │   ├── telephony_service.py        # Legacy telephony logic
│   │   ├── billing_automation.py       # Automated billing & usage
│   │   ├── usage_service.py            # Usage tracking & metrics
│   │   ├── monitoring_service.py       # System monitoring
│   │   ├── email_service.py            # 📧 SendGrid email integration
│   │   └── context_manager.py          # Request context management
│   │
│   ├── models/                         # 🗄️ Database Models
│   │   ├── models.py                   # Complete SQLAlchemy schema
│   │   ├── calendar_models.py          # 📅 Calendar & attendee models
│   │   └── stripe_models.py            # Stripe billing models
│   │
│   ├── schemas/                        # 📋 Pydantic Schemas
│   │   ├── schemas.py                  # API request/response models
│   │   └── calendar_schemas.py         # 📅 Calendar API schemas
│   │
│   ├── core/                           # ⚡ Core Utilities
│   │   ├── config.py                   # Configuration management
│   │   ├── buffer_manager.py           # Audio buffer management
│   │   ├── websocket_queue.py          # WebSocket message queuing
│   │   ├── input_sanitizer.py          # Input validation & sanitization
│   │   └── common_calculator.py        # Utility calculations
│   │
│   ├── db/                            # 🗄️ Database Configuration
│   │   └── database.py                 # Database connection & session
│   │
│   ├── auth/                          # 🔐 Authentication
│   │   └── auth.py                     # JWT & security utilities
│   │
│   ├── tasks/                         # ⏰ Background Tasks
│   │   └── telephony_cleanup.py       # Call cleanup & maintenance
│   │
│   └── main.py                        # 🚀 FastAPI application entry
│
├── tests/                             # 🧪 Test Suite (72% coverage)
│   ├── unit/                          # Unit tests
│   ├── integration/                   # Integration tests
│   ├── fixtures/                      # Test fixtures
│   └── conftest.py                    # Test configuration
│
├── alembic/                           # 📊 Database Migrations
│   └── versions/                      # Migration scripts
│
├── additional_tests/                  # 🔬 Development Tests
│   ├── test_voice_agent.py           # Voice Agent connectivity
│   ├── debug_voice_agent_events.py   # Real-time event monitoring
│   └── test_deepgram_*.py            # Deepgram service tests
│
├── requirements.txt                   # 📦 Python dependencies
├── run.py                            # 🏃 Development server
├── gunicorn_config.py                # 🌐 Production server config
└── alembic.ini                       # 📊 Migration configuration
```

### **Frontend Code Structure**

```
frontend/
├── src/
│   ├── app/                           # 📱 Next.js App Router
│   │   ├── conversations/             # 💬 Chat Interface
│   │   │   ├── [id]/                  # Individual conversation
│   │   │   │   ├── components/        # Chat UI components
│   │   │   │   │   ├── MessageList.tsx
│   │   │   │   │   ├── MessageInput.tsx
│   │   │   │   │   ├── VoiceControls.tsx
│   │   │   │   │   ├── LanguageSelector.tsx
│   │   │   │   │   ├── StreamingIndicator.tsx
│   │   │   │   │   └── TypingIndicator.tsx
│   │   │   │   ├── hooks/             # Chat-specific hooks
│   │   │   │   │   ├── useConversation.ts
│   │   │   │   │   ├── useVoice.ts
│   │   │   │   │   ├── useWebSocket.ts
│   │   │   │   │   └── useMessageLoader.ts
│   │   │   │   ├── types/             # TypeScript definitions
│   │   │   │   │   ├── message.types.ts
│   │   │   │   │   └── websocket.types.ts
│   │   │   │   └── page.tsx           # Conversation page
│   │   │   ├── new/page.tsx           # New conversation
│   │   │   └── page.tsx               # Conversation list
│   │   │
│   │   ├── organizations/             # 🏢 Multi-Tenant Management
│   │   │   ├── calendar/              # 📅 Calendar Management
│   │   │   │   └── page.tsx           # Calendar main page
│   │   │   ├── telephony/             # ☎️ Telephony Management
│   │   │   │   ├── setup/page.tsx     # Telephony setup wizard
│   │   │   │   ├── calls/             # 📞 Call Management
│   │   │   │   │   ├── [id]/page.tsx  # Individual call details
│   │   │   │   │   ├── components/    # Call UI components
│   │   │   │   │   │   ├── CallMessagesList.tsx
│   │   │   │   │   │   ├── CallMessageItem.tsx
│   │   │   │   │   │   └── CallMessageGroup.tsx
│   │   │   │   │   ├── hooks/         # Call-specific hooks
│   │   │   │   │   │   └── useCallMessages.ts
│   │   │   │   │   └── page.tsx       # Call list
│   │   │   │   ├── active-calls/page.tsx # Live call monitoring
│   │   │   │   ├── analytics/page.tsx # Call analytics
│   │   │   │   ├── test/page.tsx      # Telephony testing
│   │   │   │   └── components/        # Telephony components
│   │   │   │       ├── PhoneVerificationModal.tsx
│   │   │   │       ├── BusinessHoursEditor.tsx
│   │   │   │       └── ForwardingInstructionsModal.tsx
│   │   │   ├── crm/                    # 📇 CRM Interface
│   │   │   │   ├── page.tsx            # Contact list & dashboard
│   │   │   │   └── components/         # CRM UI components
│   │   │   ├── admin/page.tsx         # Organization admin
│   │   │   ├── members/page.tsx       # Member management
│   │   │   ├── edit/page.tsx          # Organization settings
│   │   │   ├── new/page.tsx           # New organization
│   │   │   └── page.tsx               # 🎯 Organizations dashboard with Calendar section
│   │   │
│   │   ├── rsvp/                      # 📅 Calendar RSVP System
│   │   │   └── [token]/               # Event RSVP pages
│   │   │       ├── page.tsx           # RSVP landing page
│   │   │       └── respond/page.tsx   # RSVP response form
│   │   │
│   │   ├── billing/page.tsx           # 💳 Billing & Usage
│   │   ├── login/page.tsx             # 🔐 Authentication
│   │   ├── register/page.tsx          # 📝 User registration
│   │   ├── greeting/page.tsx          # 👋 Welcome page
│   │   ├── layout.tsx                 # 🎨 Root layout
│   │   ├── globals.css                # 🎨 Global styles
│   │   └── page.tsx                   # 🏠 Dashboard
│   │
│   ├── components/                    # 🧩 Reusable Components
│   │   ├── ui/                        # 🎨 UI Component Library
│   │   │   ├── button.tsx             # Button component
│   │   │   ├── input.tsx              # Input fields
│   │   │   ├── dialog.tsx             # Modal dialogs
│   │   │   ├── table.tsx              # Data tables
│   │   │   ├── card.tsx               # Card layouts
│   │   │   ├── tabs.tsx               # Tab navigation
│   │   │   ├── command.tsx            # 🎯 Command palette UI
│   │   │   ├── popover.tsx            # 🎯 Popover components
│   │   │   ├── scroll-area.tsx        # 🎯 Scrollable areas
│   │   │   └── use-toast.tsx          # Toast notifications
│   │   │
│   │   ├── calendar/                  # 📅 Calendar Components
│   │   │   ├── CalendarView.tsx       # 🎯 Main calendar interface
│   │   │   ├── EventForm.tsx          # 🎯 Event creation/editing
│   │   │   ├── EventCard.tsx          # 🎯 Event display card
│   │   │   ├── AttendeeManager.tsx    # 🎯 Basic attendee management
│   │   │   └── AttendeeManagerEnhanced.tsx # 🎯 Advanced attendee selection
│   │   │
│   │   ├── telephony/                 # ☎️ Telephony Components
│   │   │   ├── TelephonySystemInitializer.tsx
│   │   │   └── TelephonyTestPanel.tsx
│   │   │
│   │   ├── navigation/                # 🧭 Navigation
│   │   │   └── OrganizationNavigation.tsx
│   │   │
│   │   ├── MainLayout.tsx             # 🏗️ Layout wrapper
│   │   ├── ProtectedRoute.tsx         # 🔐 Route protection
│   │   ├── BillingDashboard.tsx       # 💳 Billing UI
│   │   ├── SubscriptionPlans.tsx      # 📋 Subscription plans
│   │   ├── SuperAdminBilling.tsx      # 👑 Admin billing
│   │   └── WingedSolarIcon.tsx        # 🦅 Brand icon
│   │
│   ├── services/                      # 🔧 Frontend Services
│   │   ├── telephony/                 # ☎️ Telephony Services
│   │   │   ├── TelephonyCallManager.ts
│   │   │   ├── TelephonyWebSocketManager.ts
│   │   │   ├── TelephonyErrorHandler.ts
│   │   │   ├── TelephonyTTSSTTProcessor.ts
│   │   │   ├── IncomingCallHandler.ts
│   │   │   └── TwilioAudioService.ts
│   │   │
│   │   ├── voice/                     # 🎤 Voice Services
│   │   │   ├── StreamingSpeechToTextService.ts
│   │   │   ├── TelephonyStreamingService.ts
│   │   │   ├── AdvancedLanguageDetection.ts
│   │   │   └── voiceConfig.ts
│   │   │
│   │   ├── calendar.ts                # 📅 Calendar API client
│   │   ├── api.ts                     # 🌐 API client
│   │   ├── conversations.ts           # 💬 Conversation API
│   │   ├── telephony.ts               # ☎️ Telephony API
│   │   ├── websocket.ts               # 🔌 WebSocket client
│   │   └── admin.ts                   # 👑 Admin API
│   │
│   ├── contexts/                      # 🔄 React Contexts
│   │   └── AuthContext.tsx            # 🔐 Authentication context
│   │
│   ├── hooks/                         # 🪝 Custom React Hooks
│   │   └── useActiveCall.ts           # ☎️ Active call management
│   │
│   ├── lib/                           # 📚 Utilities
│   │   ├── utils.ts                   # General utilities
│   │   ├── circuitBreaker.ts          # Error handling
│   │   ├── requestQueue.ts            # Request management
│   │   └── participantStorage.ts      # Call participant storage
│   │
│   ├── types/                         # 📝 TypeScript Definitions
│   │   ├── conversation.ts            # Conversation types
│   │   └── user.types.ts              # User types
│   │
│   └── middleware.ts                  # 🛡️ Route middleware
│
├── public/                            # 📁 Static Assets
│   ├── favicon.ico                    # Site icon
│   └── winged-solar-disk.png          # Brand logo
│
├── __tests__/                         # 🧪 Frontend Tests
│   ├── App.integration.test.js        # Integration tests
│   ├── AuthContext.test.js            # Authentication tests
│   ├── Dashboard.test.js              # Dashboard tests
│   └── Login.test.js                  # Login tests
│
├── package.json                       # 📦 Dependencies & scripts
├── next.config.js                     # ⚙️ Next.js configuration
├── tailwind.config.js                 # 🎨 Tailwind CSS config
├── tsconfig.json                      # 📝 TypeScript config
└── jest.config.js                     # 🧪 Jest test config
```

## 🚀 Quick Start

### **Prerequisites**
- **Python 3.11+** (Backend)
- **Node.js 18+** (Frontend)
- **PostgreSQL 14+** (Database with pgvector extension)
- **Deepgram API Key** (Voice Agent)
- **Twilio Account** (Telephony)

### **Backend Setup**

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Environment configuration
cp .env.example .env
# Edit .env with your API keys:
#   DEEPGRAM_API_KEY=your_deepgram_key
#   TWILIO_ACCOUNT_SID=your_twilio_sid
#   TWILIO_AUTH_TOKEN=your_twilio_token
#   DATABASE_URL=postgresql://user:pass@localhost:5432/thanotopolis

# Database setup
alembic upgrade head

# Create admin user
python create_admin_user.py

# Start development server
python run.py
```

### **Frontend Setup**

```bash
cd frontend

# Install Node dependencies
npm install

# Environment configuration
cp .env.local.example .env.local
# Edit .env.local:
#   NEXT_PUBLIC_API_URL=http://localhost:8000
#   NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Start development server
npm run dev
```

### **Voice Agent Configuration**

```bash
# Backend environment variables
USE_VOICE_AGENT=true                    # Enable Voice Agent
VOICE_AGENT_ROLLOUT_PERCENTAGE=100      # 100% rollout
VOICE_AGENT_LISTENING_MODEL=nova-3      # STT model
VOICE_AGENT_THINKING_MODEL=gpt-4o-mini  # LLM model
VOICE_AGENT_SPEAKING_MODEL=aura-2-thalia-en # TTS voice
```

## ☎️ Telephony System Features

### **🎙️ Deepgram Voice Agent**
- **Unified Processing**: STT + LLM + TTS in single WebSocket
- **Ultra-Low Latency**: <500ms response time (90% improvement)
- **Native Audio**: Direct mulaw support for telephony
- **Real-time Streaming**: Continuous conversation flow
- **Auto-Greetings**: Immediate call engagement

### **🤖 Agent Collaboration**
- **Consent-Based**: User chooses when to access specialist expertise
- **20+ Specialist Agents**: Cultural, regulatory, financial, emergency
- **Seamless Handoff**: Expert knowledge integrated into voice conversation
- **Graceful Fallback**: Clear error handling and timeout management

### **📞 Call Management**
- **Call Forwarding**: Organizations keep existing numbers
- **Multi-language Support**: Automatic language detection
- **Real-time Analytics**: Live call monitoring and metrics
- **Message-Based Transcripts**: Granular conversation tracking
- **Recording & Transcription**: Automated call documentation

### **How Telephony Works**
1. **Customer calls** organization's existing number
2. **Call forwards** to platform's Twilio number
3. **Voice Agent answers** with personalized greeting
4. **Real-time conversation** with specialist agent collaboration
5. **Call analytics** and transcript automatically generated

## 📅 Calendar System

### **Comprehensive Event Management**
A fully-featured calendar system integrated into the platform, providing organizations with professional appointment scheduling, event management, and attendee coordination. The calendar system is designed specifically for organizations requiring sophisticated scheduling capabilities alongside their AI-powered communication services.

### **Core Calendar Features**
- **Multi-View Calendar**: Interactive month, week, and day views
- **Event Management**: Create, edit, delete events with full details
- **CRM Integration**: Link events directly to CRM contacts
- **Multi-Type Attendees**: Internal users, CRM contacts, and external participants
- **RSVP System**: Complete invitation and response tracking
- **Real-time Updates**: Automatic refresh and synchronization
- **Statistics Dashboard**: Event analytics and usage reports

### **Advanced Attendee Management** 🎯
Revolutionary attendee selection interface with three distinct types:

#### **Internal Users (Team Members)**
- **Dropdown Selection**: Multi-select dropdown with checkboxes
- **Organization Filtering**: Only shows users from current organization
- **Role Information**: Display names, emails, and roles
- **Bulk Selection**: Select multiple team members simultaneously

#### **CRM Contacts**
- **Searchable Interface**: Real-time search with command palette UI
- **Checkbox Selection**: Multi-select with visual feedback
- **Contact Details**: Business names, contact names, and emails
- **Smart Filtering**: Search across all contact fields

#### **External Attendees**
- **Email/Name Input**: Simple form for external participants
- **Batch Addition**: Add multiple external attendees
- **Validation**: Email format and required field validation
- **Management**: Easy removal and editing of external attendees

### **Event Types & Status Management**
- **Event Types**: Appointment, Service, Meeting, Call, Reminder, Other
- **Status Tracking**: Confirmed, Tentative, Cancelled
- **All-Day Events**: Support for full-day events
- **Location Tracking**: Optional location field for events
- **Event Metadata**: Flexible JSON metadata storage

### **RSVP & Invitation System**
- **Invitation Tokens**: Unique tokens for secure RSVP links
- **Response Tracking**: Accepted, Declined, Tentative, No Response
- **Custom Messages**: Personalized invitation messages
- **Email Integration**: Automated invitation sending
- **Public RSVP Pages**: Accessible response forms for external attendees

### **API Endpoints**
- **`GET /api/calendar/events`** - List events with filtering and pagination
- **`GET /api/calendar/events/range`** - Get events in specific date range
- **`GET /api/calendar/events/{id}`** - Get single event details
- **`POST /api/calendar/events`** - Create new event
- **`PUT /api/calendar/events/{id}`** - Update existing event
- **`DELETE /api/calendar/events/{id}`** - Delete event
- **`GET /api/calendar/events/stats/summary`** - Calendar statistics
- **`GET /api/calendar/events/{id}/attendees`** - List event attendees
- **`POST /api/calendar/events/{id}/attendees`** - Add attendee to event
- **`DELETE /api/calendar/events/{id}/attendees/{attendee_id}`** - Remove attendee
- **`POST /api/calendar/events/{id}/send-invitations`** - Send invitations

## 🎯 Voice-to-CRM-to-Calendar Integration

### **Revolutionary AI-Powered Voice Automation** 
The most advanced feature in Thanotopolis - a complete voice conversation automation system that transforms how cemetery and funeral homes handle customer calls. This system enables "talk-to-book" experiences where customers can call and have everything handled in one compassionate conversation.

### **Core Concept**
The AI phone agent acts as an intelligent intake system, leveraging the existing voice agent collaboration framework to:
1. **Extract Customer Information** from natural conversation in real-time
2. **Create CRM Contacts** automatically with cemetery-specific details  
3. **Schedule Appointments** based on voiced preferences and real-time availability
4. **Provide Confirmations** and maintain complete conversation documentation

### **Technical Architecture - 3 Phase Implementation**

#### **Phase 1: Customer Information Extraction** ✅ **COMPLETED**
**File**: `app/services/voice/customer_extraction.py`
- **CustomerData** dataclass with cemetery-specific fields
- **CustomerExtractionService** with LLM-powered extraction
- **Real-time Analysis**: Extracts data from conversation segments
- **Progressive Building**: Accumulates customer information over conversation
- **Contact Creation**: Automatic CRM contact creation when sufficient data available

**Key Capabilities**:
- Extract customer name, phone, email, family name automatically
- Cemetery-specific: deceased name, relationship, service type, urgency
- Confidence scoring and data validation
- Phone/email normalization and duplicate prevention

#### **Phase 2: Scheduling Intent Detection** ✅ **COMPLETED**
**File**: `app/services/voice/scheduling_intent.py`
- **SchedulingIntentService** with natural language processing
- **Intent Detection**: Recognizes scheduling requests in conversation
- **Preference Extraction**: Captures dates, times, service types, urgency
- **Smart Analysis**: Understands context clues and family needs

**Detection Patterns**:
- "I need to schedule a service" → Direct scheduling intent
- "When can I come in?" → Availability inquiry
- "We were hoping for Friday" → Date preference
- "This is urgent" → Priority escalation

#### **Phase 3: Voice-Driven Appointment Booking** ✅ **COMPLETED**
**File**: `app/services/voice/voice_calendar.py`
- **VoiceCalendarService** with real-time availability checking
- **Business Rules**: Office hours, service-specific requirements
- **Slot Optimization**: Intelligent suggestions based on preferences
- **Natural Language**: Voice-friendly availability responses

**Booking Workflow**:
1. Validate customer information completeness
2. Check real-time calendar availability
3. Offer 2-3 specific time slots via voice
4. Handle customer selection and confirmation
5. Create calendar event linked to CRM contact
6. Generate confirmation number
7. Send confirmation via preferred method

### **Integration with Voice Agent**
**File**: `app/api/telephony_voice_agent.py` (Enhanced)
- **Real-time Processing**: Customer data extraction during conversation
- **Session Management**: Enhanced session state with extraction context
- **Contact Creation**: Automatic CRM contact creation from voice data
- **Appointment Booking**: Seamless calendar integration during calls
- **Conversation History**: Complete interaction logging

### **Enhanced Session State**
```python
enhanced_session_info = {
    'contact_id': str,              # CRM contact ID once created
    'extracted_data': {},           # Accumulated customer information
    'scheduling_state': {},         # Current scheduling workflow state
    'conversation_history': [],     # Full conversation context
    'intent_history': [],           # Detected intents over time
    'data_confidence': {},          # Confidence levels for extracted data
    'workflow_stage': str           # Current workflow stage
}
```

### **Example Conversation Flow**

```
Customer: "Hi, I need to schedule a burial service for my mother who passed away yesterday."

Voice Agent: [Extracts: contact_name="Mary Smith", deceased_name="John", relationship="spouse"]
"I'm so sorry for your loss. I'd be happy to help you arrange a burial service for your mother. 
Could you tell me your name and your mother's name?"

Customer: "I'm Sarah Williams, and my mother was Elizabeth Williams."

Voice Agent: [Updates extraction, creates CRM contact]
"Thank you, Sarah. I understand this is a difficult time. For the burial service, 
do you have any preferred dates? We typically recommend 3-5 days to allow family to gather."

Customer: "We were hoping for this Friday or Saturday if possible."

Voice Agent: [Detects scheduling intent, checks calendar availability]
"Let me check our availability for burial services this Friday and Saturday... 
I have Friday at 10 AM or 2 PM available, and Saturday at 11 AM or 3 PM. 
Which would work best for your family?"

Customer: "Saturday at 11 AM would be perfect."

Voice Agent: [Books appointment, creates contact, links everything]
"Excellent. I'm booking a burial service for Elizabeth Williams on Saturday at 11 AM. 
Can I get your phone number for confirmations?"

Customer: "It's 555-123-4567."

Voice Agent: [Updates contact with phone]
"Thank you. I've scheduled your service and you'll receive a confirmation shortly. 
Your reference number is BUR-001234. We'll call you tomorrow to discuss details. 
Is there anything else I can help you with today?"

Backend Processing:
✅ Contact Created: Sarah Williams (daughter of Elizabeth Williams)
✅ Calendar Event: "Burial Service - Elizabeth Williams" Saturday 11 AM
✅ CRM Interaction: Full conversation logged
✅ Confirmation: SMS sent to 555-123-4567
✅ Follow-up: Scheduled call for next day
```

### **Benefits & Impact**

#### **Operational Benefits**
- **24/7 Scheduling**: Families can call anytime, even outside business hours
- **Zero Manual Entry**: Information flows automatically from voice to CRM
- **Real-time Coordination**: Staff see appointments and customer data immediately
- **Complete Documentation**: Full conversation history linked to contacts and events
- **Reduced Administrative Load**: Automatic data entry and appointment booking

#### **Customer Experience Benefits**
- **One-Call Resolution**: Complete intake and scheduling in single conversation
- **Compassionate Efficiency**: Professional handling without multiple transfers
- **Immediate Confirmation**: Instant booking confirmation reduces anxiety
- **Reduced Repetition**: Information captured once, available to all staff
- **Flexible Scheduling**: Real-time availability checking

#### **Technical Benefits**
- **Cemetery-Optimized**: Fields and workflows designed for funeral homes
- **Scalable Architecture**: Handles multiple concurrent voice sessions
- **Error Resilient**: Comprehensive fallback mechanisms
- **Performance Optimized**: Async processing with minimal latency

## 💬 Web Chat Application

### **Multi-Agent Chat Interface**
A sophisticated web-based chat application that enables organizations to deploy AI-powered customer service through their websites. The platform supports real-time conversations with intelligent agent collaboration and multi-tenant architecture.

### **Core Chat Features**
- **Real-time Messaging**: WebSocket-based instant messaging with typing indicators
- **Multi-Agent Collaboration**: Dynamic routing to specialist agents based on query complexity
- **Voice Integration**: Browser-based voice recording and playback capabilities
- **Language Support**: Multi-language conversation support with automatic detection
- **Session Management**: Persistent conversation history and context preservation
- **Mobile Responsive**: Optimized interface for desktop and mobile devices

### **Agent Collaboration System**
- **MODERATOR Agent**: Central orchestrator for intelligent query routing
- **Parallel Processing**: Multiple specialist agents process complex queries simultaneously
- **Response Synthesis**: AI-powered combination of multiple agent perspectives
- **Timeout Management**: 30-second individual and 90-second total response timeouts
- **Graceful Fallback**: Automatic fallback to primary agent when collaboration fails

### **Voice Agent Customization for Organizations**

Organizations can customize their telephony voice agent's behavior and personality through the Admin UI:

1. **Navigate to Organization Settings**:
   - Go to `/organizations/admin` or click "Admin" in the organization navigation
   - Click "Edit Organization" button

2. **Configure Voice Agent Instructions**:
   - Scroll to the **"Additional instructions for agent"** section
   - Add custom instructions that will shape the voice agent's behavior
   - Instructions can include:
     - **Greeting Style**: Custom welcome messages and conversation tone
     - **Business Context**: Specific services, pricing, policies
     - **Personality Traits**: Professional, friendly, empathetic, etc.
     - **Cultural Considerations**: Language preferences, customs
     - **Knowledge Base**: Organization-specific information
     - **Call Handling**: How to route specific types of inquiries

3. **Example Customizations**:
   ```
   You are a compassionate funeral home assistant. Always:
   - Express empathy and understanding
   - Speak in a calm, soothing tone
   - Offer specific services: burial, cremation, memorial planning
   - Mention our 24/7 availability for immediate needs
   - Provide pricing information when asked
   - Use formal language unless the caller prefers informal
   ```

4. **Save and Apply**:
   - Click "Update Organization" to save changes
   - Voice agent instructions take effect immediately for new calls
   - No system restart or deployment required

These instructions are dynamically loaded for each call, allowing organizations to tailor the AI voice assistant to their specific needs, industry requirements, and brand personality.

### **Specialist Agent Network**
The web chat leverages the same 20+ specialist agents available to telephony:

#### **Cultural Specialists (17 Agents)**
- Mexican, Filipino, Vietnamese, Korean, Jewish, Persian, Thai, Cambodian
- Russian, Ukrainian, Japanese, Somali, Ethiopian, Chinese, Polish, Armenian, Salvadoran
- Each agent provides culturally-sensitive guidance for memorial and funeral services

#### **Service Specialists**
- **Financial Services**: Payment plans, billing assistance, cost estimation
- **Compliance & Documentation**: Regulatory requirements, permit assistance
- **Emergency & Crisis**: Urgent situation handling, crisis intervention
- **Inventory & Facilities**: Equipment availability, venue management
- **Grief Support**: Emotional support, counseling resources
- **Regulatory**: Legal compliance, industry regulations
- **Religious Services**: Interfaith religious coordination
- **Web Search**: Real-time information retrieval and verification

### **Technical Implementation**
- **Frontend**: Next.js 14 with TypeScript and real-time WebSocket connections
- **Backend**: FastAPI with async/await architecture for high concurrency
- **Real-time Communication**: WebSocket endpoints for instant message delivery
- **State Management**: React Context with custom hooks for conversation state
- **Authentication**: JWT-based authentication with role-based access control
- **Multi-tenant Support**: Organization-specific branding and agent configuration

### **User Experience Features**
- **Conversation Management**: Create, view, and manage multiple conversations
- **Message History**: Persistent storage and retrieval of conversation history
- **Typing Indicators**: Real-time indication when agents are responding
- **File Attachments**: Support for document and image sharing (planned)
- **Conversation Search**: Search across conversation history and messages
- **Export Capabilities**: Download conversation transcripts and summaries

### **How Web Chat Works**
1. **User visits** organization's website with embedded chat widget
2. **Chat initiates** with organization-specific greeting and branding
3. **MODERATOR analyzes** user query complexity and intent
4. **Specialist agents** collaborate when advanced expertise is needed
5. **Unified response** delivered through natural conversation flow
6. **Conversation history** preserved for follow-up and reference

## 📇 CRM System

### **Comprehensive Customer Relationship Management**
A fully-featured CRM system integrated into the platform, providing organizations with professional contact management, interaction tracking, email campaigns, and direct billing integration. The CRM is designed specifically for organizations needing to manage customer relationships alongside their AI-powered communication services.

### **Core CRM Features**
- **Contact Management**: Complete customer database with business and personal information
- **Interaction Tracking**: Log calls, emails, meetings, notes, and tasks with timeline view
- **Email Campaigns**: SendGrid-powered bulk email with personalized templates
- **CSV Import**: Bulk contact import with intelligent field mapping and validation
- **Custom Fields**: Organization-specific dynamic fields with validation rules
- **Billing Integration**: Direct link to Stripe subscription and payment status
- **Cemetery-Specific Fields**: Enhanced with specialized fields for funeral home operations
- **Calendar Integration**: Direct linking between contacts and calendar events
- **Admin-Only Access**: Secure access restricted to admin and super_admin roles

### **Cemetery CRM Enhancement** 🎯
Specialized fields designed for cemetery and funeral home operations:

#### **Cultural & Language Fields**
- **Ethnic Orientation**: Cultural background for service customization
- **Preferred Language**: Primary language for communication
- **Secondary Language**: Additional language support
- **Religious Preferences**: Faith-based service requirements

#### **Family & Deceased Information**
- **Family Name**: Family surname for service coordination
- **Relationship to Deceased**: Caller's relationship (spouse, child, parent, etc.)
- **Deceased Name**: Full name of the deceased person
- **Date of Death**: When the person passed away
- **Date of Birth**: Birth date for service planning

#### **Service Details**
- **Service Type**: Burial, cremation, memorial, consultation
- **Service Date**: Scheduled service date
- **Service Location**: Venue or chapel information
- **Plot Number**: Cemetery plot assignment
- **Plot Type**: Type of burial plot

#### **Financial Tracking**
- **Contract Amount**: Total service contract value (stored in cents)
- **Amount Paid**: Payments received (stored in cents)
- **Balance Due**: Outstanding balance (stored in cents)
- **Payment Plan**: Payment schedule details
- **Payment Status**: Current payment status

#### **Special Considerations**
- **Special Requests**: Flowers, music, special arrangements
- **Veteran Status**: Military service recognition
- **Custom Requirements**: Additional family-specific needs

### **Contact Management System**
- **Business Information**: Company name, address, website, industry details
- **Contact Person**: Name, email, phone, role, and communication preferences
- **Status Workflow**: Lead → Prospect → Qualified → Customer → Closed Won/Lost
- **Custom Fields**: Add organization-specific data fields dynamically
- **Search & Filter**: Real-time search by name, email, or status
- **Duplicate Prevention**: Email-based duplicate detection within organizations

### **Interaction Tracking**
Comprehensive timeline of all customer touchpoints:
- **Phone Calls**: Log inbound/outbound calls with notes and duration
- **Emails**: Track sent/received emails with subject and content
- **Meetings**: Schedule and document in-person or virtual meetings
- **Notes**: Add internal notes and observations
- **Tasks**: Create follow-up tasks with due dates
- **Follow-ups**: Set reminders for future actions

### **Email Campaign System**
#### **SendGrid Integration**
- Professional email delivery with tracking and analytics
- HTML and plain text email support
- Bulk sending with personalization
- Template variable substitution
- Error handling and delivery reports

#### **Template System**
- **Jinja2 Templates**: Dynamic content with variable substitution
- **Default Templates**: Pre-built for common scenarios (welcome, follow-up, reminders)
- **Custom Templates**: Create organization-specific templates
- **Variable Support**: `{{contact_name}}`, `{{business_name}}`, `{{organization_name}}`, etc.
- **Preview System**: Test templates before sending

#### **Example Email Template**
```html
<h2>Welcome {{contact_name}}!</h2>
<p>Thank you for your interest in {{organization_name}}. We're excited to work with {{business_name}}.</p>
<p>Our team specializes in providing compassionate funeral and memorial services.</p>
<p>Best regards,<br>{{organization_name}} Team</p>
```

### **CSV Import Features**
- **Drag-and-Drop Interface**: Intuitive field mapping UI
- **Smart Field Detection**: Automatic column recognition
- **Duplicate Handling**: Update existing or skip duplicates
- **Validation**: Real-time error detection with row-by-row feedback
- **Preview Mode**: Review mapped data before import
- **Large File Support**: Efficient batch processing

#### **CSV Format Example**
```csv
business_name,contact_name,contact_email,phone,city,state,status,notes
"Smith Funeral Home","John Smith","john@smithfh.com","+1-555-123-4567","New York","NY","lead","Interested in voice agent services"
"Memorial Gardens","Jane Doe","jane@memorial.com","+1-555-987-6543","Los Angeles","CA","customer","Active subscriber since 2024"
```

### **Billing Integration**
- **Stripe Customer Link**: Connect CRM contacts to billing accounts
- **Subscription Status**: View active/canceled/trial status
- **Payment History**: Access invoice and payment records
- **Usage Metrics**: See voice agent and call usage statistics
- **Demo Accounts**: Special handling for demo organizations

### **Technical Implementation**
#### **Database Schema**
- **contacts**: Core contact information with tenant isolation and cemetery fields
- **contact_interactions**: Complete interaction history
- **custom_fields**: Dynamic field definitions per organization
- **email_templates**: Reusable email templates with variables

#### **API Endpoints**
- **`GET /api/crm/dashboard`**: Statistics and recent activity
- **`GET/POST/PUT/DELETE /api/crm/contacts`**: Full CRUD operations
- **`POST /api/crm/contacts/import`**: CSV import with mapping
- **`GET/POST /api/crm/contacts/{id}/interactions`**: Interaction management
- **`POST /api/crm/contacts/bulk-email`**: Send emails to multiple contacts
- **`GET/POST/PUT/DELETE /api/crm/custom-fields`**: Custom field management
- **`GET/POST/PUT/DELETE /api/crm/email-templates`**: Template management

#### **Frontend Interface**
- **Location**: `/organizations/crm` (admin-only access)
- **Card Layout**: Visual contact cards with key information
- **Responsive Design**: Desktop and mobile optimized
- **Real-time Search**: Instant filtering as you type
- **Status Filters**: Quick filter by lead status
- **Action Buttons**: Quick access to email, call, and edit functions

### **Security & Access Control**
- **Role-Based Access**: CRM restricted to admin and super_admin users
- **Tenant Isolation**: Contacts strictly segregated by organization
- **API Authentication**: JWT token required for all endpoints
- **Data Validation**: Input sanitization and validation
- **Audit Trail**: Track who created/modified contacts

### **Configuration Requirements**
```bash
# SendGrid Email Configuration
SENDGRID_API_KEY=your_sendgrid_api_key
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your Organization Name
```

### **How CRM Works**
1. **Admin accesses** CRM through organization navigation
2. **Contacts imported** via manual entry or CSV upload
3. **Interactions logged** for complete customer history
4. **Email campaigns** sent using personalized templates
5. **Billing status** monitored through Stripe integration
6. **Follow-ups tracked** ensuring no opportunity is missed

## 🌐 API Architecture

### **Core API Endpoints**
- **`/api/auth/*`** - Authentication & user management
- **`/api/conversations/*`** - Chat & message handling
- **`/api/agents/*`** - Agent discovery & configuration
- **`/api/telephony/*`** - Phone system integration
- **`/api/organizations/*`** - Multi-tenant management
- **`/api/billing/*`** - Usage tracking & payments
- **`/api/crm/*`** - Contact management & CRM operations
- **`/api/calendar/*`** - Calendar & event management 📅

### **Real-time WebSocket Endpoints**
- **`/api/ws/conversation/{id}`** - Chat conversations
- **`/api/ws/telephony/voice-agent/stream`** - 🎙️ Voice Agent streaming
- **`/api/ws/telephony/stream/{call_id}`** - Legacy telephony streaming
- **`/api/ws/voice/{conversation_id}`** - Voice chat

### **Call Message APIs**
- **`GET /api/telephony/calls/{call_id}/messages`** - Retrieve call messages
- **`POST /api/telephony/calls/{call_id}/messages`** - Add call messages
- **`PATCH /api/telephony/calls/{call_id}/messages/{message_id}`** - Update messages
- **`DELETE /api/telephony/calls/{call_id}/messages/{message_id}`** - Delete messages

### **CRM APIs**
- **`GET /api/crm/dashboard`** - CRM statistics and recent activity
- **`GET /api/crm/contacts`** - List contacts with search/filter
- **`POST /api/crm/contacts`** - Create new contact
- **`PUT /api/crm/contacts/{id}`** - Update contact information
- **`DELETE /api/crm/contacts/{id}`** - Delete contact
- **`POST /api/crm/contacts/import`** - CSV import with field mapping
- **`GET /api/crm/contacts/{id}/interactions`** - Get contact interactions
- **`POST /api/crm/contacts/{id}/interactions`** - Log new interaction
- **`POST /api/crm/contacts/bulk-email`** - Send bulk emails
- **`GET /api/crm/custom-fields`** - List custom fields
- **`POST /api/crm/custom-fields`** - Create custom field
- **`GET /api/crm/email-templates`** - List email templates
- **`POST /api/crm/email-templates`** - Create email template

### **Calendar APIs** 📅
- **`GET /api/calendar/events`** - List events with filtering and pagination
- **`GET /api/calendar/events/range`** - Get events in specific date range
- **`GET /api/calendar/events/{id}`** - Get single event details
- **`POST /api/calendar/events`** - Create new event
- **`PUT /api/calendar/events/{id}`** - Update existing event
- **`DELETE /api/calendar/events/{id}`** - Delete event
- **`GET /api/calendar/events/stats/summary`** - Calendar statistics
- **`GET /api/calendar/events/{id}/attendees`** - List event attendees
- **`POST /api/calendar/events/{id}/attendees`** - Add attendee to event
- **`DELETE /api/calendar/events/{id}/attendees/{attendee_id}`** - Remove attendee
- **`POST /api/calendar/events/{id}/send-invitations`** - Send invitations

## 🤖 AI Agent Ecosystem

### **Agent Architecture**
```python
# Agent ownership models
class BaseAgent:
    OWNER_DOMAINS = []          # Free agent (all organizations)
    OWNER_DOMAINS = ["demo"]    # Proprietary (specific org)
    OWNER_DOMAINS = ["demo", "enterprise"]  # Multi-organization
```

### **Cultural Agents (17 Specialized)**
- **🇲🇽 Mexican**: Traditional customs & Day of the Dead
- **🇵🇭 Filipino**: Wake & burial traditions
- **🇻🇳 Vietnamese**: Ancestor veneration practices
- **🇰🇷 Korean**: Funeral rites & memorial services
- **✡️ Jewish**: Burial & shiva traditions
- **🇮🇷 Persian**: Iranian funeral customs
- **🇹🇭 Thai**: Buddhist funeral practices
- **🇰🇭 Cambodian**: Memorial traditions
- **🇷🇺 Russian**: Orthodox funeral customs
- **🇺🇦 Ukrainian**: Memorial services
- **🇯🇵 Japanese**: Buddhist & Shinto practices
- **🇸🇴 Somali**: Islamic funeral traditions
- **🇪🇹 Ethiopian**: Orthodox customs
- **🇨🇳 Chinese**: Ancestor worship & funeral rites
- **🇵🇱 Polish**: Catholic traditions
- **🇦🇲 Armenian**: Apostolic funeral customs
- **🇸🇻 Salvadoran**: Memorial traditions

### **Service Agents**
- **💰 Financial Services**: Payment plans & billing assistance
- **📋 Compliance**: Regulatory & documentation support
- **🚨 Emergency**: Crisis & urgent situation handling
- **🏢 Inventory**: Facilities & equipment management
- **💙 Grief Support**: Emotional support & counseling
- **⚖️ Regulatory**: Legal & regulatory compliance
- **🙏 Religious**: Interfaith religious services
- **🔍 Web Search**: Real-time information retrieval

### **MODERATOR System**
- **Central Routing**: Intelligent agent selection based on query analysis
- **Parallel Execution**: Multiple agents process queries simultaneously
- **Response Synthesis**: LLM-powered combination of agent insights
- **Collaboration Management**: 30s individual / 90s total timeouts

## 🧪 Testing & Quality

### **Backend Testing (72% Coverage)**
```bash
# Run full test suite
pytest

# Coverage analysis
pytest --cov=app --cov-report=html

# Voice Agent testing
python test_voice_agent.py           # Connection testing
python debug_voice_agent_events.py   # Real-time monitoring

# Frontend test simulation
curl -X POST http://localhost:8000/api/telephony/test/simulate-call
```

### **Frontend Testing**
```bash
# Unit & integration tests
npm test

# Coverage report
npm run test:coverage

# End-to-end testing
npm run test:integration
```

### **Test Statistics**
- **Overall Coverage**: 72% (improvement from 63%)
- **Test Success Rate**: 98.4% (1,360 of 1,382 tests passing)
- **Test Organization**: Comprehensive unit and integration suites
- **Voice Agent Tests**: Dedicated testing tools for WebSocket connections

## 📊 Monitoring & Analytics

### **System Metrics**
- **API Performance**: Response times, error rates, throughput
- **Voice Agent Performance**: Call success rates, latency metrics
- **Agent Analytics**: Usage patterns, collaboration success rates
- **Database Performance**: Query optimization, connection pooling
- **Real-time Monitoring**: Live call status, WebSocket connections
- **Calendar Analytics**: Event creation patterns, attendee statistics

### **Usage Tracking**
- **Word-Based Billing**: STT/TTS word counts for accurate pricing
- **Call Duration**: Precise timing for telephony costs
- **Agent Usage**: Token consumption and collaboration metrics
- **Multi-tenant Analytics**: Organization-specific usage patterns
- **Calendar Usage**: Event scheduling patterns and trends

### **Logging & Alerting**
- **Structured Logging**: Correlation IDs for request tracing
- **Error Tracking**: Comprehensive error capture and alerting
- **Audit Trails**: Security and compliance logging
- **Performance Alerts**: Automated monitoring and notifications

## 🛡️ Security & Compliance

### **Authentication & Authorization**
- **JWT-based Authentication**: Secure token-based auth
- **Role Hierarchy**: `user` → `org_admin` → `admin` → `super_admin`
- **Multi-tenant Isolation**: Strict data segregation
- **API Rate Limiting**: DDoS protection and abuse prevention

### **Data Protection**
- **Encrypted Communications**: TLS/SSL for all API traffic
- **Secure Voice Streaming**: Encrypted WebSocket connections
- **PII Handling**: GDPR/CCPA compliant data processing
- **Input Sanitization**: XSS and injection attack prevention

### **Infrastructure Security**
- **Environment Variables**: Secure configuration management
- **Database Security**: Connection encryption, access controls
- **Service Isolation**: Containerized deployment with network isolation
- **Backup & Recovery**: Automated backup with encryption at rest

## 📦 Deployment & Operations

### **Production Deployment**
```bash
# Docker deployment
docker-compose up -d

# Environment configuration
USE_VOICE_AGENT=true
VOICE_AGENT_ROLLOUT_PERCENTAGE=100
DATABASE_URL=postgresql://user:pass@prod-db:5432/thanotopolis
DEEPGRAM_API_KEY=your_production_key
TWILIO_ACCOUNT_SID=your_production_sid
```

### **Infrastructure Requirements**
- **Database**: PostgreSQL 14+ with pgvector extension
- **Web Server**: Nginx + Gunicorn for production
- **WebSocket Support**: Load balancer with WebSocket support
- **SSL Certificates**: TLS termination for secure communications

### **Scalability Features**
- **Async Architecture**: FastAPI with async/await throughout
- **Connection Pooling**: Optimized database connections
- **WebSocket Scaling**: Horizontal scaling support
- **CDN Integration**: Static asset optimization
- **Monitoring**: Comprehensive observability stack

## 🤝 Contributing

### **Development Workflow**
1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** changes with comprehensive tests
4. **Run** test suite (`pytest` + `npm test`)
5. **Submit** pull request with detailed description

### **Code Standards**
- **Python**: PEP 8 compliance with Black formatting
- **TypeScript**: Strict typing with ESLint rules
- **Testing**: Minimum 70% coverage for new features
- **Documentation**: Comprehensive docstrings and comments
- **Security**: Security review for all auth/telephony changes

### **Voice Agent Development**
```bash
# Voice Agent testing environment
python test_voice_agent.py           # Test WebSocket connectivity
python debug_voice_agent_events.py   # Monitor real-time events

# Frontend testing
npm run dev                           # Start frontend
# Navigate to: /organizations/telephony/test
```

## 📖 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive development guide
- **[Backend Guide](backend/CLAUDE.md)** - Backend architecture & Voice Agent details
- **[Frontend Guide](frontend/CLAUDE.md)** - Frontend architecture & UI components
- **[Agent Ownership Guide](backend/AGENT_OWNERSHIP_GUIDE.md)** - Multi-tenant agent system
- **[Barney Agent Summary](backend/BARNEY_AGENT_SUMMARY.md)** - Demo agent details

## 📄 License

This project is proprietary software owned by **Cyberiad.ai**. All rights reserved.

## 🚀 About Cyberiad.ai

**Cyberiad.ai** develops advanced agentic AI frameworks that enable organizations to deploy sophisticated AI assistants across telephony and web chat channels. Our platforms combine voice technology, multi-agent collaboration, and enterprise-grade scalability to deliver enhanced customer experiences.

**Key Features:**
- **Voice Agent Technology**: Deepgram Voice Agent integration with revolutionary automation
- **Multi-Agent Collaboration**: Consent-based specialist agent collaboration
- **Cultural Sensitivity**: 17 culturally-aware specialist agents
- **Voice-to-CRM-to-Calendar**: Revolutionary conversation automation system
- **Enterprise Architecture**: Multi-tenant, scalable, secure platform

---

**Built with ❤️ by the Cyberiad.ai team**

*Advanced telephony and web chat AI • Enhanced customer service • Intelligent conversational AI • Revolutionary voice automation*