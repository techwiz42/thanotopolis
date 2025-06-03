# app/services/voice/hybrid_tts_service.py
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from langdetect import detect
import langdetect.lang_detect_exception

from app.services.voice.elevenlabs_tts_service import elevenlabs_tts_service
from app.services.voice.google_tts_service import tts_service as google_tts_service

logger = logging.getLogger(__name__)

class HybridTTSService:
    """
    Hybrid TTS service that automatically routes to ElevenLabs for supported languages
    and falls back to Google TTS for unsupported languages.
    """
    
    def __init__(self):
        self.elevenlabs_service = elevenlabs_tts_service
        self.google_service = google_tts_service
        
        # Language support mapping
        self.elevenlabs_languages = {
            # ElevenLabs supported languages (32 total)
            "en": "English",
            "es": "Spanish", 
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
            "hi": "Hindi",
            "pl": "Polish",
            "ru": "Russian",
            "nl": "Dutch",
            "tr": "Turkish",
            "sv": "Swedish",
            "id": "Indonesian",
            "tl": "Filipino",
            "uk": "Ukrainian",  # ✅ Your requirement
            "el": "Greek",
            "cs": "Czech",
            "fi": "Finnish",
            "ro": "Romanian",
            "da": "Danish",
            "bg": "Bulgarian",
            "ms": "Malay",
            "sk": "Slovak",
            "hr": "Croatian",
            "ar": "Arabic",
            "ta": "Tamil",
            "hu": "Hungarian",
            "no": "Norwegian",
            "vi": "Vietnamese"
        }
        
        # Languages that require Google TTS fallback
        self.google_fallback_languages = {
            "th": "Thai",      # ❌ Not in ElevenLabs
            "hy": "Armenian",  # ❌ Not in ElevenLabs
            # Add more as needed
            "he": "Hebrew",
            "is": "Icelandic",
            "mt": "Maltese",
            "cy": "Welsh",
            "ga": "Irish",
            "eu": "Basque",
            "ca": "Catalan",
            "gl": "Galician",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "sl": "Slovenian",
            "mk": "Macedonian",
            "sq": "Albanian",
            "be": "Belarusian",
            "kk": "Kazakh",
            "ky": "Kyrgyz",
            "uz": "Uzbek",
            "tg": "Tajik",
            "mn": "Mongolian",
            "ne": "Nepali",
            "si": "Sinhala",
            "my": "Burmese",
            "km": "Khmer",
            "lo": "Lao",
            "ka": "Georgian",
            "am": "Amharic",
            "sw": "Swahili",
            "zu": "Zulu",
            "af": "Afrikaans",
            "bn": "Bengali",
            "gu": "Gujarati",
            "te": "Telugu",
            "kn": "Kannada",
            "ml": "Malayalam",
            "or": "Odia",
            "pa": "Punjabi",
            "ur": "Urdu",
            "fa": "Persian",
            "ps": "Pashto",
            "sd": "Sindhi"
        }
        
        # Unified voice recommendations
        self.voice_mappings = {
            "elevenlabs": {
                "female": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                "male": "ErXwobaYiN019PkySvjV"      # Antoni
            },
            "google": {
                "female": "en-US-Studio-O",
                "male": "en-US-Studio-M"
            }
        }
        
        logger.info("HybridTTSService initialized")
        logger.info(f"ElevenLabs languages: {len(self.elevenlabs_languages)}")
        logger.info(f"Google fallback languages: {len(self.google_fallback_languages)}")
    
    def detect_language(self, text: str) -> str:
        """
        Detect language from text using langdetect library.
        Returns ISO 639-1 language code.
        """
        try:
            # Clean text for better detection
            clean_text = re.sub(r'[^\w\s]', ' ', text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if len(clean_text) < 10:
                logger.warning(f"Text too short for reliable detection: '{text[:50]}...'")
                return "en"  # Default to English
            
            detected = detect(clean_text)
            logger.info(f"Detected language: {detected} for text: '{text[:50]}...'")
            return detected
            
        except langdetect.lang_detect_exception.LangDetectException as e:
            logger.warning(f"Language detection failed: {e}. Defaulting to English.")
            return "en"
        except Exception as e:
            logger.error(f"Unexpected error in language detection: {e}")
            return "en"
    
    def get_provider_for_language(self, language_code: str) -> Tuple[str, str]:
        """
        Determine which TTS provider to use for a given language.
        Returns (provider_name, language_name).
        """
        # Check ElevenLabs support first (higher quality)
        if language_code in self.elevenlabs_languages:
            provider = "elevenlabs"
            language_name = self.elevenlabs_languages[language_code]
            logger.info(f"Using ElevenLabs for {language_code} ({language_name})")
            return provider, language_name
        
        # Fall back to Google TTS
        if language_code in self.google_fallback_languages:
            provider = "google"
            language_name = self.google_fallback_languages[language_code]
            logger.info(f"Using Google TTS fallback for {language_code} ({language_name})")
            return provider, language_name
        
        # Default fallback to Google for unknown languages
        provider = "google"
        language_name = "Unknown"
        logger.warning(f"Unknown language {language_code}, using Google TTS fallback")
        return provider, language_name
    
    def get_provider_voice(self, provider: str, language_code: str, requested_voice: Optional[str], gender: Optional[str]) -> str:
        """
        Get appropriate voice for the provider and language.
        """
        if provider == "elevenlabs":
            # Use requested voice if it exists in ElevenLabs
            if requested_voice and requested_voice in self.elevenlabs_service.voices:
                return requested_voice
            
            # Use gender-based recommendation
            if gender and gender.lower() in ["female", "male"]:
                return self.voice_mappings["elevenlabs"][gender.lower()]
            
            # Use default
            return self.elevenlabs_service.default_voice
        
        elif provider == "google":
            # Map language code to Google language format
            google_lang_code = self._map_to_google_language(language_code)
            
            # Use requested voice if it exists in Google
            if requested_voice and requested_voice.startswith(google_lang_code):
                return requested_voice
            
            # Generate appropriate Google voice
            if gender and gender.lower() == "female":
                return f"{google_lang_code}-Standard-A"  # Usually female
            else:
                return f"{google_lang_code}-Standard-B"  # Usually male
        
        return None
    
    def _map_to_google_language(self, language_code: str) -> str:
        """
        Map ISO 639-1 language codes to Google TTS language codes.
        """
        google_mappings = {
            "en": "en-US",
            "es": "es-ES", 
            "fr": "fr-FR",
            "de": "de-DE",
            "it": "it-IT",
            "pt": "pt-BR",
            "ja": "ja-JP",
            "zh": "zh-CN",
            "ko": "ko-KR",
            "hi": "hi-IN",
            "pl": "pl-PL",
            "ru": "ru-RU",
            "nl": "nl-NL",
            "tr": "tr-TR",
            "sv": "sv-SE",
            "uk": "uk-UA",  # Ukrainian
            "th": "th-TH",  # Thai
            "hy": "hy-AM",  # Armenian
            "ar": "ar-SA",
            "he": "he-IL",
            "cs": "cs-CZ",
            "da": "da-DK",
            "fi": "fi-FI",
            "no": "nb-NO",
            "hu": "hu-HU",
            "bg": "bg-BG",
            "hr": "hr-HR",
            "sk": "sk-SK",
            "sl": "sl-SI",
            "et": "et-EE",
            "lv": "lv-LV",
            "lt": "lt-LT",
            "mt": "mt-MT",
            "ga": "ga-IE",
            "cy": "cy-GB",
            "is": "is-IS",
            "mk": "mk-MK",
            "sq": "sq-AL",
            "be": "be-BY",
            "ka": "ka-GE",
            "am": "am-ET",
            "sw": "sw-KE",
            "af": "af-ZA",
            "bn": "bn-IN",
            "gu": "gu-IN",
            "te": "te-IN",
            "kn": "kn-IN",
            "ml": "ml-IN",
            "pa": "pa-IN",
            "ta": "ta-IN",
            "ur": "ur-PK",
            "fa": "fa-IR",
            "vi": "vi-VN",
            "id": "id-ID",
            "ms": "ms-MY",
            "tl": "fil-PH",
            "my": "my-MM",
            "km": "km-KH",
            "lo": "lo-LA",
            "si": "si-LK",
            "ne": "ne-NP"
        }
        
        return google_mappings.get(language_code, "en-US")
    
    async def synthesize_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        encoding: str = "mp3",
        sample_rate: Optional[int] = None,
        container: Optional[str] = None,
        preprocess_text: bool = True,
        language_code: Optional[str] = None,
        gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize speech using the hybrid approach.
        Automatically detects language and routes to appropriate provider.
        """
        try:
            # Detect language if not provided
            if not language_code:
                language_code = self.detect_language(text)
            
            # Determine provider
            provider, language_name = self.get_provider_for_language(language_code)
            
            # Get appropriate voice for the provider
            selected_voice = self.get_provider_voice(provider, language_code, voice_id, gender)
            
            logger.info(f"Hybrid TTS: Using {provider} for '{language_name}' with voice '{selected_voice}'")
            
            # Route to appropriate provider
            if provider == "elevenlabs":
                result = await self.elevenlabs_service.synthesize_speech(
                    text=text,
                    voice_id=selected_voice,
                    encoding=encoding,
                    sample_rate=sample_rate,
                    container=container,
                    preprocess_text=preprocess_text
                )
                
                # Add hybrid metadata
                if result.get("success"):
                    result["provider"] = "elevenlabs"
                    result["hybrid_routing"] = "primary"
                    result["language_detected"] = language_code
                    result["language_name"] = language_name
                
                return result
            
            elif provider == "google":
                # Map parameters for Google TTS
                google_language_code = self._map_to_google_language(language_code)
                
                result = self.google_service.synthesize_speech(
                    text=text,
                    voice_id=selected_voice,
                    language_code=google_language_code,
                    audio_encoding=encoding.upper(),
                    preprocess_text=preprocess_text
                )
                
                # Add hybrid metadata  
                if result.get("success"):
                    result["provider"] = "google"
                    result["hybrid_routing"] = "fallback"
                    result["language_detected"] = language_code
                    result["language_name"] = language_name
                    result["encoding"] = encoding.lower()  # Normalize for consistency
                
                return result
            
            else:
                return {
                    "success": False,
                    "error": f"No provider available for language: {language_code}",
                    "provider": "none"
                }
                
        except Exception as e:
            logger.error(f"Error in hybrid TTS synthesis: {e}")
            return {
                "success": False,
                "error": f"Hybrid TTS error: {str(e)}",
                "provider": "error"
            }
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get combined list of available voices from both providers.
        """
        voices = []
        
        # Get ElevenLabs voices
        elevenlabs_voices = self.elevenlabs_service.get_available_voices()
        for voice in elevenlabs_voices:
            voice["provider"] = "elevenlabs"
            voice["supported_languages"] = list(self.elevenlabs_languages.keys())
            voices.append(voice)
        
        # Get Google voices (sample - Google has many more)
        google_voices = self.google_service.get_available_voices()
        for voice in google_voices:
            voice["provider"] = "google"
            voice["supported_languages"] = list(self.google_fallback_languages.keys())
            voices.append(voice)
        
        return voices
    
    def get_recommended_voice(self, gender: Optional[str] = None, quality: str = "conversational", language_code: Optional[str] = None) -> str:
        """
        Get recommended voice based on language and preferences.
        """
        # If language specified, route to appropriate provider
        if language_code:
            provider, _ = self.get_provider_for_language(language_code)
            
            if provider == "elevenlabs":
                return self.elevenlabs_service.get_recommended_voice(gender=gender, quality=quality)
            elif provider == "google":
                return self.google_service.get_recommended_voice(gender=gender, accent="US")
        
        # Default to ElevenLabs recommendation
        return self.elevenlabs_service.get_recommended_voice(gender=gender, quality=quality)
    
    def get_audio_mime_type(self, encoding: str) -> str:
        """Get MIME type for audio encoding."""
        return self.elevenlabs_service.get_audio_mime_type(encoding)
    
    def get_provider_info(self, language_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about which provider will be used for a language.
        """
        if not language_code:
            return {
                "default_provider": "elevenlabs",
                "fallback_provider": "google",
                "total_languages": len(self.elevenlabs_languages) + len(self.google_fallback_languages)
            }
        
        provider, language_name = self.get_provider_for_language(language_code)
        
        return {
            "language_code": language_code,
            "language_name": language_name,
            "provider": provider,
            "routing": "primary" if provider == "elevenlabs" else "fallback"
        }

# Create singleton instance
hybrid_tts_service = HybridTTSService()
