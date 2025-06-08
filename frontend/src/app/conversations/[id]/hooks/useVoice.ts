// src/app/conversations/[id]/hooks/useVoice.ts
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';
import { useStreamingSpeechToText } from '@/services/voice/StreamingSpeechToTextService';

interface VoiceState {
  isSTTEnabled: boolean;
  isTTSEnabled: boolean;
  isSTTActive: boolean;
  isTTSActive: boolean;
  isSTTConnecting: boolean;
}

interface UseVoiceProps {
  conversationId: string;
  onTranscript?: (transcript: string, isFinal: boolean, speechFinal?: boolean) => void;
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
    isSTTConnecting: false
  });

  // Refs for managing resources
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  // Initialize streaming STT service
  const sttService = useStreamingSpeechToText({
    token: token || '', // Pass the authentication token
    languageCode: 'en-US',
    model: 'nova-2',
    onTranscription: (text, isFinal) => {
      if (onTranscript) {
        onTranscript(text, isFinal, isFinal); // speechFinal = isFinal for simplicity
      }
    },
    onConnectionChange: (isConnected) => {
      console.log('STT connection change:', isConnected);
      setVoiceState(prev => ({ 
        ...prev, 
        isSTTActive: isConnected,
        isSTTConnecting: !isConnected && prev.isSTTEnabled
      }));
    },
    onError: (error) => {
      console.error('STT Error:', error);
      toast({
        title: "Voice Input Error",
        description: error,
        variant: "destructive"
      });
      setVoiceState(prev => ({ 
        ...prev, 
        isSTTEnabled: false,
        isSTTActive: false,
        isSTTConnecting: false
      }));
    }
  });

  // Cleanup function
  const cleanup = useCallback(() => {
    console.log('Voice hook cleanup called');
    // Stop STT service
    if (sttService.isListening) {
      console.log('Stopping STT service from cleanup');
      sttService.stopListening();
    }

    // Stop any playing audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
  }, []); // Remove sttService dependency to prevent constant re-runs

  // Initialize STT service
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
      
      await sttService.startListening();
      
      if (sttService.isConnected) {
        setVoiceState(prev => ({ 
          ...prev, 
          isSTTConnecting: false,
          isSTTActive: true
        }));
        return true;
      } else {
        setVoiceState(prev => ({ ...prev, isSTTConnecting: false }));
        return false;
      }
      
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
  }, [token, toast, sttService]);

  // Stop STT
  const stopSTT = useCallback(() => {
    console.log('Stopping STT...');
    
    sttService.stopListening();

    setVoiceState(prev => ({ 
      ...prev, 
      isSTTActive: false
    }));
    
    console.log('STT stopped');
  }, [sttService]);

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

  // Update state based on service state
  useEffect(() => {
    setVoiceState(prev => ({
      ...prev,
      isSTTActive: sttService.isConnected,
      isSTTConnecting: sttService.isListening && !sttService.isConnected
    }));
  }, [sttService.isConnected, sttService.isListening]);

  // Toggle TTS
  const toggleTTS = useCallback(() => {
    setVoiceState(prev => {
      // Stop any currently playing audio when disabling TTS
      if (prev.isTTSEnabled && currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      
      return { 
        ...prev, 
        isTTSEnabled: !prev.isTTSEnabled,
        isTTSActive: prev.isTTSEnabled ? false : prev.isTTSActive
      };
    });
  }, []);

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
  }, [voiceState, token, toast]);

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
