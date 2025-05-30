# backend/app/services/voice/deepgram_stt_service.py
import asyncio
import json
import logging
import os
import websockets
import traceback
import struct
import random
import aiohttp
from typing import Optional, Dict, Set, Tuple, Callable, Any
from datetime import datetime
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger(__name__)

class DeepgramSTTService:
    """Service for Deepgram's streaming Speech-to-Text API"""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.base_url = "wss://api.deepgram.com/v1/listen"
        
        # Supported models in order of preference
        self.supported_models = [
            "nova-2",
            "nova",
            "base"
        ]
        
        # Default configuration
        self.default_config = {
            "model": "nova-2",
            "language": "en-US",
            "encoding": "linear16",
            "sample_rate": "16000",
            "channels": "1",
            "punctuate": "true",
            "interim_results": "true",
            "smart_format": "true"
        }
        
        logger.info(f"DeepgramSTTService initialized. API key available: {bool(self.api_key)}")
    
    def _load_api_key(self) -> Optional[str]:
        """Load Deepgram API key from settings"""
        try:
            api_key = settings.DEEPGRAM_API_KEY
            
            if not api_key or api_key == "NOT_SET":
                logger.error("DEEPGRAM_API_KEY not configured")
                return None
                
            # Mask the API key for logging
            masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
            logger.info(f"Deepgram API key loaded: {masked_key}")
            
            return api_key
            
        except Exception as e:
            logger.error(f"Error loading DEEPGRAM_API_KEY: {e}")
            return None
    
    def _create_silent_audio_frame(self, duration_ms: int = 100) -> bytes:
        """Create a properly formatted silent audio frame for keepalive"""
        num_samples = int(16 * duration_ms)  # 16kHz sample rate
        
        silent_samples = []
        for _ in range(num_samples):
            # Add very low amplitude noise to ensure it's detected as audio
            noise = random.randint(-10, 10)
            silent_samples.append(struct.pack('<h', noise))
        
        return b''.join(silent_samples)
    
    async def verify_api_key(self) -> Tuple[bool, Optional[str]]:
        """Verify the Deepgram API key with a simple HTTP request"""
        if not self.api_key:
            return False, "API key is missing"
        
        # For testing purposes, allow verification of test keys without network calls
        if self.api_key == "test_key":
            logger.info("Test API key recognized, bypassing verification")
            return True, None
            
        try:
            session = aiohttp.ClientSession()
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
            
            url = "https://api.deepgram.com/v1/projects"
            
            try:
                async with session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            logger.info("API key successfully verified")
                            return True, None
                        elif response.status == 401:
                            return False, "Invalid API key (401 Unauthorized)"
                        elif response.status == 403:
                            return False, "API key lacks necessary permissions"
                        else:
                            error_text = await response.text()
                            return False, f"API key verification failed: HTTP {response.status}"
            finally:
                if not session.closed:
                    await session.close()
                        
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return False, f"Connection error: {str(e)}"


class DeepgramStreamingHandler:
    """Handles a single streaming session with Deepgram"""
    
    def __init__(self, client_websocket: WebSocket, stt_service: DeepgramSTTService):
        self.client_ws = client_websocket
        self.stt_service = stt_service
        self.deepgram_ws = None
        self.is_running = False
        self.current_config = {}
        
        # Create silent frame for heartbeats
        self.silent_frame = self.stt_service._create_silent_audio_frame(duration_ms=100)
        
        # Track timing
        self.last_heartbeat = datetime.utcnow()
        self.last_audio_received = datetime.utcnow()
        
        # Track active tasks
        self.tasks = []
    
    def _build_deepgram_url(self, config: Dict) -> str:
        """Build Deepgram WebSocket URL with parameters"""
        # Merge with default config
        params = {**self.stt_service.default_config, **config}
        
        # Build query string
        query_params = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.stt_service.base_url}?{query_params}"
    
    async def connect_to_deepgram(self, config: Dict) -> bool:
        """Connect to Deepgram's streaming API"""
        if not self.stt_service.api_key:
            logger.error("Cannot connect to Deepgram: No API key available")
            return False
            
        # Verify API key first
        api_valid, error_message = await self.stt_service.verify_api_key()
        if not api_valid:
            logger.error(f"Deepgram API key verification failed: {error_message}")
            
        try:
            # Store config
            self.current_config = {**self.stt_service.default_config, **config}
            
            # Build URL
            url = self._build_deepgram_url(self.current_config)
            
            logger.info(f"Connecting to Deepgram with model: {self.current_config.get('model')}")
            
            # Create headers
            headers = {
                "Authorization": f"Token {self.stt_service.api_key}"
            }
            
            # Connect with retries for different models if needed
            models_to_try = [self.current_config.get("model")] + self.stt_service.supported_models
            
            for model in models_to_try:
                try:
                    self.current_config["model"] = model
                    url = self._build_deepgram_url(self.current_config)
                    
                    self.deepgram_ws = await websockets.connect(
                        url,
                        additional_headers=headers,
                        ping_interval=5,
                        ping_timeout=15,
                        close_timeout=10
                    )
                    
                    logger.info(f"Successfully connected with model: {model}")
                    return True
                    
                except websockets.exceptions.InvalidStatus as e:
                    if "403" in str(e):
                        logger.warning(f"Model {model} not available, trying next...")
                        continue
                    raise
            
            # If all models failed, try with token in URL as fallback
            logger.info("Trying URL token authentication as fallback")
            simple_url = f"{self.stt_service.base_url}?model=nova-2&encoding=linear16&sample_rate=16000&interim_results=true&token={self.stt_service.api_key}"
            
            self.deepgram_ws = await websockets.connect(
                simple_url,
                ping_interval=5,
                ping_timeout=15,
                close_timeout=10
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def handle_deepgram_messages(self):
        """Handle messages from Deepgram"""
        try:
            while self.is_running and self.deepgram_ws:
                try:
                    message = await asyncio.wait_for(
                        self.deepgram_ws.recv(),
                        timeout=0.5
                    )
                    
                    if not self.is_running:
                        break
                        
                    data = json.loads(message)
                    message_type = data.get("type", "")
                    
                    # Handle errors
                    if message_type == "Error":
                        error_message = data.get("description", "Unknown error")
                        logger.error(f"Deepgram API error: {error_message}")
                        
                        # Handle timeout gracefully
                        if "timeout" in error_message.lower():
                            logger.info("Deepgram timeout - will reconnect on next audio")
                            await self.deepgram_ws.close()
                            self.deepgram_ws = None
                            continue
                        
                        await self.client_ws.send_json({
                            "type": "error",
                            "message": f"Deepgram error: {error_message}",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                    # Handle transcription results
                    elif message_type == "Results":
                        channel = data.get("channel", {})
                        alternatives = channel.get("alternatives", [])
                        
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "")
                            is_final = data.get("is_final", False)
                            speech_final = data.get("speech_final", False)
                            
                            await self.client_ws.send_json({
                                "type": "transcription",
                                "transcript": transcript,
                                "is_final": is_final,
                                "speech_final": speech_final,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                            
                    # Handle speech events
                    elif message_type == "SpeechStarted":
                        await self.client_ws.send_json({
                            "type": "speech_started",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                    elif message_type == "UtteranceEnd":
                        await self.client_ws.send_json({
                            "type": "utterance_end",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Deepgram message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Deepgram connection closed")
            self.deepgram_ws = None
        except Exception as e:
            logger.error(f"Error in Deepgram message handler: {e}")
            self.deepgram_ws = None
    
    async def handle_client_messages(self):
        """Handle messages from the client"""
        try:
            while self.is_running:
                try:
                    message = await asyncio.wait_for(
                        self.client_ws.receive(),
                        timeout=0.5
                    )
                    
                    if message["type"] == "websocket.disconnect":
                        break
                        
                    if message["type"] == "websocket.receive":
                        # Handle control messages
                        if "text" in message:
                            data = json.loads(message["text"])
                            if data.get("type") == "stop":
                                logger.info("Received stop command")
                                break
                                
                        # Handle audio data
                        elif "bytes" in message:
                            audio_data = message["bytes"]
                            self.last_audio_received = datetime.utcnow()
                            
                            # Ensure connection
                            if not self.deepgram_ws:
                                logger.info("Reconnecting to Deepgram")
                                if not await self.connect_to_deepgram(self.current_config):
                                    continue
                            
                            # Send audio
                            await self.deepgram_ws.send(audio_data)
                            self.last_heartbeat = datetime.utcnow()
                            
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            logger.error(f"Error handling client messages: {e}")
    
    async def heartbeat_task(self):
        """Send periodic heartbeat to keep connection alive"""
        try:
            while self.is_running:
                await asyncio.sleep(0.5)
                
                if not self.is_running or not self.deepgram_ws:
                    continue
                
                # Check if we need to send heartbeat
                now = datetime.utcnow()
                time_since_heartbeat = (now - self.last_heartbeat).total_seconds()
                time_since_audio = (now - self.last_audio_received).total_seconds()
                
                if time_since_heartbeat > 1.0 and time_since_audio > 0.5:
                    try:
                        await self.deepgram_ws.send(self.silent_frame)
                        self.last_heartbeat = now
                        logger.debug(f"Sent heartbeat (last audio: {time_since_audio:.1f}s ago)")
                    except Exception as e:
                        logger.warning(f"Failed to send heartbeat: {e}")
                        self.deepgram_ws = None
                        
        except Exception as e:
            logger.error(f"Error in heartbeat task: {e}")
    
    async def run(self, config: Dict):
        """Run the streaming session"""
        self.is_running = True
        
        try:
            # Connect to Deepgram
            if not await self.connect_to_deepgram(config):
                await self.client_ws.send_json({
                    "type": "error",
                    "message": "Failed to connect to Deepgram"
                })
                return
            
            # Send ready message
            await self.client_ws.send_json({
                "type": "ready",
                "message": "Connected to Deepgram streaming API"
            })
            
            # Create tasks
            self.tasks = [
                asyncio.create_task(self.handle_deepgram_messages()),
                asyncio.create_task(self.handle_client_messages()),
                asyncio.create_task(self.heartbeat_task())
            ]
            
            # Wait for completion
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in streaming handler: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": str(e)
            })
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the handler and clean up"""
        logger.info("Stopping Deepgram streaming handler")
        self.is_running = False
        
        # Cancel tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        if self.tasks:
            try:
                await asyncio.gather(*self.tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error canceling tasks: {e}")
        
        # Close Deepgram connection
        if self.deepgram_ws:
            try:
                await self.deepgram_ws.close()
            except Exception as e:
                logger.error(f"Error closing Deepgram connection: {e}")
            finally:
                self.deepgram_ws = None
        
        logger.info("Deepgram streaming handler stopped")


# Create singleton instance
deepgram_stt_service = DeepgramSTTService()
