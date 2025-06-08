# services/voice/deepgram_service.py
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional, Callable
import websockets
import aiofiles
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    PrerecordedOptions,
    FileSource
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class DeepgramService:
    """Service for handling Speech-to-Text using Deepgram."""
    
    def __init__(self):
        """Initialize Deepgram client."""
        if not settings.DEEPGRAM_API_KEY or settings.DEEPGRAM_API_KEY == "NOT_SET":
            logger.warning("Deepgram API key not configured")
            self.client = None
        else:
            try:
                # Simple client without extra options to avoid auth issues
                self.client = DeepgramClient(settings.DEEPGRAM_API_KEY)
                logger.info("Deepgram client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Deepgram client: {e}")
                self.client = None
    
    def is_available(self) -> bool:
        """Check if Deepgram service is available."""
        return self.client is not None
    
    async def transcribe_file(
        self,
        audio_data: bytes,
        content_type: str = "audio/wav",
        language: str = None,
        model: str = None,
        punctuate: bool = True,
        diarize: bool = False,
        smart_format: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using Deepgram.
        
        Args:
            audio_data: Raw audio file bytes
            content_type: MIME type of audio file
            language: Language code (defaults to settings.DEEPGRAM_LANGUAGE)
            model: Model to use (defaults to settings.DEEPGRAM_MODEL)
            punctuate: Whether to add punctuation
            diarize: Whether to identify speakers
            smart_format: Whether to apply smart formatting
            
        Returns:
            Dictionary containing transcription results
        """
        if not self.is_available():
            raise RuntimeError("Deepgram service not available")
        
        try:
            # Prepare audio source
            source = {
                "buffer": audio_data,
                "mimetype": content_type
            }
            
            # Configure options
            options = PrerecordedOptions(
                model=model or settings.DEEPGRAM_MODEL,
                language=language or settings.DEEPGRAM_LANGUAGE,
                punctuate=punctuate,
                diarize=diarize,
                smart_format=smart_format,
                utterances=True,
                paragraphs=True
            )
            
            # Send to Deepgram
            response = await self.client.listen.asyncrest.v("1").transcribe_file(
                source, options
            )
            
            # Extract transcription
            result = response.to_dict()
            
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
            
            # Extract main transcript
            if (result.get("results") and 
                result["results"].get("channels") and 
                len(result["results"]["channels"]) > 0):
                
                channel = result["results"]["channels"][0]
                
                if channel.get("alternatives") and len(channel["alternatives"]) > 0:
                    alternative = channel["alternatives"][0]
                    
                    formatted_result["transcript"] = alternative.get("transcript", "")
                    formatted_result["confidence"] = alternative.get("confidence", 0.0)
                    
                    # Extract words with timestamps
                    if alternative.get("words"):
                        formatted_result["words"] = [
                            {
                                "word": word.get("word", ""),
                                "start": word.get("start", 0.0),
                                "end": word.get("end", 0.0),
                                "confidence": word.get("confidence", 0.0),
                                "speaker": word.get("speaker")
                            }
                            for word in alternative["words"]
                        ]
                    
                    # Extract paragraphs
                    if alternative.get("paragraphs") and alternative["paragraphs"].get("paragraphs"):
                        formatted_result["paragraphs"] = [
                            {
                                "text": para.get("text", ""),
                                "start": para.get("start", 0.0),
                                "end": para.get("end", 0.0),
                                "speaker": para.get("speaker")
                            }
                            for para in alternative["paragraphs"]["paragraphs"]
                        ]
            
            # Extract speaker information if diarization was enabled
            if diarize and formatted_result["words"]:
                speakers = set(word.get("speaker") for word in formatted_result["words"] if word.get("speaker") is not None)
                formatted_result["speakers"] = list(speakers)
            
            logger.info(f"Successfully transcribed audio: {len(formatted_result['transcript'])} characters")
            return formatted_result
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
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
        channels: int = 1
    ) -> 'LiveTranscriptionSession':
        """
        Start a live transcription session.
        
        Args:
            on_message: Callback function for transcript messages
            on_error: Optional callback function for errors
            language: Language code
            model: Model to use
            punctuate: Whether to add punctuation
            interim_results: Whether to return interim results
            smart_format: Whether to apply smart formatting
            encoding: Audio encoding
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            
        Returns:
            LiveTranscriptionSession object
        """
        if not self.is_available():
            raise RuntimeError("Deepgram service not available")
        
        options = LiveOptions(
            model=model or settings.DEEPGRAM_MODEL,
            language=language or settings.DEEPGRAM_LANGUAGE,
            punctuate=punctuate,
            interim_results=interim_results,
            smart_format=smart_format,
            encoding=encoding,
            sample_rate=sample_rate,
            channels=channels,
            utterance_end_ms=1000,  # End utterance after 1 second of silence
            vad_events=True,        # Enable voice activity detection events
            endpointing=True        # Enable endpointing to detect utterance boundaries
        )
        
        return LiveTranscriptionSession(
            self.client,
            options,
            on_message,
            on_error
        )


class LiveTranscriptionSession:
    """Handles a live transcription session with Deepgram."""
    
    def __init__(
        self,
        client: DeepgramClient,
        options: LiveOptions,
        on_message: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        self.client = client
        self.options = options
        self.on_message = on_message
        self.on_error = on_error
        self.connection = None
        self.is_connected = False
        
    async def start(self):
        """Start the live transcription session."""
        try:
            # Create connection using the new asyncwebsocket API
            self.connection = self.client.listen.asyncwebsocket.v("1")
            
            # Set up event handlers using async closure functions
            async def transcript_handler(self_ref, *args, **kwargs):
                # Check if transcript data is in kwargs
                if kwargs:
                    transcript_data = kwargs
                    await self._handle_transcript_data(transcript_data)
                elif args:
                    transcript_data = args[0]
                    await self._handle_transcript_data(transcript_data)
                else:
                    logger.warning("No args or kwargs in transcript_handler")
            
            async def error_handler(self_ref, *args, **kwargs):
                if args:
                    await self._handle_error_data(args[0])
                elif kwargs:
                    await self._handle_error_data(kwargs)
            
            self.connection.on(LiveTranscriptionEvents.Transcript, transcript_handler)
            self.connection.on(LiveTranscriptionEvents.Error, error_handler)
            
            # Start connection
            if await self.connection.start(self.options):
                self.is_connected = True
                logger.info("Live transcription session started")
            else:
                raise RuntimeError("Failed to start live transcription session")
                
        except Exception as e:
            logger.error(f"Error starting live transcription: {e}")
            if self.on_error:
                self.on_error(e)
            raise
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to the transcription session."""
        if not self.is_connected or not self.connection:
            raise RuntimeError("Transcription session not connected")
        
        try:
            await self.connection.send(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio data: {e}")
            if self.on_error:
                self.on_error(e)
            raise
    
    async def finish(self):
        """Finish the transcription session."""
        if self.connection and self.is_connected:
            try:
                await self.connection.finish()
                self.is_connected = False
                logger.info("Live transcription session finished")
            except Exception as e:
                logger.error(f"Error finishing transcription session: {e}")
                if self.on_error:
                    self.on_error(e)
    
    async def _handle_transcript_data(self, transcript_data):
        """Handle transcript data directly."""
        try:
            if not transcript_data:
                return
            
            # Extract the result from the kwargs structure
            if isinstance(transcript_data, dict) and 'result' in transcript_data:
                result = transcript_data['result']
                
                # Check if we can access the transcript from the result
                if hasattr(result, 'channel') and hasattr(result.channel, 'alternatives'):
                    alternatives = result.channel.alternatives
                    if alternatives and len(alternatives) > 0:
                        transcript_text = alternatives[0].transcript
                        confidence = alternatives[0].confidence
                        is_final = getattr(result, 'is_final', False)
                        
                        # Only process non-empty transcripts
                        if transcript_text and transcript_text.strip():
                            # Pass through raw Deepgram results - let frontend handle accumulation
                            speech_final = getattr(result, 'speech_final', False)
                            
                            # Convert words to serializable format
                            words_data = []
                            if hasattr(alternatives[0], 'words') and alternatives[0].words:
                                for word in alternatives[0].words:
                                    words_data.append({
                                        "word": getattr(word, 'word', ''),
                                        "start": getattr(word, 'start', 0.0),
                                        "end": getattr(word, 'end', 0.0),
                                        "confidence": getattr(word, 'confidence', 0.0),
                                        "punctuated_word": getattr(word, 'punctuated_word', ''),
                                        "speaker": getattr(word, 'speaker', None)
                                    })
                            
                            # Send raw transcript data - frontend will handle proper accumulation
                            formatted_data = {
                                "type": "transcript",
                                "transcript": transcript_text,  # Send raw transcript from Deepgram
                                "confidence": confidence,
                                "is_final": is_final,
                                "speech_final": speech_final,
                                "duration": getattr(result, 'duration', 0.0),
                                "start": getattr(result, 'start', 0.0),
                                "words": words_data
                            }
                            
                            self.on_message(formatted_data)
                        else:
                            logger.debug(f"Skipping empty transcript (is_final: {is_final})")
                    else:
                        logger.debug("No alternatives in transcript result")
                else:
                    logger.warning("Result does not have expected channel/alternatives structure")
            else:
                logger.warning(f"Unexpected transcript_data structure: {type(transcript_data)}")
                return
                
        except Exception as e:
            logger.error(f"Error handling transcript: {e}")
            if self.on_error:
                self.on_error(e)
    
    async def _handle_error_data(self, error_data):
        """Handle error data directly."""
        try:
            logger.error(f"Deepgram error: {error_data}")
            
            if self.on_error:
                self.on_error(Exception(f"Deepgram error: {error_data}"))
                
        except Exception as e:
            logger.error(f"Error handling Deepgram error: {e}")
    
    async def _handle_error(self, *args, **kwargs):
        """Handle error messages from Deepgram."""
        try:
            error_data = args[-1] if args else {"error": "Unknown error"}
            logger.error(f"Deepgram error: {error_data}")
            
            if self.on_error:
                self.on_error(Exception(f"Deepgram error: {error_data}"))
                
        except Exception as e:
            logger.error(f"Error handling Deepgram error: {e}")
    
    async def _handle_warning(self, *args, **kwargs):
        """Handle warning messages from Deepgram."""
        try:
            warning_data = args[-1] if args else {"warning": "Unknown warning"}
            logger.warning(f"Deepgram warning: {warning_data}")
        except Exception as e:
            logger.error(f"Error handling Deepgram warning: {e}")
    
    async def _handle_metadata(self, *args, **kwargs):
        """Handle metadata messages from Deepgram."""
        try:
            metadata = args[-1] if args else {}
            logger.debug(f"Deepgram metadata: {metadata}")
        except Exception as e:
            logger.error(f"Error handling Deepgram metadata: {e}")
    


# Singleton instance
deepgram_service = DeepgramService()
