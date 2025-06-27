"""
Telephony WebSocket endpoint using Deepgram Voice Agent API
Bridges Twilio MediaStream with Deepgram's conversational AI
"""

import asyncio
import json
import base64
from typing import Dict, Optional, Any
from datetime import datetime
import logging

from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PhoneCall, CallDirection, CallMessage, Conversation, Message
from app.db.database import get_db
from app.services.voice.deepgram_voice_agent import get_voice_agent_service, VoiceAgentSession
from app.services.usage_service import usage_service
from app.models.models import TelephonyConfiguration
from sqlalchemy.future import select
# from app.api.telephony_status import TelephonyStatusManager  # TODO: Implement or remove

logger = logging.getLogger(__name__)

def count_words(text: str) -> int:
    """Count words in text for usage tracking"""
    if not text or not text.strip():
        return 0
    return len(text.split())


class TelephonyVoiceAgentHandler:
    """Handles telephony connections using Deepgram Voice Agent"""
    
    def __init__(self):
        self.voice_agent_service = get_voice_agent_service()
        self.call_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def handle_connection(self, websocket: WebSocket, db: AsyncSession):
        """Handle incoming Twilio WebSocket connection"""
        session_id = None
        voice_session: Optional[VoiceAgentSession] = None
        flush_task = None
        
        try:
            await websocket.accept()
            logger.info("🔌 Accepted new telephony Voice Agent connection")
            
            # Process Twilio messages
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                event_type = data.get("event")
                
                if event_type == "start":
                    # Initialize session
                    session_id = await self._handle_start(data, db)
                    
                    # Create Voice Agent session
                    session_info = self.call_sessions[session_id]
                    try:
                        voice_session = await self._create_voice_agent_session(
                            session_id, 
                            session_info
                        )
                        logger.info(f"✅ Voice Agent session created successfully")
                    except Exception as e:
                        logger.error(f"❌ Voice Agent session creation failed: {e}")
                        logger.error("📞 Voice Agent not available - calls will still work but without advanced features")
                        # Continue without Voice Agent - basic call handling still works
                        voice_session = None
                    
                    # Register handlers only if Voice Agent session was created
                    if voice_session:
                        self._setup_event_handlers(
                            voice_session, 
                            session_id, 
                            websocket,
                            db
                        )
                        
                        # Start periodic flush task to reduce latency
                        flush_task = asyncio.create_task(
                            self._periodic_flush_task(session_id, db)
                        )
                    else:
                        logger.info("📞 Continuing without Voice Agent - call will timeout gracefully")
                    
                elif event_type == "media":
                    # Forward audio to Voice Agent
                    if voice_session:
                        await self._handle_media(data, voice_session)
                        
                elif event_type == "stop":
                    logger.info("📞 Call ended by Twilio")
                    break
                    
        except WebSocketDisconnect:
            logger.info("📞 Twilio WebSocket disconnected")
        except Exception as e:
            logger.error(f"❌ Error in Voice Agent handler: {e}")
        finally:
            # Cancel periodic flush task
            if flush_task:
                flush_task.cancel()
                try:
                    await flush_task
                except asyncio.CancelledError:
                    pass
                    
            # Cleanup
            if session_id:
                await self._cleanup_session(session_id, db)
            if voice_session:
                await self.voice_agent_service.end_session(session_id)
    
    async def _handle_start(self, data: Dict[str, Any], db: AsyncSession) -> str:
        """Handle Twilio start event"""
        stream_data = data.get("start", {})
        stream_sid = stream_data.get("streamSid", "")
        custom_params = stream_data.get("customParameters", {})
        
        # Extract call info
        call_sid = custom_params.get("call_sid", "")
        from_number = custom_params.get("from", "Unknown")
        to_number = custom_params.get("to", "Unknown")
        org_phone = custom_params.get("org_phone", to_number)  # Use org_phone if available, fallback to to_number
        tenant_id = custom_params.get("tenant_id")
        
        logger.info(f"📞 New call: {from_number} → {to_number} (org: {org_phone})")
        
        # Get telephony configuration by organization phone number
        config_query = select(TelephonyConfiguration).where(
            TelephonyConfiguration.organization_phone_number == org_phone
        )
        config_result = await db.execute(config_query)
        config = config_result.scalar_one_or_none()
        
        if not config:
            logger.error(f"❌ No telephony config found for {to_number}")
            raise Exception("No telephony configuration found")
        
        # Get existing phone call record (created by webhook handler)
        phone_call_query = select(PhoneCall).where(PhoneCall.call_sid == call_sid)
        phone_call_result = await db.execute(phone_call_query)
        phone_call = phone_call_result.scalar_one_or_none()
        
        if not phone_call:
            # Fallback: create phone call record if it doesn't exist
            phone_call = PhoneCall(
                telephony_config_id=config.id,
                call_sid=call_sid,
                customer_phone_number=from_number,
                organization_phone_number=org_phone,
                platform_phone_number=to_number,
                direction=CallDirection.INBOUND.value,
                status="in-progress",
                start_time=datetime.utcnow()
            )
            db.add(phone_call)
            await db.commit()
            await db.refresh(phone_call)
        else:
            logger.info(f"📞 Using existing phone call record: {phone_call.id}")
        
        # Create conversation
        conversation = await self._create_call_conversation(db, phone_call, config)
        
        # Store session info
        session_id = stream_sid
        self.call_sessions[session_id] = {
            "stream_sid": stream_sid,
            "call_sid": call_sid,
            "phone_call": phone_call,
            "conversation": conversation,
            "config": config,
            "from_number": from_number,
            "to_number": to_number,
            "start_time": datetime.utcnow(),
            "pending_messages": []  # Initialize pending messages list
        }
        
        # TODO: Update telephony status
        # status_manager = TelephonyStatusManager()
        # await status_manager.add_active_call(
        #     tenant_id=str(config.tenant_id),
        #     call_sid=call_sid,
        #     from_number=from_number,
        #     start_time=datetime.utcnow()
        # )
        
        logger.info(f"✅ Session initialized: {session_id}")
        return session_id
    
    async def _create_voice_agent_session(
        self, 
        session_id: str, 
        session_info: Dict[str, Any]
    ) -> VoiceAgentSession:
        """Create and configure Voice Agent session"""
        config = session_info["config"]
        
        # Build system prompt
        system_prompt = self._build_system_prompt(config, session_info)
        
        # Create Voice Agent session
        voice_session = await self.voice_agent_service.create_session(
            session_id=session_id,
            system_prompt=system_prompt,
            voice_model=config.voice_id or "aura-2-thalia-en"
        )
        
        return voice_session
    
    def _build_system_prompt(
        self, 
        config: Any, 
        session_info: Dict[str, Any]
    ) -> str:
        """Build system prompt for Voice Agent"""
        from_number = session_info["from_number"]
        
        prompt = f"""You are an AI assistant answering a phone call for the organization.

Caller's phone number: {from_number}

IMPORTANT: You must start the conversation immediately with a friendly greeting. Do not wait for the caller to speak first. Begin by greeting them and asking how you can help.

Your role:
- Start every call with a warm, professional greeting
- Be helpful, professional, and conversational
- Keep responses concise and natural for phone conversations
- If asked about specific services or information, provide what you know
- If you don't know something, offer to help find the information or suggest alternatives

Important:
- This is a phone conversation, so avoid long responses
- Speak naturally, as if having a real phone conversation
- Don't mention that you're an AI unless directly asked
- Always greet the caller first when the call begins
"""
        
        # Add any custom instructions from config
        if hasattr(config, 'custom_prompt') and config.custom_prompt:
            prompt += f"\n\nAdditional instructions:\n{config.custom_prompt}"
            
        return prompt
    
    def _setup_event_handlers(
        self,
        voice_session: VoiceAgentSession,
        session_id: str,
        websocket: WebSocket,
        db: AsyncSession
    ):
        """Setup event handlers for Voice Agent events"""
        
        # Handler for audio from agent
        async def handle_agent_audio(audio_data: bytes):
            """Send agent's speech to Twilio"""
            # Audio is already in mulaw format from Voice Agent
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            media_message = {
                "event": "media",
                "streamSid": session_id,
                "media": {
                    "payload": audio_base64
                }
            }
            
            await websocket.send_text(json.dumps(media_message))
        
        voice_session.register_audio_handler(handle_agent_audio)
        
        # Handler for conversation text
        async def handle_conversation_text(event: Dict[str, Any]):
            """Save conversation messages as CallMessage objects"""
            logger.info(f"🔍 handle_conversation_text called with event: {event}")
            
            # Try both 'content' and 'text' fields (different events may use different field names)
            text = event.get("content", "") or event.get("text", "")
            role = event.get("role", "")
            
            logger.info(f"🔍 Extracted - text: '{text}', role: '{role}'")
            
            if not text:
                logger.warning(f"🔍 Empty text in conversation event, skipping save")
                return
                
            session_info = self.call_sessions.get(session_id)
            if not session_info:
                return
                
            conversation = session_info["conversation"]
            phone_call = session_info["phone_call"]
            
            # Create CallMessage for the call details page
            # Map Deepgram Voice Agent roles to our system
            # Possible user role values: "user", "human", "customer", "caller"
            # Possible agent role values: "assistant", "agent", "bot", "ai"
            is_user = role.lower() in ["user", "human", "customer", "caller"]
            is_agent = role.lower() in ["assistant", "agent", "bot", "ai"]
            
            logger.info(f"🔍 Role mapping - original: '{role}' → is_user: {is_user}, is_agent: {is_agent}")
            
            # If role is unclear, try to infer from event type or content
            if not is_user and not is_agent:
                logger.warning(f"🚨 UNKNOWN ROLE: '{role}' - treating as agent for safety")
                is_user = False
            
            call_message = CallMessage(
                call_id=phone_call.id,
                content=text,
                sender={
                    "identifier": session_info["from_number"] if is_user else "voice_agent",
                    "type": "customer" if is_user else "agent",
                    "name": "Caller" if is_user else "AI Agent",
                    "phone_number": session_info["from_number"] if is_user else None
                },
                timestamp=datetime.utcnow(),
                message_type="transcript",
                message_metadata={
                    "role": role,
                    "session_id": session_id,
                    "call_sid": session_info["call_sid"]
                }
            )
            
            # Also create Message for conversation continuity  
            message = Message(
                conversation_id=conversation.id,
                message_type="text",
                agent_type="voice_agent" if not is_user else None,
                content=text,
                message_metadata={
                    "role": role,
                    "call_sid": session_info["call_sid"],
                    "session_id": session_id
                }
            )
            
            # Add to pending messages batch (don't commit immediately to reduce latency)
            session_info["pending_messages"].extend([call_message, message])
            
            # Track usage for STT and TTS
            config = session_info["config"]
            word_count = count_words(text)
            
            if word_count > 0:
                if is_user:
                    # User speech = STT usage (Deepgram transcribed user's speech)
                    try:
                        await usage_service.record_stt_usage(
                            db=db,
                            tenant_id=config.tenant_id,
                            user_id=None,  # No specific user for phone calls
                            word_count=word_count,
                            service_provider="deepgram",
                            model_name="nova-3"  # Voice Agent uses nova-3 by default
                        )
                        logger.info(f"📊 STT usage recorded: {word_count} words for user speech")
                    except Exception as e:
                        logger.error(f"❌ Error recording STT usage: {e}")
                
                elif is_agent:
                    # Agent speech = TTS usage (Deepgram generated agent's speech)
                    try:
                        await usage_service.record_tts_usage(
                            db=db,
                            tenant_id=config.tenant_id,
                            user_id=None,  # No specific user for phone calls
                            word_count=word_count,
                            service_provider="deepgram",
                            model_name="aura-2-thalia-en"  # Default Voice Agent TTS model
                        )
                        logger.info(f"📊 TTS usage recorded: {word_count} words for agent speech")
                    except Exception as e:
                        logger.error(f"❌ Error recording TTS usage: {e}")
            
            # Batch commit every 5 messages or every 10 seconds to reduce latency
            if len(session_info["pending_messages"]) >= 10:
                await self._flush_pending_messages(session_id, db)
            
            logger.info(f"💾 Queued {role} message: {text[:50]}...")
        
        # Register handler for multiple possible transcript event types
        voice_session.register_event_handler("ConversationText", handle_conversation_text)
        voice_session.register_event_handler("Transcript", handle_conversation_text)
        voice_session.register_event_handler("TranscriptText", handle_conversation_text)
        voice_session.register_event_handler("UserText", handle_conversation_text)
        voice_session.register_event_handler("AgentText", handle_conversation_text)
        
        # Additional possible event types for user speech
        voice_session.register_event_handler("UserTranscript", handle_conversation_text)
        voice_session.register_event_handler("SpeechTranscript", handle_conversation_text)
        voice_session.register_event_handler("RecognitionResult", handle_conversation_text)
        
        # Handler for user speaking events
        async def handle_user_speaking(event: Dict[str, Any]):
            """Track when user is speaking"""
            logger.info("🗣️ User speaking detected")
            # Could add visual indicators or other logic here
        
        voice_session.register_event_handler("UserStartedSpeaking", handle_user_speaking)
        
        # Catch-all handler for debugging unknown events that might contain user speech
        async def handle_unknown_event(event_type: str, event: Dict[str, Any]):
            """Log all unhandled events to catch user speech in unexpected formats"""
            # Check if this event contains text that might be user speech
            text_content = event.get("content", "") or event.get("text", "") or event.get("transcript", "")
            role = event.get("role", "")
            
            if text_content and text_content.strip():
                logger.info(f"🔍 UNHANDLED EVENT with text: {event_type}")
                logger.info(f"🔍 Text: '{text_content}'")
                logger.info(f"🔍 Role: '{role}'")
                logger.info(f"🔍 Full event: {event}")
                
                # If this looks like user speech, try to save it
                if role.lower() in ["user", "human", "customer", "caller"] or event_type.lower().find("user") != -1:
                    logger.warning(f"🚨 POTENTIAL USER MESSAGE in unhandled event: {event_type}")
                    # Route to conversation handler
                    await handle_conversation_text(event)
        
        # Note: No fallback handler method available, but the Voice Agent service
        # logs all unhandled events in _handle_event method
    
    async def _handle_media(self, data: Dict[str, Any], voice_session: VoiceAgentSession):
        """Handle incoming audio from Twilio"""
        media_data = data.get("media", {})
        audio_base64 = media_data.get("payload", "")
        
        if not audio_base64:
            return
            
        # Decode mulaw audio from Twilio
        audio_data = base64.b64decode(audio_base64)
        
        # Send to Voice Agent
        await voice_session.agent.send_audio(audio_data)
    
    async def _create_call_conversation(
        self,
        db: AsyncSession,
        call: PhoneCall,
        config: Any
    ) -> Conversation:
        """Create a conversation record for the phone call"""
        
        conversation = Conversation(
            tenant_id=config.tenant_id,
            title=f"Phone Call - {call.customer_phone_number}",
            description=f"Incoming call from {call.customer_phone_number} (Voice Agent)",
            status="active"
        )
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        # Link call to conversation
        call.conversation_id = conversation.id
        await db.commit()
        
        return conversation
    
    async def _periodic_flush_task(self, session_id: str, db: AsyncSession):
        """Periodically flush pending messages to reduce latency"""
        while True:
            try:
                await asyncio.sleep(5)  # Flush every 5 seconds
                await self._flush_pending_messages(session_id, db)
            except asyncio.CancelledError:
                # Final flush before task ends
                await self._flush_pending_messages(session_id, db)
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic flush: {str(e)}")
    
    async def _flush_pending_messages(self, session_id: str, db: AsyncSession):
        """Flush pending messages to database in batch"""
        session_info = self.call_sessions.get(session_id)
        if not session_info or "pending_messages" not in session_info:
            return
            
        pending_messages = session_info["pending_messages"]
        if not pending_messages:
            return
            
        try:
            # Add all pending messages to session
            for message in pending_messages:
                db.add(message)
            
            # Commit all at once
            await db.commit()
            
            # Clear pending messages
            session_info["pending_messages"] = []
            
            logger.info(f"💾 Flushed {len(pending_messages)} messages to database")
            
        except Exception as e:
            logger.error(f"❌ Error flushing messages: {str(e)}")
            await db.rollback()
    
    async def _cleanup_session(self, session_id: str, db: AsyncSession):
        """Cleanup session when call ends"""
        session_info = self.call_sessions.get(session_id)
        if not session_info:
            return
            
        try:
            # Flush any remaining pending messages before cleanup
            await self._flush_pending_messages(session_id, db)
            
            # Update phone call record
            phone_call = session_info["phone_call"]
            from datetime import timezone
            phone_call.end_time = datetime.now(timezone.utc)
            phone_call.status = "completed"
            
            # Calculate duration (ensure both times are timezone-aware)
            start_time = phone_call.start_time
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            duration = (phone_call.end_time - start_time).total_seconds()
            phone_call.duration_seconds = int(duration)
            
            await db.commit()
            
            # Record call duration usage
            config = session_info["config"]
            if phone_call.duration_seconds and phone_call.duration_seconds > 0:
                try:
                    duration_minutes = phone_call.duration_seconds / 60.0
                    cost_cents = int(duration_minutes * 1.5)  # $0.015 per minute
                    
                    await usage_service.record_usage(
                        db=db,
                        tenant_id=config.tenant_id,
                        usage_type="telephony_minutes",
                        amount=int(duration_minutes),
                        cost_cents=cost_cents,
                        additional_data={
                            "call_id": str(phone_call.id),
                            "call_sid": phone_call.call_sid,
                            "voice_agent_type": "deepgram_integrated"
                        }
                    )
                    logger.info(f"📊 Call duration usage recorded: {duration_minutes:.2f} minutes (${cost_cents/100:.2f})")
                except Exception as e:
                    logger.error(f"❌ Error recording call duration usage: {e}")
            
            # Update conversation status
            conversation = session_info["conversation"]
            conversation.status = "completed"
            await db.commit()
            
            # Auto-generate summary for completed call
            try:
                await self._generate_call_summary(phone_call.id, db)
            except Exception as e:
                logger.error(f"❌ Error generating summary for call {phone_call.id}: {e}")
            
            # TODO: Update telephony status
            # status_manager = TelephonyStatusManager()
            # await status_manager.remove_active_call(
            #     tenant_id=str(session_info["config"].tenant_id),
            #     call_sid=session_info["call_sid"]
            # )
            
            # Cleanup session
            del self.call_sessions[session_id]
            
            logger.info(f"✅ Cleaned up session {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up session: {e}")
    
    async def _generate_call_summary(self, call_id: str, db: AsyncSession):
        """Generate summary for a completed call"""
        
        try:
            from sqlalchemy import and_
            
            # Check if summary already exists
            existing_summary_query = select(CallMessage).where(
                and_(
                    CallMessage.call_id == call_id,
                    CallMessage.message_type == 'summary'
                )
            )
            existing_result = await db.execute(existing_summary_query)
            if existing_result.scalar_one_or_none():
                logger.info(f"📝 Summary already exists for call {call_id}")
                return
            
            # Get transcript messages
            transcript_query = (
                select(CallMessage)
                .where(
                    and_(
                        CallMessage.call_id == call_id,
                        CallMessage.message_type == 'transcript'
                    )
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
                f"The customer initiated contact and the conversation was handled by the AI agent using Deepgram Voice Agent."
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
                    "generation_method": "voice_agent_auto_generated",
                    "message_count": message_count,
                    "customer_message_count": len(customer_messages),
                    "agent_message_count": len(agent_messages)
                }
            )
            
            db.add(summary_message)
            
            # Also update the phone_call summary field
            call.summary = summary_content
            
            await db.commit()
            logger.info(f"📝 ✅ Auto-generated summary for Voice Agent call {call_id}")
            
        except Exception as e:
            logger.error(f"❌ Error generating summary for call {call_id}: {e}")
            # Don't re-raise - summary generation is optional


# Create handler instance
telephony_voice_agent_handler = TelephonyVoiceAgentHandler()


# WebSocket endpoint
async def telephony_voice_agent_websocket(websocket: WebSocket):
    """WebSocket endpoint for Twilio Voice Agent integration"""
    # Create database session manually (dependency injection doesn't work well with add_websocket_route)
    async for db in get_db():
        try:
            await telephony_voice_agent_handler.handle_connection(websocket, db)
        finally:
            await db.close()
        break