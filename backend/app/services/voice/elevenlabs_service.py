# services/voice/elevenlabs_service.py
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
import aiohttp
import json
from app.core.config import settings

logger = logging.getLogger(__name__)


class ElevenLabsService:
    """Service for handling Text-to-Speech using ElevenLabs."""
    
    def __init__(self):
        """Initialize ElevenLabs service."""
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Default settings
        self.default_voice_id = settings.ELEVENLABS_VOICE_ID
        self.default_model = settings.ELEVENLABS_MODEL
        self.default_output_format = settings.ELEVENLABS_OUTPUT_FORMAT
        self.optimize_streaming_latency = settings.ELEVENLABS_OPTIMIZE_STREAMING_LATENCY
        
        if not self.api_key or self.api_key == "NOT_SET":
            logger.warning("ElevenLabs API key not configured")
    
    def is_available(self) -> bool:
        """Check if ElevenLabs service is available."""
        return self.api_key and self.api_key != "NOT_SET"
    
    async def get_voices(self) -> Dict[str, Any]:
        """
        Get available voices from ElevenLabs.
        
        Returns:
            Dictionary containing available voices
        """
        if not self.is_available():
            raise RuntimeError("ElevenLabs service not available")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "xi-api-key": self.api_key
                }
                
                async with session.get(f"{self.base_url}/voices", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Retrieved {len(data.get('voices', []))} voices")
                        return {
                            "success": True,
                            "voices": data.get("voices", [])
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get voices: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API error: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"Error getting voices: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_voice_info(self, voice_id: str) -> Dict[str, Any]:
        """
        Get information about a specific voice.
        
        Args:
            voice_id: The ID of the voice to get info for
            
        Returns:
            Dictionary containing voice information
        """
        if not self.is_available():
            raise RuntimeError("ElevenLabs service not available")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "xi-api-key": self.api_key
                }
                
                async with session.get(f"{self.base_url}/voices/{voice_id}", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "voice": data
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get voice info: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API error: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"Error getting voice info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def synthesize_speech(
        self,
        text: str,
        voice_id: str = None,
        model_id: str = None,
        voice_settings: Optional[Dict[str, float]] = None,
        output_format: str = None
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use (defaults to settings.ELEVENLABS_VOICE_ID)
            model_id: Model ID to use (defaults to settings.ELEVENLABS_MODEL)
            voice_settings: Voice settings (stability, similarity_boost, etc.)
            output_format: Output audio format
            
        Returns:
            Dictionary containing audio data and metadata
        """
        if not self.is_available():
            raise RuntimeError("ElevenLabs service not available")
        
        # Use defaults if not provided
        voice_id = voice_id or self.default_voice_id
        model_id = model_id or self.default_model
        output_format = output_format or self.default_output_format
        
        # Default voice settings - James with lower stability
        if voice_settings is None:
            voice_settings = {
                "stability": 0.25,  # Lower stability for more variation
                "similarity_boost": 0.4,  # Lower to reduce nasal quality
                "style": 0.1,  # Minimal emotional expression for cleaner sound
                "use_speaker_boost": True,
                "speed": 1.05  # 5% speed increase
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": f"audio/{output_format.split('_')[0]}",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key
                }
                
                data = {
                    "text": text,
                    "model_id": model_id,
                    "voice_settings": voice_settings
                }
                
                # Add output format to URL params
                params = {
                    "output_format": output_format,
                    "optimize_streaming_latency": self.optimize_streaming_latency
                }
                
                url = f"{self.base_url}/text-to-speech/{voice_id}"
                
                logger.info(f"Making TTS request to {url} with voice_id={voice_id}, model={model_id}")
                async with session.post(url, headers=headers, json=data, params=params) as response:
                    logger.info(f"TTS response status: {response.status}")
                    
                    if response.status == 200:
                        audio_data = await response.read()
                        
                        # Get content type from response
                        content_type = response.headers.get('content-type', 'audio/mpeg')
                        
                        logger.info(f"Successfully synthesized {len(text)} characters to {len(audio_data)} bytes")
                        
                        return {
                            "success": True,
                            "audio_data": audio_data,
                            "content_type": content_type,
                            "text": text,
                            "voice_id": voice_id,
                            "model_id": model_id,
                            "output_format": output_format,
                            "size_bytes": len(audio_data)
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"TTS API failed: {response.status} - {error_text}")
                        logger.error(f"Request headers: {headers}")
                        logger.error(f"Request data: {data}")
                        logger.error(f"Request params: {params}")
                        return {
                            "success": False,
                            "error": f"API error: {response.status} - {error_text}"
                        }
                        
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stream_speech(
        self,
        text: str,
        voice_id: str = None,
        model_id: str = None,
        voice_settings: Optional[Dict[str, float]] = None,
        output_format: str = None,
        chunk_size: int = 1024
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream speech synthesis from text.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            model_id: Model ID to use
            voice_settings: Voice settings
            output_format: Output audio format
            chunk_size: Size of audio chunks to yield
            
        Yields:
            Audio data chunks
        """
        if not self.is_available():
            raise RuntimeError("ElevenLabs service not available")
        
        # Use defaults if not provided
        voice_id = voice_id or self.default_voice_id
        model_id = model_id or self.default_model
        output_format = output_format or self.default_output_format
        
        # Default voice settings - James with lower stability
        if voice_settings is None:
            voice_settings = {
                "stability": 0.25,  # Lower stability for more variation
                "similarity_boost": 0.4,  # Lower to reduce nasal quality
                "style": 0.1,  # Minimal emotional expression for cleaner sound
                "use_speaker_boost": True,
                "speed": 1.05  # 5% speed increase
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": f"audio/{output_format.split('_')[0]}",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key
                }
                
                data = {
                    "text": text,
                    "model_id": model_id,
                    "voice_settings": voice_settings
                }
                
                # Add streaming parameters
                params = {
                    "output_format": output_format,
                    "optimize_streaming_latency": self.optimize_streaming_latency
                }
                
                url = f"{self.base_url}/text-to-speech/{voice_id}/stream"
                
                async with session.post(url, headers=headers, json=data, params=params) as response:
                    if response.status == 200:
                        logger.info(f"Starting speech streaming for {len(text)} characters")
                        
                        # Stream the response
                        async for chunk in response.content.iter_chunked(chunk_size):
                            if chunk:
                                yield chunk
                                
                        logger.info("Speech streaming completed")
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to stream speech: {response.status} - {error_text}")
                        raise RuntimeError(f"API error: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error streaming speech: {e}")
            raise
    
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get user subscription information.
        
        Returns:
            Dictionary containing user info and usage
        """
        if not self.is_available():
            raise RuntimeError("ElevenLabs service not available")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "xi-api-key": self.api_key
                }
                
                async with session.get(f"{self.base_url}/user", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "user_info": data
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get user info: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API error: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_models(self) -> Dict[str, Any]:
        """
        Get available models from ElevenLabs.
        
        Returns:
            Dictionary containing available models
        """
        if not self.is_available():
            raise RuntimeError("ElevenLabs service not available")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "xi-api-key": self.api_key
                }
                
                async with session.get(f"{self.base_url}/models", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "models": data
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get models: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API error: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
elevenlabs_service = ElevenLabsService()
