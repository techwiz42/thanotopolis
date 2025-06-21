# services/voice/soniox_service.py
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional, Callable
import soniox.speech_service as speech_service
from soniox.speech_service_pb2 import TranscriptionConfig, Result, Word
from app.core.config import settings

logger = logging.getLogger(__name__)


class SonioxService:
    """Service for handling Speech-to-Text using Soniox."""
    
    def __init__(self):
        """Initialize Soniox client."""
        if not settings.SONIOX_API_KEY or settings.SONIOX_API_KEY == "NOT_SET":
            logger.warning("Soniox API key not configured")
            self.available = False
        else:
            try:
                # Set the API key for Soniox
                speech_service.set_api_key(settings.SONIOX_API_KEY)
                self.available = True
                logger.info("Soniox client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Soniox client: {e}")
                self.available = False
    
    def is_available(self) -> bool:
        """Check if Soniox service is available."""
        return self.available
    
    async def transcribe_file(
        self,
        audio_data: bytes,
        content_type: str = "audio/wav",
        language: str = None,
        model: str = None,
        punctuate: bool = True,
        diarize: bool = False,
        smart_format: bool = True,
        detect_language: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using Soniox.
        
        Args:
            audio_data: Raw audio file bytes
            content_type: MIME type of audio file
            language: Language code (Soniox uses auto-detection by default)
            model: Model to use (Soniox auto-selects best model)
            punctuate: Whether to add punctuation
            diarize: Whether to identify speakers
            smart_format: Whether to apply smart formatting
            detect_language: Whether to enable language detection
            
        Returns:
            Dictionary containing transcription results
        """
        if not self.is_available():
            raise RuntimeError("Soniox service not available")
        
        try:
            # Create configuration
            config = TranscriptionConfig()
            
            # Set basic audio parameters
            config.sample_rate_hertz = 16000
            config.num_audio_channels = 1
            
            # Enable features
            config.enable_profanity_filter = False
            config.enable_global_speaker_diarization = diarize
            config.enable_speaker_identification = diarize
            
            # Create client and transcribe
            client = speech_service.SpeechClient()
            result = client.transcribe(audio_data, config)
            
            # Format response
            formatted_result = {
                "success": True,
                "transcript": "",
                "confidence": 0.0,
                "words": [],
                "speakers": [],
                "paragraphs": [],
                "raw_response": result
            }
            
            # Extract transcript
            if result and result.words:
                transcript_parts = []
                word_data = []
                speakers = set()
                
                for word in result.words:
                    transcript_parts.append(word.text)
                    
                    word_info = {
                        "word": word.text,
                        "start": word.start_ms / 1000.0,  # Convert to seconds
                        "end": word.end_ms / 1000.0,
                        "confidence": getattr(word, 'confidence', 1.0),
                        "speaker": getattr(word, 'speaker', None)
                    }
                    word_data.append(word_info)
                    
                    if hasattr(word, 'speaker') and word.speaker is not None:
                        speakers.add(word.speaker)
                
                formatted_result["transcript"] = " ".join(transcript_parts)
                formatted_result["words"] = word_data
                formatted_result["speakers"] = list(speakers)
                
                # Calculate average confidence
                if word_data:
                    confidences = [w["confidence"] for w in word_data if w["confidence"] > 0]
                    if confidences:
                        formatted_result["confidence"] = sum(confidences) / len(confidences)
            
            logger.info(f"Successfully transcribed audio: {len(formatted_result['transcript'])} characters")
            return formatted_result
                
        except Exception as e:
            logger.error(f"Error transcribing audio with Soniox: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0,
                "words": [],
                "speakers": [],
                "paragraphs": []
            }
    
    async def start_live_transcription(
        self,
        on_message: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None,
        language: str = None,
        model: str = None,
        punctuate: bool = True,
        interim_results: bool = True,
        smart_format: bool = True,
        encoding: str = "linear16",
        sample_rate: int = 16000,
        channels: int = 1,
        detect_language: bool = False
    ) -> 'LiveTranscriptionSession':
        """
        Start a live transcription session.
        
        Args:
            on_message: Callback function for transcript messages
            on_error: Optional callback function for errors
            language: Language code (Soniox auto-detects by default)
            model: Model to use (Soniox auto-selects)
            punctuate: Whether to add punctuation
            interim_results: Whether to return interim results
            smart_format: Whether to apply smart formatting
            encoding: Audio encoding
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            detect_language: Whether to enable automatic language detection
            
        Returns:
            LiveTranscriptionSession object
        """
        if not self.is_available():
            raise RuntimeError("Soniox service not available")
        
        # Create transcript config
        config = TranscriptionConfig()
        config.sample_rate_hertz = sample_rate
        config.num_audio_channels = channels
        config.include_nonfinal = interim_results
        
        # Enable features
        config.enable_profanity_filter = False
        config.enable_streaming_speaker_diarization = False  # Can be expensive for streaming
        config.enable_global_speaker_diarization = False
        config.enable_speaker_identification = False
        
        return LiveTranscriptionSession(
            config,
            on_message,
            on_error
        )


class LiveTranscriptionSession:
    """Handles a live transcription session with Soniox."""
    
    def __init__(
        self,
        config: TranscriptionConfig,
        on_message: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        self.config = config
        self.on_message = on_message
        self.on_error = on_error
        self.client = None
        self.is_connected = False
        self._running = False
        self._audio_queue = asyncio.Queue()
        self._process_task = None
        
    async def start(self):
        """Start the live transcription session."""
        try:
            # Create client
            self.client = speech_service.SpeechClient()
            
            # Start processing audio
            self._running = True
            self.is_connected = True
            
            # Start background processing task
            self._process_task = asyncio.create_task(self._process_audio_stream())
            
            logger.info("Soniox live transcription session started successfully")
                
        except Exception as e:
            logger.error(f"Error starting Soniox live transcription: {e}")
            if self.on_error:
                self.on_error(e)
            raise
    
    async def _process_audio_stream(self):
        """Process audio stream and generate transcriptions."""
        audio_buffer = bytearray()
        chunk_size = 8192  # Process in 8KB chunks
        
        try:
            while self._running:
                try:
                    # Wait for audio data with timeout
                    audio_data = await asyncio.wait_for(
                        self._audio_queue.get(), 
                        timeout=1.0
                    )
                    
                    if audio_data is None:  # Stop signal
                        break
                        
                    audio_buffer.extend(audio_data)
                    
                    # Process when we have enough data
                    if len(audio_buffer) >= chunk_size:
                        await self._transcribe_chunk(bytes(audio_buffer))
                        audio_buffer.clear()
                        
                except asyncio.TimeoutError:
                    # Process any remaining data
                    if len(audio_buffer) > 0:
                        await self._transcribe_chunk(bytes(audio_buffer))
                        audio_buffer.clear()
                    continue
                    
        except Exception as e:
            logger.error(f"Error in Soniox audio stream processing: {e}")
            if self.on_error:
                self.on_error(e)
    
    async def _transcribe_chunk(self, audio_data: bytes):
        """Transcribe an audio chunk."""
        try:
            if not self.client or len(audio_data) < 1000:  # Skip tiny chunks
                return
                
            # Transcribe the chunk
            result = self.client.transcribe(audio_data, self.config)
            
            if result and result.words:
                await self._handle_result(result)
                
        except Exception as e:
            logger.error(f"Error transcribing Soniox chunk: {e}")
            # Don't propagate transcription errors to avoid stopping the stream
    
    async def _handle_result(self, result):
        """Handle a transcription result from Soniox."""
        try:
            if not result or not result.words:
                return
                
            # Extract transcript from words
            transcript_parts = []
            words_data = []
            
            for word in result.words:
                transcript_parts.append(word.text)
                words_data.append({
                    "word": word.text,
                    "start": word.start_ms / 1000.0,
                    "end": word.end_ms / 1000.0,
                    "confidence": getattr(word, 'confidence', 1.0),
                    "speaker": getattr(word, 'speaker', None)
                })
            
            transcript_text = " ".join(transcript_parts)
            
            if not transcript_text.strip():
                return
            
            # Soniox typically provides final results
            is_final = True
            
            # Calculate average confidence
            confidence = 1.0
            if words_data:
                confidences = [w["confidence"] for w in words_data if w["confidence"] > 0]
                if confidences:
                    confidence = sum(confidences) / len(confidences)
            
            # Soniox provides automatic language detection
            detected_language = "auto"  # Soniox handles this internally
            
            # Format response data
            formatted_data = {
                "type": "transcript",
                "transcript": transcript_text,
                "confidence": confidence,
                "is_final": is_final,
                "speech_final": is_final,  # For compatibility
                "words": words_data,
                "detected_language": detected_language
            }
            
            logger.debug(f"Soniox transcript: '{transcript_text}' (confidence: {confidence:.2f})")
            
            # Send to callback
            self.on_message(formatted_data)
                
        except Exception as e:
            logger.error(f"Error handling Soniox result: {e}")
            if self.on_error:
                self.on_error(e)
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to the transcription session."""
        if not self.is_connected:
            raise RuntimeError("Transcription session not connected")
        
        try:
            await self._audio_queue.put(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio data to Soniox: {e}")
            if self.on_error:
                self.on_error(e)
            raise
    
    async def finish(self):
        """Finish the transcription session."""
        if self._running:
            try:
                self._running = False
                
                # Send stop signal
                await self._audio_queue.put(None)
                
                # Wait for processing task to complete
                if self._process_task:
                    await asyncio.wait_for(self._process_task, timeout=5.0)
                
                self.is_connected = False
                logger.info("Soniox live transcription session finished")
            except Exception as e:
                logger.error(f"Error finishing Soniox transcription session: {e}")
                if self.on_error:
                    self.on_error(e)


# Singleton instance
soniox_service = SonioxService()