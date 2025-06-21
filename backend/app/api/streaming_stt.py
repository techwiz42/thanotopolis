# api/streaming_stt.py
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
from app.services.voice import soniox_service
from app.services.usage_service import usage_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def count_words(text: str) -> int:
    """Count words in text for usage tracking."""
    if not text:
        return 0
    return len(text.split())


class StreamingSTTManager:
    """Manages WebSocket connections for streaming speech-to-text."""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user: User) -> str:
        """Register a new STT connection."""
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
            
            logger.info(f"STT connection established: {connection_id} for user {user.email}")
            return connection_id
    
    async def disconnect(self, connection_id: str):
        """Remove an STT connection."""
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
                logger.info(f"STT connection closed: {connection_id}")
    
    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection by ID."""
        return self.active_connections.get(connection_id)


# Singleton STT manager
stt_manager = StreamingSTTManager()


async def authenticate_stt_websocket(websocket: WebSocket, token: str, db: AsyncSession) -> Optional[User]:
    """Authenticate an STT WebSocket connection."""
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
        logger.error(f"STT WebSocket authentication error: {e}")
        return None


@router.websocket("/ws/stt/stream")
async def websocket_streaming_stt(
    websocket: WebSocket,
    token: str,
    language: Optional[str] = None,
    model: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time speech-to-text streaming."""
    connection_id = None
    
    try:
        # Authenticate user
        user = await authenticate_stt_websocket(websocket, token, db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
        # Check if Soniox is available
        if not soniox_service.is_available():
            await websocket.close(code=4003, reason="Speech-to-text service unavailable")
            return
        
        # Connect to STT manager
        connection_id = await stt_manager.connect(websocket, user)
        connection = stt_manager.get_connection(connection_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "STT streaming connected",
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
                    logger.info(f"STT WebSocket disconnected: {connection_id}")
                    break
                elif message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Audio data received
                        audio_data = message["bytes"]
                        
                        # Start transcription session if not active
                        if not connection["is_transcribing"]:
                            logger.info(f"Starting live transcription session with language: {language or 'auto-detect'}")
                            
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
                                            service_provider="soniox",
                                            model_name="soniox-auto"
                                        ))
                                
                                # Include detected language if available
                                response_data = {
                                    "type": "transcript",
                                    "is_final": transcript_data.get("is_final", False),
                                    "speech_final": transcript_data.get("speech_final", False),
                                    "transcript": transcript_text,
                                    "confidence": transcript_data.get("confidence", 0.0),
                                    "words": transcript_data.get("words", []),
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                                
                                # Add detected language if available
                                if transcript_data.get("detected_language"):
                                    response_data["detected_language"] = transcript_data["detected_language"]
                                
                                asyncio.create_task(websocket.send_json(response_data))
                            
                            def on_transcript_error(error):
                                """Handle transcript errors."""
                                logger.error(f"Transcription error: {error}")
                                asyncio.create_task(websocket.send_json({
                                    "type": "error",
                                    "message": str(error),
                                    "timestamp": datetime.utcnow().isoformat()
                                }))
                            
                            # Create transcription session with specified language or auto-detection
                            # Check for language preference from control message first, then URL params
                            session_language = connection.get("language", language)
                            session_model = connection.get("model", model)
                            
                            # If language is 'auto' or None, enable auto-detection
                            use_language = None if session_language in [None, 'auto', 'auto-detect'] else session_language
                            enable_detection = session_language in [None, 'auto', 'auto-detect']
                            
                            logger.info(f"Creating Soniox transcription session - Language: {use_language or 'auto-detect'}")
                            
                            transcription_session = await soniox_service.start_live_transcription(
                                on_message=on_transcript_message,
                                on_error=on_transcript_error,
                                interim_results=True,
                                punctuate=True,
                                smart_format=True,
                                language=use_language,
                                detect_language=enable_detection,
                                encoding="linear16",
                                sample_rate=16000,
                                channels=1
                            )
                            
                            await transcription_session.start()
                            connection["transcription_session"] = transcription_session
                            connection["is_transcribing"] = True
                        
                        # Send audio to transcription with validation
                        if transcription_session and audio_data:
                            try:
                                # Validate audio data size (prevent too small or too large chunks)
                                if len(audio_data) < 10:
                                    logger.debug(f"Skipping tiny audio chunk: {len(audio_data)} bytes")
                                    continue
                                if len(audio_data) > 32768:  # 32KB max chunk
                                    logger.warning(f"Large audio chunk: {len(audio_data)} bytes")
                                
                                await transcription_session.send_audio(audio_data)
                            except Exception as audio_error:
                                logger.error(f"Error sending audio data (language: {connection.get('language', 'auto')}): {audio_error}")
                                # Don't break the loop for audio send errors - just log and continue
                    
                    elif "text" in message:
                        # Control message
                        try:
                            control_data = json.loads(message["text"])
                            control_type = control_data.get("type")
                            
                            if control_type == "start_transcription":
                                # Extract language and model from control message
                                control_language = control_data.get("language")
                                control_model = control_data.get("model")
                                
                                # Store language preference in connection for later use
                                if control_language:
                                    connection["language"] = control_language
                                if control_model:
                                    connection["model"] = control_model
                                
                                if not connection["is_transcribing"]:
                                    await websocket.send_json({
                                        "type": "transcription_ready",
                                        "message": "Ready to receive audio",
                                        "language": control_language or language or "auto-detect",
                                        "model": "soniox-auto",
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
                logger.info(f"STT WebSocket disconnected: {connection_id} (language: {connection.get('language', 'auto')})")
                break
            except Exception as e:
                logger.error(f"Error in STT WebSocket loop for {connection_id} (language: {connection.get('language', 'auto')}): {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "language": connection.get('language', 'auto'),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as send_error:
                    logger.error(f"Failed to send error message: {send_error}")
                break
    
    except Exception as e:
        logger.error(f"STT WebSocket error: {e}")
    
    finally:
        if connection_id:
            await stt_manager.disconnect(connection_id)


@router.post("/stt/file")
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
        # Check if Soniox is available
        if not soniox_service.is_available():
            raise HTTPException(status_code=503, detail="Speech-to-text service unavailable")
        
        # Read audio file
        audio_data = await audio_file.read()
        
        # Get content type
        content_type = audio_file.content_type or "audio/wav"
        
        # Transcribe with auto language detection if no language specified
        result = await soniox_service.transcribe_file(
            audio_data=audio_data,
            content_type=content_type,
            language=language,  # If None, will auto-detect
            model=model,
            punctuate=punctuate,
            diarize=diarize,
            smart_format=smart_format,
            detect_language=language is None  # Enable detection if no language specified
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
                    service_provider="soniox",
                    model_name="soniox-auto"
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
        
    except HTTPException:
        # Re-raise HTTPExceptions with their original status code
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stt/status")
async def get_stt_status():
    """Get STT service status."""
    return {
        "service": "soniox",
        "available": soniox_service.is_available(),
        "model": "soniox-auto",
        "language": "auto-detect",
        "active_connections": len(stt_manager.active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }


async def shutdown_stt_handlers():
    """Shutdown all active STT handlers."""
    try:
        logger.info("Shutting down STT handlers...")
        
        # Close all active connections
        for connection_id in list(stt_manager.active_connections.keys()):
            await stt_manager.disconnect(connection_id)
        
        logger.info("STT handlers shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down STT handlers: {e}")