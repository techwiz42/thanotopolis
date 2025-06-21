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
  detectedLanguage: string | null;
  languageConfidence: number;
  isAutoDetecting: boolean;
  isManualOverride: boolean;
}

interface UseVoiceProps {
  conversationId: string;
  onTranscript?: (transcript: string, isFinal: boolean, speechFinal?: boolean) => void;
  languageCode?: string;
  onLanguageAutoUpdate?: (detectedLanguage: string) => void;
}

interface UseVoiceReturn extends VoiceState {
  toggleSTT: () => void;
  toggleTTS: () => void;
  speakText: (text: string) => Promise<void>;
  stopSpeaking: () => void;
  currentAudio: HTMLAudioElement | null;
  setManualOverride: () => void;
}

export const useVoice = ({ conversationId, onTranscript, languageCode, onLanguageAutoUpdate }: UseVoiceProps): UseVoiceReturn => {
  const { token } = useAuth();
  const { toast } = useToast();
  
  const [voiceState, setVoiceState] = useState<VoiceState>({
    isSTTEnabled: false,
    isTTSEnabled: false,
    isSTTActive: false,
    isTTSActive: false,
    isSTTConnecting: false,
    detectedLanguage: null,
    languageConfidence: 0,
    isAutoDetecting: false,
    isManualOverride: false
  });

  // Refs for managing resources
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const isTogglingSTTRef = useRef<boolean>(false);

  // Create STT options that include the current language
  const sttOptions = useMemo(() => ({
    token: token || '', // Pass the authentication token
    languageCode: languageCode || 'auto', // Use current language or auto-detection
    model: 'nova-2', // Use nova-2 for better multilingual support
    onTranscription: (text: string, isFinal: boolean) => {
      if (onTranscript) {
        onTranscript(text, isFinal, isFinal); // speechFinal = isFinal for simplicity
      }
    },
    onConnectionChange: (isConnected: boolean) => {
      console.log('STT connection change:', isConnected);
      setVoiceState(prev => ({ 
        ...prev, 
        isSTTActive: isConnected && prev.isSTTEnabled,
        isSTTConnecting: !isConnected && prev.isSTTEnabled,
        isAutoDetecting: isConnected && prev.isSTTEnabled && (languageCode === 'auto' || !languageCode)
      }));
    },
    onLanguageDetected: (language: string, confidence: number) => {
      console.log('Language detected:', language, 'with confidence:', confidence);
      setVoiceState(prev => ({ 
        ...prev, 
        detectedLanguage: language,
        languageConfidence: confidence,
        isAutoDetecting: prev.isSTTActive && (languageCode === 'auto' || !languageCode)
      }));

      // Auto-update language selector if confidence is high and we're in auto-detection mode
      // Temporarily lowered threshold from 0.8 to 0.6 for testing
      if (confidence >= 0.6 && 
          (languageCode === 'auto' || !languageCode) && 
          onLanguageAutoUpdate) {
        console.log('High confidence language detection, auto-updating language selector to:', language);
        onLanguageAutoUpdate(language);
      }
    },
    onError: (error: string) => {
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
        isSTTConnecting: false,
        isAutoDetecting: false
      }));
    }
  }), [token, languageCode, onTranscript, toast, onLanguageAutoUpdate]);

  // Initialize streaming STT service with current options
  const sttService = useStreamingSpeechToText(sttOptions);


  // Store sttService in a ref to avoid cleanup dependency issues
  const sttServiceRef = useRef(sttService);
  sttServiceRef.current = sttService;

  // Cleanup function - use ref to avoid dependency issues
  const cleanup = useCallback(() => {
    console.log('Voice hook cleanup called');
    // Stop STT service using ref
    if (sttServiceRef.current?.isListening) {
      console.log('Stopping STT service from cleanup');
      sttServiceRef.current.stopListening();
    }

    // Stop any playing audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
  }, []); // Empty dependencies - use refs instead

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
      
      await sttServiceRef.current.startListening();
      
      // Don't check isConnected immediately - connection happens asynchronously
      // The onConnectionChange callback will update the state when connection is ready
      setVoiceState(prev => ({ ...prev, isSTTConnecting: false }));
      return true;
      
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
  }, [token, toast]); // Remove sttService dependency

  // Stop STT
  const stopSTT = useCallback(() => {
    console.log('Stopping STT...');
    
    sttServiceRef.current.stopListening();

    setVoiceState(prev => ({ 
      ...prev, 
      isSTTActive: false
    }));
    
    console.log('STT stopped');
  }, []); // Remove sttService dependency

  // Toggle STT
  const toggleSTT = useCallback(async () => {
    // Prevent multiple simultaneous toggles
    if (isTogglingSTTRef.current) {
      console.log('STT toggle already in progress, ignoring...');
      return;
    }

    isTogglingSTTRef.current = true;

    try {
      setVoiceState(prev => {
        if (prev.isSTTEnabled) {
          // Disable STT
          console.log('Disabling STT...');
          stopSTT();
          // Reset toggle ref immediately for disable
          isTogglingSTTRef.current = false;
          return { ...prev, isSTTEnabled: false };
        } else {
          // Enable STT - check if already listening to prevent duplicates
          if (sttServiceRef.current.isListening) {
            console.log('STT already listening, skipping initialization...');
            isTogglingSTTRef.current = false;
            return { ...prev, isSTTEnabled: true };
          }
          
          console.log('Enabling STT...');
          
          // Initialize in background without blocking state update
          initializeSTT().then(success => {
            if (!success) {
              console.log('STT initialization failed, reverting...');
              setVoiceState(current => ({ ...current, isSTTEnabled: false }));
            }
          }).finally(() => {
            isTogglingSTTRef.current = false;
          });
          
          return { ...prev, isSTTEnabled: true };
        }
      });
    } catch (error) {
      console.error('Error in toggleSTT:', error);
      isTogglingSTTRef.current = false;
    }
  }, [initializeSTT, stopSTT]);

  // Update state based on service state
  useEffect(() => {
    setVoiceState(prev => ({
      ...prev,
      isSTTActive: sttService.isConnected && prev.isSTTEnabled,
      isSTTConnecting: sttService.isListening && !sttService.isConnected && prev.isSTTEnabled
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

    // Remember if STT was active before starting TTS
    const wasSTTActive = voiceState.isSTTEnabled && voiceState.isSTTActive;
    
    try {
      // Stop any currently playing audio BEFORE setting active state
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      
      // Temporarily pause STT to prevent feedback
      if (wasSTTActive) {
        console.log('Pausing STT during TTS playback to prevent feedback');
        sttServiceRef.current.stopListening();
      }
      
      setVoiceState(prev => ({ ...prev, isTTSActive: true }));

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
        
        // Resume STT if it was active before TTS started
        if (wasSTTActive && voiceState.isSTTEnabled) {
          console.log('Resuming STT after TTS playback completed');
          setTimeout(() => {
            sttServiceRef.current.startListening().catch(console.error);
          }, 100); // Small delay to ensure audio cleanup
        }
      };

      audio.onerror = () => {
        setVoiceState(prev => ({ ...prev, isTTSActive: false }));
        URL.revokeObjectURL(audioUrl);
        currentAudioRef.current = null;
        console.error('Error playing TTS audio');
        
        // Resume STT if it was active before TTS started (even on error)
        if (wasSTTActive && voiceState.isSTTEnabled) {
          console.log('Resuming STT after TTS error');
          setTimeout(() => {
            sttServiceRef.current.startListening().catch(console.error);
          }, 100);
        }
      };

      await audio.play();
    } catch (error) {
      console.error('Error with TTS:', error);
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      
      // Resume STT if it was active before TTS started (even on error)
      if (wasSTTActive && voiceState.isSTTEnabled) {
        console.log('Resuming STT after TTS initialization error');
        setTimeout(() => {
          sttServiceRef.current.startListening().catch(console.error);
        }, 100);
      }
      
      toast({
        title: "Voice Output Error",
        description: "Failed to generate speech",
        variant: "destructive"
      });
    }
  }, [voiceState, token, toast]);

  // Stop speaking
  const stopSpeaking = useCallback(() => {
    const wasTTSActive = voiceState.isTTSActive;
    
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    setVoiceState(prev => ({ ...prev, isTTSActive: false }));
    
    // If TTS was manually stopped and STT is enabled but not active, try to resume STT
    if (wasTTSActive && voiceState.isSTTEnabled && !voiceState.isSTTActive) {
      console.log('Resuming STT after manually stopping TTS');
      setTimeout(() => {
        sttServiceRef.current.startListening().catch(console.error);
      }, 100);
    }
  }, [voiceState]);

  // Set manual override flag
  const setManualOverride = useCallback(() => {
    setVoiceState(prev => ({ 
      ...prev, 
      isManualOverride: true,
      isAutoDetecting: false
    }));
  }, []);

  // Handle language changes while STT is enabled
  const lastLanguageRef = useRef<string | undefined>(languageCode);
  useEffect(() => {
    // Only restart if language actually changed and STT is enabled
    if (voiceState.isSTTEnabled && 
        languageCode && 
        languageCode !== lastLanguageRef.current && 
        lastLanguageRef.current !== undefined) {
      
      console.log('Language changed from', lastLanguageRef.current, 'to', languageCode, '- restarting STT connection');
      
      // Stop current connection and ensure cleanup
      sttServiceRef.current.stopListening();
      
      // Wait for cleanup and state updates, then restart with new language
      const restartSTT = async () => {
        // Wait for service to fully stop
        let attempts = 0;
        const maxAttempts = 10;
        
        while (sttServiceRef.current.isListening && attempts < maxAttempts) {
          console.log(`Waiting for STT to stop... attempt ${attempts + 1}`);
          await new Promise(resolve => setTimeout(resolve, 100));
          attempts++;
        }
        
        if (attempts >= maxAttempts) {
          console.warn('STT did not stop within expected time, forcing restart...');
        }
        
        console.log('Attempting to restart STT with new language after cleanup...');
        await initializeSTT();
      };
      
      setTimeout(restartSTT, 200); // Shorter initial delay, but with polling
    }
    
    // Update last language reference
    lastLanguageRef.current = languageCode;
  }, [languageCode, voiceState.isSTTEnabled]); // Remove sttService and initializeSTT to prevent loops
  
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
    stopSpeaking,
    currentAudio: currentAudioRef.current,
    setManualOverride
  };
};
