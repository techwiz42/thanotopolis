# backend/app/api/voice_tts.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io
import logging

from app.auth.auth import get_current_user
from app.models.models import User
from app.services.voice.hybrid_tts_service import hybrid_tts_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    encoding: str = "mp3"
    sample_rate: Optional[int] = None
    container: Optional[str] = None
    preprocess_text: bool = True
    language_code: Optional[str] = None  # New: Allow explicit language specification
    gender: Optional[str] = None         # New: Gender preference for voice selection

@router.post("/synthesize")
async def synthesize_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Synthesize speech from text using Hybrid TTS (ElevenLabs + Google fallback).
    Automatically detects language and routes to the best available provider.
    """
    try:
        logger.info(f"Hybrid TTS request from user {current_user.email}: {len(request.text)} characters")
        
        # Log language routing for debugging
        if request.language_code:
            provider_info = hybrid_tts_service.get_provider_info(request.language_code)
            logger.info(f"Explicit language {request.language_code} -> {provider_info['provider']} ({provider_info['routing']})")
        
        # Synthesize speech using hybrid service
        result = await hybrid_tts_service.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            encoding=request.encoding,
            sample_rate=request.sample_rate,
            container=request.container,
            preprocess_text=request.preprocess_text,
            language_code=request.language_code,
            gender=request.gender
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=f"Hybrid TTS synthesis failed: {result.get('error', 'Unknown error')}"
            )
        
        # Get MIME type
        mime_type = hybrid_tts_service.get_audio_mime_type(request.encoding)
        
        # Create audio stream
        audio_stream = io.BytesIO(result["audio"])
        
        # Determine file extension
        if request.container:
            file_extension = request.container
        else:
            file_extension = result.get("encoding", "mp3")
        
        # Build headers with hybrid information
        response_headers = {
            "Content-Disposition": f"attachment; filename=speech.{file_extension}",
            "X-Voice-ID": result.get("voice_id", "unknown"),
            "X-Voice-Quality": result.get("voice_quality", "standard"),
            "X-Preprocessed": str(result.get("preprocessed", False)).lower(),
            "X-Encoding": result.get("encoding", "mp3"),
            
            # Hybrid-specific headers
            "X-Provider": result.get("provider", "unknown"),
            "X-Hybrid-Routing": result.get("hybrid_routing", "unknown"),
            "X-Language-Detected": result.get("language_detected", "unknown"),
            "X-Language-Name": result.get("language_name", "unknown")
        }
        
        # Add provider-specific headers
        if result.get("provider") == "elevenlabs":
            response_headers["X-Voice-Name"] = result.get("voice_name", "unknown")
        
        # Only add sample rate and container if they have actual values
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
        logger.error(f"Error in hybrid TTS synthesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/voices")
async def get_available_voices(current_user: User = Depends(get_current_user)):
    """Get available TTS voices from all providers."""
    try:
        voices = hybrid_tts_service.get_available_voices()
        return {
            "success": True,
            "voices": voices,
            "provider": "hybrid",
            "providers": {
                "primary": "elevenlabs",
                "fallback": "google"
            },
            "total_voices": len(voices)
        }
    except Exception as e:
        logger.error(f"Error getting hybrid TTS voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/recommended")
async def get_recommended_voice(
    gender: Optional[str] = None,
    quality: str = "conversational",
    language_code: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get recommended voice based on preferences and language."""
    try:
        voice_id = hybrid_tts_service.get_recommended_voice(
            gender=gender, 
            quality=quality,
            language_code=language_code
        )
        
        # Get provider info for the language
        provider_info = hybrid_tts_service.get_provider_info(language_code)
        
        return {
            "success": True,
            "recommended_voice": voice_id,
            "provider": "hybrid",
            "language_info": provider_info,
            "parameters": {
                "gender": gender,
                "quality": quality,
                "language_code": language_code
            }
        }
    except Exception as e:
        logger.error(f"Error getting recommended voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/language-support")
async def get_language_support(current_user: User = Depends(get_current_user)):
    """Get detailed language support information."""
    try:
        return {
            "success": True,
            "elevenlabs_languages": list(hybrid_tts_service.elevenlabs_languages.keys()),
            "google_fallback_languages": list(hybrid_tts_service.google_fallback_languages.keys()),
            "total_supported": len(hybrid_tts_service.elevenlabs_languages) + len(hybrid_tts_service.google_fallback_languages),
            "routing_info": {
                "primary_provider": "elevenlabs",
                "primary_count": len(hybrid_tts_service.elevenlabs_languages),
                "fallback_provider": "google", 
                "fallback_count": len(hybrid_tts_service.google_fallback_languages)
            },
            "your_languages": {
                "ukrainian": {
                    "code": "uk",
                    "provider": "elevenlabs",
                    "routing": "primary",
                    "quality": "premium"
                },
                "thai": {
                    "code": "th", 
                    "provider": "google",
                    "routing": "fallback",
                    "quality": "standard"
                },
                "armenian": {
                    "code": "hy",
                    "provider": "google", 
                    "routing": "fallback",
                    "quality": "standard"
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting language support info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/provider-info")
async def get_provider_info(
    language_code: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get provider routing information for a specific language."""
    try:
        provider_info = hybrid_tts_service.get_provider_info(language_code)
        return {
            "success": True,
            **provider_info
        }
    except Exception as e:
        logger.error(f"Error getting provider info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/status")
async def get_tts_status():
    """Get hybrid TTS service status."""
    # Check both providers
    elevenlabs_available = bool(hybrid_tts_service.elevenlabs_service.api_key)
    google_available = bool(hybrid_tts_service.google_service.api_key)
    
    return {
        "service": "hybrid_tts",
        "provider": "hybrid",
        "providers": {
            "elevenlabs": {
                "available": elevenlabs_available,
                "languages": len(hybrid_tts_service.elevenlabs_languages),
                "quality": "premium",
                "routing": "primary"
            },
            "google": {
                "available": google_available, 
                "languages": len(hybrid_tts_service.google_fallback_languages),
                "quality": "standard",
                "routing": "fallback"
            }
        },
        "total_languages": len(hybrid_tts_service.elevenlabs_languages) + len(hybrid_tts_service.google_fallback_languages),
        "api_keys_configured": {
            "elevenlabs": elevenlabs_available,
            "google": google_available
        },
        "supported_encodings": ["mp3", "linear16", "ogg_opus"],
        "features": [
            "automatic_language_detection",
            "intelligent_provider_routing", 
            "fallback_support",
            "unified_api",
            "cost_optimization"
        ],
        "routing_examples": {
            "ukrainian": "elevenlabs (premium)",
            "thai": "google (fallback)",
            "armenian": "google (fallback)",
            "english": "elevenlabs (premium)",
            "spanish": "elevenlabs (premium)"
        },
        "parameter_notes": {
            "automatic_routing": "Language automatically detected and routed to best provider",
            "explicit_language": "Use 'language_code' parameter to specify language",
            "voice_selection": "System selects appropriate voice for detected provider",
            "fallback_behavior": "Unsupported languages automatically fall back to Google TTS"
        }
    }
