# Thanotopolis - Multi-Agent AI Platform

A comprehensive multi-agent AI platform built by **Cyberiad.ai** that provides intelligent telephone answering services, web-based conversations, and specialized AI agents for various industries and use cases.

## 📢 What's New

### Recent Updates (June 2025)
- **17 New Cultural Agents**: Culturally-sensitive funeral and memorial service agents for diverse communities
- **Enhanced Call Message System**: Granular message tracking replacing monolithic transcripts
- **Improved Test Coverage**: From 63% to 72% with 98.4% test success rate
- **TTS Enhancements**: Fixed text-to-speech issues for better voice delivery
- **New API Endpoints**: Call message management APIs for better telephony integration

## 🌟 Overview

Thanotopolis is an advanced agentic AI framework that enables organizations to deploy sophisticated AI assistants across multiple channels. The platform features a multi-agent system where specialized AI agents can collaborate to handle complex queries, with support for telephony integration, real-time conversations, and customizable agent ownership models.

### Key Features

- 🤖 **Multi-Agent Architecture**: Specialized AI agents for different domains
- ☎️ **Telephony Integration**: AI-powered phone answering service with Twilio
- 🌍 **Multi-Language Support**: 12+ languages with automatic detection
- 🔍 **Web Search Capabilities**: Real-time information retrieval
- 🏢 **Organization Management**: Multi-tenant architecture with proprietary agents
- 💬 **Real-Time Conversations**: WebSocket-based streaming communications
- 📊 **Usage Tracking**: Comprehensive billing and analytics
- 🔒 **Enterprise Security**: Role-based access control and tenant isolation

## 🏗️ Architecture

### Backend (`/backend`)
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with pgvector for RAG
- **AI Integration**: OpenAI GPT models with specialized agents
- **Voice Services**: Deepgram (STT) + ElevenLabs (TTS)
- **Telephony**: Twilio integration with WebSocket streaming
- **Authentication**: JWT-based with role hierarchy
- **Testing**: Comprehensive unit and integration test suite

### Frontend (`/frontend`)
- **Framework**: Next.js 14 with TypeScript
- **UI**: Tailwind CSS with custom components
- **Real-time**: WebSocket connections for live conversations
- **Voice**: Browser-based audio recording and playback
- **State Management**: React Context and custom hooks
- **Testing**: Jest with React Testing Library

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis (for caching)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and database credentials

# Run database migrations
alembic upgrade head

# Start the backend server
python run.py
```

### Frontend Setup

```bash
cd frontend
npm install

# Set up environment variables
cp .env.local.example .env.local
# Edit .env.local with backend URL and other settings

# Start the development server
npm run dev
```

### Environment Variables

#### Backend (.env)
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/thanotopolis
OPENAI_API_KEY=your_openai_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
DEEPGRAM_API_KEY=your_deepgram_key
ELEVENLABS_API_KEY=your_elevenlabs_key
SECRET_KEY=your_secret_key
```

#### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## 🤖 AI Agents

### Core Agents

- **Barney (Demo Answering Service)**: Telephone receptionist for Cyberiad.ai
- **Moderator**: Agent selection and routing
- **Financial Services**: Payment plans and billing
- **Compliance**: Regulatory and documentation
- **Emergency**: Crisis and urgent situations
- **Inventory**: Facilities and equipment management
- **Web Search**: Real-time information retrieval

### Cultural Agents

Specialized agents providing culturally-sensitive funeral and memorial services:

- **Mexican Cultural Agent**: Traditional Mexican funeral customs and Day of the Dead
- **Salvadoran Cultural Agent**: Salvadoran memorial traditions
- **Filipino Cultural Agent**: Filipino wake and burial customs
- **Vietnamese Cultural Agent**: Vietnamese ancestor veneration practices
- **Korean Cultural Agent**: Korean funeral rites and memorial services
- **Jewish Cultural Agent**: Jewish burial and shiva traditions
- **Persian Cultural Agent**: Persian/Iranian funeral customs
- **Thai Cultural Agent**: Thai Buddhist funeral practices
- **Cambodian Cultural Agent**: Cambodian memorial traditions
- **Russian Cultural Agent**: Russian Orthodox funeral customs
- **Ukrainian Cultural Agent**: Ukrainian memorial services
- **Japanese Cultural Agent**: Japanese Buddhist and Shinto practices
- **Somali Cultural Agent**: Somali Islamic funeral traditions
- **Ethiopian Cultural Agent**: Ethiopian Orthodox customs
- **Chinese Cultural Agent**: Chinese ancestor worship and funeral rites
- **Polish Cultural Agent**: Polish Catholic traditions
- **Armenian Cultural Agent**: Armenian Apostolic funeral customs

### Agent Ownership

Agents can be **Free** (available to all) or **Proprietary** (organization-specific):

```python
# Free agent
class MyAgent(BaseAgent):
    OWNER_DOMAINS = []  # Available to all

# Single organization
class MyProprietaryAgent(BaseAgent):
    OWNER_DOMAINS = ["acme"]  # Only for ACME

# Multi-organization
class MySharedAgent(BaseAgent):
    OWNER_DOMAINS = ["acme", "demo", "partner"]  # Multiple orgs
```

## ☎️ Telephony Features

### Phone Integration
- **Call Forwarding**: Organizations keep existing numbers
- **Real-time Processing**: Live audio streaming with STT/TTS
- **Multi-language**: Automatic language detection and switching
- **Agent Collaboration**: Complex queries routed to specialists
- **Call Analytics**: Duration, costs, transcripts, and recordings

### How It Works
1. Customer calls organization's existing number
2. Call forwards to platform's Twilio number
3. AI agent (like Barney) answers and processes conversation
4. Real-time transcription and response generation
5. Natural voice synthesis back to caller

### Enhanced Call Message System
- **Structured Messages**: Calls now use granular message tracking instead of monolithic transcripts
- **Message Types**: 
  - `transcript`: Voice-to-text conversions
  - `system`: Platform notifications and status updates
  - `summary`: AI-generated conversation summaries
  - `note`: Manual annotations and observations
- **Better Call Details**: Formatted call history with individual message timestamps
- **Improved Analytics**: Track conversation flow and agent performance

## 🌐 API Endpoints

### Core APIs
- `/api/auth/*` - Authentication and user management
- `/api/conversations/*` - Chat and message handling
- `/api/agents/*` - Agent discovery and configuration
- `/api/telephony/*` - Phone system integration
- `/api/organizations/*` - Multi-tenant management
- `/api/billing/*` - Usage tracking and payments

### Call Message APIs
- `GET /api/telephony/calls/{call_id}/messages` - Retrieve call messages with filtering
- `POST /api/telephony/calls/{call_id}/messages` - Add new messages to calls
- `PATCH /api/telephony/calls/{call_id}/messages/{message_id}` - Update existing messages
- `DELETE /api/telephony/calls/{call_id}/messages/{message_id}` - Delete call messages

### WebSocket Endpoints
- `/api/ws/conversation/{id}` - Real-time chat
- `/api/ws/telephony/stream/{call_id}` - Voice streaming
- `/api/ws/voice/{conversation_id}` - Voice chat

## 🧪 Testing

### Backend Testing
```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests

# Generate coverage report
pytest --cov=app --cov-report=html
```

#### Test Coverage Stats
- **Overall Coverage**: 72% (up from 63%)
- **Test Success Rate**: 98.4% (1,360 of 1,382 tests passing)
- **Test Organization**: Comprehensive unit and integration test suites

### Frontend Testing
```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run integration tests
npm run test:integration
```

## 📦 Deployment

### Production Setup

1. **Database**: PostgreSQL with pgvector extension
2. **Backend**: Deploy with Gunicorn + Nginx
3. **Frontend**: Build and deploy with Next.js
4. **Voice Services**: Configure Deepgram + ElevenLabs
5. **Telephony**: Set up Twilio webhooks

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Environment Setup
- Set production environment variables
- Configure SSL certificates
- Set up monitoring and logging
- Configure backup strategies

## 🛡️ Security

### Authentication
- JWT-based authentication
- Role hierarchy: user → org_admin → admin → super_admin
- Multi-tenant isolation

### Data Protection
- Encrypted API communications
- Secure voice streaming
- PII handling compliance
- Input sanitization and validation

## 📊 Monitoring

### Metrics Tracked
- API response times and error rates
- Agent performance and usage
- Voice service quality metrics
- Database performance
- Call volume and costs

### Logging
- Structured logging with correlation IDs
- Error tracking and alerting
- Audit trails for sensitive operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Guidelines
- Follow PEP 8 for Python code
- Use TypeScript for all frontend code
- Write comprehensive tests
- Document new features
- Maintain backward compatibility

## 📖 Documentation

- [`/backend/CLAUDE.md`](backend/CLAUDE.md) - Backend development guide
- [`/frontend/CLAUDE.md`](frontend/CLAUDE.md) - Frontend development guide
- [`/backend/AGENT_OWNERSHIP_GUIDE.md`](backend/AGENT_OWNERSHIP_GUIDE.md) - Agent ownership system
- [`/backend/BARNEY_AGENT_SUMMARY.md`](backend/BARNEY_AGENT_SUMMARY.md) - Barney agent details

## 📄 License

This project is proprietary software owned by Cyberiad.ai. All rights reserved.

## 🚀 About Cyberiad.ai

Cyberiad.ai creates advanced agentic AI frameworks that enable organizations to deploy sophisticated AI assistants. Our platforms are designed for scalability, customization, and seamless integration with existing business processes.

---

**Built with ❤️ by the Cyberiad.ai team**