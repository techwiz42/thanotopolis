# backend/app/api/telephony_websocket.py
"""
WebSocket handler for telephony streaming - handles real-time voice communication
"""

import asyncio
import json
import logging
import base64
import audioop
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
                "silence_threshold": 0.5,  # 500ms of silence before processing buffer
                "min_buffer_size": 8000,   # ~500ms at 8000 Hz, 16-bit = 8000 bytes per 500ms
                "max_buffer_size": 32000   # ~2 seconds max buffer
            }
            
            logger.info(f"📞 Telephony WebSocket connected for call {call.call_sid}")
            
            # Send initial status
            await self._send_message(session_id, {
                "type": "connected",
                "call_id": str(call_id),
                "call_sid": call.call_sid,
                "conversation_id": str(conversation.id)
            })
            
            # Send initial greeting from AI agent
            logger.info(f"🎙️ About to send initial greeting for session {session_id}")
            await self._send_initial_greeting(session_id, db)
            logger.info(f"🎙️ Initial greeting method completed for session {session_id}")
            
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
            # Stream started - capture streamSid for later use
            stream_sid = message.get("start", {}).get("streamSid")
            if stream_sid:
                session["stream_sid"] = stream_sid
                logger.info(f"📻 Captured streamSid: {stream_sid}")
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
            
            # Convert mulaw to WAV and send to speech-to-text
            try:
                logger.debug(f"📢 Processing combined audio: {len(combined_audio)} bytes mulaw")
                wav_data = convert_mulaw_to_wav(combined_audio)
                logger.debug(f"📢 Converted combined audio to WAV: {len(wav_data)} bytes")
                
                transcript = await deepgram_service.transcribe_stream(
                    audio_data=wav_data,
                    content_type="audio/wav",
                    sample_rate=8000,
                    channels=1
                )
                if transcript:
                    logger.info(f"📢 Binary transcript received: {transcript}")
                    await self._handle_transcript(session_id, transcript, db)
                else:
                    logger.warning(f"📢 No binary transcript received from Deepgram (audio: {len(combined_audio)} bytes mulaw → {len(wav_data)} bytes WAV)")
            except Exception as e:
                logger.error(f"❌ STT error for session {session_id}: {e}")
    
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
            logger.debug(f"📢 Processing audio chunk: {len(mulaw_data)} bytes mulaw")
            
            # Convert mulaw to linear PCM
            pcm_data = audioop.ulaw2lin(mulaw_data, 2)  # Convert to 16-bit PCM
            
            # Add to buffer
            session["audio_buffer"].extend(pcm_data)
            session["last_audio_time"] = time.time()
            
            # Check if we should process the buffer
            current_time = time.time()
            buffer_size = len(session["audio_buffer"])
            
            should_process = (
                # Buffer is at minimum size 
                buffer_size >= session["min_buffer_size"] or
                # Buffer is at maximum size (prevent memory issues)
                buffer_size >= session["max_buffer_size"]
            )
            
            if should_process and buffer_size > 0:
                logger.debug(f"📢 Processing buffered audio: {buffer_size} bytes PCM")
                
                # Convert buffered PCM to WAV
                wav_data = self._pcm_to_wav(bytes(session["audio_buffer"]))
                
                # Clear the buffer
                session["audio_buffer"] = bytearray()
                
                # Send to Deepgram for transcription
                transcript = await deepgram_service.transcribe_stream(
                    audio_data=wav_data,
                    content_type="audio/wav",
                    sample_rate=8000,
                    channels=1
                )
                
                if transcript:
                    logger.info(f"📢 Transcript received: {transcript}")
                    await self._handle_transcript(session_id, transcript, db)
                else:
                    logger.warning(f"📢 No transcript received from Deepgram (audio: {len(wav_data)} bytes WAV)")
                
        except Exception as e:
            logger.error(f"❌ Error processing audio chunk: {e}")
    
    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM audio data to WAV format"""
        output = io.BytesIO()
        
        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(8000)  # 8kHz sample rate (Twilio standard)
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
                logger.debug(f"📢 Flushing remaining audio buffer: {buffer_size} bytes PCM")
                
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
            
            # Get agent response using tenant-aware processing
            agent_type, agent_response = await tenant_aware_agent_manager.process_conversation_with_tenant_context(
                message=user_message,
                user=telephony_user,  # Pass user context for tenant-aware filtering
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
        
        # Prevent duplicate responses by checking if TTS is already active
        if session.get("tts_active", False):
            logger.warning(f"TTS already active for session {session_id}, skipping duplicate response")
            return
            
        session["tts_active"] = True
        
        try:
            # Clean up text response to prevent TTS issues
            clean_text = self._clean_text_for_tts(text_response)
            
            # Generate speech (returns MP3 data)
            audio_data = await elevenlabs_service.generate_speech(
                text=clean_text,
                voice_id=session["voice_id"]
            )
            
            if audio_data:
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
            else:
                logger.error(f"❌ No audio data generated for text: {clean_text[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Error generating speech response: {e}")
        finally:
            # Always reset TTS flag to prevent getting stuck
            session["tts_active"] = False
    
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
            stream_sid = session.get("stream_sid", session_id)  # Fallback to session_id
            
            # Send each chunk with a small delay to prevent overwhelming Twilio
            for i, chunk in enumerate(audio_chunks):
                if chunk:  # Only send non-empty chunks
                    audio_base64 = base64.b64encode(chunk).decode('utf-8')
                    
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
            
            # Get initial greeting from the agent
            conversation = session["conversation"]
            initial_message = "CALL_START"  # Special trigger for initial greeting
            
            logger.info(f"🎙️ Processing CALL_START message with tenant-aware agent manager")
            logger.info(f"🎙️ Telephony user: {telephony_user.email}, tenant: {telephony_user.tenant_id}")
            
            agent_type, agent_response = await tenant_aware_agent_manager.process_conversation_with_tenant_context(
                message=initial_message,
                user=telephony_user,
                db=db,
                thread_id=str(conversation.id),
                owner_id=config.tenant_id
            )
            
            logger.info(f"📞 Initial greeting from {agent_type}: {agent_response}")
            
            # Convert response to speech and send to caller
            logger.info(f"🎙️ Converting greeting to speech and sending to caller")
            await self._send_speech_response(session_id, agent_response, db)
            
        except Exception as e:
            logger.error(f"❌ Error sending initial greeting: {e}")
            # Send fallback greeting if agent fails
            fallback_greeting = config.welcome_message or "Hello! Thank you for calling. How can I help you today?"
            await self._send_speech_response(session_id, fallback_greeting, db)
    
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
    prefix="/ws/telephony",
    tags=["telephony-websocket"],
    responses={404: {"description": "Not found"}},
)

@router.websocket("/stream/{call_id}")
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
    logger.info(f"🔌 Telephony WebSocket connection attempt for call_id: {call_id}")
    await telephony_stream_handler.handle_connection(websocket, call_id, db)

