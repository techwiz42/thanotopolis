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
                config = DeepgramClientOptions(
                    api_key=settings.DEEPGRAM_API_KEY,
                    options={"keepalive": "true"}
                )
                self.client = DeepgramClient(config)
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
            source = FileSource(
                buffer=audio_data,
                mimetype=content_type
            )
            
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
            response = await self.client.listen.asyncprerecorded.v("1").transcribe_file(
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
            channels=channels
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
            # Create connection
            self.connection = self.client.listen.asynclive.v("1")
            
            # Set up event handlers
            self.connection.on(LiveTranscriptionEvents.Transcript, self._handle_transcript)
            self.connection.on(LiveTranscriptionEvents.Error, self._handle_error)
            self.connection.on(LiveTranscriptionEvents.Warning, self._handle_warning)
            self.connection.on(LiveTranscriptionEvents.Metadata, self._handle_metadata)
            
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
    
    def _handle_transcript(self, *args, **kwargs):
        """Handle transcript messages from Deepgram."""
        try:
            # Extract transcript data from the response
            if args:
                transcript_data = args[0]
                
                # Format the response
                formatted_data = {
                    "type": "transcript",
                    "channel_index": transcript_data.get("channel_index", 0),
                    "duration": transcript_data.get("duration", 0.0),
                    "start": transcript_data.get("start", 0.0),
                    "is_final": transcript_data.get("is_final", False),
                    "speech_final": transcript_data.get("speech_final", False),
                    "channel": transcript_data.get("channel", {}),
                    "metadata": transcript_data.get("metadata", {})
                }
                
                # Extract alternatives
                if (transcript_data.get("channel") and 
                    transcript_data["channel"].get("alternatives")):
                    
                    alternatives = transcript_data["channel"]["alternatives"]
                    if alternatives:
                        best_alternative = alternatives[0]
                        formatted_data.update({
                            "transcript": best_alternative.get("transcript", ""),
                            "confidence": best_alternative.get("confidence", 0.0),
                            "words": best_alternative.get("words", [])
                        })
                
                # Call the message handler
                self.on_message(formatted_data)
                
        except Exception as e:
            logger.error(f"Error handling transcript: {e}")
            if self.on_error:
                self.on_error(e)
    
    def _handle_error(self, *args, **kwargs):
        """Handle error messages from Deepgram."""
        try:
            error_data = args[0] if args else {"error": "Unknown error"}
            logger.error(f"Deepgram error: {error_data}")
            
            if self.on_error:
                self.on_error(Exception(f"Deepgram error: {error_data}"))
                
        except Exception as e:
            logger.error(f"Error handling Deepgram error: {e}")
    
    def _handle_warning(self, *args, **kwargs):
        """Handle warning messages from Deepgram."""
        try:
            warning_data = args[0] if args else {"warning": "Unknown warning"}
            logger.warning(f"Deepgram warning: {warning_data}")
        except Exception as e:
            logger.error(f"Error handling Deepgram warning: {e}")
    
    def _handle_metadata(self, *args, **kwargs):
        """Handle metadata messages from Deepgram."""
        try:
            metadata = args[0] if args else {}
            logger.debug(f"Deepgram metadata: {metadata}")
        except Exception as e:
            logger.error(f"Error handling Deepgram metadata: {e}")


# Singleton instance
deepgram_service = DeepgramService()
