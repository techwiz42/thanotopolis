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
        return bool(self.api_key and self.api_key != "NOT_SET")
    
    async def get_voices(self) -> Dict[str, Any]:
        """
        Get available voices from ElevenLabs.
        
        Returns:
            Dictionary containing available voices
        """
        if not self.is_available():
            raise RuntimeError("ElevenLabs service not available")
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds for API calls
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
            timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds for API calls
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
    
    def _split_text_smartly(self, text: str, max_chars: int) -> List[str]:
        """
        Split text into chunks at natural boundaries to prevent TTS cutoffs.
        
        Args:
            text: Text to split
            max_chars: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        remaining_text = text.strip()
        
        while remaining_text:
            if len(remaining_text) <= max_chars:
                if remaining_text.strip():  # Only add non-empty chunks
                    chunks.append(remaining_text.strip())
                break
            
            # Find the best split point
            chunk = remaining_text[:max_chars]
            best_split = -1
            
            # Priority 1: Look for sentence endings with proper spacing
            for i in range(len(chunk) - 1, max_chars // 3, -1):  # Don't split too early
                if chunk[i] in '.!?':
                    # Check for proper sentence ending (followed by space or end)
                    if i == len(chunk) - 1 or chunk[i + 1] in ' \n\t':
                        # Avoid common abbreviations
                        if not self._is_abbreviation(chunk, i):
                            best_split = i + 1
                            break
            
            # Priority 2: Special handling for number sequences (avoid splitting mid-sequence)
            if best_split == -1:
                # Check if we're in a number sequence like "1, 2, 3, 4..."
                import re
                number_pattern = r'\b\d+\s*,\s*\d+\b'
                if re.search(number_pattern, chunk):
                    # For number sequences, prefer longer chunks to avoid voice degradation
                    # Look for natural breaks after every 10-15 numbers
                    for i in range(len(chunk) - 1, max_chars // 2, -1):  # Allow longer chunks for numbers
                        if chunk[i] == ',' and i < len(chunk) - 1 and chunk[i + 1] == ' ':
                            # Check if this comma is after a number ending in 0 or 5 (good break points)
                            preceding_text = chunk[:i]
                            if re.search(r'\b[0-9]*[05]\s*$', preceding_text):
                                best_split = i + 1
                                break
                
                # Priority 2b: Regular clause boundaries (comma with space)
                if best_split == -1:
                    for i in range(len(chunk) - 1, max_chars // 3, -1):
                        if chunk[i] == ',' and i < len(chunk) - 1 and chunk[i + 1] == ' ':
                            best_split = i + 1
                            break
            
            # Priority 3: Look for paragraph breaks
            if best_split == -1:
                for i in range(len(chunk) - 1, max_chars // 3, -1):
                    if chunk[i] == '\n':
                        best_split = i + 1
                        break
            
            # Priority 4: Look for word boundaries (spaces)
            if best_split == -1:
                for i in range(len(chunk) - 1, max_chars // 3, -1):
                    if chunk[i] == ' ':
                        best_split = i + 1
                        break
            
            # Fallback: split at max_chars (should rarely happen)
            if best_split == -1:
                best_split = max_chars
            
            chunk_text = remaining_text[:best_split].strip()
            if chunk_text:  # Only add non-empty chunks
                chunks.append(chunk_text)
            
            remaining_text = remaining_text[best_split:].strip()
        
        return chunks
    
    def _is_abbreviation(self, text: str, period_index: int) -> bool:
        """Check if a period is part of a common abbreviation."""
        if period_index == 0:
            return False
        
        # Get the word before the period
        start = period_index - 1
        while start >= 0 and text[start] != ' ':
            start -= 1
        start += 1
        
        word_before = text[start:period_index].lower()
        
        # Common abbreviations that shouldn't end sentences
        abbreviations = {
            'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr',
            'vs', 'etc', 'inc', 'ltd', 'corp', 'co',
            'st', 'ave', 'blvd', 'rd', 'dept', 'govt',
            'min', 'max', 'no', 'vol', 'pg', 'pp',
            'a.m', 'p.m', 'am', 'pm', 'est', 'pst'
        }
        
        return word_before in abbreviations
    
    async def _synthesize_long_text(
        self,
        text: str,
        voice_id: str = None,
        model_id: str = None,
        voice_settings: Optional[Dict[str, float]] = None,
        output_format: str = None
    ) -> Dict[str, Any]:
        """
        Synthesize long text by splitting it into chunks and concatenating audio properly.
        
        Args:
            text: Long text to synthesize
            voice_id: Voice ID to use
            model_id: Model ID to use
            voice_settings: Voice settings
            output_format: Output audio format
            
        Returns:
            Dictionary containing concatenated audio data and metadata
        """
        import io
        import tempfile
        import os
        
        # Split text into manageable chunks
        chunks = self._split_text_smartly(text, 4000)
        logger.info(f"Splitting long text ({len(text)} chars) into {len(chunks)} chunks")
        
        # Synthesize each chunk and save to temporary files for proper concatenation
        temp_files = []
        try:
            for i, chunk in enumerate(chunks):
                logger.info(f"Synthesizing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
                
                # Synthesize this chunk (recursive call, but won't infinite loop due to size check)
                result = await self.synthesize_speech(
                    text=chunk,
                    voice_id=voice_id,
                    model_id=model_id,
                    voice_settings=voice_settings,
                    output_format=output_format
                )
                
                if not result["success"]:
                    logger.error(f"Failed to synthesize chunk {i+1}: {result['error']}")
                    return result
                
                # Save chunk to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.write(result["audio_data"])
                temp_file.close()
                temp_files.append(temp_file.name)
            
            # Use ffmpeg to properly concatenate MP3 files
            try:
                import subprocess
                output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                output_file.close()
                
                # Create file list for ffmpeg
                file_list = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
                for temp_file in temp_files:
                    file_list.write(f"file '{temp_file}'\n")
                file_list.close()
                
                # Concatenate using ffmpeg
                cmd = [
                    'ffmpeg', '-f', 'concat', '-safe', '0', '-i', file_list.name,
                    '-c', 'copy', output_file.name, '-y'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"ffmpeg concatenation failed: {result.stderr}")
                    # Fallback to simple byte concatenation (may have audio artifacts)
                    concatenated_audio = b''
                    for temp_file in temp_files:
                        with open(temp_file, 'rb') as f:
                            concatenated_audio += f.read()
                else:
                    # Read properly concatenated audio
                    with open(output_file.name, 'rb') as f:
                        concatenated_audio = f.read()
                
                # Clean up temporary files
                os.unlink(file_list.name)
                os.unlink(output_file.name)
                
            except (ImportError, FileNotFoundError):
                logger.warning("ffmpeg not available, using basic concatenation (may have audio artifacts)")
                # Fallback to simple byte concatenation
                concatenated_audio = b''
                for temp_file in temp_files:
                    with open(temp_file, 'rb') as f:
                        concatenated_audio += f.read()
            
            total_size = len(concatenated_audio)
            logger.info(f"Successfully synthesized long text: {len(text)} chars -> {total_size} bytes")
            
            return {
                "success": True,
                "audio_data": concatenated_audio,
                "content_type": "audio/mpeg",
                "text": text,
                "voice_id": voice_id or self.default_voice_id,
                "model_id": model_id or self.default_model,
                "output_format": output_format or self.default_output_format,
                "size_bytes": total_size,
                "chunks_processed": len(chunks)
            }
            
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
    
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
        
        # ElevenLabs has a character limit per request (typically ~5000 chars)
        # If text is too long, split it and concatenate the audio
        MAX_CHARS_PER_REQUEST = 4000  # Conservative limit
        
        if len(text) > MAX_CHARS_PER_REQUEST:
            return await self._synthesize_long_text(text, voice_id, model_id, voice_settings, output_format)
        
        # Use defaults if not provided
        voice_id = voice_id or self.default_voice_id
        model_id = model_id or self.default_model
        output_format = output_format or self.default_output_format
        
        # Default voice settings - optimized for natural speech flow and number sequences
        if voice_settings is None:
            voice_settings = {
                "stability": 0.75,  # Reduced from 0.95 - allows more natural flow for number sequences
                "similarity_boost": 0.75,  # Balanced for consistency without artifacts
                "style": 0.15,  # Small amount of style for natural speech rhythm
                "use_speaker_boost": False  # Disable speaker boost to prevent audio artifacts
            }
        
        try:
            # Set a longer timeout for TTS requests (especially for long text)
            timeout = aiohttp.ClientTimeout(total=120)  # 2 minutes
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
        
        # Default voice settings - optimized for natural speech flow and number sequences
        if voice_settings is None:
            voice_settings = {
                "stability": 0.75,  # Reduced from 0.95 - allows more natural flow for number sequences
                "similarity_boost": 0.75,  # Balanced for consistency without artifacts
                "style": 0.15,  # Small amount of style for natural speech rhythm
                "use_speaker_boost": False  # Disable speaker boost to prevent audio artifacts
            }
        
        try:
            # Set a longer timeout for TTS streaming requests
            timeout = aiohttp.ClientTimeout(total=180)  # 3 minutes for streaming
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
            timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds for API calls
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
            timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds for API calls
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
    
    async def generate_speech(
        self,
        text: str,
        voice_id: str = None,
        model_id: str = None,
        voice_settings: Optional[Dict[str, float]] = None,
        output_format: str = None
    ) -> Optional[bytes]:
        """
        Generate speech from text and return audio data.
        This method is used by the telephony WebSocket handler.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use (defaults to settings.ELEVENLABS_VOICE_ID)
            model_id: Model ID to use (defaults to settings.ELEVENLABS_MODEL)
            voice_settings: Voice settings (stability, similarity_boost, etc.)
            output_format: Output audio format
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:
            result = await self.synthesize_speech(
                text=text,
                voice_id=voice_id,
                model_id=model_id,
                voice_settings=voice_settings,
                output_format=output_format
            )
            
            if result.get("success"):
                return result.get("audio_data")
            else:
                logger.error(f"Failed to generate speech: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error in generate_speech: {e}")
            return None


# Singleton instance
elevenlabs_service = ElevenLabsService()
