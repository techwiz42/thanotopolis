#!/usr/bin/env python3
"""Test what audio formats work with Deepgram live transcription."""

import asyncio
from app.services.voice.deepgram_service import deepgram_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_formats():
    """Test different audio format configurations."""
    
    formats_to_test = [
        {"encoding": "linear16", "sample_rate": 16000},
        {"encoding": "opus", "sample_rate": 48000},
        {"encoding": "webm", "sample_rate": 48000},
        {"encoding": "webm-opus", "sample_rate": 48000},
        {"encoding": "flac", "sample_rate": 16000},
        {"encoding": "mulaw", "sample_rate": 8000},
        {},  # Default settings
    ]
    
    for config in formats_to_test:
        logger.info(f"\nTesting format: {config}")
        
        try:
            def on_message(data):
                logger.info(f"Transcript received: {data}")
            
            def on_error(error):
                logger.error(f"Error: {error}")
            
            session = await deepgram_service.start_live_transcription(
                on_message=on_message,
                on_error=on_error,
                interim_results=True,
                **config
            )
            
            await session.start()
            logger.info(f"Session started successfully with config: {config}")
            await session.finish()
            
        except Exception as e:
            logger.error(f"Failed with config {config}: {e}")

if __name__ == "__main__":
    asyncio.run(test_formats())