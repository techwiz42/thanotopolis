# backend/app/api/telephony_websocket.py
"""
WebSocket handler for telephony streaming - handles real-time voice communication
"""

import asyncio
import json
import logging
import base64
from typing import Dict, Optional, Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.models.models import PhoneCall, TelephonyConfiguration, Conversation, Message, CallStatus
from app.services.telephony_service import telephony_service
from app.services.voice.deepgram_service import deepgram_service
from app.services.voice.elevenlabs_service import elevenlabs_service
from app.services.usage_service import usage_service
from app.agents.agent_manager import agent_manager
from app.agents.common_context import CommonAgentContext

logger = logging.getLogger(__name__)


def count_words(text: str) -> int:
    """Count words in text for usage tracking."""
    if not text:
        return 0
    return len(text.split())


class TelephonyStreamHandler:
    """Handles telephony streaming WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.call_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        call_id: UUID,
        db: AsyncSession
    ):
        """Handle new telephony WebSocket connection"""
        
        try:
            await websocket.accept()
            
            # Get call details
            call_query = select(PhoneCall).where(PhoneCall.id == call_id)
            call_result = await db.execute(call_query)
            call = call_result.scalar_one_or_none()
            
            if not call:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Call not found"
                }))
                await websocket.close()
                return
            
            # Get telephony configuration
            config_query = select(TelephonyConfiguration).where(
                TelephonyConfiguration.id == call.telephony_config_id
            )
            config_result = await db.execute(config_query)
            config = config_result.scalar_one()
            
            # Update call status to answered
            await telephony_service.update_call_status(
                db=db,
                call_sid=call.call_sid,
                status=CallStatus.ANSWERED
            )
            
            # Create conversation for this call
            conversation = await self._create_call_conversation(db, call, config)
            
            # Initialize session
            session_id = str(call_id)
            self.active_connections[session_id] = websocket
            
            self.call_sessions[session_id] = {
                "call": call,
                "config": config,
                "conversation": conversation,
                "stt_active": False,
                "tts_active": False,
                "agent_processing": False,
                "audio_buffer": [],
                "transcript_buffer": "",
                "voice_id": config.voice_id or "default"
            }
            
            logger.info(f"📞 Telephony WebSocket connected for call {call.call_sid}")
            
            # Send initial status
            await self._send_message(session_id, {
                "type": "connected",
                "call_id": str(call_id),
                "call_sid": call.call_sid,
                "conversation_id": str(conversation.id)
            })
            
            # Start processing loop
            await self._process_call_session(websocket, session_id, db)
            
        except Exception as e:
            logger.error(f"❌ Error in telephony WebSocket connection: {e}")
            await websocket.close()
        finally:
            # Cleanup
            if session_id in self.active_connections:
                del self.active_connections[session_id]
            if session_id in self.call_sessions:
                del self.call_sessions[session_id]
    
    async def _process_call_session(
        self,
        websocket: WebSocket,
        session_id: str,
        db: AsyncSession
    ):
        """Process the call session with continuous audio streaming"""
        
        session = self.call_sessions[session_id]
        
        try:
            while True:
                # Receive data from Twilio
                data = await websocket.receive()
                
                if data["type"] == "websocket.disconnect":
                    break
                
                # Parse message
                if "text" in data:
                    message = json.loads(data["text"])
                    await self._handle_twilio_message(session_id, message, db)
                elif "bytes" in data:
                    # Handle binary audio data
                    await self._handle_audio_data(session_id, data["bytes"], db)
        
        except WebSocketDisconnect:
            logger.info(f"📞 Telephony WebSocket disconnected for session {session_id}")
        except Exception as e:
            logger.error(f"❌ Error processing call session {session_id}: {e}")
        finally:
            # Update call status to completed
            call = session["call"]
            await telephony_service.update_call_status(
                db=db,
                call_sid=call.call_sid,
                status=CallStatus.COMPLETED
            )
    
    async def _handle_twilio_message(
        self,
        session_id: str,
        message: Dict[str, Any],
        db: AsyncSession
    ):
        """Handle messages from Twilio stream"""
        
        session = self.call_sessions[session_id]
        message_type = message.get("event")
        
        if message_type == "connected":
            # Stream connected
            await self._send_message(session_id, {
                "type": "stream_connected",
                "message": "Audio stream connected"
            })
            
        elif message_type == "start":
            # Stream started
            session["stt_active"] = True
            await self._send_message(session_id, {
                "type": "stream_started",
                "message": "Audio processing started"
            })
            
        elif message_type == "media":
            # Audio data received
            audio_data = message.get("media", {}).get("payload", "")
            if audio_data:
                await self._process_audio_chunk(session_id, audio_data, db)
        
        elif message_type == "stop":
            # Stream stopped
            session["stt_active"] = False
            await self._finalize_transcript(session_id, db)
    
    async def _handle_audio_data(
        self,
        session_id: str,
        audio_bytes: bytes,
        db: AsyncSession
    ):
        """Handle binary audio data"""
        
        session = self.call_sessions[session_id]
        
        if not session["stt_active"]:
            return
        
        # Add to audio buffer
        session["audio_buffer"].append(audio_bytes)
        
        # Process audio in chunks
        if len(session["audio_buffer"]) >= 10:  # Process every 10 chunks
            combined_audio = b''.join(session["audio_buffer"])
            session["audio_buffer"] = []
            
            # Send to speech-to-text
            try:
                transcript = await deepgram_service.transcribe_stream(combined_audio)
                if transcript:
                    await self._handle_transcript(session_id, transcript, db)
            except Exception as e:
                logger.error(f"❌ STT error for session {session_id}: {e}")
    
    async def _process_audio_chunk(
        self,
        session_id: str,
        audio_payload: str,
        db: AsyncSession
    ):
        """Process incoming audio chunk from Twilio"""
        
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_payload)
            
            # Send to Deepgram for transcription
            transcript = await deepgram_service.transcribe_stream(audio_data)
            
            if transcript:
                await self._handle_transcript(session_id, transcript, db)
                
        except Exception as e:
            logger.error(f"❌ Error processing audio chunk: {e}")
    
    async def _handle_transcript(
        self,
        session_id: str,
        transcript: str,
        db: AsyncSession
    ):
        """Handle transcribed text from caller"""
        
        session = self.call_sessions[session_id]
        
        # Add to transcript buffer
        session["transcript_buffer"] += " " + transcript.strip()
        
        # Check if we have a complete utterance (simple heuristic)
        if self._is_complete_utterance(session["transcript_buffer"]):
            complete_text = session["transcript_buffer"].strip()
            session["transcript_buffer"] = ""
            
            logger.info(f"📝 Complete transcript: {complete_text}")
            
            # Record STT usage
            word_count = count_words(complete_text)
            if word_count > 0:
                config = session["config"]
                try:
                    await usage_service.record_stt_usage(
                        db=db,
                        tenant_id=config.tenant_id,
                        user_id=None,  # No specific user for phone calls
                        word_count=word_count,
                        service_provider="deepgram",
                        model_name="nova-2"  # Default telephony model
                    )
                    logger.info(f"📊 Recorded STT usage: {word_count} words for tenant {config.tenant_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to record STT usage: {e}")
            
            # Send transcript to conversation
            await self._send_message(session_id, {
                "type": "transcript",
                "text": complete_text,
                "is_final": True
            })
            
            # Process with AI agents
            await self._process_with_agents(session_id, complete_text, db)
    
    async def _process_with_agents(
        self,
        session_id: str,
        user_message: str,
        db: AsyncSession
    ):
        """Process user message with AI agents"""
        
        session = self.call_sessions[session_id]
        
        if session["agent_processing"]:
            return  # Already processing
        
        session["agent_processing"] = True
        
        try:
            conversation = session["conversation"]
            config = session["config"]
            
            # Create message record
            message = Message(
                conversation_id=conversation.id,
                content=user_message,
                message_type="text",
                participant_id=None,  # Phone caller
                additional_data=json.dumps({
                    "sender_type": "caller",
                    "call_id": str(session["call"].id),
                    "phone_number": session["call"].customer_phone_number
                })
            )
            db.add(message)
            await db.commit()
            
            # Get agent response using process_conversation
            agent_type, agent_response = await agent_manager.process_conversation(
                message=user_message,
                conversation_agents=[],  # Will be discovered dynamically
                agents_config={},  # Will use default config
                db=db,
                thread_id=str(conversation.id),
                owner_id=config.tenant_id
            )
            
            # Convert response to speech
            await self._send_speech_response(session_id, agent_response, db)
            
        except Exception as e:
            logger.error(f"❌ Error processing with agents: {e}")
            # Send error response
            await self._send_speech_response(
                session_id,
                "I'm sorry, I'm having trouble processing your request. Could you please try again?",
                db
            )
        finally:
            session["agent_processing"] = False
    
    async def _send_speech_response(
        self,
        session_id: str,
        text_response: str,
        db: AsyncSession
    ):
        """Convert text response to speech and send to caller"""
        
        session = self.call_sessions[session_id]
        
        try:
            # Generate speech
            audio_data = await elevenlabs_service.generate_speech(
                text=text_response,
                voice_id=session["voice_id"]
            )
            
            if audio_data:
                # Record TTS usage
                word_count = count_words(text_response)
                if word_count > 0:
                    config = session["config"]
                    try:
                        await usage_service.record_tts_usage(
                            db=db,
                            tenant_id=config.tenant_id,
                            user_id=None,  # No specific user for phone calls
                            word_count=word_count,
                            service_provider="elevenlabs",
                            model_name="eleven_turbo_v2"  # Default telephony model
                        )
                        logger.info(f"📊 Recorded TTS usage: {word_count} words for tenant {config.tenant_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to record TTS usage: {e}")
                
                # Send audio to Twilio stream
                await self._send_audio_to_caller(session_id, audio_data)
                
                # Save response message
                conversation = session["conversation"]
                response_message = Message(
                    conversation_id=conversation.id,
                    content=text_response,
                    message_type="text",
                    agent_type="ASSISTANT",
                    additional_data=json.dumps({
                        "sender_type": "agent",
                        "call_id": str(session["call"].id),
                        "has_audio": True
                    })
                )
                db.add(response_message)
                await db.commit()
                
                logger.info(f"🗣️ Speech response sent to caller: {text_response[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Error generating speech response: {e}")
    
    async def _send_audio_to_caller(
        self,
        session_id: str,
        audio_data: bytes
    ):
        """Send audio data to caller via Twilio stream"""
        
        try:
            # Convert audio to base64 for Twilio
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Send to Twilio stream
            await self._send_message(session_id, {
                "event": "media",
                "streamSid": session_id,
                "media": {
                    "payload": audio_base64
                }
            })
            
        except Exception as e:
            logger.error(f"❌ Error sending audio to caller: {e}")
    
    async def _create_call_conversation(
        self,
        db: AsyncSession,
        call: PhoneCall,
        config: TelephonyConfiguration
    ) -> Conversation:
        """Create a conversation record for the phone call"""
        
        conversation = Conversation(
            tenant_id=config.tenant_id,
            title=f"Phone Call - {call.customer_phone_number}",
            description=f"Incoming call from {call.customer_phone_number}",
            status="active"
        )
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        # Link call to conversation
        call.conversation_id = conversation.id
        await db.commit()
        
        return conversation
    
    def _is_complete_utterance(self, text: str) -> bool:
        """Simple heuristic to detect complete utterances"""
        
        if not text.strip():
            return False
        
        # Check for sentence endings
        if text.strip().endswith(('.', '!', '?')):
            return True
        
        # Check for pauses (multiple spaces or length)
        if len(text.strip()) > 100:
            return True
        
        # Check for question words at the beginning
        question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'can', 'could', 'would', 'will']
        first_word = text.strip().lower().split()[0] if text.strip() else ""
        if first_word in question_words and len(text.strip()) > 20:
            return True
        
        return False
    
    async def _finalize_transcript(
        self,
        session_id: str,
        db: AsyncSession
    ):
        """Finalize any remaining transcript"""
        
        session = self.call_sessions[session_id]
        
        if session["transcript_buffer"].strip():
            complete_text = session["transcript_buffer"].strip()
            session["transcript_buffer"] = ""
            
            await self._send_message(session_id, {
                "type": "transcript",
                "text": complete_text,
                "is_final": True
            })
            
            await self._process_with_agents(session_id, complete_text, db)
    
    async def _send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"❌ Error sending message to {session_id}: {e}")

# Create global handler instance
telephony_stream_handler = TelephonyStreamHandler()

# Create FastAPI router
from fastapi import APIRouter

router = APIRouter(
    prefix="/telephony/ws",
    tags=["telephony-websocket"],
    responses={404: {"description": "Not found"}},
)

@router.websocket("/{call_id}")
async def telephony_websocket_endpoint(
    websocket: WebSocket,
    call_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for telephony streaming.
    
    This endpoint handles real-time voice communication for phone calls,
    including:
    - Audio streaming from/to Twilio
    - Speech-to-text conversion
    - AI agent processing
    - Text-to-speech response generation
    """
    await telephony_stream_handler.handle_connection(websocket, call_id, db)

