# backend/app/services/voice/__init__.py
from .deepgram_stt_service import DeepgramSTTService, deepgram_stt_service
from .hybrid_tts_service import HybridTTSService, hybrid_tts_service

# Individual provider services (available but not default)
from .elevenlabs_tts_service import ElevenLabsTTSService, elevenlabs_tts_service
from .google_tts_service import GoogleTTSService, tts_service as google_tts_service
from .deepgram_tts_service import DeepgramTTSService, deepgram_tts_service

# Keep Google STT service for backward compatibility
from .google_stt_service import GoogleSTTService, stt_service as google_stt_service

__all__ = [
    # Primary services (hybrid)
    "HybridTTSService",
    "hybrid_tts_service",
    
    # STT services
    "DeepgramSTTService", 
    "deepgram_stt_service",
    "GoogleSTTService",
    "google_stt_service",
    
    # Individual TTS providers (available for direct use)
    "ElevenLabsTTSService",
    "elevenlabs_tts_service", 
    "GoogleTTSService",
    "google_tts_service",
    "DeepgramTTSService",
    "deepgram_tts_service"
]
