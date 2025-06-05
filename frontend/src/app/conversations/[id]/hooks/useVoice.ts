// src/app/conversations/[id]/hooks/useVoice.ts
import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';

interface VoiceState {
  isSTTEnabled: boolean;
  isTTSEnabled: boolean;
  isSTTActive: boolean;
  isTTSActive: boolean;
  isSTTConnecting: boolean;
  isRecording: boolean;
}

interface UseVoiceProps {
  conversationId: string;
  onTranscript?: (transcript: string, isFinal: boolean) => void;
}

interface UseVoiceReturn extends VoiceState {
  toggleSTT: () => void;
  toggleTTS: () => void;
  speakText: (text: string) => Promise<void>;
  stopSpeaking: () => void;
}

export const useVoice = ({ conversationId, onTranscript }: UseVoiceProps): UseVoiceReturn => {
  const { token } = useAuth();
  const { toast } = useToast();
  
  const [voiceState, setVoiceState] = useState<VoiceState>({
    isSTTEnabled: false,
    isTTSEnabled: false,
    isSTTActive: false,
    isTTSActive: false,
    isSTTConnecting: false,
    isRecording: false
  });

  // Refs for managing resources
  const sttWebSocketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup function
  const cleanup = useCallback(() => {
    // Stop recording
    if (mediaRecorderRef.current && voiceState.isRecording) {
      mediaRecorderRef.current.stop();
    }
    
    // Close audio stream
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }
    
    // Close STT WebSocket
    if (sttWebSocketRef.current) {
      sttWebSocketRef.current.close();
      sttWebSocketRef.current = null;
    }

    // Stop any playing audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }

    // Clear intervals
    if (recordingIntervalRef.current) {
      clearInterval(recordingIntervalRef.current);
      recordingIntervalRef.current = null;
    }
  }, [voiceState.isRecording]);

  // Initialize STT WebSocket connection
  const initializeSTT = useCallback(async () => {
    if (!token) {
      toast({
        title: "Authentication Required",
        description: "Please log in to use voice features",
        variant: "destructive"
      });
      return false;
    }

    try {
      setVoiceState(prev => ({ ...prev, isSTTConnecting: true }));

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      
      audioStreamRef.current = stream;

      // Create WebSocket connection to STT service
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const backendHost = process.env.NEXT_PUBLIC_API_URL ? new URL(process.env.NEXT_PUBLIC_API_URL).host : 'localhost:8000';
      const wsUrl = `${protocol}//${backendHost}/api/ws/voice/streaming-stt?token=${encodeURIComponent(token)}`;
      
      const ws = new WebSocket(wsUrl);
      sttWebSocketRef.current = ws;

      return new Promise<boolean>((resolve) => {
        ws.onopen = () => {
          console.log('STT WebSocket connected');
          
          // Initialize MediaRecorder for audio capture
          const mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
          });
          
          mediaRecorderRef.current = mediaRecorder;

          mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
              ws.send(event.data);
            }
          };

          setVoiceState(prev => ({ 
            ...prev, 
            isSTTConnecting: false, 
            isSTTActive: true,
            isRecording: true
          }));

          // Start recording
          mediaRecorder.start(100); // Send data every 100ms
          
          resolve(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'transcript' && data.transcript) {
              onTranscript?.(data.transcript, data.is_final || data.speech_final);
            }
          } catch (error) {
            console.error('Error parsing STT message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('STT WebSocket error:', error);
          toast({
            title: "Voice Input Error",
            description: "Failed to connect to speech recognition service",
            variant: "destructive"
          });
          setVoiceState(prev => ({ ...prev, isSTTConnecting: false }));
          resolve(false);
        };

        ws.onclose = () => {
          console.log('STT WebSocket closed');
          setVoiceState(prev => ({ 
            ...prev, 
            isSTTActive: false, 
            isRecording: false 
          }));
        };
      });
    } catch (error) {
      console.error('Error initializing STT:', error);
      toast({
        title: "Microphone Access Denied",
        description: "Please allow microphone access to use voice input",
        variant: "destructive"
      });
      setVoiceState(prev => ({ ...prev, isSTTConnecting: false }));
      return false;
    }
  }, [token, toast, onTranscript]);

  // Stop STT
  const stopSTT = useCallback(() => {
    if (mediaRecorderRef.current && voiceState.isRecording) {
      mediaRecorderRef.current.stop();
    }
    
    if (sttWebSocketRef.current) {
      // Send stop signal
      sttWebSocketRef.current.send(JSON.stringify({ type: 'stop_transcription' }));
      sttWebSocketRef.current.close();
      sttWebSocketRef.current = null;
    }
    
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }

    setVoiceState(prev => ({ 
      ...prev, 
      isSTTActive: false, 
      isRecording: false 
    }));
  }, [voiceState.isRecording]);

  // Toggle STT
  const toggleSTT = useCallback(async () => {
    if (voiceState.isSTTEnabled) {
      stopSTT();
      setVoiceState(prev => ({ ...prev, isSTTEnabled: false }));
    } else {
      const success = await initializeSTT();
      if (success) {
        setVoiceState(prev => ({ ...prev, isSTTEnabled: true }));
      }
    }
  }, [voiceState.isSTTEnabled, initializeSTT, stopSTT]);

  // Toggle TTS
  const toggleTTS = useCallback(() => {
    setVoiceState(prev => ({ ...prev, isTTSEnabled: !prev.isTTSEnabled }));
    
    // Stop any currently playing audio when disabling TTS
    if (voiceState.isTTSEnabled && currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
    }
  }, [voiceState.isTTSEnabled]);

  // Speak text using TTS
  const speakText = useCallback(async (text: string) => {
    if (!voiceState.isTTSEnabled || !token || !text.trim()) {
      return;
    }

    try {
      setVoiceState(prev => ({ ...prev, isTTSActive: true }));

      // Stop any currently playing audio
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
      }

      const response = await fetch('/api/voice/tts/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          text: text,
          stability: '0.5',
          similarity_boost: '0.5',
          style: '0.0',
          use_speaker_boost: 'true'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to generate speech');
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      currentAudioRef.current = audio;

      audio.onended = () => {
        setVoiceState(prev => ({ ...prev, isTTSActive: false }));
        URL.revokeObjectURL(audioUrl);
        currentAudioRef.current = null;
      };

      audio.onerror = () => {
        setVoiceState(prev => ({ ...prev, isTTSActive: false }));
        URL.revokeObjectURL(audioUrl);
        currentAudioRef.current = null;
        console.error('Error playing TTS audio');
      };

      await audio.play();
    } catch (error) {
      console.error('Error with TTS:', error);
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      toast({
        title: "Voice Output Error",
        description: "Failed to generate speech",
        variant: "destructive"
      });
    }
  }, [voiceState.isTTSEnabled, token, toast]);

  // Stop speaking
  const stopSpeaking = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    setVoiceState(prev => ({ ...prev, isTTSActive: false }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return {
    ...voiceState,
    toggleSTT,
    toggleTTS,
    speakText,
    stopSpeaking
  };
};
