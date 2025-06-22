"""
Unit tests for Audio Converter service
"""
import pytest
import tempfile
import os
import subprocess
from unittest.mock import patch, MagicMock, mock_open
from app.services.voice.audio_converter import AudioConverter, audio_converter


class TestAudioConverter:
    """Test AudioConverter class functionality"""
    
    def test_singleton_instance(self):
        """Test that audio_converter is a singleton instance"""
        assert isinstance(audio_converter, AudioConverter)
        assert audio_converter is not None
    
    def test_is_webm_opus_with_valid_webm(self):
        """Test WebM detection with valid WebM header"""
        # WebM magic number: 0x1A45DFA3
        webm_data = b'\x1a\x45\xdf\xa3' + b'additional_data'
        assert AudioConverter.is_webm_opus(webm_data) is True
    
    def test_is_webm_opus_with_invalid_data(self):
        """Test WebM detection with invalid data"""
        invalid_data = b'\x00\x00\x00\x00' + b'not_webm'
        assert AudioConverter.is_webm_opus(invalid_data) is False
    
    def test_is_webm_opus_with_short_data(self):
        """Test WebM detection with data too short"""
        short_data = b'\x1a\x45'  # Only 2 bytes
        assert AudioConverter.is_webm_opus(short_data) is False
    
    def test_is_webm_opus_with_empty_data(self):
        """Test WebM detection with empty data"""
        assert AudioConverter.is_webm_opus(b'') is False


class TestWebmToPcmConversion:
    """Test WebM to PCM conversion functionality"""
    
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    @patch('builtins.open', new_callable=mock_open, read_data=b'converted_pcm_data')
    @patch('app.services.voice.audio_converter.os.path.exists')
    @patch('app.services.voice.audio_converter.os.unlink')
    def test_webm_to_pcm_success(self, mock_unlink, mock_exists, mock_file_open, mock_tempfile, mock_subprocess):
        """Test successful WebM to PCM conversion"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stderr = ""
        mock_subprocess.return_value = mock_subprocess_result
        
        mock_exists.return_value = True
        
        # Test conversion
        webm_data = b'fake_webm_data'
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Assertions
        assert result == b'converted_pcm_data'
        mock_temp_file.write.assert_called_once_with(webm_data)
        mock_subprocess.assert_called_once()
        
        # Verify ffmpeg command
        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == 'ffmpeg'
        assert '-i' in call_args
        assert '-f' in call_args
        assert 's16le' in call_args
        assert '-ar' in call_args
        assert '16000' in call_args
        assert '-ac' in call_args
        assert '1' in call_args
        
        # Verify cleanup
        assert mock_unlink.call_count == 2  # Both temp files deleted
    
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    @patch('app.services.voice.audio_converter.os.path.exists')
    @patch('app.services.voice.audio_converter.os.unlink')
    def test_webm_to_pcm_ffmpeg_failure(self, mock_unlink, mock_exists, mock_tempfile, mock_subprocess):
        """Test WebM to PCM conversion when ffmpeg fails"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 1
        mock_subprocess_result.stderr = "FFmpeg error message"
        mock_subprocess.return_value = mock_subprocess_result
        
        mock_exists.return_value = True
        
        # Test conversion
        webm_data = b'fake_webm_data'
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Assertions
        assert result is None
        mock_temp_file.write.assert_called_once_with(webm_data)
        mock_subprocess.assert_called_once()
        
        # Verify cleanup still happens
        assert mock_unlink.call_count == 2
    
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    @patch('app.services.voice.audio_converter.os.path.exists')
    @patch('app.services.voice.audio_converter.os.unlink')
    def test_webm_to_pcm_timeout(self, mock_unlink, mock_exists, mock_tempfile, mock_subprocess):
        """Test WebM to PCM conversion timeout"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess.side_effect = subprocess.TimeoutExpired('ffmpeg', 5)
        mock_exists.return_value = True
        
        # Test conversion
        webm_data = b'fake_webm_data'
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Assertions
        assert result is None
        mock_temp_file.write.assert_called_once_with(webm_data)
        mock_subprocess.assert_called_once()
    
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    @patch('app.services.voice.audio_converter.os.path.exists')
    @patch('app.services.voice.audio_converter.os.unlink')
    def test_webm_to_pcm_ffmpeg_not_found(self, mock_unlink, mock_exists, mock_tempfile, mock_subprocess):
        """Test WebM to PCM conversion when ffmpeg is not installed"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess.side_effect = FileNotFoundError("FFmpeg not found")
        mock_exists.return_value = True
        
        # Test conversion
        webm_data = b'fake_webm_data'
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Assertions
        assert result is None
        mock_temp_file.write.assert_called_once_with(webm_data)
        mock_subprocess.assert_called_once()
    
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    @patch('builtins.open')
    @patch('app.services.voice.audio_converter.os.path.exists')
    @patch('app.services.voice.audio_converter.os.unlink')
    def test_webm_to_pcm_file_read_error(self, mock_unlink, mock_exists, mock_file_open, mock_tempfile, mock_subprocess):
        """Test WebM to PCM conversion when output file cannot be read"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess.return_value = mock_subprocess_result
        
        mock_file_open.side_effect = IOError("Cannot read file")
        mock_exists.return_value = True
        
        # Test conversion
        webm_data = b'fake_webm_data'
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Assertions
        assert result is None
        mock_temp_file.write.assert_called_once_with(webm_data)
        mock_subprocess.assert_called_once()
        
        # Verify cleanup still happens
        assert mock_unlink.call_count == 2


class TestProcessBrowserAudio:
    """Test browser audio processing functionality"""
    
    @patch.object(AudioConverter, 'is_webm_opus')
    @patch.object(AudioConverter, 'webm_to_pcm')
    def test_process_browser_audio_webm_success(self, mock_webm_to_pcm, mock_is_webm):
        """Test processing WebM audio successfully"""
        # Setup mocks
        mock_is_webm.return_value = True
        mock_webm_to_pcm.return_value = b'converted_pcm_data'
        
        # Test processing
        webm_data = b'webm_audio_data'
        result_data, result_format = AudioConverter.process_browser_audio(webm_data)
        
        # Assertions
        assert result_data == b'converted_pcm_data'
        assert result_format == "linear16"
        mock_is_webm.assert_called_once_with(webm_data)
        mock_webm_to_pcm.assert_called_once_with(webm_data)
    
    @patch.object(AudioConverter, 'is_webm_opus')
    @patch.object(AudioConverter, 'webm_to_pcm')
    def test_process_browser_audio_webm_conversion_failure(self, mock_webm_to_pcm, mock_is_webm):
        """Test processing WebM audio when conversion fails"""
        # Setup mocks
        mock_is_webm.return_value = True
        mock_webm_to_pcm.return_value = None  # Conversion failed
        
        # Test processing
        webm_data = b'webm_audio_data'
        result_data, result_format = AudioConverter.process_browser_audio(webm_data)
        
        # Assertions - should fall back to original data
        assert result_data == webm_data
        assert result_format == "webm"
        mock_is_webm.assert_called_once_with(webm_data)
        mock_webm_to_pcm.assert_called_once_with(webm_data)
    
    @patch.object(AudioConverter, 'is_webm_opus')
    def test_process_browser_audio_non_webm(self, mock_is_webm):
        """Test processing non-WebM audio (assume PCM)"""
        # Setup mocks
        mock_is_webm.return_value = False
        
        # Test processing
        pcm_data = b'raw_pcm_data'
        result_data, result_format = AudioConverter.process_browser_audio(pcm_data)
        
        # Assertions
        assert result_data == pcm_data
        assert result_format == "linear16"
        mock_is_webm.assert_called_once_with(pcm_data)
    
    def test_process_browser_audio_empty_data(self):
        """Test processing empty audio data"""
        result_data, result_format = AudioConverter.process_browser_audio(b'')
        
        # Should treat as non-WebM (raw PCM)
        assert result_data == b''
        assert result_format == "linear16"


class TestAudioConverterIntegration:
    """Integration tests for AudioConverter"""
    
    @patch.object(AudioConverter, 'webm_to_pcm')
    def test_full_webm_processing_pipeline(self, mock_webm_to_pcm):
        """Test the full WebM processing pipeline"""
        # Setup
        webm_header = b'\x1a\x45\xdf\xa3'
        webm_data = webm_header + b'webm_content'
        converted_pcm = b'converted_pcm_output'
        mock_webm_to_pcm.return_value = converted_pcm
        
        # Test the full pipeline
        result_data, result_format = AudioConverter.process_browser_audio(webm_data)
        
        # Verify detection and conversion
        assert AudioConverter.is_webm_opus(webm_data) is True
        assert result_data == converted_pcm
        assert result_format == "linear16"
        mock_webm_to_pcm.assert_called_once_with(webm_data)
    
    def test_full_pcm_processing_pipeline(self):
        """Test the full PCM processing pipeline"""
        # Setup - non-WebM data
        pcm_data = b'\x00\x01\x02\x03' + b'pcm_content'
        
        # Test the full pipeline
        result_data, result_format = AudioConverter.process_browser_audio(pcm_data)
        
        # Verify detection and passthrough
        assert AudioConverter.is_webm_opus(pcm_data) is False
        assert result_data == pcm_data
        assert result_format == "linear16"


class TestAudioConverterLogging:
    """Test logging behavior in AudioConverter"""
    
    @patch('app.services.voice.audio_converter.logger')
    @patch.object(AudioConverter, 'webm_to_pcm')
    def test_logging_webm_detection(self, mock_webm_to_pcm, mock_logger):
        """Test that WebM detection is logged"""
        # Setup
        webm_data = b'\x1a\x45\xdf\xa3' + b'webm_content'
        mock_webm_to_pcm.return_value = b'converted_pcm'
        
        # Test processing
        AudioConverter.process_browser_audio(webm_data)
        
        # Verify logging
        mock_logger.info.assert_called_with("Detected WebM audio, converting to PCM")
    
    @patch('app.services.voice.audio_converter.logger')
    @patch.object(AudioConverter, 'webm_to_pcm')
    def test_logging_conversion_failure(self, mock_webm_to_pcm, mock_logger):
        """Test that conversion failure is logged"""
        # Setup
        webm_data = b'\x1a\x45\xdf\xa3' + b'webm_content'
        mock_webm_to_pcm.return_value = None  # Conversion failed
        
        # Test processing
        AudioConverter.process_browser_audio(webm_data)
        
        # Verify logging
        mock_logger.info.assert_called_with("Detected WebM audio, converting to PCM")
        mock_logger.warning.assert_called_with("Failed to convert WebM, using original")
    
    @patch('app.services.voice.audio_converter.logger')
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    @patch('builtins.open', new_callable=mock_open, read_data=b'converted_data')
    @patch('app.services.voice.audio_converter.os.path.exists')
    @patch('app.services.voice.audio_converter.os.unlink')
    def test_logging_successful_conversion(self, mock_unlink, mock_exists, mock_file_open, 
                                         mock_tempfile, mock_subprocess, mock_logger):
        """Test that successful conversion is logged with data sizes"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess.return_value = mock_subprocess_result
        
        mock_exists.return_value = True
        
        # Test conversion
        webm_data = b'fake_webm_data_12345'  # 20 bytes
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Verify logging with correct sizes
        mock_logger.info.assert_called_with("Converted 20 bytes WebM to 14 bytes PCM")
        assert result == b'converted_data'


class TestAudioConverterErrorHandling:
    """Test error handling in AudioConverter"""
    
    @patch('app.services.voice.audio_converter.logger')
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    def test_error_logging_ffmpeg_failure(self, mock_tempfile, mock_subprocess, mock_logger):
        """Test that ffmpeg errors are properly logged"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 1
        mock_subprocess_result.stderr = "Invalid format error"
        mock_subprocess.return_value = mock_subprocess_result
        
        # Test conversion
        webm_data = b'invalid_webm_data'
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Verify error logging
        assert result is None
        mock_logger.error.assert_called_with("FFmpeg conversion failed: Invalid format error")
    
    @patch('app.services.voice.audio_converter.logger')
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    def test_error_logging_timeout(self, mock_tempfile, mock_subprocess, mock_logger):
        """Test that timeout errors are properly logged"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess.side_effect = subprocess.TimeoutExpired('ffmpeg', 5)
        
        # Test conversion
        webm_data = b'large_webm_data'
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Verify timeout logging
        assert result is None
        mock_logger.error.assert_called_with("FFmpeg conversion timed out")
    
    @patch('app.services.voice.audio_converter.logger')
    @patch('app.services.voice.audio_converter.subprocess.run')
    @patch('app.services.voice.audio_converter.tempfile.NamedTemporaryFile')
    def test_error_logging_ffmpeg_not_found(self, mock_tempfile, mock_subprocess, mock_logger):
        """Test that missing ffmpeg is properly logged"""
        # Setup mocks
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/test.webm'
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        mock_subprocess.side_effect = FileNotFoundError("FFmpeg not found")
        
        # Test conversion
        webm_data = b'webm_data'
        result = AudioConverter.webm_to_pcm(webm_data)
        
        # Verify error logging
        assert result is None
        mock_logger.error.assert_called_with("FFmpeg not found. Please install ffmpeg.")


# Test the module-level singleton instance
def test_module_singleton():
    """Test that the module exports a singleton instance"""
    from app.services.voice.audio_converter import audio_converter
    assert isinstance(audio_converter, AudioConverter)
    
    # Import again to verify it's the same instance
    from app.services.voice.audio_converter import audio_converter as audio_converter2
    assert audio_converter is audio_converter2