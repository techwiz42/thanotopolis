# backend/app/api/voice_tts.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io
import logging

from app.auth.auth import get_current_user
from app.models.models import User
from app.services.voice.deepgram_tts_service import deepgram_tts_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    encoding: str = "mp3"
    sample_rate: Optional[int] = None
    container: Optional[str] = None
    preprocess_text: bool = True

@router.post("/synthesize")
async def synthesize_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user)
):
    """Synthesize speech from text using Deepgram TTS."""
    try:
        logger.info(f"TTS request from user {current_user.email}: {len(request.text)} characters")
        
        # Synthesize speech
        result = await deepgram_tts_service.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            encoding=request.encoding,
            sample_rate=request.sample_rate,
            container=request.container,
            preprocess_text=request.preprocess_text
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=f"TTS synthesis failed: {result.get('error', 'Unknown error')}"
            )
        
        # Get MIME type
        mime_type = deepgram_tts_service.get_audio_mime_type(request.encoding)
        
        # Create audio stream
        audio_stream = io.BytesIO(result["audio"])
        
        # Determine file extension based on encoding and container
        if request.container:
            file_extension = request.container
        else:
            file_extension = request.encoding
        
        # Build headers carefully - avoid None values that cause encoding errors
        response_headers = {
            "Content-Disposition": f"attachment; filename=speech.{file_extension}",
            "X-Voice-ID": result.get("voice_id", "unknown"),
            "X-Voice-Quality": result.get("voice_quality", "conversational"),
            "X-Preprocessed": str(result.get("preprocessed", False)).lower(),
            "X-Encoding": result.get("encoding", request.encoding)
        }
        
        # Only add sample rate and container if they have actual values (not None)
        sample_rate_value = result.get("sample_rate") or request.sample_rate
        if sample_rate_value is not None:
            response_headers["X-Sample-Rate"] = str(sample_rate_value)
        
        container_value = result.get("container") or request.container
        if container_value is not None:
            response_headers["X-Container"] = str(container_value)
        
        return StreamingResponse(
            io.BytesIO(result["audio"]), 
            media_type=mime_type,
            headers=response_headers
        )
        
    except Exception as e:
        logger.error(f"Error in TTS synthesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/voices")
async def get_available_voices(current_user: User = Depends(get_current_user)):
    """Get available TTS voices."""
    try:
        voices = deepgram_tts_service.get_available_voices()
        return {
            "success": True,
            "voices": voices,
            "default_voice": deepgram_tts_service.default_voice,
            "provider": "deepgram"
        }
    except Exception as e:
        logger.error(f"Error getting TTS voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/recommended")
async def get_recommended_voice(
    gender: Optional[str] = None,
    quality: str = "conversational",
    current_user: User = Depends(get_current_user)
):
    """Get recommended voice based on preferences."""
    try:
        voice_id = deepgram_tts_service.get_recommended_voice(gender=gender, quality=quality)
        return {
            "success": True,
            "recommended_voice": voice_id,
            "voice_details": deepgram_tts_service.voices.get(voice_id, {}),
            "provider": "deepgram"
        }
    except Exception as e:
        logger.error(f"Error getting recommended voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/status")
async def get_tts_status():
    """Get TTS service status."""
    api_key_loaded = bool(deepgram_tts_service.api_key)
    
    return {
        "service": "deepgram_tts",
        "provider": "deepgram",
        "api_key_configured": api_key_loaded,
        "available_voices": len(deepgram_tts_service.voices),
        "default_voice": deepgram_tts_service.default_voice,
        "supported_encodings": ["mp3", "linear16", "flac", "opus", "aac"],
        "recommended_formats": {
            "mp3": {
                "encoding": "mp3",
                "description": "Standard MP3 format - use encoding only, no container/sample_rate",
                "parameters": ["model", "encoding"]
            },
            "wav": {
                "encoding": "linear16",
                "container": "wav", 
                "description": "WAV format - use linear16 encoding with wav container",
                "parameters": ["model", "encoding", "container", "sample_rate"]
            }
        },
        "parameter_notes": {
            "mp3_encoding": "Do not use 'container' or 'sample_rate' with MP3 - causes 400 errors",
            "linear16_encoding": "Can use 'container' and 'sample_rate' parameters",
            "working_combinations": [
                "model + encoding=mp3",
                "model + encoding=linear16 + container=wav",
                "model only (uses defaults)"
            ]
        }
    }
