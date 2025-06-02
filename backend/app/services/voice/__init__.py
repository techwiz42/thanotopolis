# backend/app/services/voice/__init__.py
from .deepgram_stt_service import DeepgramSTTService, deepgram_stt_service
from .deepgram_tts_service import DeepgramTTSService, deepgram_tts_service

# Keep Google STT service for backward compatibility if needed
from .google_stt_service import GoogleSTTService, stt_service

__all__ = [
    "DeepgramSTTService", 
    "deepgram_stt_service",
    "DeepgramTTSService",
    "deepgram_tts_service",
    "GoogleSTTService", 
    "stt_service"  # Google STT backup
]
