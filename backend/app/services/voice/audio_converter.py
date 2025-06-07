"""Audio format converter for handling browser audio formats."""

import io
import logging
from typing import Optional, Tuple
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


class AudioConverter:
    """Convert various audio formats to raw PCM for Deepgram."""
    
    @staticmethod
    def webm_to_pcm(webm_data: bytes) -> Optional[bytes]:
        """Convert WebM audio to raw PCM using ffmpeg.
        
        Args:
            webm_data: WebM audio data
            
        Returns:
            Raw PCM audio data (16-bit, 16kHz, mono) or None if conversion fails
        """
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as webm_file:
                webm_file.write(webm_data)
                webm_path = webm_file.name
            
            pcm_path = webm_path.replace('.webm', '.raw')
            
            try:
                # Use ffmpeg to convert WebM to raw PCM
                # -f s16le: 16-bit signed little-endian PCM
                # -ar 16000: 16kHz sample rate
                # -ac 1: mono
                cmd = [
                    'ffmpeg',
                    '-i', webm_path,
                    '-f', 's16le',
                    '-acodec', 'pcm_s16le',
                    '-ar', '16000',
                    '-ac', '1',
                    '-y',  # Overwrite output
                    pcm_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg conversion failed: {result.stderr}")
                    return None
                
                # Read the converted PCM data
                with open(pcm_path, 'rb') as pcm_file:
                    pcm_data = pcm_file.read()
                
                logger.info(f"Converted {len(webm_data)} bytes WebM to {len(pcm_data)} bytes PCM")
                return pcm_data
                
            finally:
                # Clean up temporary files
                if os.path.exists(webm_path):
                    os.unlink(webm_path)
                if os.path.exists(pcm_path):
                    os.unlink(pcm_path)
                    
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg conversion timed out")
            return None
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install ffmpeg.")
            return None
        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            return None
    
    @staticmethod
    def is_webm_opus(data: bytes) -> bool:
        """Check if data is WebM with Opus codec.
        
        WebM files start with EBML header (0x1A45DFA3)
        """
        if len(data) < 4:
            return False
        return data[:4] == b'\x1a\x45\xdf\xa3'
    
    @staticmethod
    def process_browser_audio(audio_data: bytes) -> Tuple[bytes, str]:
        """Process audio data from browser.
        
        Returns:
            Tuple of (processed_audio_data, encoding_format)
        """
        # Check if it's WebM
        if AudioConverter.is_webm_opus(audio_data):
            logger.info("Detected WebM audio, converting to PCM")
            pcm_data = AudioConverter.webm_to_pcm(audio_data)
            if pcm_data:
                return pcm_data, "linear16"
            else:
                logger.warning("Failed to convert WebM, using original")
                return audio_data, "webm"
        
        # Assume it's already raw PCM
        return audio_data, "linear16"


# Singleton instance
audio_converter = AudioConverter()