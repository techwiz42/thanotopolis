# api/voice_streaming.py
import asyncio
import json
import logging
import uuid
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.auth.auth import get_current_user, get_current_active_user
from app.db.database import get_db
from app.models.models import User
from app.services.voice import deepgram_service, elevenlabs_service
from app.services.usage_service import usage_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def count_words(text: str) -> int:
    """Count words in text for usage tracking."""
    if not text:
        return 0
    return len(text.split())

# Active WebSocket connections for voice streaming
active_voice_connections: Dict[str, WebSocket] = {}
connection_lock = asyncio.Lock()


class VoiceConnectionManager:
    """Manages WebSocket connections for voice streaming."""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user: User) -> str:
        """Register a new voice connection."""
        async with self.lock:
            connection_id = str(uuid.uuid4())
            
            await websocket.accept()
            
            self.active_connections[connection_id] = {
                "websocket": websocket,
                "user": user,
                "connected_at": datetime.utcnow(),
                "transcription_session": None,
                "is_transcribing": False
            }
            
            logger.info(f"Voice connection established: {connection_id} for user {user.email}")
            return connection_id
    
    async def disconnect(self, connection_id: str):
        """Remove a voice connection."""
        async with self.lock:
            if connection_id in self.active_connections:
                connection = self.active_connections[connection_id]
                
                # Clean up transcription session if active
                if connection.get("transcription_session"):
                    try:
                        await connection["transcription_session"].finish()
                    except Exception as e:
                        logger.error(f"Error finishing transcription session: {e}")
                
                del self.active_connections[connection_id]
                logger.info(f"Voice connection closed: {connection_id}")
    
    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection by ID."""
        return self.active_connections.get(connection_id)


# Singleton connection manager
voice_connection_manager = VoiceConnectionManager()


async def authenticate_voice_websocket(websocket: WebSocket, token: str, db: AsyncSession) -> Optional[User]:
    """Authenticate a voice WebSocket connection."""
    try:
        from app.auth.auth import AuthService
        payload = AuthService.decode_token(token)
        user_id = payload.sub
        
        if not user_id:
            return None
        
        from sqlalchemy import select
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Voice WebSocket authentication error: {e}")
        return None


@router.websocket("/ws/voice/streaming-stt")
async def websocket_streaming_stt(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time speech-to-text."""
    connection_id = None
    
    try:
        # Authenticate user
        user = await authenticate_voice_websocket(websocket, token, db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
        # Check if Deepgram is available
        if not deepgram_service.is_available():
            await websocket.close(code=4003, reason="Speech-to-text service unavailable")
            return
        
        # Connect to voice manager
        connection_id = await voice_connection_manager.connect(websocket, user)
        connection = voice_connection_manager.get_connection(connection_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Voice streaming connected",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        transcription_session = None
        
        while True:
            try:
                # Receive message
                message = await websocket.receive()
                
                # Handle different message types
                if message["type"] == "websocket.disconnect":
                    logger.info(f"Voice WebSocket disconnected: {connection_id}")
                    break
                elif message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Audio data received
                        audio_data = message["bytes"]
                        
                        # Audio data received - process silently
                        
                        # Start transcription session if not active
                        if not connection["is_transcribing"]:
                            logger.info("Starting live transcription session")
                            
                            def on_transcript_message(transcript_data):
                                """Handle transcript messages."""
                                # Track usage for final transcripts
                                transcript_text = transcript_data.get("transcript", "")
                                if transcript_data.get("is_final", False) and transcript_text.strip():
                                    word_count = count_words(transcript_text)
                                    if word_count > 0:
                                        # Record STT usage asynchronously
                                        asyncio.create_task(usage_service.record_stt_usage(
                                            db=db,
                                            tenant_id=user.tenant_id,
                                            user_id=user.id,
                                            word_count=word_count,
                                            service_provider="deepgram",
                                            model_name=settings.DEEPGRAM_MODEL
                                        ))
                                
                                asyncio.create_task(websocket.send_json({
                                    "type": "transcript",
                                    "is_final": transcript_data.get("is_final", False),
                                    "speech_final": transcript_data.get("speech_final", False),
                                    "transcript": transcript_text,
                                    "confidence": transcript_data.get("confidence", 0.0),
                                    "words": transcript_data.get("words", []),
                                    "timestamp": datetime.utcnow().isoformat()
                                }))
                            
                            def on_transcript_error(error):
                                """Handle transcript errors."""
                                logger.error(f"Transcription error: {error}")
                                asyncio.create_task(websocket.send_json({
                                    "type": "error",
                                    "message": str(error),
                                    "timestamp": datetime.utcnow().isoformat()
                                }))
                            
                            # Create transcription session
                            # Frontend now sends resampled PCM audio at 16kHz
                            transcription_session = await deepgram_service.start_live_transcription(
                                on_message=on_transcript_message,
                                on_error=on_transcript_error,
                                interim_results=True,
                                punctuate=True,
                                smart_format=True,
                                language="en-US",
                                encoding="linear16",
                                sample_rate=16000,
                                channels=1
                            )
                            
                            await transcription_session.start()
                            connection["transcription_session"] = transcription_session
                            connection["is_transcribing"] = True
                        
                        # Send audio to transcription
                        if transcription_session and audio_data:
                            await transcription_session.send_audio(audio_data)
                    
                    elif "text" in message:
                        # Control message
                        try:
                            control_data = json.loads(message["text"])
                            control_type = control_data.get("type")
                            
                            if control_type == "start_transcription":
                                if not connection["is_transcribing"]:
                                    await websocket.send_json({
                                        "type": "transcription_ready",
                                        "message": "Ready to receive audio",
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                            
                            elif control_type == "stop_transcription":
                                if transcription_session:
                                    await transcription_session.finish()
                                    connection["transcription_session"] = None
                                    connection["is_transcribing"] = False
                                    
                                    await websocket.send_json({
                                        "type": "transcription_stopped",
                                        "message": "Transcription stopped",
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                            
                            elif control_type == "ping":
                                await websocket.send_json({
                                    "type": "pong",
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                        
                        except json.JSONDecodeError:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Invalid control message format",
                                "timestamp": datetime.utcnow().isoformat()
                            })
                
            except WebSocketDisconnect:
                logger.info(f"Voice WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error in voice WebSocket loop: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                break
    
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
    
    finally:
        if connection_id:
            await voice_connection_manager.disconnect(connection_id)


@router.post("/voice/stt/file")
async def transcribe_audio_file(
    audio_file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    punctuate: bool = Form(True),
    diarize: bool = Form(False),
    smart_format: bool = Form(True),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Transcribe an uploaded audio file."""
    try:
        # Check if Deepgram is available
        if not deepgram_service.is_available():
            raise HTTPException(status_code=503, detail="Speech-to-text service unavailable")
        
        # Read audio file
        audio_data = await audio_file.read()
        
        # Get content type
        content_type = audio_file.content_type or "audio/wav"
        
        # Transcribe
        result = await deepgram_service.transcribe_file(
            audio_data=audio_data,
            content_type=content_type,
            language=language,
            model=model,
            punctuate=punctuate,
            diarize=diarize,
            smart_format=smart_format
        )
        
        # Log transcription
        logger.info(f"Transcribed file {audio_file.filename} for user {current_user.email}")
        
        # Track STT usage
        transcript_text = result["transcript"]
        if transcript_text.strip():
            word_count = count_words(transcript_text)
            if word_count > 0:
                await usage_service.record_stt_usage(
                    db=db,
                    tenant_id=current_user.tenant_id,
                    user_id=current_user.id,
                    word_count=word_count,
                    service_provider="deepgram",
                    model_name=model or settings.DEEPGRAM_MODEL
                )
        
        return {
            "success": result["success"],
            "transcript": result["transcript"],
            "confidence": result["confidence"],
            "words": result["words"],
            "speakers": result["speakers"],
            "paragraphs": result["paragraphs"],
            "metadata": {
                "filename": audio_file.filename,
                "content_type": content_type,
                "file_size": len(audio_data),
                "language": language,
                "model": model
            }
        }
        
    except Exception as e:
        logger.error(f"Error transcribing audio file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/tts/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice_id: Optional[str] = Form(None),
    model_id: Optional[str] = Form(None),
    stability: float = Form(0.5),
    similarity_boost: float = Form(0.5),
    style: float = Form(0.0),
    use_speaker_boost: bool = Form(True),
    output_format: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Synthesize speech from text."""
    try:
        # Check if ElevenLabs is available
        if not elevenlabs_service.is_available():
            raise HTTPException(status_code=503, detail="Text-to-speech service unavailable")
        
        # Prepare voice settings
        voice_settings = {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost
        }
        
        # Log TTS request details
        logger.info(f"TTS request from user {current_user.email}: text_len={len(text)}, voice={voice_id}, model={model_id}")
        
        # Synthesize speech
        result = await elevenlabs_service.synthesize_speech(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings=voice_settings,
            output_format=output_format
        )
        
        if not result["success"]:
            logger.error(f"TTS synthesis failed for user {current_user.email}: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Log synthesis details
        audio_size = len(result["audio_data"])
        chunks_processed = result.get("chunks_processed", 1)
        logger.info(f"Successfully synthesized {len(text)} characters for user {current_user.email}: {audio_size} bytes, {chunks_processed} chunks")
        
        # Track TTS usage
        word_count = count_words(text)
        if word_count > 0:
            await usage_service.record_tts_usage(
                db=db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                word_count=word_count,
                service_provider="elevenlabs",
                model_name=model_id or elevenlabs_service.default_model
            )
        
        # Return audio as response
        return Response(
            content=result["audio_data"],
            media_type=result["content_type"],
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3",
                "Content-Length": str(len(result["audio_data"])),
                "Accept-Ranges": "bytes",
                "X-Text-Length": str(len(text)),
                "X-Voice-ID": result["voice_id"],
                "X-Model-ID": result["model_id"],
                "X-Output-Format": result["output_format"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/tts/stream")
async def stream_speech(
    text: str = Form(...),
    voice_id: Optional[str] = Form(None),
    model_id: Optional[str] = Form(None),
    stability: float = Form(0.5),
    similarity_boost: float = Form(0.5),
    style: float = Form(0.0),
    use_speaker_boost: bool = Form(True),
    output_format: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Stream speech synthesis from text."""
    try:
        # Check if ElevenLabs is available
        if not elevenlabs_service.is_available():
            raise HTTPException(status_code=503, detail="Text-to-speech service unavailable")
        
        # Prepare voice settings
        voice_settings = {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost
        }
        
        # Log streaming start
        logger.info(f"Starting speech streaming for {len(text)} characters for user {current_user.email}")
        
        # Track TTS usage
        word_count = count_words(text)
        if word_count > 0:
            await usage_service.record_tts_usage(
                db=db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                word_count=word_count,
                service_provider="elevenlabs",
                model_name=model_id or elevenlabs_service.default_model
            )
        
        # Stream speech
        async def generate_audio():
            try:
                async for chunk in elevenlabs_service.stream_speech(
                    text=text,
                    voice_id=voice_id,
                    model_id=model_id,
                    voice_settings=voice_settings,
                    output_format=output_format
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"Error in speech streaming: {e}")
                raise
        
        # Determine content type based on output format
        output_fmt = output_format or elevenlabs_service.default_output_format
        if output_fmt.startswith("mp3"):
            content_type = "audio/mpeg"
        elif output_fmt.startswith("wav"):
            content_type = "audio/wav"
        elif output_fmt.startswith("ogg"):
            content_type = "audio/ogg"
        else:
            content_type = "audio/mpeg"
        
        return StreamingResponse(
            generate_audio(),
            media_type=content_type,
            headers={
                "Content-Disposition": "attachment; filename=speech_stream.mp3",
                "X-Text-Length": str(len(text)),
                "X-Voice-ID": voice_id or elevenlabs_service.default_voice_id,
                "X-Model-ID": model_id or elevenlabs_service.default_model,
                "X-Output-Format": output_fmt
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/tts/voices")
async def get_available_voices(
    current_user: User = Depends(get_current_active_user)
):
    """Get available TTS voices."""
    try:
        # Check if ElevenLabs is available
        if not elevenlabs_service.is_available():
            raise HTTPException(status_code=503, detail="Text-to-speech service unavailable")
        
        result = await elevenlabs_service.get_voices()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result["voices"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/tts/voice/{voice_id}")
async def get_voice_info(
    voice_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get information about a specific voice."""
    try:
        # Check if ElevenLabs is available
        if not elevenlabs_service.is_available():
            raise HTTPException(status_code=503, detail="Text-to-speech service unavailable")
        
        result = await elevenlabs_service.get_voice_info(voice_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result["voice"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/tts/models")
async def get_available_models(
    current_user: User = Depends(get_current_active_user)
):
    """Get available TTS models."""
    try:
        # Check if ElevenLabs is available
        if not elevenlabs_service.is_available():
            raise HTTPException(status_code=503, detail="Text-to-speech service unavailable")
        
        result = await elevenlabs_service.get_models()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result["models"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/stt/status")
async def get_stt_status():
    """Get STT service status."""
    return {
        "service": "deepgram",
        "available": deepgram_service.is_available(),
        "model": settings.DEEPGRAM_MODEL,
        "language": settings.DEEPGRAM_LANGUAGE,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/voice/tts/status")
async def get_tts_status():
    """Get TTS service status."""
    return {
        "service": "elevenlabs",
        "available": elevenlabs_service.is_available(),
        "model": settings.ELEVENLABS_MODEL,
        "voice_id": settings.ELEVENLABS_VOICE_ID,
        "output_format": settings.ELEVENLABS_OUTPUT_FORMAT,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/voice/status")
async def get_voice_status():
    """Get overall voice service status."""
    # Get user info if available
    user_info = None
    if elevenlabs_service.is_available():
        try:
            user_result = await elevenlabs_service.get_user_info()
            if user_result["success"]:
                user_info = user_result["user_info"]
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
    
    return {
        "stt": {
            "service": "deepgram",
            "available": deepgram_service.is_available(),
            "model": settings.DEEPGRAM_MODEL,
            "language": settings.DEEPGRAM_LANGUAGE
        },
        "tts": {
            "service": "elevenlabs",
            "available": elevenlabs_service.is_available(),
            "model": settings.ELEVENLABS_MODEL,
            "voice_id": settings.ELEVENLABS_VOICE_ID,
            "output_format": settings.ELEVENLABS_OUTPUT_FORMAT,
            "user_info": user_info
        },
        "active_connections": len(voice_connection_manager.active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }


async def shutdown_all_handlers():
    """Shutdown all active voice handlers."""
    try:
        logger.info("Shutting down voice handlers...")
        
        # Close all active connections
        for connection_id in list(voice_connection_manager.active_connections.keys()):
            await voice_connection_manager.disconnect(connection_id)
        
        logger.info("Voice handlers shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down voice handlers: {e}")
