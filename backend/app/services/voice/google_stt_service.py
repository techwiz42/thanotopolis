# app/services/voice/google_stt_service.py
import base64
import json
import logging
import os
import requests
import traceback
from typing import Dict, List, Optional, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

class GoogleSTTService:
    """Service for Google Speech-to-Text API integration."""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.base_url = "https://speech.googleapis.com/v1/speech:recognize"
        
        # List of supported encodings
        self.supported_encodings = [
            "LINEAR16", "FLAC", "MP3", "WEBM_OPUS", "OGG_OPUS", 
            "MULAW", "AMR", "AMR_WB", "SPEEX_WITH_HEADER_BYTE"
        ]
        
        # Dict of supported languages
        self.supported_languages = {
            "en-US": "English (United States)",
            "en-GB": "English (United Kingdom)",
            "en-AU": "English (Australia)",
            "en-IN": "English (India)",
            "fr-FR": "French (France)",
            "es-ES": "Spanish (Spain)",
            "es-US": "Spanish (United States)",
            "de-DE": "German (Germany)",
            "it-IT": "Italian (Italy)",
            "ja-JP": "Japanese (Japan)",
            "ko-KR": "Korean (South Korea)",
            "pt-BR": "Portuguese (Brazil)",
            "ru-RU": "Russian (Russia)",
            "zh-CN": "Chinese (Simplified, China)",
            "zh-TW": "Chinese (Traditional, Taiwan)"
        }
        
        logger.info(f"GoogleSTTService initialized. API key available: {bool(self.api_key)}")
    
    def _load_api_key(self) -> Optional[str]:
        """Load Google API key from environment."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        logger.info(f"Checking env vars for GOOGLE_API_KEY: {'Found' if api_key else 'Not found'}")
        
        # If not in env vars, try to load from .env file in the project root
        if not api_key and os.path.exists('/home/peter/agent_framework/backend/.env'):
            logger.info("Checking local .env file in project root")
            try:
                with open('/home/peter/agent_framework/backend/.env') as f:
                    for line in f:
                        if 'GOOGLE_API_KEY' in line:
                            api_key = line.strip().split('=')[1].strip('"')
                            logger.info("Found GOOGLE_API_KEY in project root .env file")
                            break
            except Exception as e:
                logger.error(f"Error loading Google API key from project .env file: {e}")
        
        # If not in project root, try to load from /etc/cyberiad/.env
        if not api_key and os.path.exists('/etc/cyberiad/.env'):
            logger.info("Checking /etc/cyberiad/.env file")
            try:
                with open('/etc/cyberiad/.env') as f:
                    for line in f:
                        if 'GOOGLE_API_KEY' in line:
                            api_key = line.strip().split('=')[1].strip('"')
                            logger.info("Found GOOGLE_API_KEY in /etc/cyberiad/.env file")
                            break
            except Exception as e:
                logger.error(f"Error loading Google API key from /etc/cyberiad/.env file: {e}")
        
        if not api_key:
            logger.error("Google API key not found in environment variables or .env files")
            return None
            
        # Mask the API key for logging
        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
        logger.info(f"Google API key successfully loaded: {masked_key}")
        return api_key
    
    def transcribe_audio(
        self,
        audio_content: bytes,
        language_code: str = "en-US",
        sample_rate_hertz: Optional[int] = None,
        encoding: str = "WEBM_OPUS",
        model: str = "default",
        enhanced: bool = True
    ) -> dict:
        """
        Transcribe audio using Google's Speech-to-Text API.
        
        Args:
            audio_content: Audio content bytes
            language_code: Language code (e.g., 'en-US')
            sample_rate_hertz: Sample rate in Hz (None to auto-detect, mainly for WebM files)
            encoding: Audio encoding (WEBM_OPUS, LINEAR16, etc.)
            model: Model to use (default, phone_call, video, etc.)
            enhanced: Whether to use enhanced model
            
        Returns:
            Dictionary with transcription results
        """
        if not self.api_key:
            logger.error("Cannot transcribe: Google API key not configured")
            return {"success": False, "error": "Google API key not configured"}
        
        try:
            # Ensure encoding is uppercase and valid first
            encoding = encoding.upper() if encoding else "LINEAR16"
            valid_encodings = ["LINEAR16", "FLAC", "MP3", "WEBM_OPUS", "OGG_OPUS", "MULAW", "AMR", "AMR_WB"]
            if encoding not in valid_encodings:
                logger.warning(f"Encoding {encoding} not in valid encodings: {valid_encodings}")
                encoding = "LINEAR16"  # Default to LINEAR16
                logger.info(f"Using fallback encoding: {encoding}")
            
            # SPECIAL CASE: For WebM/OPUS and OGG/OPUS encoding, always use 48000 Hz as it's the standard
            # This ensures compatibility regardless of what the client sends
            if encoding == "WEBM_OPUS" or encoding == "OGG_OPUS":
                logger.info(f"Forcing 48000 Hz sample rate for {encoding} encoding")
                sample_rate_hertz = 48000
            # For other formats, ensure it's a valid integer
            elif sample_rate_hertz is not None:
                try:
                    sample_rate_hertz = int(sample_rate_hertz)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid sample_rate_hertz: {sample_rate_hertz}, defaulting to 16000")
                    sample_rate_hertz = 16000
                
                # Google STT requires specific sample rates
                valid_sample_rates = [8000, 12000, 16000, 22050, 24000, 32000, 44100, 48000]
                if sample_rate_hertz not in valid_sample_rates:
                    logger.warning(f"Sample rate {sample_rate_hertz} not in valid rates: {valid_sample_rates}")
                    # Use closest valid rate
                    original_rate = sample_rate_hertz
                    sample_rate_hertz = min(valid_sample_rates, key=lambda x: abs(x - sample_rate_hertz))
                    logger.info(f"Adjusted sample rate from {original_rate} to {sample_rate_hertz} Hz")
            else:
                # For formats other than WebM/OPUS and OGG/OPUS that don't specify sample rate
                logger.info("No sample rate specified - will be extracted from audio header")
            
            logger.info(f"Transcribing audio: encoding={encoding}, sample_rate={sample_rate_hertz}Hz, language={language_code}")
            
            # Prepare request payload
            payload = {
                "config": {
                    "languageCode": language_code,
                    "encoding": encoding,
                    "model": model,
                    "useEnhanced": enhanced,
                    "enableAutomaticPunctuation": True,
                    # Add speech context hints to improve recognition
                    "speechContexts": [{
                        "phrases": ["question", "help", "information", "support", "problem", "issue"],
                        "boost": 10
                    }],
                    # Enable word-level timestamps
                    "enableWordTimeOffsets": True
                },
                "audio": {
                    "content": base64.b64encode(audio_content).decode("utf-8")
                }
            }
            
            # Only include sampleRateHertz if provided (don't include for WebM files)
            if sample_rate_hertz is not None:
                payload["config"]["sampleRateHertz"] = sample_rate_hertz
                
            # Log the config for debugging
            logger.debug(f"STT config: {json.dumps(payload['config'])}")
            
            # Construct API URL with key
            url = f"{self.base_url}?key={self.api_key}"
            
            # Make API request
            response = requests.post(url, json=payload)
            
            # Check for successful response
            if response.status_code == 200:
                response_json = response.json()
                
                logger.debug(f"STT response: {json.dumps(response_json)}")
                
                # Extract transcription result
                if "results" in response_json and response_json["results"]:
                    # Get the top alternative from the first result
                    first_result = response_json["results"][0]
                    if "alternatives" in first_result and first_result["alternatives"]:
                        top_alternative = first_result["alternatives"][0]
                        
                        transcript = top_alternative.get("transcript", "")
                        confidence = top_alternative.get("confidence", 0)
                        
                        return {
                            "success": True,
                            "transcript": transcript,
                            "confidence": confidence
                        }
                    else:
                        logger.warning("No alternatives found in response")
                elif "totalBilledTime" in response_json:
                    # This is a special case where Google STT returned a billable result
                    # but no transcription (likely no speech detected)
                    
                    # Add more detailed logging for debugging the chat widget issue
                    logger.info(f"No speech detected in audio from Google STT API")
                    logger.info(f"Raw response: {json.dumps(response_json)}")
                    
                    # Get the audio size for logging
                    audio_size = len(audio_content) if audio_content else 0
                    logger.info(f"Audio stats: {audio_size} bytes, encoding: {encoding}, sample_rate: {sample_rate_hertz}, model: {model}")
                    
                    # Log first few bytes even in info mode to help debug the anonymous chat issue
                    if audio_content and len(audio_content) > 0:
                        first_few_bytes = ', '.join([f'{b:02x}' for b in audio_content[:30]])
                        logger.info(f"First few bytes of audio with no speech: {first_few_bytes}")
                    
                    # Add information about the totalBilledTime to understand API behavior
                    billed_time = response_json.get("totalBilledTime", "unknown")
                    logger.info(f"Google STT billed time: {billed_time}")
                    
                    # IMPORTANT: Return success=True with empty transcript for no speech detected
                    # This is consistent with the behavior expected by the frontend
                    # and prevents errors from propagating to the UI
                    return {
                        "success": True,
                        "transcript": "",
                        "confidence": 0,
                        "message": "No speech detected",
                        "audio_info": {
                            "size_bytes": audio_size,
                            "encoding": encoding,
                            "sample_rate": sample_rate_hertz,
                            "billed_time": billed_time
                        }
                    }
                else:
                    logger.warning(f"No results found in response: {json.dumps(response_json)}")
                
                return {
                    "success": False,
                    "error": "No transcription result",
                    "details": "The API processed the audio but did not return any transcription"
                }
            else:
                error_message = "Unknown error"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_message = error_data["error"].get("message", "Unknown error")
                        logger.error(f"Google STT API error: {response.status_code} - {json.dumps(error_data)}")
                except:
                    error_message = response.text
                    
                logger.error(f"Google STT API error: {response.status_code} - {error_message}")
                
                stack_trace = traceback.format_stack()
                logger.error(f"Stack trace:\n{''.join(stack_trace)}")
                
                return {
                    "success": False,
                    "error": f"API request failed with status {response.status_code}",
                    "details": error_message
                }
                
        except Exception as e:
            logger.error(f"Exception in Google STT service: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error": f"Exception: {str(e)}",
                "details": traceback.format_exc()
            }
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get a list of supported languages."""
        return [
            {"code": code, "name": name} 
            for code, name in self.supported_languages.items()
        ]
    
    def get_supported_encodings(self) -> List[str]:
        """Get a list of supported audio encodings."""
        return self.supported_encodings

# Create a singleton instance of the service
stt_service = GoogleSTTService()
