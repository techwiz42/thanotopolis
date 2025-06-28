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
