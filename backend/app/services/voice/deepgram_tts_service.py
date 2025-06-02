# app/services/voice/deepgram_tts_service.py - COMPLETE FIXED VERSION
import aiohttp
import asyncio
import base64
import logging
import os
import traceback
import json
import re
from typing import Optional, Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)

class DeepgramTTSService:
    """Enhanced Deepgram Text-to-Speech service with natural voice processing."""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.base_url = "https://api.deepgram.com/v1/speak"
        logger.info(f"DeepgramTTSService initialized. API key available: {bool(self.api_key)}")
        
        # Define available voices - Deepgram Aura voices
        self.voices = {
            # Conversational voices
            "aura-asteria-en": {"gender": "FEMALE", "name": "aura-asteria-en", "quality": "conversational", "language": "en"},
            "aura-luna-en": {"gender": "FEMALE", "name": "aura-luna-en", "quality": "conversational", "language": "en"},
            "aura-stella-en": {"gender": "FEMALE", "name": "aura-stella-en", "quality": "conversational", "language": "en"},
            "aura-athena-en": {"gender": "FEMALE", "name": "aura-athena-en", "quality": "conversational", "language": "en"},
            "aura-hera-en": {"gender": "FEMALE", "name": "aura-hera-en", "quality": "conversational", "language": "en"},
            "aura-orion-en": {"gender": "MALE", "name": "aura-orion-en", "quality": "conversational", "language": "en"},
            "aura-arcas-en": {"gender": "MALE", "name": "aura-arcas-en", "quality": "conversational", "language": "en"},
            "aura-perseus-en": {"gender": "MALE", "name": "aura-perseus-en", "quality": "conversational", "language": "en"},
            "aura-angus-en": {"gender": "MALE", "name": "aura-angus-en", "quality": "conversational", "language": "en"},
            "aura-orpheus-en": {"gender": "MALE", "name": "aura-orpheus-en", "quality": "conversational", "language": "en"},
            "aura-helios-en": {"gender": "MALE", "name": "aura-helios-en", "quality": "conversational", "language": "en"},
            "aura-zeus-en": {"gender": "MALE", "name": "aura-zeus-en", "quality": "conversational", "language": "en"}
        }
        
        # Default to a high-quality female voice
        self.default_voice = "aura-asteria-en"
        
    def _load_api_key(self) -> Optional[str]:
        """Load Deepgram API key from settings or environment."""
        try:
            # Try settings first
            api_key = getattr(settings, 'DEEPGRAM_API_KEY', None)
            if api_key and api_key != "NOT_SET":
                logger.info("Found DEEPGRAM_API_KEY in settings")
                masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
                logger.info(f"Deepgram API key successfully loaded from settings: {masked_key}")
                return api_key
        except AttributeError:
            logger.info("Settings not available, checking environment variables")
        
        # Check environment variables
        api_key = os.environ.get("DEEPGRAM_API_KEY")
        if api_key and api_key != "NOT_SET":
            logger.info("Found DEEPGRAM_API_KEY in environment variables")
            masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
            logger.info(f"Deepgram API key successfully loaded from environment: {masked_key}")
            return api_key
        
        # If not in env vars, try to load from .env file
        env_file_paths = [
            '/home/peter/thanotopolis/backend/.env',
            '/home/peter/agent_framework/backend/.env',
            '/etc/cyberiad/.env'
        ]
        
        for env_file_path in env_file_paths:
            if os.path.exists(env_file_path):
                logger.info(f"Checking {env_file_path} file")
                try:
                    with open(env_file_path) as f:
                        for line in f:
                            if 'DEEPGRAM_API_KEY' in line and not line.strip().startswith('#'):
                                api_key = line.strip().split('=')[1].strip('"').strip("'")
                                if api_key and api_key != "NOT_SET":
                                    logger.info(f"Found DEEPGRAM_API_KEY in {env_file_path} file")
                                    masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
                                    logger.info(f"Deepgram API key successfully loaded: {masked_key}")
                                    return api_key
                except Exception as e:
                    logger.error(f"Error loading Deepgram API key from {env_file_path} file: {e}")
        
        logger.error("Deepgram API key not found in settings, environment variables, or .env files")
        logger.error("Please set DEEPGRAM_API_KEY in your settings or environment variables")
        return None
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get a list of available voices sorted by quality."""
        voices = []
        for voice_id, details in self.voices.items():
            voices.append({
                "id": voice_id, 
                "name": voice_id, 
                "gender": details["gender"],
                "quality": details.get("quality", "conversational"),
                "language": details.get("language", "en")
            })
        # Sort by gender and then by name for better organization
        return sorted(voices, key=lambda x: (x["gender"], x["name"]))
    
    async def synthesize_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        encoding: str = "mp3",
        sample_rate: Optional[int] = None,
        container: Optional[str] = None,
        preprocess_text: bool = True
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text using Deepgram's TTS API.
        
        Note: Based on testing, certain parameter combinations don't work:
        - MP3 encoding + container parameter = 400 error
        - MP3 encoding + sample_rate parameter = 400 error
        - Use encoding="linear16" + container="wav" for WAV files
        - Use encoding="mp3" (no container/sample_rate) for MP3 files
        """
        if not self.api_key:
            logger.error("Cannot synthesize: Deepgram API key not configured")
            return {"success": False, "error": "Deepgram API key not configured"}
        
        # Validate and select voice
        selected_voice = voice_id if voice_id and voice_id in self.voices else self.default_voice
        
        try:
            # Process text if requested
            processed_text = text
            if preprocess_text:
                processed_text = self.preprocess_text(text)
            
            # Prepare request payload - Deepgram expects JSON body with 'text' field
            payload = {
                "text": processed_text
            }
            
            # Build parameters carefully - CRITICAL FIX: Handle None values properly
            params = {
                "model": selected_voice,
                "encoding": encoding
            }
            
            # Only add container/sample_rate for specific encodings that support them
            # IMPORTANT: Never add None values - aiohttp will reject them
            if encoding == "linear16":
                # For linear16, we can specify container and sample_rate
                if container is not None and container != "":
                    params["container"] = str(container)
                if sample_rate is not None:
                    params["sample_rate"] = str(sample_rate)  # Convert to string for URL
            elif encoding == "mp3":
                # For MP3, DO NOT add container or sample_rate (causes 400 errors)
                logger.debug("Using MP3 encoding - omitting container and sample_rate parameters")
                # Don't add container or sample_rate at all for MP3
            else:
                # For other encodings, add parameters if provided (and not None)
                if container is not None and container != "":
                    params["container"] = str(container)
                if sample_rate is not None:
                    params["sample_rate"] = str(sample_rate)  # Convert to string for URL
            
            # CRITICAL FIX: Final safety check to remove any None or empty values from params
            filtered_params = {}
            for k, v in params.items():
                if v is not None and v != "":
                    filtered_params[k] = str(v)
            params = filtered_params
            
            # Prepare headers - Deepgram uses "Token" prefix, not "Bearer"
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Sending TTS request: Voice: {selected_voice}, Encoding: {encoding}")
            logger.debug(f"Request URL: {self.base_url}")
            logger.debug(f"Final filtered params: {params}")
            logger.debug(f"Request payload: {payload}")
            
            # Make API request using aiohttp for async support
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    params=params,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        # Read the audio content
                        audio_content = await response.read()
                        
                        if audio_content:
                            return {
                                "success": True,
                                "audio": audio_content,
                                "encoding": encoding,
                                "voice_id": selected_voice,
                                "voice_quality": self.voices[selected_voice].get("quality", "conversational"),
                                "preprocessed": preprocess_text,
                                "sample_rate": sample_rate if encoding == "linear16" else None,
                                "container": container if encoding == "linear16" else None,
                                "actual_params": params  # Include actual params used
                            }
                        else:
                            logger.warning("Deepgram TTS response is empty")
                            return {
                                "success": False,
                                "error": "Empty audio content in response",
                                "details": "The API response did not contain audio content"
                            }
                    else:
                        error_message = "Unknown error"
                        try:
                            error_data = await response.json()
                            if isinstance(error_data, dict):
                                error_message = error_data.get("message", error_data.get("error", "Unknown error"))
                            else:
                                error_message = str(error_data)
                        except:
                            error_message = await response.text()
                            
                        logger.error(f"Deepgram TTS API error: {response.status} - {error_message}")
                        return {
                            "success": False,
                            "error": f"API request failed with status {response.status}",
                            "details": error_message
                        }
                        
        except Exception as e:
            logger.error(f"Exception in Deepgram TTS service: {str(e)}")
            stack_trace = traceback.format_exc()
            logger.error(f"Stack trace:\n{stack_trace}")
            
            return {
                "success": False,
                "error": f"Exception: {str(e)}",
                "details": traceback.format_exc()
            }
    
    def preprocess_text(self, text: str) -> str:
        """
        Basic text preprocessing for natural TTS.
        Deepgram handles most text normalization automatically.
        """
        if not text:
            return text
            
        # Basic text cleaning
        text = text.strip()
        
        # Handle common abbreviations
        text = re.sub(r'\bDr\.', 'Doctor', text)
        text = re.sub(r'\bMr\.', 'Mister', text)
        text = re.sub(r'\bMrs\.', 'Missus', text)
        text = re.sub(r'\bMs\.', 'Miss', text)
        text = re.sub(r'\betc\.', 'etcetera', text)
        text = re.sub(r'\be\.g\.', 'for example', text)
        text = re.sub(r'\bi\.e\.', 'that is', text)
        
        # Handle URLs
        text = re.sub(r'https?://(?:www\.)?([^/\s]+)(?:/[^\s]*)?', r'website \1', text)
        
        # Handle email addresses
        text = re.sub(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
                      r'\1 at \2', text)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def get_audio_mime_type(self, encoding: str) -> str:
        """Get the MIME type for an audio encoding."""
        mapping = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "linear16": "audio/wav",  # linear16 is typically WAV
            "flac": "audio/flac",
            "opus": "audio/opus",
            "aac": "audio/aac"
        }
        return mapping.get(encoding.lower(), "audio/mpeg")
    
    def get_recommended_voice(self, gender: Optional[str] = None, quality: str = "conversational") -> str:
        """
        Get recommended voice based on preferences.
        """
        # Filter by gender if specified
        matching_voices = self.voices
        if gender:
            matching_voices = {k: v for k, v in matching_voices.items() if v["gender"] == gender.upper()}
        
        # Filter by quality
        matching_voices = {k: v for k, v in matching_voices.items() if v.get("quality", "conversational") == quality}
        
        # Return first match or default
        if matching_voices:
            return list(matching_voices.keys())[0]
        else:
            return self.default_voice

# Create a singleton instance of the service
deepgram_tts_service = DeepgramTTSService()
