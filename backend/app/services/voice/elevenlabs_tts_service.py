# app/services/voice/elevenlabs_tts_service.py
import aiohttp
import asyncio
import logging
import os
import traceback
import json
import re
from typing import Optional, Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)

class ElevenLabsTTSService:
    """ElevenLabs Text-to-Speech service with natural voice processing."""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.base_url = "https://api.elevenlabs.io/v1"
        logger.info(f"ElevenLabsTTSService initialized. API key available: {bool(self.api_key)}")
        
        # Define available voices - ElevenLabs premium voices
        self.voices = {
            # Female voices
            "21m00Tcm4TlvDq8ikWAM": {"gender": "FEMALE", "name": "Rachel", "quality": "conversational", "language": "en"},
            "AZnzlk1XvdvUeBnXmlld": {"gender": "FEMALE", "name": "Domi", "quality": "conversational", "language": "en"},
            "EXAVITQu4vr4xnSDxMaL": {"gender": "FEMALE", "name": "Bella", "quality": "conversational", "language": "en"},
            "MF3mGyEYCl7XYWbV9V6O": {"gender": "FEMALE", "name": "Elli", "quality": "conversational", "language": "en"},
            "TxGEqnHWrfWFTfGW9XjX": {"gender": "FEMALE", "name": "Josh", "quality": "conversational", "language": "en"},
            "pNInz6obpgDQGcFmaJgB": {"gender": "FEMALE", "name": "Adam", "quality": "conversational", "language": "en"},
            "XrExE9yKIg1WjnnlVkGX": {"gender": "FEMALE", "name": "Matilda", "quality": "conversational", "language": "en"},
            
            # Male voices  
            "2EiwWnXFnvU5JabPnv8n": {"gender": "MALE", "name": "Clyde", "quality": "conversational", "language": "en"},
            "5Q0t7uMcjvnagumLfvZi": {"gender": "MALE", "name": "Thomas", "quality": "conversational", "language": "en"},
            "29vD33N1CtxCmqQRPOHJ": {"gender": "MALE", "name": "Drew", "quality": "conversational", "language": "en"},
            "D38z5RcWu1voky8WS1ja": {"gender": "MALE", "name": "Ethan", "quality": "conversational", "language": "en"},
            "IKne3meq5aSn9XLyUdCD": {"gender": "MALE", "name": "Paul", "quality": "conversational", "language": "en"},
            "JBFqnCBsd6RMkjVDRZzb": {"gender": "MALE", "name": "George", "quality": "conversational", "language": "en"},
            "N2lVS1w4EtoT3dr4eOWO": {"gender": "MALE", "name": "Callum", "quality": "conversational", "language": "en"},
            "VR6AewLTigWG4xSOukaG": {"gender": "MALE", "name": "Arnold", "quality": "conversational", "language": "en"},
            "yoZ06aMxZJJ28mfd3POQ": {"gender": "MALE", "name": "Sam", "quality": "conversational", "language": "en"},
            
            # Premium voices
            "ErXwobaYiN019PkySvjV": {"gender": "MALE", "name": "Antoni", "quality": "premium", "language": "en"},
            "VR6AewLTigWG4xSOukaG": {"gender": "MALE", "name": "Arnold", "quality": "premium", "language": "en"},
        }
        
        # Default to a high-quality female voice (Rachel)
        self.default_voice = "21m00Tcm4TlvDq8ikWAM"
        
    def _load_api_key(self) -> Optional[str]:
        """Load ElevenLabs API key from settings or environment."""
        try:
            # Try settings first
            api_key = getattr(settings, 'ELEVENLABS_API_KEY', None)
            if api_key and api_key != "NOT_SET":
                logger.info("Found ELEVENLABS_API_KEY in settings")
                masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
                logger.info(f"ElevenLabs API key successfully loaded from settings: {masked_key}")
                return api_key
        except AttributeError:
            logger.info("Settings not available, checking environment variables")
        
        # Check environment variables
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if api_key and api_key != "NOT_SET":
            logger.info("Found ELEVENLABS_API_KEY in environment variables")
            masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
            logger.info(f"ElevenLabs API key successfully loaded from environment: {masked_key}")
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
                            if 'ELEVENLABS_API_KEY' in line and not line.strip().startswith('#'):
                                api_key = line.strip().split('=')[1].strip('"').strip("'")
                                if api_key and api_key != "NOT_SET":
                                    logger.info(f"Found ELEVENLABS_API_KEY in {env_file_path} file")
                                    masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
                                    logger.info(f"ElevenLabs API key successfully loaded: {masked_key}")
                                    return api_key
                except Exception as e:
                    logger.error(f"Error loading ElevenLabs API key from {env_file_path} file: {e}")
        
        logger.error("ElevenLabs API key not found in settings, environment variables, or .env files")
        logger.error("Please set ELEVENLABS_API_KEY in your settings or environment variables")
        return None
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get a list of available voices sorted by quality."""
        voices = []
        for voice_id, details in self.voices.items():
            voices.append({
                "id": voice_id, 
                "name": details["name"], 
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
        Synthesize speech from text using ElevenLabs TTS API.
        
        Note: ElevenLabs always returns MP3, so encoding parameter is maintained for API compatibility.
        """
        if not self.api_key:
            logger.error("Cannot synthesize: ElevenLabs API key not configured")
            return {"success": False, "error": "ElevenLabs API key not configured"}
        
        # Validate and select voice
        selected_voice = voice_id if voice_id and voice_id in self.voices else self.default_voice
        
        try:
            # Process text if requested
            processed_text = text
            if preprocess_text:
                processed_text = self.preprocess_text(text)
            
            # Prepare request payload for ElevenLabs
            payload = {
                "text": processed_text,
                "model_id": "eleven_multilingual_v2",  # Use the latest multilingual model
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.5,
                    "use_speaker_boost": True
                }
            }
            
            # Prepare headers
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            # Build URL
            url = f"{self.base_url}/text-to-speech/{selected_voice}"
            
            logger.info(f"Sending TTS request: Voice: {selected_voice} ({self.voices[selected_voice]['name']})")
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request payload: {payload}")
            
            # Make API request using aiohttp for async support
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        # Read the audio content
                        audio_content = await response.read()
                        
                        if audio_content:
                            return {
                                "success": True,
                                "audio": audio_content,
                                "encoding": "mp3",  # ElevenLabs always returns MP3
                                "voice_id": selected_voice,
                                "voice_quality": self.voices[selected_voice].get("quality", "conversational"),
                                "preprocessed": preprocess_text,
                                "sample_rate": None,  # ElevenLabs handles this automatically
                                "container": None,    # Not applicable for MP3
                                "voice_name": self.voices[selected_voice].get("name", "Unknown")
                            }
                        else:
                            logger.warning("ElevenLabs TTS response is empty")
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
                                error_message = error_data.get("detail", error_data.get("message", "Unknown error"))
                            else:
                                error_message = str(error_data)
                        except:
                            error_message = await response.text()
                            
                        logger.error(f"ElevenLabs TTS API error: {response.status} - {error_message}")
                        return {
                            "success": False,
                            "error": f"API request failed with status {response.status}",
                            "details": error_message
                        }
                        
        except Exception as e:
            logger.error(f"Exception in ElevenLabs TTS service: {str(e)}")
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
        ElevenLabs handles most text normalization automatically.
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
        # ElevenLabs always returns MP3, but maintain compatibility
        return "audio/mpeg"
    
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
elevenlabs_tts_service = ElevenLabsTTSService()
