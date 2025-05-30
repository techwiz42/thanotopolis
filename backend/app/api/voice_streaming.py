# backend/app/api/voice_streaming.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from uuid import uuid4
from typing import Set

from app.services.voice.deepgram_stt_service import deepgram_stt_service, DeepgramStreamingHandler
from app.core.websocket_queue import connection_health

logger = logging.getLogger(__name__)
router = APIRouter()

# Track active handlers for cleanup
ACTIVE_HANDLERS: Set[DeepgramStreamingHandler] = set()


async def shutdown_all_handlers():
    """Shutdown all active handlers gracefully"""
    logger.info(f"Shutting down {len(ACTIVE_HANDLERS)} active handlers")
    
    handlers = list(ACTIVE_HANDLERS)
    if handlers:
        await asyncio.gather(
            *[handler.stop() for handler in handlers],
            return_exceptions=True
        )
    
    ACTIVE_HANDLERS.clear()
    logger.info("All handlers shut down")


@router.websocket("/ws/voice/streaming-stt")
async def streaming_stt_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming speech-to-text"""
    logger.info("New streaming STT connection attempt")
    logger.info(f"Client: {websocket.client}")
    
    # Generate unique identifier for this connection
    user_identifier = f"streaming_stt_{uuid4()}"
    connection_id = None
    handler = None
    
    try:
        # Accept the connection
        await websocket.accept()
        
        # Initialize connection health manager
        await connection_health._ensure_initialized()
        
        # Register with connection health manager for resource management
        try:
            temp_conversation_id = uuid4()
            
            connection_id = await connection_health.enqueue_connection(
                websocket=websocket,
                conversation_id=temp_conversation_id,
                user_identifier=user_identifier
            )
            
            if not connection_id:
                logger.error("Failed to register STT connection")
                await websocket.send_json({
                    "type": "error",
                    "message": "Server is currently at capacity. Please try again later."
                })
                await websocket.close()
                return
                
        except Exception as conn_error:
            logger.error(f"Failed to register STT connection: {conn_error}")
            # Continue anyway - handle manually if needed
        
        # Wait for configuration
        try:
            config_message = await asyncio.wait_for(websocket.receive_json(), timeout=30)
            logger.info(f"Received config: {config_message}")
        except asyncio.TimeoutError:
            await websocket.send_json({
                "type": "error",
                "message": "Timeout waiting for configuration"
            })
            return
        except Exception as e:
            logger.error(f"Failed to receive config: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Failed to receive configuration"
            })
            return
        
        # Validate config message
        if config_message.get("type") != "config":
            await websocket.send_json({
                "type": "error",
                "message": "Expected config message"
            })
            return
        
        config = config_message.get("config", {})
        logger.info(f"STT config: {config}")
        
        # Create and run handler
        handler = DeepgramStreamingHandler(websocket, deepgram_stt_service)
        ACTIVE_HANDLERS.add(handler)
        
        await handler.run(config)
        
    except WebSocketDisconnect:
        logger.info("STT client disconnected")
    except Exception as e:
        logger.error(f"Error in streaming STT endpoint: {e}")
        
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Clean up
        if handler:
            ACTIVE_HANDLERS.discard(handler)
            await handler.stop()
        
        # Disconnect from connection health manager
        if connection_id:
            try:
                await connection_health.disconnect(
                    uuid4(),
                    connection_id,
                    reason="STT connection closed"
                )
            except Exception as e:
                logger.error(f"Error cleaning up STT connection: {e}")
        
        # Close websocket
        try:
            await websocket.close()
        except:
            pass


@router.get("/voice/stt/status")
async def stt_status():
    """Get the status of the STT service"""
    api_key_loaded = bool(deepgram_stt_service.api_key)
    
    # Verify API key if loaded
    if api_key_loaded:
        is_valid, error_message = await deepgram_stt_service.verify_api_key()
    else:
        is_valid = False
        error_message = "API key not configured"
    
    return {
        "service": "deepgram_stt",
        "api_key_configured": api_key_loaded,
        "api_key_valid": is_valid,
        "error": error_message if not is_valid else None,
        "active_connections": len(ACTIVE_HANDLERS),
        "supported_models": deepgram_stt_service.supported_models
    }
