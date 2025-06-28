"""
Deepgram Voice Agent API Service
Handles real-time conversational AI with integrated STT, LLM, and TTS
"""

import asyncio
import json
import base64
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import websockets
import logging
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VoiceAgentConfig:
    """Configuration for Deepgram Voice Agent"""
    api_key: str
    listening_model: str = "nova-3"  # STT model
    thinking_model: str = "gpt-4o-mini"  # LLM model
    speaking_model: str = "aura-2-thalia-en"  # TTS voice
    
    # Audio settings for Twilio
    input_encoding: str = "mulaw"
    input_sample_rate: int = 8000
    output_encoding: str = "mulaw"
    output_sample_rate: int = 8000
    
    # Agent behavior
    system_prompt: str = "You are a professional AI assistant answering a phone call. Be helpful, respectful, and keep responses concise for phone conversation. If you don't have specific information, offer to connect the caller with more specialized agent or a human representative."
    turn_detection_mode: str = "server_vad"  # Voice Activity Detection
    end_of_speech_threshold: int = 1000  # ms of silence before considering speech complete


class DeepgramVoiceAgent:
    """Manages Deepgram Voice Agent WebSocket connections"""
    
    def __init__(self, config: VoiceAgentConfig):
        self.config = config
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.settings_applied = False  # Track if settings have been applied
        self.event_handlers: Dict[str, Callable] = {}
        self._receive_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        """Establish WebSocket connection to Deepgram Voice Agent"""
        try:
            # Use Authorization header for authentication 
            headers = {
                "Authorization": f"Token {self.config.api_key}"
            }
            
            # Voice Agent WebSocket endpoint - correct v1 endpoint
            url = "wss://agent.deepgram.com/v1/agent/converse"
            
            logger.info("🔑 Using configured API key...")
            logger.info(f"🌐 Connecting to: {url}")
            logger.info("🔌 Connecting to Deepgram Voice Agent with Authorization header...")
            
            self.websocket = await websockets.connect(url, additional_headers=headers)
            self.is_connected = True
            
            # Send initial configuration
            await self._send_settings()
            
            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            # Start keep-alive task (send every 5 seconds as per docs)
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            
            logger.info("✅ Connected to Deepgram Voice Agent")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Voice Agent: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        self.is_connected = False
        self.settings_applied = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if hasattr(self, '_keepalive_task') and self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
        logger.info("🔌 Disconnected from Deepgram Voice Agent")
    
    async def _send_settings(self):
        """Send initial settings to configure the Voice Agent"""
        settings_message = {
            "type": "Settings",
            "audio": {
                "input": {
                    "encoding": self.config.input_encoding,
                    "sample_rate": self.config.input_sample_rate
                },
                "output": {
                    "encoding": self.config.output_encoding,
                    "sample_rate": self.config.output_sample_rate,
                    "container": "none"
                }
            },
            "agent": {
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": self.config.listening_model
                    }
                },
                "think": {
                    "provider": {
                        "type": "open_ai",
                        "model": self.config.thinking_model,
                        "temperature": 0.7
                    },
                    "prompt": self.config.system_prompt
                },
                "speak": {
                    "provider": {
                        "type": "deepgram", 
                        "model": self.config.speaking_model
                    }
                }
            }
        }
        
        settings_json = json.dumps(settings_message)
        logger.info(f"📤 Sending Voice Agent settings: {settings_json}")
        await self.websocket.send(settings_json)
        logger.info("📤 Sent Voice Agent settings")
    
    async def send_greeting_message(self, greeting_content: str):
        """Send an actual greeting message that the agent will speak"""
        try:
            inject_message = {
                "type": "InjectAgentMessage", 
                "content": greeting_content
            }
            
            await self.websocket.send(json.dumps(inject_message))
            logger.info(f"📤 Sent greeting message to Voice Agent")
        except Exception as e:
            logger.error(f"❌ Failed to send greeting message: {e}")
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to Voice Agent"""
        if not self.is_connected or not self.websocket:
            # Only log this once per session to avoid spam
            if not hasattr(self, '_logged_not_connected'):
                logger.warning("Cannot send audio - not connected")
                self._logged_not_connected = True
            return
            
        if not self.settings_applied:
            # Only log this once per session to avoid spam
            if not hasattr(self, '_logged_settings_not_ready'):
                logger.warning("Cannot send audio - settings not yet applied by Voice Agent")
                self._logged_settings_not_ready = True
            return
            
        # Voice Agent expects raw binary audio data, not JSON
        # Only log occasionally to avoid spam (every 100th packet)
        if not hasattr(self, '_audio_count'):
            self._audio_count = 0
        self._audio_count += 1
        if self._audio_count % 100 == 1:
            logger.debug(f"📤 Sending audio data (packet {self._audio_count}: {len(audio_data)} bytes)")
        
        await self.websocket.send(audio_data)
    
    async def update_instructions(self, instructions: str):
        """Update the agent's instructions/prompt mid-conversation"""
        if not self.is_connected or not self.websocket:
            return
            
        message = {
            "type": "UpdateInstructions",
            "instructions": instructions
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info("📤 Updated agent instructions")
    
    async def inject_message(self, text: str, role: str = "assistant"):
        """Inject a message into the conversation"""
        if not self.is_connected or not self.websocket:
            return
            
        # Use correct V1 API format - same as working _send_greeting_injection
        if role.lower() == "assistant" or role.lower() == "agent":
            message = {
                "type": "InjectAgentMessage",
                "content": text
            }
        else:
            # For user messages, try InjectUserMessage format
            message = {
                "type": "InjectUserMessage",
                "content": text
            }
        
        await self.websocket.send(json.dumps(message))
        logger.info(f"📤 Injected {role} message to Voice Agent")
    
    def on_event(self, event_type: str, handler: Callable):
        """Register an event handler"""
        self.event_handlers[event_type] = handler
    
    async def _receive_loop(self):
        """Receive and process messages from Voice Agent"""
        try:
            while self.is_connected and self.websocket:
                message = await self.websocket.recv()
                
                if isinstance(message, str):
                    # JSON message (events)
                    data = json.loads(message)
                    await self._handle_event(data)
                else:
                    # Binary message (audio)
                    await self._handle_audio(message)
                    
        except websockets.ConnectionClosed:
            logger.info("Voice Agent connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            self.is_connected = False
    
    async def _keepalive_loop(self):
        """Send keep-alive messages every 5 seconds"""
        try:
            # Wait longer before first keep-alive to avoid interfering with settings
            await asyncio.sleep(10)  
            while self.is_connected and self.websocket:
                if self.is_connected and self.websocket:
                    keepalive_message = {"type": "KeepAlive"}  # Use correct case
                    await self.websocket.send(json.dumps(keepalive_message))
                    logger.debug("💓 Sent keep-alive to Voice Agent")
                await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error in keep-alive loop: {e}")
    
    async def _handle_event(self, event: Dict[str, Any]):
        """Process Voice Agent events"""
        event_type = event.get("type", "")
        
        # Log events (sanitized for security)
        logger.info(f"📥 Voice Agent event: {event_type}")
        logger.debug(f"🔍 Event data: {self._sanitize_event_for_logging(event)}")
        
        # Handle specific events
        if event_type == "Welcome":
            logger.info("👋 Received Welcome from Voice Agent")
            
        elif event_type == "SettingsApplied":
            logger.info("⚙️ Settings applied successfully")
            self.settings_applied = True
            logger.info("✅ Voice Agent ready to receive audio")
            
            # Will be triggered by telephony handler with custom greeting
            
        elif event_type == "Error":
            # Log the error details
            error_msg = event.get("message", "Unknown error")
            error_code = event.get("code", "Unknown code")
            error_type = event.get("type", "Unknown type")
            logger.error(f"❌ Voice Agent Error: {error_code} - {error_msg}")
            logger.error(f"❌ Error type: {error_type}")
            logger.error(f"❌ Full error event: {event}")
            
            # If this is a parsing error, we may need to disconnect and reconnect
            if "UNPARSABLE" in error_msg or "UNPARSABLE" in error_code:
                logger.error("🔌 UNPARSABLE error detected - Voice Agent cannot parse our audio format")
                logger.error("💡 This suggests audio format mismatch between Twilio and Voice Agent")
            
        elif event_type == "ConversationText":
            # Text of what was spoken - try both field names
            text = event.get("content", "") or event.get("text", "")
            role = event.get("role", "")
            logger.info(f"💬 ConversationText received - role='{role}': text='{text}'")
            logger.info(f"🔍 Full ConversationText event: {event}")
            
        elif event_type == "Transcript":
            # Alternative transcript event type  
            text = event.get("content", "") or event.get("text", "")
            role = event.get("role", "")
            is_final = event.get("is_final", False)
            logger.info(f"💬 Transcript received - role='{role}': text='{text}' (final: {is_final})")
            
        elif event_type == "TranscriptText":
            # Another possible transcript event type
            text = event.get("content", "") or event.get("text", "")
            role = event.get("role", "")
            logger.info(f"💬 TranscriptText received - role='{role}': text='{text}'")
            
        elif event_type == "UserText":
            # User speaking
            text = event.get("content", "") or event.get("text", "")
            logger.info(f"💬 UserText received: text='{text}'")
            
        elif event_type == "AgentText":
            # Agent speaking
            text = event.get("content", "") or event.get("text", "")
            logger.info(f"💬 AgentText received: text='{text}'")
            
        elif event_type == "UserStartedSpeaking":
            logger.info("🗣️ User started speaking")
            
        elif event_type == "AgentStartedSpeaking":
            logger.info("🤖 Agent started speaking")
            
        elif event_type == "AgentThinking":
            logger.info("🤔 Agent is thinking...")
            
        elif event_type == "FunctionCallRequest":
            # Agent wants to call a function
            function_name = event.get("function_name")
            parameters = event.get("parameters")
            logger.info(f"🔧 Function call request: {function_name}")
            
        else:
            # Log unhandled events to see what we're missing
            logger.info(f"🔍 Unhandled Voice Agent event: {event_type}")
            logger.info(f"🔍 Event data: {event}")
            
            # Check if unhandled event contains text that might be user speech
            text_content = event.get("content", "") or event.get("text", "") or event.get("transcript", "")
            role = event.get("role", "")
            
            if text_content and text_content.strip():
                logger.warning(f"🚨 UNHANDLED EVENT WITH TEXT: {event_type}")
                logger.warning(f"🚨 Text: '{text_content}' | Role: '{role}'")
                logger.warning(f"🚨 This might be user speech that we're missing!")
            
        # Call registered handler if exists
        handler = self.event_handlers.get(event_type)
        if handler:
            logger.info(f"📞 Calling registered handler for {event_type}")
            await handler(event)
        else:
            logger.warning(f"⚠️ No handler registered for event type: {event_type}")
    
    def _sanitize_event_for_logging(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize event data for safe logging"""
        sanitized = event.copy()
        
        # Remove or truncate sensitive fields
        sensitive_fields = ["content", "text", "transcript", "message", "response"]
        for field in sensitive_fields:
            if field in sanitized and sanitized[field]:
                # Keep first 50 chars only
                sanitized[field] = str(sanitized[field])[:50] + "..." if len(str(sanitized[field])) > 50 else sanitized[field]
        
        # Remove any API keys or tokens
        if "api_key" in sanitized:
            sanitized["api_key"] = "***REDACTED***"
        if "token" in sanitized:
            sanitized["token"] = "***REDACTED***"
            
        return sanitized

    async def _handle_audio(self, audio_data: bytes):
        """Process audio data from Voice Agent"""
        # Audio from Voice Agent (agent's speech)
        handler = self.event_handlers.get("AudioData")
        if handler:
            await handler(audio_data)


class VoiceAgentSession:
    """Manages a single Voice Agent conversation session"""
    
    def __init__(self, session_id: str, config: VoiceAgentConfig):
        self.session_id = session_id
        self.agent = DeepgramVoiceAgent(config)
        self.start_time = datetime.utcnow()
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        # Store original instructions for restoration after collaboration
        self.original_instructions = config.system_prompt if hasattr(config, 'system_prompt') else None
        
    async def start(self):
        """Start the Voice Agent session"""
        success = await self.agent.connect()
        if not success:
            raise Exception("Failed to connect to Voice Agent")
            
        logger.info(f"🚀 Voice Agent session {self.session_id} started")
        
    async def stop(self):
        """Stop the Voice Agent session"""
        await self.agent.disconnect()
        logger.info(f"🛑 Voice Agent session {self.session_id} stopped")
        
    def register_audio_handler(self, handler: Callable):
        """Register handler for audio from agent"""
        self.agent.on_event("AudioData", handler)
        
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register handler for specific event type"""
        self.agent.on_event(event_type, handler)
    
    async def inject_message(self, text: str, role: str = "assistant"):
        """Inject a message into the conversation (convenience method)"""
        return await self.agent.inject_message(text, role)
    
    async def update_instructions(self, instructions: str):
        """Update the agent's instructions (convenience method)"""
        return await self.agent.update_instructions(instructions)
    
    async def send_greeting_message(self, greeting_content: str):
        """Send an actual greeting message that the agent will speak (convenience method)"""
        return await self.agent.send_greeting_message(greeting_content)


# Service singleton
_voice_agent_service: Optional['VoiceAgentService'] = None


class VoiceAgentService:
    """Service for managing Voice Agent sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, VoiceAgentSession] = {}
        
    async def create_session(
        self,
        session_id: str,
        system_prompt: Optional[str] = None,
        voice_model: Optional[str] = None
    ) -> VoiceAgentSession:
        """Create a new Voice Agent session"""
        
        config = VoiceAgentConfig(
            api_key=settings.DEEPGRAM_API_KEY,
            listening_model=settings.VOICE_AGENT_LISTENING_MODEL,
            thinking_model=settings.VOICE_AGENT_THINKING_MODEL,
            speaking_model=voice_model or settings.VOICE_AGENT_SPEAKING_MODEL,
            system_prompt=system_prompt or "You are a professional AI assistant answering a phone call. Be helpful, respectful, and keep responses concise for phone conversation. If you don't have specific information, offer to connect the caller with more specialized agent or a human representative."
        )
        
        session = VoiceAgentSession(session_id, config)
        self.sessions[session_id] = session
        
        await session.start()
        return session
        
    async def get_session(self, session_id: str) -> Optional[VoiceAgentSession]:
        """Get existing session"""
        return self.sessions.get(session_id)
        
    async def end_session(self, session_id: str):
        """End and cleanup session"""
        session = self.sessions.get(session_id)
        if session:
            await session.stop()
            del self.sessions[session_id]


def get_voice_agent_service() -> VoiceAgentService:
    """Get Voice Agent service singleton"""
    global _voice_agent_service
    if _voice_agent_service is None:
        _voice_agent_service = VoiceAgentService()
    return _voice_agent_service