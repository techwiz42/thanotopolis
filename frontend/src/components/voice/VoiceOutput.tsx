// src/components/voice/VoiceOutput.tsx
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, Download, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { useToast } from '@/components/ui/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';

export interface VoiceOutputProps {
  text: string;
  autoPlay?: boolean;
  onPlayStateChange?: (isPlaying: boolean) => void;
  className?: string;
  compact?: boolean;
  voiceId?: string;
  messageId?: string;
}

interface TTSOptions {
  voice_id?: string;
  language_code: string;
  speaking_rate: number;
  pitch: number;
  volume_gain_db: number;
  audio_encoding: string;
  preprocess_text: boolean;
}

export const VoiceOutput: React.FC<VoiceOutputProps> = ({
  text,
  autoPlay = false,
  onPlayStateChange,
  className = '',
  compact = false,
  voiceId,
  messageId
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const { token } = useAuth();
  const { toast } = useToast();

  // Clean up audio URL when component unmounts
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  // Auto-play functionality will be defined after synthesizeAndPlay is defined

  // Update parent when play state changes
  useEffect(() => {
    onPlayStateChange?.(isPlaying);
  }, [isPlaying, onPlayStateChange]);

  const synthesizeAudio = useCallback(async (options?: Partial<TTSOptions>): Promise<string> => {
    if (!token) {
      throw new Error('Authentication required');
    }

    if (!text.trim()) {
      throw new Error('No text to synthesize');
    }

    const defaultOptions: TTSOptions = {
      voice_id: voiceId,
      language_code: 'en-US',
      speaking_rate: 0.95,
      pitch: -1.0,
      volume_gain_db: 1.0,
      audio_encoding: 'MP3',
      preprocess_text: true
    };

    const requestOptions = { ...defaultOptions, ...options };

    try {
      // Use fetch directly for binary data
      const response = await fetch('/api/voice/synthesize', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: text,
          ...requestOptions
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      // Create blob URL from response
      const audioBlob = await response.blob();
      const url = URL.createObjectURL(audioBlob);
      
      return url;
    } catch (error) {
      console.error('TTS synthesis error:', error);
      throw new Error('Failed to synthesize speech');
    }
  }, [text, token, voiceId]);

  const synthesizeAndPlay = useCallback(async (options?: Partial<TTSOptions>) => {
    try {
      setIsLoading(true);
      setError(null);

      // Clear previous audio URL
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }

      const url = await synthesizeAudio(options);
      setAudioUrl(url);

      // Create new audio element
      const audio = new Audio(url);
      audioRef.current = audio;

      // Set up event listeners
      audio.addEventListener('loadedmetadata', () => {
        setDuration(audio.duration);
      });

      audio.addEventListener('timeupdate', () => {
        setCurrentTime(audio.currentTime);
      });

      audio.addEventListener('ended', () => {
        setIsPlaying(false);
        setCurrentTime(0);
      });

      audio.addEventListener('error', (e) => {
        console.error('Audio playback error:', e);
        setError('Audio playback failed');
        setIsPlaying(false);
      });

      // Set volume and play
      audio.volume = isMuted ? 0 : volume;
      await audio.play();
      setIsPlaying(true);

    } catch (error) {
      console.error('Error in synthesizeAndPlay:', error);
      setError(error instanceof Error ? error.message : 'Unknown error');
      toast({
        title: "Voice Synthesis Error",
        description: error instanceof Error ? error.message : "Failed to generate speech",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  }, [audioUrl, synthesizeAudio, volume, isMuted, toast]);

  // Auto-play functionality defined after synthesizeAndPlay
  useEffect(() => {
    if (autoPlay && text && !audioUrl) {
      synthesizeAndPlay();
    }
  }, [autoPlay, text, audioUrl, synthesizeAndPlay]);

  const togglePlayPause = useCallback(async () => {
    if (!audioRef.current && !audioUrl) {
      // No audio available, synthesize and play
      await synthesizeAndPlay();
      return;
    }

    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        try {
          await audioRef.current.play();
          setIsPlaying(true);
        } catch (error) {
          console.error('Playback error:', error);
          setError('Playback failed');
        }
      }
    }
  }, [audioUrl, isPlaying, synthesizeAndPlay]);  // Removed audioRef.current

  const handleSeek = useCallback((value: number[]) => {
    if (audioRef.current && duration > 0) {
      const newTime = (value[0] / 100) * duration;
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  }, [duration]);

  const handleVolumeChange = useCallback((value: number[]) => {
    const newVolume = value[0] / 100;
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : newVolume;
    }
  }, [isMuted]);

  const toggleMute = useCallback(() => {
    setIsMuted(!isMuted);
    if (audioRef.current) {
      audioRef.current.volume = !isMuted ? 0 : volume;
    }
  }, [isMuted, volume]);

  const downloadAudio = useCallback(async () => {
    try {
      if (!audioUrl) {
        setIsLoading(true);
        const url = await synthesizeAudio();
        setAudioUrl(url);
      }

      if (audioUrl) {
        const link = document.createElement('a');
        link.href = audioUrl;
        link.download = `speech_${messageId || Date.now()}.mp3`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch (error) {
      toast({
        title: "Download Failed",
        description: "Could not download audio file",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  }, [audioUrl, synthesizeAudio, messageId, toast]);

  const regenerateAudio = useCallback(async () => {
    // Clear existing audio
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    
    // Generate new audio
    await synthesizeAndPlay();
  }, [audioUrl, synthesizeAndPlay]);

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Button
          onClick={togglePlayPause}
          disabled={isLoading || !text.trim()}
          size="sm"
          variant="ghost"
          className="p-1 h-8 w-8"
        >
          {isLoading ? (
            <div className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin" />
          ) : isPlaying ? (
            <Pause className="w-3 h-3" />
          ) : (
            <Play className="w-3 h-3" />
          )}
        </Button>
        
        {duration > 0 && (
          <span className="text-xs text-gray-500">
            {formatTime(currentTime)}
          </span>
        )}
        
        {error && (
          <span className="text-xs text-red-500" title={error}>
            ⚠️
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-2 p-3 bg-gray-50 rounded-lg border ${className}`}>
      {/* Main controls */}
      <div className="flex items-center gap-3">
        <Button
          onClick={togglePlayPause}
          disabled={isLoading || !text.trim()}
          size="sm"
          className="flex-shrink-0"
        >
          {isLoading ? (
            <div className="w-4 h-4 border border-white border-t-transparent rounded-full animate-spin" />
          ) : isPlaying ? (
            <Pause className="w-4 h-4" />
          ) : (
            <Play className="w-4 h-4" />
          )}
        </Button>

        {/* Progress bar */}
        {duration > 0 && (
          <div className="flex-1 flex items-center gap-2">
            <span className="text-xs text-gray-500 min-w-[35px]">
              {formatTime(currentTime)}
            </span>
            <Slider
              value={[progressPercentage]}
              onValueChange={handleSeek}
              max={100}
              step={1}
              className="flex-1"
            />
            <span className="text-xs text-gray-500 min-w-[35px]">
              {formatTime(duration)}
            </span>
          </div>
        )}

        {/* Volume controls */}
        <div className="flex items-center gap-1">
          <Button
            onClick={toggleMute}
            size="sm"
            variant="ghost"
            className="p-1 h-6 w-6"
          >
            {isMuted ? (
              <VolumeX className="w-3 h-3" />
            ) : (
              <Volume2 className="w-3 h-3" />
            )}
          </Button>
          <Slider
            value={[volume * 100]}
            onValueChange={handleVolumeChange}
            max={100}
            step={5}
            className="w-16"
          />
        </div>

        {/* Action buttons */}
        <div className="flex gap-1">
          <Button
            onClick={regenerateAudio}
            disabled={isLoading}
            size="sm"
            variant="ghost"
            className="p-1 h-6 w-6"
            title="Regenerate audio"
          >
            <RotateCcw className="w-3 h-3" />
          </Button>
          
          <Button
            onClick={downloadAudio}
            disabled={isLoading}
            size="sm"
            variant="ghost"
            className="p-1 h-6 w-6"
            title="Download audio"
          >
            <Download className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}
    </div>
  );
};
