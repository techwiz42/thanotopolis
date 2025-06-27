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