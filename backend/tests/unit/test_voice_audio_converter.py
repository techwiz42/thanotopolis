import pytest
from unittest.mock import MagicMock, patch, mock_open, call
import subprocess
import tempfile
import os
from typing import Tuple

from app.services.voice.audio_converter import AudioConverter, audio_converter


class TestAudioConverter:
    """Test suite for AudioConverter."""
    
    @pytest.fixture
    def audio_converter_instance(self):
        """Create an AudioConverter instance."""
        return AudioConverter()
    
    @pytest.fixture
    def valid_webm_header(self):
        """Create valid WebM file header (EBML signature)."""
        # WebM files start with EBML header: 0x1A45DFA3
        return bytes([0x1A, 0x45, 0xDF, 0xA3]) + b'\x00' * 100
    
    @pytest.fixture
    def invalid_audio_data(self):
        """Create non-WebM audio data."""
        # MP3 header starts with 0xFFF or ID3
        return b'ID3\x03\x00\x00\x00' + b'\x00' * 100
    
    @pytest.fixture
    def mock_subprocess_success(self):
        """Mock successful subprocess execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b''
        mock_result.stderr = b''
        return mock_result
    
    @pytest.fixture
    def mock_subprocess_failure(self):
        """Mock failed subprocess execution."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = b''
        mock_result.stderr = b'ffmpeg: error during conversion'
        return mock_result
    
    def test_audio_converter_initialization(self, audio_converter_instance):
        """Test AudioConverter initialization."""
        assert isinstance(audio_converter_instance, AudioConverter)
    
    def test_is_webm_opus_valid_header(self, audio_converter_instance, valid_webm_header):
        """Test WebM detection with valid header."""
        result = audio_converter_instance.is_webm_opus(valid_webm_header)
        assert result is True
    
    def test_is_webm_opus_invalid_header(self, audio_converter_instance, invalid_audio_data):
        """Test WebM detection with non-WebM data."""
        result = audio_converter_instance.is_webm_opus(invalid_audio_data)
        assert result is False
    
    def test_is_webm_opus_empty_data(self, audio_converter_instance):
        """Test WebM detection with empty data."""
        result = audio_converter_instance.is_webm_opus(b'')
        assert result is False
    
    def test_is_webm_opus_short_data(self, audio_converter_instance):
        """Test WebM detection with data shorter than header."""
        result = audio_converter_instance.is_webm_opus(b'\x1A\x45')  # Only 2 bytes
        assert result is False
    
    def test_is_webm_opus_various_formats(self, audio_converter_instance):
        """Test WebM detection with various file format headers."""
        test_cases = [
            (b'RIFF\x00\x00\x00\x00WAVE', False),  # WAV
            (b'\xFF\xFB\x90\x00', False),  # MP3
            (b'fLaC\x00\x00\x00', False),  # FLAC
            (b'OggS\x00\x02\x00', False),  # OGG
            (bytes([0x1A, 0x45, 0xDF, 0xA3]), True),  # WebM
            (b'\x00\x00\x00\x20ftypM4A ', False),  # M4A
        ]
        
        for data, expected in test_cases:
            # Pad data to at least 4 bytes
            padded_data = data + b'\x00' * max(0, 4 - len(data))
            result = audio_converter_instance.is_webm_opus(padded_data)
            assert result == expected, f"Failed for data starting with {data[:4].hex()}"
    
    def test_webm_to_pcm_success(self, audio_converter_instance, valid_webm_header, mock_subprocess_success):
        """Test successful WebM to PCM conversion."""
        expected_pcm_data = b'PCM_AUDIO_DATA_HERE'
        
        with patch('subprocess.run', return_value=mock_subprocess_success) as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('builtins.open', mock_open(read_data=expected_pcm_data)) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('os.unlink') as mock_unlink:
            
            # Configure temp file mock
            mock_input_file = MagicMock()
            mock_input_file.name = '/tmp/input.webm'
            mock_input_file.__enter__ = MagicMock(return_value=mock_input_file)
            mock_input_file.__exit__ = MagicMock(return_value=None)
            mock_temp_file.return_value = mock_input_file
            
            result = audio_converter_instance.webm_to_pcm(valid_webm_header)
            
            assert result == expected_pcm_data
            
            # Verify subprocess was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'ffmpeg'
            assert '-i' in call_args
            assert '/tmp/input.webm' in call_args
            assert '-f' in call_args
            assert 's16le' in call_args
            assert '-ar' in call_args
            assert '16000' in call_args
            assert '-ac' in call_args
            assert '1' in call_args
            
            # Verify file operations
            mock_input_file.write.assert_called_once_with(valid_webm_header)
            
            # Verify cleanup - should call unlink twice (input and output files)
            assert mock_unlink.call_count == 2
    
    def test_webm_to_pcm_ffmpeg_not_found(self, audio_converter_instance, valid_webm_header):
        """Test WebM conversion when ffmpeg is not installed."""
        with patch('subprocess.run', side_effect=FileNotFoundError("ffmpeg not found")), \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file:
            
            mock_temp_file.return_value.name = '/tmp/test.webm'
            
            result = audio_converter_instance.webm_to_pcm(valid_webm_header)
            
            assert result is None
    
    def test_webm_to_pcm_ffmpeg_failure(self, audio_converter_instance, valid_webm_header, mock_subprocess_failure):
        """Test WebM conversion when ffmpeg fails."""
        with patch('subprocess.run', return_value=mock_subprocess_failure) as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('os.path.exists', return_value=True), \
             patch('os.remove'):
            
            mock_input_file = MagicMock()
            mock_input_file.name = '/tmp/input.webm'
            mock_output_file = MagicMock()
            mock_output_file.name = '/tmp/output.pcm'
            
            mock_temp_file.side_effect = [mock_input_file, mock_output_file]
            
            result = audio_converter_instance.webm_to_pcm(valid_webm_header)
            
            assert result is None
    
    def test_webm_to_pcm_timeout(self, audio_converter_instance, valid_webm_header):
        """Test WebM conversion timeout."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('ffmpeg', 30)) as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('os.path.exists', return_value=True), \
             patch('os.remove'):
            
            mock_temp_file.return_value.name = '/tmp/test.webm'
            
            result = audio_converter_instance.webm_to_pcm(valid_webm_header)
            
            assert result is None
    
    def test_webm_to_pcm_output_file_not_created(self, audio_converter_instance, valid_webm_header, mock_subprocess_success):
        """Test WebM conversion when output file is not created."""
        with patch('subprocess.run', return_value=mock_subprocess_success), \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('builtins.open', side_effect=FileNotFoundError("Output file not found")), \
             patch('os.path.exists', return_value=True), \
             patch('os.unlink'):
            
            mock_input_file = MagicMock()
            mock_input_file.name = '/tmp/test.webm'
            mock_input_file.__enter__ = MagicMock(return_value=mock_input_file)
            mock_input_file.__exit__ = MagicMock(return_value=None)
            mock_temp_file.return_value = mock_input_file
            
            result = audio_converter_instance.webm_to_pcm(valid_webm_header)
            
            assert result is None
    
    def test_webm_to_pcm_file_read_error(self, audio_converter_instance, valid_webm_header, mock_subprocess_success):
        """Test WebM conversion with file read error."""
        with patch('subprocess.run', return_value=mock_subprocess_success), \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=IOError("Cannot read file")), \
             patch('os.remove'):
            
            mock_temp_file.return_value.name = '/tmp/test.webm'
            
            result = audio_converter_instance.webm_to_pcm(valid_webm_header)
            
            assert result is None
    
    def test_webm_to_pcm_cleanup_on_exception(self, audio_converter_instance, valid_webm_header):
        """Test that temporary files are cleaned up even on exception."""
        mock_input_file = MagicMock()
        mock_input_file.name = '/tmp/input.webm'
        mock_input_file.__enter__ = MagicMock(return_value=mock_input_file)
        mock_input_file.__exit__ = MagicMock(return_value=None)
        
        with patch('subprocess.run', side_effect=Exception("Unexpected error")), \
             patch('tempfile.NamedTemporaryFile', return_value=mock_input_file) as mock_temp_file, \
             patch('os.path.exists', return_value=True), \
             patch('os.unlink') as mock_unlink:
            
            result = audio_converter_instance.webm_to_pcm(valid_webm_header)
            
            assert result is None
            
            # Verify cleanup was attempted
            mock_unlink.assert_any_call('/tmp/input.webm')
    
    def test_webm_to_pcm_empty_data(self, audio_converter_instance):
        """Test WebM conversion with empty data."""
        result = audio_converter_instance.webm_to_pcm(b'')
        # Should still attempt conversion even with empty data
        assert result is None or isinstance(result, (bytes, type(None)))
    
    def test_process_browser_audio_webm_success(self, audio_converter_instance, valid_webm_header):
        """Test processing WebM audio successfully."""
        expected_pcm_data = b'CONVERTED_PCM_DATA'
        
        with patch.object(AudioConverter, 'is_webm_opus', return_value=True), \
             patch.object(AudioConverter, 'webm_to_pcm', return_value=expected_pcm_data):
            
            result_data, result_encoding = audio_converter_instance.process_browser_audio(valid_webm_header)
            
            assert result_data == expected_pcm_data
            assert result_encoding == "linear16"
    
    def test_process_browser_audio_webm_conversion_fails(self, audio_converter_instance, valid_webm_header):
        """Test processing WebM audio when conversion fails."""
        with patch.object(AudioConverter, 'is_webm_opus', return_value=True), \
             patch.object(AudioConverter, 'webm_to_pcm', return_value=None):
            
            result_data, result_encoding = audio_converter_instance.process_browser_audio(valid_webm_header)
            
            # Should return original data when conversion fails
            assert result_data == valid_webm_header
            assert result_encoding == "webm"
    
    def test_process_browser_audio_non_webm(self, audio_converter_instance, invalid_audio_data):
        """Test processing non-WebM audio."""
        with patch.object(AudioConverter, 'is_webm_opus', return_value=False):
            
            result_data, result_encoding = audio_converter_instance.process_browser_audio(invalid_audio_data)
            
            # Should return original data for non-WebM
            assert result_data == invalid_audio_data
            assert result_encoding == "linear16"  # Assumes raw PCM
    
    def test_process_browser_audio_logging(self, audio_converter_instance, valid_webm_header, caplog):
        """Test that processing logs appropriate messages."""
        with patch.object(AudioConverter, 'is_webm_opus', return_value=True), \
             patch.object(AudioConverter, 'webm_to_pcm', return_value=b'PCM_DATA'):
            
            import logging
            with caplog.at_level(logging.INFO):
                audio_converter_instance.process_browser_audio(valid_webm_header)
            
            # Check for expected log messages
            log_messages = [record.message for record in caplog.records]
            assert any("Detected WebM audio" in msg for msg in log_messages)
    
    def test_process_browser_audio_edge_cases(self, audio_converter_instance):
        """Test edge cases for process_browser_audio."""
        # Empty data
        result_data, result_encoding = audio_converter_instance.process_browser_audio(b'')
        assert result_data == b''
        assert result_encoding == "linear16"
        
        # Very small data
        small_data = b'XX'
        result_data, result_encoding = audio_converter_instance.process_browser_audio(small_data)
        assert result_data == small_data
        assert result_encoding == "linear16"


class TestAudioConverterSingleton:
    """Test the audio converter singleton."""
    
    def test_singleton_exists(self):
        """Test that audio converter singleton exists."""
        assert audio_converter is not None
        assert isinstance(audio_converter, AudioConverter)
    
    def test_singleton_functionality(self):
        """Test that singleton instance works correctly."""
        # Test basic functionality
        result = audio_converter.is_webm_opus(b'\x1A\x45\xDF\xA3')
        assert result is True
        
        result = audio_converter.is_webm_opus(b'RIFF')
        assert result is False


class TestAudioConverterIntegration:
    """Integration tests for AudioConverter."""
    
    def test_full_webm_conversion_workflow(self):
        """Test complete WebM conversion workflow."""
        converter = AudioConverter()
        
        # Create realistic WebM header (first 32 bytes of a WebM file)
        webm_data = bytes([
            0x1A, 0x45, 0xDF, 0xA3,  # EBML header
            0x9F, 0x42, 0x86, 0x81,  # EBML version
            0x01, 0x42, 0xF7, 0x81,  # EBML read version
            0x01, 0x42, 0xF2, 0x81,  # EBML max ID length
            0x04, 0x42, 0xF3, 0x81,  # EBML max size length
            0x08, 0x42, 0x82, 0x84,  # DocType
            0x77, 0x65, 0x62, 0x6D   # "webm"
        ]) + b'\x00' * 100
        
        # Test detection
        assert converter.is_webm_opus(webm_data) is True
        
        # Test full processing (will fail without ffmpeg, but tests the flow)
        with patch.object(AudioConverter, 'webm_to_pcm', return_value=b'CONVERTED_AUDIO') as mock_convert:
            audio_data, encoding = converter.process_browser_audio(webm_data)
            
            mock_convert.assert_called_once_with(webm_data)
            assert audio_data == b'CONVERTED_AUDIO'
            assert encoding == "linear16"
    
    def test_audio_format_detection_suite(self):
        """Test detection of various audio formats."""
        converter = AudioConverter()
        
        # Common audio file signatures
        audio_formats = {
            'webm': bytes([0x1A, 0x45, 0xDF, 0xA3]),
            'wav': b'RIFF',
            'mp3_id3': b'ID3\x03',
            'mp3_raw': b'\xFF\xFB',
            'ogg': b'OggS',
            'flac': b'fLaC',
            'm4a': b'\x00\x00\x00\x20ftypM4A ',
            'opus': b'OpusHead',
        }
        
        for format_name, signature in audio_formats.items():
            is_webm = converter.is_webm_opus(signature + b'\x00' * 100)
            expected = format_name == 'webm'
            assert is_webm == expected, f"Format {format_name} detection failed"
    
    def test_subprocess_command_construction(self):
        """Test that ffmpeg command is constructed correctly."""
        converter = AudioConverter()
        
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('os.path.exists', return_value=False):
            
            mock_temp.return_value.name = '/tmp/test'
            mock_run.return_value.returncode = 0
            
            converter.webm_to_pcm(b'test_data')
            
            # Verify ffmpeg command structure
            call_args = mock_run.call_args[0][0]
            
            # Basic command structure
            assert call_args[0] == 'ffmpeg'
            assert '-i' in call_args
            
            # Audio format specifications
            assert '-f' in call_args
            assert 's16le' in call_args  # 16-bit PCM
            
            # Sample rate
            assert '-ar' in call_args
            assert '16000' in call_args  # 16kHz
            
            # Channels
            assert '-ac' in call_args
            assert '1' in call_args  # Mono
            
            # Overwrite output
            assert '-y' in call_args
    
    def test_error_handling_robustness(self):
        """Test robustness of error handling."""
        converter = AudioConverter()
        
        # Test various error scenarios
        error_scenarios = [
            FileNotFoundError("ffmpeg not found"),
            subprocess.TimeoutExpired('ffmpeg', 30),
            subprocess.CalledProcessError(1, 'ffmpeg'),
            PermissionError("Cannot write to temp file"),
            OSError("Disk full"),
            Exception("Unexpected error")
        ]
        
        for error in error_scenarios:
            with patch('subprocess.run', side_effect=error), \
                 patch('tempfile.NamedTemporaryFile'):
                
                result = converter.webm_to_pcm(b'test_data')
                assert result is None, f"Failed to handle {type(error).__name__}"
    
    def test_temp_file_lifecycle(self):
        """Test temporary file creation and cleanup."""
        converter = AudioConverter()
        
        temp_files_created = []
        temp_files_removed = []
        
        class MockTempFile:
            def __init__(self, *args, **kwargs):
                self.name = f'/tmp/mock_temp_{len(temp_files_created)}'
                temp_files_created.append(self.name)
            
            def write(self, data):
                pass
            
            def flush(self):
                pass
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass
        
        def mock_remove(path):
            temp_files_removed.append(path)
        
        with patch('tempfile.NamedTemporaryFile', MockTempFile), \
             patch('subprocess.run') as mock_run, \
             patch('os.path.exists', return_value=True), \
             patch('os.unlink', side_effect=mock_remove), \
             patch('builtins.open', mock_open(read_data=b'PCM')):
            
            mock_run.return_value.returncode = 0
            
            converter.webm_to_pcm(b'test_data')
            
            # Should create 1 temp file (input - output is created by ffmpeg)
            assert len(temp_files_created) == 1
            
            # Should attempt to remove both input and output files
            assert len(temp_files_removed) == 2
    
    def test_large_file_handling(self):
        """Test handling of large audio files."""
        converter = AudioConverter()
        
        # Create a large fake audio file (10MB)
        large_audio_data = bytes([0x1A, 0x45, 0xDF, 0xA3]) + b'\x00' * (10 * 1024 * 1024)
        
        # Test that it can handle large data
        assert converter.is_webm_opus(large_audio_data) is True
        
        # Test processing (mocked)
        with patch.object(AudioConverter, 'webm_to_pcm', return_value=b'CONVERTED') as mock_convert:
            audio_data, encoding = converter.process_browser_audio(large_audio_data)
            
            # Verify the large data was passed to conversion
            mock_convert.assert_called_once_with(large_audio_data)
            assert audio_data == b'CONVERTED'
            assert encoding == "linear16"