# backend/app/api/telephony_websocket.py
"""
WebSocket handler for telephony streaming - handles real-time voice communication
"""

import asyncio
import json
import logging
import base64
import struct
import io
import time
import wave
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
from app.agents.tenant_aware_agent_manager import tenant_aware_agent_manager
from app.agents.common_context import CommonAgentContext
from app.core.config import settings

logger = logging.getLogger(__name__)


def count_words(text: str) -> int:
    """Count words in text for usage tracking."""
    if not text:
        return 0
    return len(text.split())


def convert_mulaw_to_wav(mulaw_data: bytes) -> bytes:
    """
    Convert mulaw audio data to WAV format for better Deepgram compatibility.
    
    Twilio sends mulaw (G.711) encoded audio which needs to be converted
    to linear PCM for better transcription accuracy.
    """
    try:
        # Convert mulaw to linear PCM (16-bit)
        linear_pcm = audioop.ulaw2lin(mulaw_data, 2)  # 2 bytes per sample (16-bit)
        
        # Create a WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)     # Mono
            wav_file.setsampwidth(2)     # 2 bytes per sample (16-bit)
            wav_file.setframerate(8000)  # 8kHz sample rate (Twilio standard)
            wav_file.writeframes(linear_pcm)
        
        wav_buffer.seek(0)
        return wav_buffer.getvalue()
    
    except Exception as e:
        logger.error(f"Error converting mulaw to WAV: {e}")
        # Return the original mulaw data as fallback
        return mulaw_data


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
        
        session_id = str(call_id)  # Initialize session_id early
        
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
            self.active_connections[session_id] = websocket
            
            self.call_sessions[session_id] = {
                "call": call,
                "config": config,
                "conversation": conversation,
                "stt_active": False,
                "tts_active": False,
                "agent_processing": False,
                "audio_buffer": bytearray(),
                "transcript_buffer": "",
                "voice_id": config.voice_id or settings.ELEVENLABS_VOICE_ID,
                "last_audio_time": time.time(),
                "silence_threshold": 0.3,  # 300ms of silence before processing buffer
                "min_buffer_size": 12000,  # ~0.75 seconds at 8000 Hz, 16-bit = 16000 bytes per second  
                "max_buffer_size": 32000,  # ~2 seconds max buffer
                "greeting_sent": False,    # Track if initial greeting was sent
                "last_process_time": time.time(),  # Track last audio processing time
                "pending_response_task": None,  # Track delayed response task
                "last_transcript_time": None    # Track when last transcript was received
            }
            
            logger.info(f"📞 Telephony WebSocket connected for call {call.call_sid}")
            
            # Send initial status
            await self._send_message(session_id, {
                "type": "connected",
                "call_id": str(call_id),
                "call_sid": call.call_sid,
                "conversation_id": str(conversation.id)
            })
            
            # Don't send initial greeting here - wait for Twilio to send "start" event with streamSid
            logger.info(f"🎙️ Waiting for Twilio stream to start before sending greeting...")
            
            # Start processing loop
            await self._process_call_session(websocket, session_id, db)
            
        except Exception as e:
            logger.error(f"❌ Error in telephony WebSocket connection: {e}")
            await websocket.close()
        finally:
            # Cleanup - flush any remaining audio buffer
            if session_id in self.call_sessions:
                await self._flush_audio_buffer(session_id, db)
            
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
            
            # Auto-generate summary for completed call
            try:
                await self._generate_call_summary(call.id, db)
            except Exception as e:
                logger.error(f"❌ Error generating summary for call {call.id}: {e}")
                # Don't fail the call completion if summary generation fails
    
    async def _handle_twilio_message(
        self,
        session_id: str,
        message: Dict[str, Any],
        db: AsyncSession
    ):
        """Handle messages from Twilio stream or frontend"""
        
        session = self.call_sessions[session_id]
        
        # Handle frontend message types first
        frontend_type = message.get("type")
        if frontend_type:
            if frontend_type == "agent_message":
                # Handle agent message from frontend for TTS
                agent_text = message.get("message", "")
                language = message.get("language", "en")
                logger.info(f"📞 Received agent message from frontend: {agent_text[:50]}...")
                
                # Process with TTS and send to caller
                await self._send_speech_response(session_id, agent_text, db)
                return
            
            elif frontend_type == "init_telephony_stream":
                # Frontend initialization - acknowledge
                logger.info(f"📞 Frontend telephony stream initialized for call: {message.get('call_id')}")
                await self._send_message(session_id, {
                    "type": "telephony_connected",
                    "call_id": session_id,
                    "status": "ready"
                })
                return
            
            elif frontend_type == "ping":
                # Heartbeat from frontend
                await self._send_message(session_id, {"type": "pong"})
                return
        
        # Handle Twilio message types
        message_type = message.get("event")
        
        if message_type == "connected":
            # Stream connected
            await self._send_message(session_id, {
                "type": "stream_connected",
                "message": "Audio stream connected"
            })
            
        elif message_type == "start":
            # Stream started - capture streamSid for later use
            start_data = message.get("start", {})
            stream_sid = start_data.get("streamSid")
            logger.error(f"📻 DEBUG: Twilio start event received. Full message: {message}")
            logger.error(f"📻 DEBUG: Start data: {start_data}")
            
            if stream_sid:
                session["stream_sid"] = stream_sid
                logger.error(f"📻 ✅ Captured streamSid: {stream_sid}")
            else:
                # Try alternative ways to get streamSid
                stream_sid = message.get("streamSid")  # Direct from message
                if stream_sid:
                    session["stream_sid"] = stream_sid
                    logger.error(f"📻 ✅ Captured streamSid from message root: {stream_sid}")
                else:
                    logger.error(f"❌ No streamSid found! Message keys: {list(message.keys())}")
                    logger.error(f"❌ Start data keys: {list(start_data.keys())}")
                    
            session["stt_active"] = True
            await self._send_message(session_id, {
                "type": "stream_started",
                "message": "Audio processing started"
            })
            
            # NOW send the initial greeting since we have the streamSid
            if not session.get("greeting_sent", False):
                logger.info(f"🎙️ Stream ready, sending initial greeting for session {session_id}")
                await self._send_initial_greeting(session_id, db)
                session["greeting_sent"] = True
            else:
                logger.info(f"🎙️ Initial greeting already sent for session {session_id}")
            
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
        
        # This is now handled by the main audio processing logic below
    
    async def _process_audio_chunk(
        self,
        session_id: str,
        audio_payload: str,
        db: AsyncSession
    ):
        """Process incoming audio chunk from Twilio with buffering"""
        
        try:
            session = self.call_sessions[session_id]
            
            # Decode base64 audio
            mulaw_data = base64.b64decode(audio_payload)
            
            # Convert mulaw to linear PCM
            pcm_data = audioop.ulaw2lin(mulaw_data, 2)  # Convert to 16-bit PCM
            
            # Add to buffer
            session["audio_buffer"].extend(pcm_data)
            session["last_audio_time"] = time.time()
            
            # Check if we should process the buffer
            current_time = time.time()
            buffer_size = len(session["audio_buffer"])
            
            # Time since last processing
            time_since_last = current_time - session.get("last_process_time", current_time)
            
            should_process = (
                # Buffer is at minimum size 
                buffer_size >= session["min_buffer_size"] or
                # Buffer is at maximum size (prevent memory issues)
                buffer_size >= session["max_buffer_size"] or
                # Timeout - process after 0.5 second even if buffer is small
                (buffer_size > 0 and time_since_last > 0.5)
            )
            
            if should_process and buffer_size > 0:
                # Convert buffered PCM to WAV
                wav_data = self._pcm_to_wav(bytes(session["audio_buffer"]))
                
                # Clear the buffer and update process time
                session["audio_buffer"] = bytearray()
                session["last_process_time"] = current_time
                
                # Send to Deepgram for transcription
                transcript = await deepgram_service.transcribe_stream(
                    audio_data=wav_data,
                    content_type="audio/wav",
                    sample_rate=8000,
                    channels=1
                )
                
                if transcript and transcript.strip():
                    logger.info(f"📢 ✅ TRANSCRIPT: {transcript}")
                    await self._handle_transcript(session_id, transcript, db)
                
        except Exception as e:
            logger.error(f"❌ Error processing audio chunk: {e}")
    
    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM audio data to WAV format with volume normalization"""
        import struct
        import numpy as np
        
        try:
            # Convert PCM bytes to numpy array for processing
            if len(pcm_data) < 2:
                return b''
            
            samples = struct.unpack(f'<{len(pcm_data)//2}h', pcm_data)
            audio_array = np.array(samples, dtype=np.float32)
            
            # Check if audio has any content
            max_amplitude = np.max(np.abs(audio_array))
            if max_amplitude == 0:
                # Return original WAV for silent audio
                output = io.BytesIO()
                with wave.open(output, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(8000)  # 8kHz sample rate
                    wav_file.writeframes(pcm_data)
                return output.getvalue()
            
            # Normalize audio to use more of the dynamic range
            # Target peak at around 80% of max value for better speech recognition
            target_peak = 26214  # 80% of 32767 (max 16-bit value)
            
            # Calculate normalization factor
            normalization_factor = target_peak / max_amplitude
            
            # Apply more aggressive normalization for telephony audio
            normalization_factor = min(normalization_factor, 50.0)  # Max 50x amplification for very quiet audio
            
            normalized_audio = audio_array * normalization_factor
            
            # Clip to prevent overflow
            normalized_audio = np.clip(normalized_audio, -32767, 32767)
            
            # Convert back to 16-bit integers
            normalized_samples = normalized_audio.astype(np.int16)
            normalized_pcm = normalized_samples.tobytes()
            
            
            # Create WAV file with normalized audio
            output = io.BytesIO()
            with wave.open(output, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(8000)  # 8kHz sample rate
                wav_file.writeframes(normalized_pcm)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error normalizing audio: {e}")
            # Fall back to original method
            output = io.BytesIO()
            with wave.open(output, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(8000)  # 8kHz sample rate
                wav_file.writeframes(pcm_data)
            return output.getvalue()
    
    async def _flush_audio_buffer(self, session_id: str, db: AsyncSession):
        """Flush any remaining audio in the buffer when call ends"""
        try:
            if session_id not in self.call_sessions:
                return
                
            session = self.call_sessions[session_id]
            buffer_size = len(session["audio_buffer"])
            
            if buffer_size > 0:
                
                # Convert buffered PCM to WAV
                wav_data = self._pcm_to_wav(bytes(session["audio_buffer"]))
                
                # Clear the buffer
                session["audio_buffer"] = bytearray()
                
                # Send to Deepgram for final transcription
                transcript = await deepgram_service.transcribe_stream(
                    audio_data=wav_data,
                    content_type="audio/wav",
                    sample_rate=8000,
                    channels=1
                )
                
                if transcript:
                    logger.info(f"📢 Final transcript received: {transcript}")
                    await self._handle_transcript(session_id, transcript, db)
                
        except Exception as e:
            logger.error(f"❌ Error flushing audio buffer: {e}")
    
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
        logger.info(f"📝 Transcript buffer: '{session['transcript_buffer'].strip()}' (length: {len(session['transcript_buffer'].strip())})")
        
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
            
            # Cancel any pending response if caller is still speaking
            session = self.call_sessions[session_id]
            if session.get("pending_response_task") and not session["pending_response_task"].done():
                session["pending_response_task"].cancel()
                logger.info(f"📝 Cancelled previous response - caller still speaking")
            
            # Schedule delayed response - wait 5 seconds before agent responds
            session["last_transcript_time"] = time.time()
            session["pending_response_task"] = asyncio.create_task(
                self._delayed_agent_response(session_id, complete_text, db)
            )
    
    async def _delayed_agent_response(
        self,
        session_id: str,
        user_message: str,
        db: AsyncSession
    ):
        """Wait 5 seconds then process with agents, unless cancelled by new speech"""
        try:
            logger.info(f"📝 Waiting 5 seconds before agent response to: '{user_message}'")
            await asyncio.sleep(5.0)
            
            # Check if we're still the most recent transcript
            session = self.call_sessions[session_id]
            current_time = time.time()
            
            # If more than 5 seconds have passed since last transcript, proceed with response
            if (session.get("last_transcript_time") and 
                current_time - session["last_transcript_time"] >= 4.9):  # Small buffer for timing
                logger.info(f"📝 Proceeding with agent response after 5-second delay")
                await self._process_with_agents(session_id, user_message, db)
            else:
                logger.info(f"📝 Skipping response - newer transcript received")
                
        except asyncio.CancelledError:
            logger.info(f"📝 Agent response cancelled - caller continued speaking")
            raise
        except Exception as e:
            logger.error(f"❌ Error in delayed agent response: {e}")
            import traceback
            logger.error(f"❌ Delayed response traceback: {traceback.format_exc()}")
    
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
            
            # Create CallMessage record for call details page
            from app.models.models import CallMessage
            from datetime import datetime
            call_message = CallMessage(
                call_id=session["call"].id,
                content=user_message,
                sender={
                    "identifier": session["call"].customer_phone_number,
                    "type": "customer",
                    "name": "Caller",
                    "phone_number": session["call"].customer_phone_number
                },
                timestamp=datetime.utcnow(),
                message_type="transcript",
                message_metadata={
                    "sender_type": "caller",
                    "call_id": str(session["call"].id)
                }
            )
            
            db.add(message)
            db.add(call_message)
            await db.commit()
            
            # Create a user context for tenant-aware agent selection
            from app.models.models import Tenant
            tenant_query = select(Tenant).where(Tenant.id == config.tenant_id)
            tenant_result = await db.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            # Create a telephony user context for agent filtering
            class TelephonyUserContext:
                def __init__(self, tenant_id, tenant_domain=None):
                    self.tenant_id = tenant_id
                    self.email = f"telephony@{tenant_domain or 'system'}"
                    # Additional attributes that may be expected
                    self.role = "telephony_user"
                    self.username = "telephony_system"
                    
            telephony_user = TelephonyUserContext(
                config.tenant_id, 
                tenant.subdomain if tenant else None
            )
            
            # Force DEMO_ANSWERING_SERVICE selection by temporarily filtering discovered agents  
            original_agents = tenant_aware_agent_manager.discovered_agents.copy()
            try:
                # Temporarily keep only DEMO_ANSWERING_SERVICE and MODERATOR
                if "DEMO_ANSWERING_SERVICE" in original_agents:
                    tenant_aware_agent_manager.discovered_agents = {
                        "DEMO_ANSWERING_SERVICE": original_agents["DEMO_ANSWERING_SERVICE"],
                        "MODERATOR": original_agents.get("MODERATOR", original_agents["DEMO_ANSWERING_SERVICE"])
                    }
                    logger.info(f"📞 Filtering agents to use DEMO_ANSWERING_SERVICE for telephony")
                
                # Process with filtered agents - MODERATOR should now select DEMO_ANSWERING_SERVICE
                agent_type, agent_response = await tenant_aware_agent_manager.process_conversation(
                    message=user_message,
                    conversation_agents=[],  # Ignored
                    agents_config={},       # Ignored  
                    db=db,
                    thread_id=str(conversation.id),
                    owner_id=str(config.tenant_id)  # Ensure UUID is converted to string
                )
                
                # Store the agent type in session for saving with response
                session["last_agent_type"] = agent_type
                
            finally:
                # Restore original discovered agents
                tenant_aware_agent_manager.discovered_agents = original_agents
            
            # Ensure response is brief for telephony (safety measure)
            truncated_response = self._truncate_for_telephony(agent_response)
            
            # Convert response to speech
            logger.info(f"🎤 About to send speech response: {truncated_response[:50]}...")
            await self._send_speech_response(session_id, truncated_response, db)
            logger.info(f"✅ Speech response sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Error processing with agents: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            # Send error response
            try:
                await self._send_speech_response(
                    session_id,
                    "I'm sorry, I'm having trouble processing your request. Could you please try again?",
                    db
                )
            except Exception as e2:
                logger.error(f"❌ Error sending fallback response: {e2}")
        finally:
            session["agent_processing"] = False
    
    async def _send_speech_response(
        self,
        session_id: str,
        text_response: str,
        db: AsyncSession
    ):
        """Convert text response to speech and send to caller"""
        
        logger.info(f"🎙️ _send_speech_response called for session {session_id}")
        logger.info(f"🎙️ Text to convert: '{text_response[:100]}...'")
        
        session = self.call_sessions[session_id]
        
        # Prevent duplicate responses by checking if TTS is already active
        if session.get("tts_active", False):
            logger.warning(f"TTS already active for session {session_id}, skipping duplicate response")
            return
            
        session["tts_active"] = True
        logger.info(f"🎙️ TTS marked as active, proceeding with speech generation")
        
        try:
            # Clean up text response to prevent TTS issues
            clean_text = self._clean_text_for_tts(text_response)
            logger.info(f"🎙️ Cleaned text for TTS: '{clean_text}'")
            
            # Generate speech (returns MP3 data)
            logger.info(f"🎙️ Calling ElevenLabs TTS service...")
            audio_data = await elevenlabs_service.generate_speech(
                text=clean_text,
                voice_id=session["voice_id"]
            )
            
            if audio_data:
                logger.info(f"🎙️ ✅ TTS generated {len(audio_data)} bytes of MP3 audio")
                # Record TTS usage
                word_count = count_words(clean_text)
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
                logger.info(f"🎙️ About to send audio to caller via Twilio stream...")
                await self._send_audio_to_caller(session_id, audio_data)
                logger.info(f"🎙️ ✅ Audio sending completed")
                
                # Save response message
                conversation = session["conversation"]
                response_message = Message(
                    conversation_id=conversation.id,
                    content=text_response,
                    message_type="text",
                    agent_type=session.get("last_agent_type", "ASSISTANT"),  # Use actual agent type
                    additional_data=json.dumps({
                        "sender_type": "agent",
                        "call_id": str(session["call"].id),
                        "has_audio": True
                    })
                )
                
                # Create CallMessage record for call details page
                from app.models.models import CallMessage
                from datetime import datetime
                call_response_message = CallMessage(
                    call_id=session["call"].id,
                    content=text_response,
                    sender={
                        "identifier": "ai_agent",
                        "type": "agent",
                        "name": "AI Agent",
                        "phone_number": None
                    },
                    timestamp=datetime.utcnow(),
                    message_type="transcript",
                    message_metadata={
                        "sender_type": "agent",
                        "call_id": str(session["call"].id),
                        "has_audio": True,
                        "agent_type": session.get("last_agent_type", "ASSISTANT")
                    }
                )
                
                db.add(response_message)
                db.add(call_response_message)
                await db.commit()
                
                logger.info(f"🗣️ Speech response sent to caller: {text_response[:50]}...")
            else:
                logger.error(f"❌ No audio data generated for text: {clean_text[:50]}...")
                logger.error(f"❌ TTS service failed to generate audio")
            
        except Exception as e:
            logger.error(f"❌ Error generating speech response: {e}")
            import traceback
            logger.error(f"❌ TTS pipeline traceback: {traceback.format_exc()}")
        finally:
            # Always reset TTS flag to prevent getting stuck
            session["tts_active"] = False
            logger.info(f"🎙️ TTS flag reset for session {session_id}")
    
    def _truncate_for_telephony(self, text: str) -> str:
        """Truncate response to keep it brief for telephony conversations."""
        if not text:
            return ""
        
        # Split into sentences
        import re
        sentences = re.split(r'[.!?]+', text.strip())
        
        # For telephony, be VERY aggressive - only ONE sentence at a time
        if len(sentences) > 1:
            # Take only the first complete sentence
            first_sentence = sentences[0].strip()
            if first_sentence:
                if not first_sentence.endswith(('.', '!', '?')):
                    first_sentence += '.'
                logger.info(f"📞 Truncated to first sentence: {first_sentence}")
                return first_sentence
        
        # If only one sentence, still limit total length aggressively
        if len(text) > 100:  # ~15-20 words max for telephony
            words = text.split()
            if len(words) > 20:
                truncated = ' '.join(words[:20])
                if not truncated.endswith(('.', '!', '?')):
                    truncated += '.'
                logger.info(f"📞 Truncated to 20 words: {truncated}")
                return truncated
        
        return text
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text to prevent TTS issues and improve stability."""
        if not text:
            return ""
        
        import re
        
        # Remove or replace problematic characters
        text = text.strip()
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters but keep newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Handle common formatting issues
        text = text.replace('&', ' and ')
        text = text.replace('<', ' less than ')
        text = text.replace('>', ' greater than ')
        
        # Ensure proper sentence endings for natural speech flow
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text
    
    async def _send_audio_to_caller(
        self,
        session_id: str,
        audio_data: bytes
    ):
        """Send audio data to caller via Twilio stream with improved error handling"""
        
        if not audio_data or len(audio_data) == 0:
            logger.warning("❌ No audio data to send")
            return
            
        try:
            logger.info(f"🔊 Processing audio: {len(audio_data)} bytes MP3")
            
            # Convert MP3 to mulaw using ffmpeg (more reliable than librosa)
            audio_to_send = await self._convert_mp3_to_mulaw(audio_data)
            
            if not audio_to_send:
                logger.error("❌ Audio conversion failed, cannot send to caller")
                return
                
            # Split large audio into smaller chunks to prevent Twilio timeout/cutoff
            chunk_size = 4000  # ~250ms at 8kHz (smaller chunks for smoother streaming)
            audio_chunks = [audio_to_send[i:i+chunk_size] for i in range(0, len(audio_to_send), chunk_size)]
            
            logger.info(f"🔊 Sending audio in {len(audio_chunks)} chunks")
            
            # Get the stored streamSid for this session
            session = self.call_sessions.get(session_id, {})
            stream_sid = session.get("stream_sid")
            
            if not stream_sid:
                logger.error(f"❌ No streamSid found for session {session_id}! Available session keys: {list(session.keys())}")
                logger.error(f"❌ Cannot send audio without proper streamSid")
                return
            
            logger.error(f"📡 DEBUG: Sending audio with streamSid: {stream_sid}")
            logger.error(f"📡 DEBUG: Session info: {list(session.keys())}")
            logger.error(f"📡 DEBUG: Audio chunks: {len(audio_chunks)}")
            logger.info(f"📡 Session info: {[k for k in session.keys()]}")
            
            # Send each chunk with a small delay to prevent overwhelming Twilio
            for i, chunk in enumerate(audio_chunks):
                if chunk:  # Only send non-empty chunks
                    audio_base64 = base64.b64encode(chunk).decode('utf-8')
                    
                    logger.error(f"📡 DEBUG: Sending WebSocket message to session {session_id}")
                    await self._send_message(session_id, {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": audio_base64
                        }
                    })
                    
                    # Small delay between chunks to prevent audio cutoffs
                    if i < len(audio_chunks) - 1:  # No delay after last chunk
                        await asyncio.sleep(0.02)  # 20ms delay
            
            logger.info(f"📤 Successfully sent {len(audio_to_send)} bytes mulaw audio in {len(audio_chunks)} chunks")
            
        except Exception as e:
            logger.error(f"❌ Error sending audio to caller: {e}")
    
    async def _convert_mp3_to_mulaw(self, mp3_data: bytes) -> Optional[bytes]:
        """Convert MP3 audio data to mulaw format for Twilio."""
        import tempfile
        import subprocess
        import audioop
        import os
        
        try:
            # Save MP3 to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3:
                temp_mp3.write(mp3_data)
                temp_mp3.flush()
                
                try:
                    # Use ffmpeg for reliable audio conversion
                    result = subprocess.run([
                        'ffmpeg', '-i', temp_mp3.name,
                        '-f', 's16le',  # 16-bit signed little-endian PCM
                        '-acodec', 'pcm_s16le',
                        '-ar', '8000',  # 8kHz sample rate (Twilio requirement)
                        '-ac', '1',     # mono
                        '-loglevel', 'error',  # Suppress verbose output
                        '-'
                    ], capture_output=True, check=True)
                    
                    pcm_data = result.stdout
                    
                    if not pcm_data:
                        logger.error("❌ No PCM data produced by ffmpeg")
                        return None
                    
                    # Convert PCM to mulaw
                    mulaw_data = audioop.lin2ulaw(pcm_data, 2)
                    logger.info(f"✅ Converted MP3 to mulaw: {len(mp3_data)} → {len(pcm_data)} → {len(mulaw_data)} bytes")
                    
                    return mulaw_data
                    
                except subprocess.CalledProcessError as e:
                    logger.error(f"❌ ffmpeg conversion failed: {e.stderr.decode() if e.stderr else 'Unknown error'}")
                    return None
                except Exception as e:
                    logger.error(f"❌ Audio conversion error: {e}")
                    return None
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_mp3.name)
                    except OSError:
                        pass
                        
        except Exception as e:
            logger.error(f"❌ Error in audio conversion: {e}")
            return None
    
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
        """Simple heuristic to detect complete utterances - made more responsive for phone calls"""
        
        cleaned_text = text.strip()
        if not cleaned_text:
            return False
        
        logger.debug(f"📝 Checking if complete utterance: '{cleaned_text}' (length: {len(cleaned_text)})")
        
        # Check for sentence endings
        if cleaned_text.endswith(('.', '!', '?')):
            logger.debug(f"📝 Complete utterance detected: ends with punctuation")
            return True
        
        # Very short threshold for phone conversations (20 chars = ~3-4 words)
        if len(cleaned_text) > 20:
            logger.debug(f"📝 Complete utterance detected: length > 20 chars")
            return True
        
        # Common conversation endings
        if cleaned_text.lower().endswith(('please', 'thanks', 'yes', 'no', 'okay', 'help', 'hello', 'hi')):
            logger.debug(f"📝 Complete utterance detected: ends with conversation word")
            return True
        
        # Check for question words at the beginning with shorter threshold
        question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'can', 'could', 'would', 'will', 'is', 'are', 'do', 'does']
        first_word = cleaned_text.lower().split()[0] if cleaned_text else ""
        if first_word in question_words and len(text.strip()) > 10:
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
    
    async def _send_initial_greeting(
        self,
        session_id: str,
        db: AsyncSession
    ):
        """Send initial greeting from AI agent when call connects"""
        
        logger.info(f"🎙️ Starting initial greeting for session {session_id}")
        
        session = self.call_sessions[session_id]
        config = session["config"]
        
        logger.info(f"🎙️ Session config - tenant_id: {config.tenant_id}")
        
        try:
            # Create a user context for tenant-aware agent selection
            from app.models.models import Tenant
            tenant_query = select(Tenant).where(Tenant.id == config.tenant_id)
            tenant_result = await db.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            # Create a telephony user context for agent filtering
            class TelephonyUserContext:
                def __init__(self, tenant_id, tenant_domain=None):
                    self.tenant_id = tenant_id
                    self.email = f"telephony@{tenant_domain or 'system'}"
                    # Additional attributes that may be expected
                    self.role = "telephony_user"
                    self.username = "telephony_system"
                    
            telephony_user = TelephonyUserContext(
                config.tenant_id, 
                tenant.subdomain if tenant else None
            )
            
            # Send a simple, brief greeting - don't invoke AI agent yet
            conversation = session["conversation"]
            
            # Use the actual AI agent for the initial greeting to be consistent
            logger.info(f"📞 Using AI agent for initial greeting")
            
            # Process "CALL_START" trigger with the actual agent (no delay for initial greeting)
            await self._process_with_agents(session_id, "CALL_START", db)
            
        except Exception as e:
            logger.error(f"❌ Error sending initial greeting: {e}")
            # Log error but don't send fallback - let the agent handle it
    
    async def _send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"❌ Error sending message to {session_id}: {e}")
    
    async def _generate_call_summary(self, call_id: UUID, db: AsyncSession):
        """Generate summary for a completed call"""
        
        try:
            from app.models.models import CallMessage
            from datetime import datetime
            
            # Check if summary already exists
            existing_summary_query = select(CallMessage).where(
                CallMessage.call_id == call_id,
                CallMessage.message_type == 'summary'
            )
            existing_result = await db.execute(existing_summary_query)
            if existing_result.scalar_one_or_none():
                logger.info(f"📝 Summary already exists for call {call_id}")
                return
            
            # Get transcript messages
            transcript_query = (
                select(CallMessage)
                .where(
                    CallMessage.call_id == call_id,
                    CallMessage.message_type == 'transcript'
                )
                .order_by(CallMessage.timestamp)
            )
            
            result = await db.execute(transcript_query)
            transcript_messages = result.scalars().all()
            
            if not transcript_messages:
                logger.info(f"📝 No transcript messages found for call {call_id}")
                return
            
            # Get call details
            call_query = select(PhoneCall).where(PhoneCall.id == call_id)
            call_result = await db.execute(call_query)
            call = call_result.scalar_one_or_none()
            
            if not call:
                logger.error(f"❌ Call {call_id} not found")
                return
            
            # Generate basic summary
            duration_info = ""
            if call.duration_seconds:
                minutes = call.duration_seconds // 60
                seconds = call.duration_seconds % 60
                duration_info = f" The call lasted {minutes} minutes and {seconds} seconds."
            
            message_count = len(transcript_messages)
            customer_messages = [m for m in transcript_messages if m.sender.get('type') == 'customer']
            agent_messages = [m for m in transcript_messages if m.sender.get('type') == 'agent']
            
            summary_content = (
                f"Call between customer {call.customer_phone_number} and organization "
                f"on {call.created_at.strftime('%B %d, %Y at %I:%M %p')}.{duration_info} "
                f"The conversation included {message_count} messages "
                f"({len(customer_messages)} from customer, {len(agent_messages)} from agent). "
                f"The customer initiated contact and the conversation was handled by the AI agent."
            )
            
            # Create summary message
            summary_message = CallMessage(
                call_id=call_id,
                content=summary_content,
                sender={
                    "identifier": "system",
                    "name": "AI Summarizer",
                    "type": "system"
                },
                timestamp=datetime.utcnow(),
                message_type='summary',
                message_metadata={
                    "is_automated": True,
                    "generation_method": "auto_generated",
                    "message_count": message_count,
                    "customer_message_count": len(customer_messages),
                    "agent_message_count": len(agent_messages)
                }
            )
            
            db.add(summary_message)
            
            # Also update the phone_call summary field
            call.summary = summary_content
            
            await db.commit()
            logger.info(f"📝 ✅ Auto-generated summary for call {call_id}")
            
        except Exception as e:
            logger.error(f"❌ Error generating summary for call {call_id}: {e}")
            # Don't re-raise - summary generation is optional

# Create global handler instance
telephony_stream_handler = TelephonyStreamHandler()

# Create FastAPI router
from fastapi import APIRouter

router = APIRouter(
    prefix="/ws/telephony",
    tags=["telephony-websocket"],
    responses={404: {"description": "Not found"}},
)

@router.websocket("/stream/{call_id}")
async def telephony_websocket_endpoint(
    websocket: WebSocket,
    call_id: UUID,
    token: str = None,
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
    
    Authentication via token query parameter is optional for now to support
    both Twilio (no auth) and frontend (with auth) connections.
    """
    logger.info(f"🔌 Telephony WebSocket connection attempt for call_id: {call_id}, token: {'present' if token else 'none'}")
    
    # For now, accept connections with or without tokens
    # In production, you might want to validate the token and ensure
    # the user has access to this specific call
    if token:
        try:
            # Optional: validate token and get user
            from app.auth.auth import verify_token
            user = await verify_token(token)
            logger.info(f"🔐 Authenticated WebSocket connection for user: {user.email}")
        except Exception as e:
            logger.warning(f"⚠️ Token validation failed for WebSocket, but allowing connection: {e}")
            # Allow connection anyway for testing
    
    await telephony_stream_handler.handle_connection(websocket, call_id, db)

