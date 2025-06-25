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


def map_language_code_to_deepgram(language: str) -> str:
    """
    Map standard locale codes to Deepgram's expected format.
    
    Deepgram uses simplified language codes:
    - 'en' or 'en-US' for English
    - 'fr' for French (not 'fr-FR')
    - 'fr-CA' for Canadian French
    - etc.
    """
    if not language:
        return None
    
    # Map common locale codes to Deepgram format
    language_mapping = {
        'fr-FR': 'fr',      # French (France) -> French
        'en-GB': 'en-GB',   # English (UK) stays as is
        'en-US': 'en-US',   # English (US) stays as is
        'es-ES': 'es',      # Spanish (Spain) -> Spanish
        'es-MX': 'es',      # Spanish (Mexico) -> Spanish
        'de-DE': 'de',      # German (Germany) -> German
        'de-CH': 'de-CH',   # German (Switzerland) -> German (Swiss)
        'it-IT': 'it',      # Italian (Italy) -> Italian
        'pt-PT': 'pt',      # Portuguese (Portugal) -> Portuguese
        'pt-BR': 'pt-BR',   # Portuguese (Brazil) stays as is
        'nl-NL': 'nl',      # Dutch (Netherlands) -> Dutch
        'ja-JP': 'ja',      # Japanese (Japan) -> Japanese
        'ko-KR': 'ko',      # Korean (Korea) -> Korean
        'zh-CN': 'zh-CN',   # Chinese (Simplified) stays as is
        'zh-TW': 'zh-TW',   # Chinese (Traditional) stays as is
        'ru-RU': 'ru',      # Russian (Russia) -> Russian
        'ar-SA': 'ar',      # Arabic (Saudi Arabia) -> Arabic
        'hi-IN': 'hi',      # Hindi (India) -> Hindi
        'sv-SE': 'sv',      # Swedish (Sweden) -> Swedish
        'da-DK': 'da',      # Danish (Denmark) -> Danish
        'fi-FI': 'fi',      # Finnish (Finland) -> Finnish
        'no-NO': 'no',      # Norwegian (Norway) -> Norwegian
        'pl-PL': 'pl',      # Polish (Poland) -> Polish
        'uk-UA': 'uk',      # Ukrainian (Ukraine) -> Ukrainian
        'tr-TR': 'tr',      # Turkish (Turkey) -> Turkish
        'id-ID': 'id',      # Indonesian (Indonesia) -> Indonesian
        'th-TH': 'th',      # Thai (Thailand) -> Thai
        'ms-MY': 'ms',      # Malay (Malaysia) -> Malay
        'vi-VN': 'vi',      # Vietnamese (Vietnam) -> Vietnamese
        'he-IL': 'he',      # Hebrew (Israel) -> Hebrew (note: not in Nova-2 docs)
        'el-GR': 'el',      # Greek (Greece) -> Greek
        'cs-CZ': 'cs',      # Czech (Czech Republic) -> Czech
        'sk-SK': 'sk',      # Slovak (Slovakia) -> Slovak
        'hu-HU': 'hu',      # Hungarian (Hungary) -> Hungarian
        'ro-RO': 'ro',      # Romanian (Romania) -> Romanian
    }
    
    # Return mapped value or original if not in mapping
    mapped = language_mapping.get(language, language)
    logger.debug(f"Language mapping: {language} -> {mapped}")
    return mapped


def get_compatible_model_for_language(language: str, requested_model: str) -> str:
    """
    Get a compatible model for the specified language.
    
    Nova-3 model has limited language support. For unsupported languages,
    fallback to nova-2 or base model.
    """
    if not language:
        return requested_model
    
    # Nova-3 supported languages (confirmed through testing and Deepgram docs)
    # Nova-3 has more limited language support compared to nova-2 and base models
    nova3_supported_languages = {
        'en', 'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-IN', 'en-NZ', 'en-ZA',  # English variants
        'es', 'es-ES',  # Spanish (confirmed)
        # Note: French (fr), German (de), and many other languages are NOT supported by nova-3
        # They work fine with nova-2 and base models
    }
    
    # If requesting nova-3 but language is not supported, fallback to nova-2
    if requested_model == 'nova-3' and language not in nova3_supported_languages:
        logger.warning(f"Nova-3 model does not support language '{language}', falling back to nova-2")
        return 'nova-2'
    
    return requested_model


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
        smart_format: bool = True,
        detect_language: bool = False
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
            
            # Determine the model to use
            requested_model = model or settings.DEEPGRAM_MODEL
            
            # Get mapped language first to check compatibility
            mapped_language = None
            if not detect_language and language:
                mapped_language = map_language_code_to_deepgram(language)
            elif not detect_language:
                mapped_language = map_language_code_to_deepgram(settings.DEEPGRAM_LANGUAGE)
            
            # Get compatible model for the language
            compatible_model = get_compatible_model_for_language(mapped_language, requested_model)
            
            # Configure options
            options = PrerecordedOptions(
                model=compatible_model,
                punctuate=punctuate,
                diarize=diarize,
                smart_format=smart_format,
                utterances=True,
                paragraphs=True
            )
            
            # Try to set detect_language if supported
            if detect_language:
                try:
                    options.detect_language = detect_language
                except AttributeError:
                    # If detect_language is not supported, just don't set a language
                    pass
            
            # Only set language if not detecting and language is provided
            if not detect_language and mapped_language:
                options.language = mapped_language
                logger.info(f"Using language: {language} -> {mapped_language} with model: {compatible_model}")
                
                # Log model fallback information if applicable
                if compatible_model != requested_model:
                    logger.info(f"Model changed from {requested_model} to {compatible_model} for language compatibility")
            
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
    
    async def transcribe_stream(
        self,
        audio_data: bytes,
        content_type: str = "audio/x-mulaw",
        language: str = None,
        model: str = None,
        sample_rate: int = 8000,
        channels: int = 1
    ) -> str:
        """
        Transcribe audio stream data using Deepgram.
        
        This is a simplified method for transcribing audio chunks from streaming sources
        like telephony. It returns just the transcript text.
        
        Args:
            audio_data: Raw audio bytes from stream
            content_type: MIME type of audio (defaults to mulaw for telephony)
            language: Language code (optional)
            model: Model to use (optional)
            
        Returns:
            Transcript text string or empty string if no transcript
        """
        if not self.is_available():
            raise RuntimeError("Deepgram service not available")
        
        try:
            logger.info(f"📞 Deepgram transcribe_stream: {len(audio_data)} bytes, content_type: {content_type}, sample_rate: {sample_rate}, channels: {channels}")
            
            # Prepare audio source with proper telephony format
            source = {
                "buffer": audio_data,
                "mimetype": content_type
            }
            
            # Determine the model to use
            requested_model = model or settings.DEEPGRAM_MODEL
            
            # For telephony, assume English to avoid auto-detection issues with small chunks
            mapped_language = "en-US"  # Default to US English for telephony
            if language:
                mapped_language = map_language_code_to_deepgram(language)
            
            # For telephony, use nova-2 model which has better speech detection
            compatible_model = "nova-2"  # nova-2 is more robust for telephony than base
            if requested_model and requested_model not in ["nova-2", "base"]:
                compatible_model = get_compatible_model_for_language(mapped_language, requested_model)
            
            # Configure options specifically for telephony audio (mulaw, 8kHz)
            options = PrerecordedOptions(
                model=compatible_model,
                language=mapped_language,  # Always specify language for telephony
                punctuate=True,
                diarize=False,
                smart_format=True,
                utterances=True,
                detect_language=False,  # Disable auto-detection for better performance
                # Telephony-specific options
                numerals=True,
                profanity_filter=False,
                redact=False
            )
            
            logger.debug(f"Using telephony language: {mapped_language} with model: {compatible_model}")
            
            # Send to Deepgram
            logger.debug(f"📞 Sending to Deepgram with options: model={compatible_model}, language={mapped_language}, detect_language={not mapped_language}")
            response = await self.client.listen.asyncrest.v("1").transcribe_file(
                source, options
            )
            
            # Extract transcription
            result = response.to_dict()
            
            # Extract transcript text
            if (result.get("results") and 
                result["results"].get("channels") and 
                len(result["results"]["channels"]) > 0):
                
                channel = result["results"]["channels"][0]
                
                if channel.get("alternatives") and len(channel["alternatives"]) > 0:
                    alternative = channel["alternatives"][0]
                    transcript = alternative.get("transcript", "")
                    confidence = alternative.get("confidence", 0.0)
                    
                    if transcript and transcript.strip():
                        logger.info(f"✅ Transcribed: '{transcript}' (confidence: {confidence:.2f})")
                        return transcript.strip()
                    else:
                        # Even low confidence might be useful for telephony
                        if confidence > 0.0:
                            logger.info(f"📞 Low confidence transcript: '{transcript}' (confidence: {confidence:.2f})")
                        else:
                            logger.debug(f"📞 Empty transcript, confidence: {confidence:.2f}")
                else:
                    logger.debug(f"📞 No alternatives in channel")
            else:
                logger.debug(f"📞 No results or channels in response")
            
            logger.debug("📞 Deepgram returned empty transcript")
            return ""
                
        except Exception as e:
            logger.error(f"Error transcribing stream: {e}")
            return ""
    
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
            language: Language code (None for auto-detection)
            model: Model to use
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
            raise RuntimeError("Deepgram service not available")
        
        # Determine the model to use
        requested_model = model or settings.DEEPGRAM_MODEL
        
        # Get mapped language first to check compatibility
        mapped_language = None
        if not detect_language and language:
            mapped_language = map_language_code_to_deepgram(language)
        elif not detect_language:
            mapped_language = map_language_code_to_deepgram(settings.DEEPGRAM_LANGUAGE)
        
        # Get compatible model for the language
        compatible_model = get_compatible_model_for_language(mapped_language, requested_model)
        
        options = LiveOptions(
            model=compatible_model,
            punctuate=punctuate,
            interim_results=interim_results,
            smart_format=smart_format,
            encoding=encoding,
            sample_rate=sample_rate,
            channels=channels,
            utterance_end_ms=1500,  # Increased to 1.5 seconds for better multilingual support
            vad_events=True,        # Enable voice activity detection events
            endpointing=True,       # Enable endpointing to detect utterance boundaries
            # Additional options for better multilingual stability
            no_delay=True,          # Reduce latency
            numerals=True,          # Better number handling across languages
            multichannel=False      # Ensure single channel processing
        )
        
        # For live transcription, language auto-detection is enabled by not setting a language
        # Only set language if explicitly provided and not auto-detecting
        if not detect_language and language:
            options.language = mapped_language
            logger.info(f"Using specified language: {language} -> {mapped_language} with model: {compatible_model}")
        elif not detect_language:
            options.language = mapped_language
            logger.info(f"Using default language: {settings.DEEPGRAM_LANGUAGE} -> {mapped_language} with model: {compatible_model}")
        else:
            # If detect_language=True, we don't set any language (enables auto-detection)
            logger.info(f"Language auto-detection enabled - no language specified with model: {compatible_model}")
        
        # Log the complete options being sent to Deepgram
        options_dict = {
            'model': options.model,
            'language': getattr(options, 'language', None),
            'punctuate': options.punctuate,
            'interim_results': options.interim_results,
            'smart_format': options.smart_format,
            'encoding': options.encoding,
            'sample_rate': options.sample_rate,
            'channels': options.channels,
            'utterance_end_ms': getattr(options, 'utterance_end_ms', None),
            'vad_events': getattr(options, 'vad_events', None),
            'endpointing': getattr(options, 'endpointing', None)
        }
        logger.info(f"Complete LiveOptions being sent to Deepgram: {options_dict}")
        
        # Log model fallback information if applicable
        if compatible_model != requested_model:
            logger.info(f"Model changed from {requested_model} to {compatible_model} for language compatibility")
        
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
            
            # Log the exact options being used for connection
            logger.info(f"Starting Deepgram connection with options: {self.options.__dict__}")
            
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
                logger.error(f"Deepgram error handler called with args: {args}, kwargs: {kwargs}")
                if args:
                    await self._handle_error_data(args[0])
                elif kwargs:
                    await self._handle_error_data(kwargs)
            
            self.connection.on(LiveTranscriptionEvents.Transcript, transcript_handler)
            self.connection.on(LiveTranscriptionEvents.Error, error_handler)
            
            # Start connection
            logger.info("Attempting to start Deepgram connection...")
            connection_result = await self.connection.start(self.options)
            logger.info(f"Deepgram connection start result: {connection_result}")
            
            if connection_result:
                self.is_connected = True
                logger.info("Live transcription session started successfully")
            else:
                logger.error("Deepgram connection.start() returned False")
                raise RuntimeError("Failed to start live transcription session")
                
        except Exception as e:
            logger.error(f"Error starting live transcription: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"HTTP Response: {e.response}")
            if hasattr(e, 'status_code'):
                logger.error(f"Status code: {e.status_code}")
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
            # Enhanced error logging for audio transmission issues
            logger.error(f"Error sending audio data (model: {getattr(self.options, 'model', 'unknown')}, language: {getattr(self.options, 'language', 'auto')}): {e}")
            logger.error(f"Audio data size: {len(audio_data)} bytes")
            logger.error(f"Connection status: connected={self.is_connected}")
            
            # Provide specific error context for debugging
            if 'connection' in str(e).lower():
                logger.error("Audio transmission failed due to connection issue - may need reconnection")
            elif 'invalid' in str(e).lower():
                logger.error("Audio data format may be invalid for the selected language/model")
            
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
                            
                            # Log transcript details for debugging
                            logger.debug(f"Transcript received - Text: '{transcript_text[:50]}...', is_final: {is_final}, speech_final: {speech_final}")
                            
                            # Check for detected language information
                            detected_language = None
                            if hasattr(result, 'language') and result.language:
                                detected_language = result.language
                                logger.debug(f"Language detected from result: {detected_language}")
                            elif hasattr(result.channel, 'detected_language'):
                                detected_language = result.channel.detected_language
                                logger.debug(f"Language detected from channel: {detected_language}")
                            elif hasattr(alternatives[0], 'language'):
                                detected_language = alternatives[0].language
                                logger.debug(f"Language detected from alternative: {detected_language}")
                            
                            # Log when language detection is enabled but no language detected
                            if detected_language:
                                logger.info(f"Language detected: {detected_language} for transcript: {transcript_text[:50]}...")
                            elif transcript_text and len(transcript_text) > 10:
                                logger.debug(f"No language detected for transcript: {transcript_text[:50]}...")
                            
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
                                "words": words_data,
                                "detected_language": detected_language
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
