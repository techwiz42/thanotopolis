# app/services/voice/google_tts_service.py - Updated to use GOOGLE_CLIENT_ID

import base64
import logging
import os
import requests
import traceback
import json
import re
import random
from typing import Optional, Dict, Any, List, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

class GoogleTTSService:
    """Enhanced Google Text-to-Speech service with natural voice processing."""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.base_url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        logger.info(f"GoogleTTSService initialized. API key available: {bool(self.api_key)}")
        
        # Define available voices - prioritizing Studio and Neural2 for naturalness
        self.voices = {
            # Studio voices - most natural sounding
            "en-US-Studio-O": {"gender": "FEMALE", "name": "en-US-Studio-O", "quality": "studio"},
            "en-US-Studio-M": {"gender": "MALE", "name": "en-US-Studio-M", "quality": "studio"},
            "en-US-Studio-Q": {"gender": "MALE", "name": "en-US-Studio-Q", "quality": "studio"},
            
            # Neural2 voices - very natural
            "en-US-Neural2-A": {"gender": "MALE", "name": "en-US-Neural2-A", "quality": "neural2"},
            "en-US-Neural2-C": {"gender": "FEMALE", "name": "en-US-Neural2-C", "quality": "neural2"},
            "en-US-Neural2-D": {"gender": "MALE", "name": "en-US-Neural2-D", "quality": "neural2"},
            "en-US-Neural2-E": {"gender": "FEMALE", "name": "en-US-Neural2-E", "quality": "neural2"},
            "en-US-Neural2-F": {"gender": "FEMALE", "name": "en-US-Neural2-F", "quality": "neural2"},
            "en-US-Neural2-G": {"gender": "FEMALE", "name": "en-US-Neural2-G", "quality": "neural2"},
            "en-US-Neural2-H": {"gender": "FEMALE", "name": "en-US-Neural2-H", "quality": "neural2"},
            "en-US-Neural2-I": {"gender": "MALE", "name": "en-US-Neural2-I", "quality": "neural2"},
            "en-US-Neural2-J": {"gender": "MALE", "name": "en-US-Neural2-J", "quality": "neural2"},
            
            # British voices for variety
            "en-GB-Neural2-A": {"gender": "FEMALE", "name": "en-GB-Neural2-A", "quality": "neural2"},
            "en-GB-Neural2-B": {"gender": "MALE", "name": "en-GB-Neural2-B", "quality": "neural2"},
            "en-GB-Neural2-C": {"gender": "FEMALE", "name": "en-GB-Neural2-C", "quality": "neural2"},
            "en-GB-Neural2-D": {"gender": "MALE", "name": "en-GB-Neural2-D", "quality": "neural2"},
            
            # Standard voices (kept for compatibility)
            "en-US-Standard-E": {"gender": "FEMALE", "name": "en-US-Standard-E", "quality": "standard"},
        }
        
        # Default to the most natural female Studio voice
        self.default_voice = "en-US-Studio-O"
        
    def _load_api_key(self) -> Optional[str]:
        """Load Google API key from settings or environment."""
        # Try settings first (priority order: GOOGLE_CLIENT_ID, then GOOGLE_API_KEY for backward compatibility)
        try:
            api_key = getattr(settings, 'GOOGLE_CLIENT_ID', None)
            if api_key:
                logger.info("Found GOOGLE_CLIENT_ID in settings")
                masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
                logger.info(f"Google Client ID successfully loaded from settings: {masked_key}")
                return api_key
            
        except AttributeError:
            logger.info("Settings not available, checking environment variables")
        
        # Check environment variables
        api_key = os.environ.get("GOOGLE_CLIENT_ID")
        if api_key:
            logger.info("Found GOOGLE_CLIENT_ID in environment variables")
            masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
            logger.info(f"Google Client ID successfully loaded from environment: {masked_key}")
            return api_key
        
        # If not in env vars, try to load from .env file in the project root
        env_file_paths = [
            '/home/peter/agent_framework/backend/.env',
            '/etc/cyberiad/.env'
        ]
        
        for env_file_path in env_file_paths:
            if os.path.exists(env_file_path):
                logger.info(f"Checking {env_file_path} file")
                try:
                    with open(env_file_path) as f:
                        for line in f:
                            if 'GOOGLE_CLIENT_ID' in line:
                                api_key = line.strip().split('=')[1].strip('"')
                                logger.info(f"Found GOOGLE_CLIENT_ID in {env_file_path} file")
                                masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
                                logger.info(f"Google Client ID successfully loaded: {masked_key}")
                                return api_key
                except Exception as e:
                    logger.error(f"Error loading Google client ID key from {env_file_path} file: {e}")
        
        logger.error("Google Client ID not found in settings, environment variables, or .env files")
        logger.error("Please set GOOGLE_CLIENT_ID in your settings or environment variables")
        return None
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get a list of available voices sorted by quality."""
        voices = []
        for voice_id, details in self.voices.items():
            voices.append({
                "id": voice_id, 
                "name": voice_id, 
                "gender": details["gender"],
                "quality": details.get("quality", "standard")
            })
        # Sort by quality: studio > neural2 > standard
        quality_order = {"studio": 0, "neural2": 1, "standard": 2}
        return sorted(voices, key=lambda x: quality_order.get(x["quality"], 3))
    
    def synthesize_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        language_code: str = "en-US",
        speaking_rate: float = 0.95,
        pitch: float = -1.0,
        volume_gain_db: float = 1.0,
        audio_encoding: str = "MP3",
        preprocess_text: bool = True
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text using Google's Text-to-Speech API.
        """
        if not self.api_key:
            logger.error("Cannot synthesize: Google API key/client ID not configured")
            return {"success": False, "error": "Google API key/client ID not configured"}
        
        # Validate and select voice
        selected_voice = voice_id if voice_id and voice_id in self.voices else self.default_voice
        
        try:
            # Process text if requested
            processed_text = text
            if preprocess_text:
                processed_text = self.preprocess_text(text, enhance=True)
                input_type = "ssml"
            else:
                input_type = "text"
            
            # Prepare request payload
            payload = {
                "input": {
                    input_type: processed_text
                },
                "voice": {
                    "languageCode": language_code,
                    "name": selected_voice
                },
                "audioConfig": {
                    "audioEncoding": audio_encoding,
                    "speakingRate": speaking_rate,
                    "pitch": pitch,
                    "volumeGainDb": volume_gain_db,
                    "effectsProfileId": ["headphone-class-device"]
                }
            }
            
            # Construct API URL with key
            url = f"{self.base_url}?key={self.api_key}"
            
            logger.info(f"Sending TTS request: Voice: {selected_voice}, Preprocessing: {preprocess_text}")
            
            # Make API request
            response = requests.post(url, json=payload)
            
            # Check for successful response
            if response.status_code == 200:
                response_json = response.json()
                
                # Extract audio content
                if "audioContent" in response_json:
                    audio_content_base64 = response_json["audioContent"]
                    audio_bytes = base64.b64decode(audio_content_base64)
                    
                    return {
                        "success": True,
                        "audio": audio_bytes,
                        "encoding": audio_encoding.lower(),
                        "voice_id": selected_voice,
                        "voice_quality": self.voices[selected_voice].get("quality", "standard"),
                        "preprocessed": preprocess_text
                    }
                else:
                    logger.warning("Google TTS response missing audioContent")
                    return {
                        "success": False,
                        "error": "Missing audio content in response",
                        "details": "The API response did not contain audio content"
                    }
            else:
                error_message = "Unknown error"
                try:
                    error_data = response.json()
                    if "error" in error_data and "message" in error_data["error"]:
                        error_message = error_data["error"]["message"]
                except:
                    error_message = response.text
                    
                logger.error(f"Google TTS API error: {response.status_code} - {error_message}")
                return {
                    "success": False,
                    "error": f"API request failed with status {response.status_code}",
                    "details": error_message
                }
                    
        except Exception as e:
            logger.error(f"Exception in Google TTS service: {str(e)}")
            stack_trace = traceback.format_exc()
            logger.error(f"Stack trace:\n{stack_trace}")
            
            return {
                "success": False,
                "error": f"Exception: {str(e)}",
                "details": traceback.format_exc()
            }
    
    def escape_for_ssml(self, text: str) -> str:
        """Escape special characters for SSML."""
        # Escape XML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        
        # Replace smart quotes and em dashes with standard versions
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('—', '--')  # Replace em dash with double hyphen
        
        return text
    
    def preprocess_text(self, text: str, enhance: bool = True) -> str:
        """
        Comprehensive text preprocessing for natural TTS.
        """
        # Skip if already SSML
        if text.startswith('<speak>'):
            return text
        
        # Escape special characters for SSML
        text = self.escape_for_ssml(text)
        
        if enhance:
            # Handle special content
            text = self.handle_special_content(text)
            
            # Add contextual emphasis
            text = self.add_contextual_emphasis(text)
            
            # Add natural variations
            text = self.add_natural_variations(text)
        
        # Add basic pauses and formatting
        text = re.sub(r'([.!?])(?![<])\s+', r'\1<break time="700ms"/>', text)
        text = re.sub(r'([;:])(?![<])\s+', r'\1<break time="400ms"/>', text)
        text = re.sub(r',(?![<])\s+', r',<break time="150ms"/>', text)
        
        # Clean up any double breaks or excessive spaces
        text = re.sub(r'(<break[^>]*/>)\s*\1', r'\1', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s*(<break[^>]*/>)\s*', r'\1', text)
        
        # Wrap in speak tags
        return f'<speak>{text.strip()}</speak>'
    
    def handle_special_content(self, text: str) -> str:
        """Handle special content like numbers, dates, URLs, etc."""
        # Convert URLs to spoken form
        text = re.sub(r'https?://(?:www\.)?([^/\s]+)(?:/[^\s]*)?', r'website \1', text)
        
        # Handle email addresses
        text = re.sub(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
                      r'\1 at \2', text)
        
        # Handle percentages
        text = re.sub(r'(\d+(?:\.\d+)?)\s*%', 
                      r'<say-as interpret-as="cardinal">\1</say-as> percent', text)
        
        # Handle all-caps words (acronyms)
        text = re.sub(r'\b([A-Z]{2,})\b(?![</])', 
                      r'<say-as interpret-as="characters">\1</say-as>', text)
        
        return text
    
    def add_contextual_emphasis(self, text: str) -> str:
        """Add emphasis based on context and sentence structure."""
        # Emphasize words after intensifiers
        text = re.sub(r'\b(very|really|extremely|quite|rather|absolutely|completely|totally)\s+(\w+)', 
                      r'\1 <emphasis level="strong">\2</emphasis>', text, flags=re.IGNORECASE)
        
        # Add emphasis to contrasting conjunctions with breaks
        text = re.sub(r'\s+(but|however|although|yet|nevertheless|nonetheless)\s+', 
                      r' <break time="200ms"/><emphasis level="moderate">\1</emphasis> ', text, flags=re.IGNORECASE)
        
        return text
    
    def add_natural_variations(self, text: str) -> str:
        """Add subtle prosody variations to make speech less monotone."""
        # Split into sentences while preserving delimiters
        sentences = re.split(r'(?<=[.!?])(?![^(]*\))(?:\s+|$)', text)
        processed_sentences = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                processed_sentences.append(sentence)
                continue
            
            # Apply different prosody patterns based on sentence position and content
            if i == 0:  # First sentence - slightly slower and lower
                sentence = f'<prosody rate="95%" pitch="-5%">{sentence}</prosody>'
            elif '?' in sentence and sentence.endswith('?'):  # Questions
                sentence = f'<prosody pitch="+5%" rate="98%">{sentence}</prosody>'
            elif len(sentence) > 100:  # Long sentences
                sentence = f'<prosody rate="102%">{sentence}</prosody>'
            elif i % 3 == 0 and i > 0:  # Every third sentence
                if random.random() > 0.5:
                    sentence = f'<prosody pitch="-3%" rate="97%">{sentence}</prosody>'
                else:
                    sentence = f'<prosody pitch="+2%" rate="98%">{sentence}</prosody>'
            
            processed_sentences.append(sentence)
        
        return ' '.join(s for s in processed_sentences if s)
    
    def get_audio_mime_type(self, encoding: str) -> str:
        """Get the MIME type for an audio encoding."""
        mapping = {
            "mp3": "audio/mpeg",
            "linear16": "audio/wav",
            "ogg_opus": "audio/ogg",
            "mulaw": "audio/basic",
            "alaw": "audio/alaw"
        }
        return mapping.get(encoding.lower(), "audio/mpeg")
    
    def get_recommended_voice(self, gender: Optional[str] = None, accent: str = "US") -> str:
        """
        Get recommended voice based on preferences.
        """
        # Filter by accent
        accent_prefix = f"en-{accent}-"
        matching_voices = {k: v for k, v in self.voices.items() if k.startswith(accent_prefix)}
        
        # Filter by gender if specified
        if gender:
            matching_voices = {k: v for k, v in matching_voices.items() if v["gender"] == gender.upper()}
        
        # Sort by quality (studio > neural2 > standard)
        quality_priority = {"studio": 0, "neural2": 1, "standard": 2}
        sorted_voices = sorted(
            matching_voices.items(), 
            key=lambda x: quality_priority.get(x[1].get("quality", "standard"), 3)
        )
        
        # Return the highest quality match, or default if no matches
        return sorted_voices[0][0] if sorted_voices else self.default_voice

# Create a singleton instance of the service
tts_service = GoogleTTSService()
