# backend/app/api/voice_tts.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io
import logging

from app.auth.auth import get_current_user
from app.models.models import User
from app.services.voice.google_tts_service import GoogleTTSService

# Create TTS service instance
tts_service = GoogleTTSService()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    language_code: str = "en-US"
    speaking_rate: float = 0.95
    pitch: float = -1.0
    volume_gain_db: float = 1.0
    audio_encoding: str = "MP3"
    preprocess_text: bool = True

@router.post("/synthesize")
async def synthesize_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user)
):
    """Synthesize speech from text using Google TTS."""
    try:
        logger.info(f"TTS request from user {current_user.email}: {len(request.text)} characters")
        
        # Synthesize speech
        result = tts_service.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            language_code=request.language_code,
            speaking_rate=request.speaking_rate,
            pitch=request.pitch,
            volume_gain_db=request.volume_gain_db,
            audio_encoding=request.audio_encoding,
            preprocess_text=request.preprocess_text
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=f"TTS synthesis failed: {result.get('error', 'Unknown error')}"
            )
        
        # Get MIME type
        mime_type = tts_service.get_audio_mime_type(request.audio_encoding)
        
        # Create audio stream
        audio_stream = io.BytesIO(result["audio"])
        
        return StreamingResponse(
            io.BytesIO(result["audio"]), 
            media_type=mime_type,
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3",
                "X-Voice-ID": result.get("voice_id", "unknown"),
                "X-Voice-Quality": result.get("voice_quality", "standard"),
                "X-Preprocessed": str(result.get("preprocessed", False)).lower()
            }
        )
        
    except Exception as e:
        logger.error(f"Error in TTS synthesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/voices")
async def get_available_voices(current_user: User = Depends(get_current_user)):
    """Get available TTS voices."""
    try:
        voices = tts_service.get_available_voices()
        return {
            "success": True,
            "voices": voices,
            "default_voice": tts_service.default_voice
        }
    except Exception as e:
        logger.error(f"Error getting TTS voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/recommended")
async def get_recommended_voice(
    gender: Optional[str] = None,
    accent: str = "US",
    current_user: User = Depends(get_current_user)
):
    """Get recommended voice based on preferences."""
    try:
        voice_id = tts_service.get_recommended_voice(gender=gender, accent=accent)
        return {
            "success": True,
            "recommended_voice": voice_id,
            "voice_details": tts_service.voices.get(voice_id, {})
        }
    except Exception as e:
        logger.error(f"Error getting recommended voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/status")
async def get_tts_status():
    """Get TTS service status."""
    api_key_loaded = bool(tts_service.api_key)
    
    return {
        "service": "google_tts",
        "api_key_configured": api_key_loaded,
        "available_voices": len(tts_service.voices),
        "default_voice": tts_service.default_voice,
        "supported_encodings": ["MP3", "LINEAR16", "OGG_OPUS", "MULAW", "ALAW"]
    }
