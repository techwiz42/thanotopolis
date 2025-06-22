# Thanotopolis - Multi-Agent AI Platform

A comprehensive multi-agent AI platform built by **Cyberiad.ai** that provides intelligent telephone answering services, web-based conversations, and specialized AI agents for various industries and use cases.

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

## 🌐 API Endpoints

### Core APIs
- `/api/auth/*` - Authentication and user management
- `/api/conversations/*` - Chat and message handling
- `/api/agents/*` - Agent discovery and configuration
- `/api/telephony/*` - Phone system integration
- `/api/organizations/*` - Multi-tenant management
- `/api/billing/*` - Usage tracking and payments

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
```

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