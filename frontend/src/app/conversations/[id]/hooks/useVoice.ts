// Enhanced useVoice hook with advanced multi-engine language detection
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';
import { useStreamingSpeechToText } from '@/services/voice/StreamingSpeechToTextService';
import { advancedLanguageDetection, LanguageDetectionResult } from '@/services/voice/AdvancedLanguageDetection';
import { cleanTextForTTS, chunkTextForTTS } from '../utils/voiceUtils';

// Simple fallback detection function
function detectLanguageFallback(text: string): { language: string | null, confidence: number } {
  if (!text || text.length < 5) return { language: null, confidence: 0 };
  
  const lowerText = text.toLowerCase();
  const patterns = {
    'es': {
      words: ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'como', 'está', 'muy', 'bien', 'sí', 'gracias', 'hola', 'qué', 'cómo', 'dónde'],
      endings: ['ción', 'dad', 'mente', 'ando', 'endo'],
      chars: ['ñ', 'á', 'é', 'í', 'ó', 'ú']
    },
    'fr': {
      words: ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir', 'que', 'pour', 'dans', 'ce', 'son', 'une', 'sur', 'avec', 'ne', 'se', 'pas', 'tout', 'plus', 'par', 'grand', 'en', 'je', 'tu', 'nous', 'vous', 'ils', 'bonjour', 'merci', 'où', 'comment'],
      endings: ['tion', 'ment', 'eur', 'euse', 'ique'],
      chars: ['à', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'ù', 'û', 'ü', 'ÿ', 'ç']
    }
  };
  
  const scores: { [key: string]: number } = {};
  
  for (const [lang, data] of Object.entries(patterns)) {
    let score = 0;
    const words = lowerText.split(/\s+/);
    for (const word of words) {
      if (data.words.includes(word)) score += 2;
    }
    for (const ending of data.endings) {
      const matches = lowerText.match(new RegExp(ending + '\\b', 'g'));
      if (matches) score += matches.length * 1.5;
    }
    for (const char of data.chars) {
      const matches = lowerText.match(new RegExp(char, 'g'));
      if (matches) score += matches.length * 1;
    }
    scores[lang] = score;
  }
  
  // Remove English bias - let languages compete fairly
  const sortedLangs = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  const topLang = sortedLangs[0];
  
  if (topLang && topLang[1] > 0) {
    const confidence = Math.min(0.9, topLang[1] / Math.max(1, text.length / 4));
    return { language: topLang[0], confidence: Math.max(0.1, confidence) };
  }
  
  return { language: null, confidence: 0 };
}

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
  sessionLanguageLock: {
    language: string | null;
    confidence: number;
    timestamp: number;
    isLocked: boolean;
  };
  resetLanguageLock: () => void;
  clearDetectionAccumulation: () => void;
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

  // Session language lock state - locks when we're very confident about a language
  const [sessionLanguageLock, setSessionLanguageLock] = useState({
    language: null as string | null,
    confidence: 0,
    timestamp: 0,
    isLocked: false
  });

  // Audio state for TTS
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  
  // Track user override state
  const userOverrideRef = useRef(false);
  
  // Track session language lock to avoid dependency issues
  const sessionLanguageLockRef = useRef(sessionLanguageLock);
  
  // Track previous language to detect changes
  const previousLanguageRef = useRef(languageCode);
  
  // Track STT state before TTS starts
  const sttWasEnabledRef = useRef(false);
  
  // Update ref when state changes
  useEffect(() => {
    sessionLanguageLockRef.current = sessionLanguageLock;
  }, [sessionLanguageLock]);
  
  // Clear language lock
  const resetLanguageLock = useCallback(() => {
    setSessionLanguageLock({
      language: null,
      confidence: 0,
      timestamp: 0,
      isLocked: false
    });
    console.log('🔓 Language lock reset');
  }, []);

  // Set manual override flag when user manually changes language
  const setManualOverride = useCallback(() => {
    userOverrideRef.current = true;
    setVoiceState(prev => ({ ...prev, isManualOverride: true }));
    console.log('👤 Manual language override detected');
  }, []);

  // Clear accumulated language detection data
  const clearDetectionAccumulation = useCallback(() => {
    console.log('🧹 Clearing language detection accumulation');
    // This could clear any accumulated detection data if needed
  }, []);

  // VOICE-BASED LANGUAGE DETECTION (for speech, not text!)
  const performAdvancedLanguageDetection = useCallback(async (transcript: string) => {
    if (!transcript || transcript.length < 10) return;
    
    console.log('🎤 VOICE DETECTION analyzing speech transcript:', transcript.substring(0, 50) + '...');
    
    const text = transcript.toLowerCase().trim();
    
    // Helper function to set detected language
    function setDetectedLanguage(language: string, confidence: number, method: string) {
      console.log(`🎯 VOICE DETECTED: ${language} (${Math.round(confidence * 100)}%) via ${method}`);
      
      setVoiceState(prev => ({
        ...prev,
        detectedLanguage: language,
        languageConfidence: confidence,
      }));
      
      // Auto-update if confidence is high enough
      if (onLanguageAutoUpdate && confidence > 0.85 && !sessionLanguageLockRef.current.isLocked) {
        onLanguageAutoUpdate(language);
        
        toast({
          title: "Language Detected",
          description: `${language.toUpperCase()} detected from speech (${Math.round(confidence * 100)}%)`,
          variant: "default"
        });
      }
    }
    
    // Spanish - distinctive phonetic words
    if (/\b(hola|gracias|buenos|días|señor|señora|cómo|está|donde|cuando|porque|español|muy|bien|por|favor|hasta|luego)\b/.test(text)) {
      console.log('🔥 VOICE: Spanish via distinctive word');
      setDetectedLanguage('es', 0.95, 'spanish_distinctive_word');
      return;
    }
    
    // French - distinctive phonetic words  
    if (/\b(bonjour|merci|français|comment|être|avoir|faire|aller|très|tout|maintenant|toujours|jamais|aujourd|hier|demain)\b/.test(text)) {
      console.log('🔥 VOICE: French via distinctive word');
      setDetectedLanguage('fr', 0.94, 'french_distinctive_word');
      return;
    }
    
    // Spanish phonetic patterns
    const spanishPatterns = [
      /\b(el|la|los|las)\s+\w+/g, // Articles + nouns
      /\b\w+(ción|sión)\b/g, // Common Spanish endings
      /\b(que|pero|también|siempre|nunca)\b/g, // Common words
      /\b(yo|tu|el|ella|nosotros|ustedes|ellos)\b/g // Pronouns
    ];
    
    let spanishMatches = 0;
    spanishPatterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) spanishMatches += matches.length;
    });
    
    if (spanishMatches >= 2) {
      console.log('🔥 VOICE: Spanish via phonetic patterns');
      setDetectedLanguage('es', 0.91 + Math.min(0.07, spanishMatches * 0.02), 'spanish_phonetic');
      return;
    }
    
    // French phonetic patterns
    const frenchPatterns = [
      /\b(le|la|les|un|une|des)\s+\w+/g, // Articles + nouns
      /\b\w+(tion|ment|eur|euse)\b/g, // French endings
      /\b(que|mais|avec|pour|dans|sans)\b/g, // Common words
      /\b(je|tu|il|elle|nous|vous|ils|elles)\b/g // Pronouns
    ];
    
    let frenchMatches = 0;
    frenchPatterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) frenchMatches += matches.length;
    });
    
    if (frenchMatches >= 2) {
      console.log('🔥 VOICE: French via phonetic patterns');
      setDetectedLanguage('fr', 0.89 + Math.min(0.08, frenchMatches * 0.02), 'french_phonetic');
      return;
    }
    
    // German phonetic patterns
    const germanPatterns = [
      /\b(der|die|das|ein|eine)\s+\w+/g, // Articles + nouns
      /\b\w+(ung|heit|keit|schaft)\b/g, // German endings
      /\b(und|aber|oder|wenn|weil)\b/g, // Common conjunctions
      /\b(ich|du|er|sie|es|wir|ihr|sie)\b/g // Pronouns
    ];
    
    let germanMatches = 0;
    germanPatterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) germanMatches += matches.length;
    });
    
    if (germanMatches >= 2) {
      console.log('🔥 VOICE: German via phonetic patterns');
      setDetectedLanguage('de', 0.86 + Math.min(0.08, germanMatches * 0.02), 'german_phonetic');
      return;
    }
    
    // 3️⃣ ENGLISH - ONLY with high certainty and no other language indicators
    
    const englishDistinctive = /\b(hello|thank|please|english|would|could|should|through|thought|right|night|light)\b/.test(text);
    const englishCommon = text.match(/\b(the|and|that|have|for|not|with|you|this|but|from|they|she|been)\b/g);
    
    if (englishDistinctive && englishCommon && englishCommon.length >= 3 && text.length > 20) {
      console.log('🔥 VOICE: English via distinctive + common words');
      setDetectedLanguage('en', 0.82, 'english_high_certainty');
      return;
    }
    
    console.log('❌ No reliable voice-based detection possible with text:', text);
  }, [onLanguageAutoUpdate, toast]);

  // Handle transcription with language detection
  const handleTranscription = useCallback((text: string, isFinal: boolean) => {
    if (onTranscript) {
      onTranscript(text, isFinal, isFinal);
    }
    
    // Perform language detection on final transcripts
    if (isFinal && text && text.length > 8 && !userOverrideRef.current) {
      performAdvancedLanguageDetection(text);
    }
  }, [onTranscript, performAdvancedLanguageDetection]);

  // Handle connection changes
  const handleConnectionChange = useCallback((isConnected: boolean) => {
    console.log('STT connection change:', isConnected);
    setVoiceState(prev => ({ 
      ...prev, 
      isSTTActive: isConnected && prev.isSTTEnabled,
      isSTTConnecting: !isConnected && prev.isSTTEnabled,
      isAutoDetecting: isConnected && prev.isSTTEnabled && (languageCode === 'auto' || !languageCode)
    }));
  }, [languageCode]);

  // Handle built-in language detection
  const handleLanguageDetected = useCallback((detectedLang: string, confidence: number) => {
    console.log('🔬 Built-in detection result:', detectedLang, confidence);
    
    // Only use built-in detection if we don't have better detection yet
    setVoiceState(prev => {
      if (!prev.detectedLanguage || prev.languageConfidence < confidence) {
        return {
          ...prev,
          detectedLanguage: detectedLang,
          languageConfidence: confidence,
        };
      }
      return prev;
    });
  }, []);

  // Create STT options that include the current language
  const sttOptions = useMemo(() => ({
    token: token || '',
    languageCode: languageCode || 'auto',
    model: 'nova-2',
    onTranscription: handleTranscription,
    onConnectionChange: handleConnectionChange,
    onLanguageDetected: handleLanguageDetected
  }), [token, languageCode, handleTranscription, handleConnectionChange, handleLanguageDetected]);

  // STT service hook
  const {
    isConnected: sttConnected,
    startListening: startSTT,
    stopListening: stopSTT,
    error: sttError,
    isListening: isRecording
  } = useStreamingSpeechToText(sttOptions);

  // Handle language changes - restart STT connection when language changes
  useEffect(() => {
    if (languageCode !== previousLanguageRef.current && voiceState.isSTTEnabled) {
      console.log('Language changed from', previousLanguageRef.current, 'to', languageCode, '- restarting STT');
      
      // Stop current STT
      stopSTT();
      
      // Restart STT with new language after a brief delay
      setTimeout(async () => {
        try {
          await startSTT();
          console.log('STT restarted with new language:', languageCode);
        } catch (error) {
          console.error('Failed to restart STT with new language:', error);
          setVoiceState(prev => ({ 
            ...prev, 
            isSTTEnabled: false, 
            isSTTActive: false, 
            isSTTConnecting: false 
          }));
        }
      }, 500);
    }
    
    // Update the previous language reference
    previousLanguageRef.current = languageCode;
  }, [languageCode, voiceState.isSTTEnabled, stopSTT, startSTT]);

  // Update STT state based on service state
  useEffect(() => {
    setVoiceState(prev => ({
      ...prev,
      isSTTActive: isRecording && prev.isSTTEnabled,
      isSTTConnecting: !sttConnected && prev.isSTTEnabled
    }));
  }, [isRecording, sttConnected]);

  // Toggle STT
  const toggleSTT = useCallback(async () => {
    try {
      if (!voiceState.isSTTEnabled) {
        await startSTT();
        setVoiceState(prev => ({ ...prev, isSTTEnabled: true, isAutoDetecting: true }));
      } else {
        stopSTT();
        setVoiceState(prev => ({ 
          ...prev, 
          isSTTEnabled: false, 
          isSTTActive: false, 
          isSTTConnecting: false,
          isAutoDetecting: false 
        }));
      }
    } catch (error) {
      console.error('STT toggle error:', error);
      toast({
        title: "Voice Input Error",
        description: error instanceof Error ? error.message : "Failed to toggle voice input",
        variant: "destructive"
      });
    }
  }, [voiceState.isSTTEnabled, startSTT, stopSTT, toast]);

  // Toggle TTS
  const toggleTTS = useCallback(() => {
    setVoiceState(prev => ({ ...prev, isTTSEnabled: !prev.isTTSEnabled }));
    
    // Stop current audio if disabling TTS - but only if manually disabling
    if (voiceState.isTTSEnabled && currentAudio) {
      try {
        // Mark as intentionally stopped to prevent error logging
        currentAudio.dataset.intentionallyStopped = 'true';
        currentAudio.pause();
        setCurrentAudio(null);
        setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      } catch (error) {
        console.warn('Error stopping TTS audio during toggle:', error);
        setCurrentAudio(null);
        setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      }
    }
  }, [voiceState.isTTSEnabled, currentAudio]);

  // Create refs for stable values to avoid dependency issues
  const tokenRef = useRef(token);
  const voiceStateRef = useRef(voiceState);
  const languageCodeRef = useRef(languageCode);
  const stopSTTRef = useRef(stopSTT);
  const startSTTRef = useRef(startSTT);
  
  // Update refs when values change
  useEffect(() => {
    tokenRef.current = token;
    voiceStateRef.current = voiceState;
    languageCodeRef.current = languageCode;
    stopSTTRef.current = stopSTT;
    startSTTRef.current = startSTT;
  }, [token, voiceState, languageCode, stopSTT, startSTT]);

  // Text-to-speech function with improved processing and chunking
  const speakText = useCallback(async (text: string) => {
    if (!voiceStateRef.current.isTTSEnabled || !text.trim()) return;

    // Capture state variables at the start to avoid closure issues
    const originalDetectionEnabled = voiceStateRef.current.isAutoDetecting;

    try {
      // Stop any currently playing audio with proper error handling
      if (currentAudio) {
        try {
          // Set a flag to indicate we're intentionally stopping
          currentAudio.dataset.intentionallyStopped = 'true';
          currentAudio.pause();
          setCurrentAudio(null);
        } catch (pauseError) {
          console.warn('Audio pause error (expected during interruption):', pauseError);
          setCurrentAudio(null);
        }
      }

      // Temporarily disable STT during TTS to prevent feedback
      sttWasEnabledRef.current = voiceStateRef.current.isSTTEnabled;
      if (sttWasEnabledRef.current) {
        console.log('🔇 Temporarily stopping STT during TTS to prevent feedback');
        try {
          stopSTTRef.current();
        } catch (sttStopError) {
          console.warn('Error stopping STT during TTS (non-critical):', sttStopError);
        }
      }

      setVoiceState(prev => ({ ...prev, isTTSActive: true }));

      // Get current language for stable voice selection
      const currentLanguage = voiceStateRef.current.detectedLanguage || languageCodeRef.current || 'en';
      
      // Split text into manageable chunks for long messages
      const textChunks = chunkTextForTTS(text, 800);
      console.log(`🎙️ TTS processing ${textChunks.length} chunks for language: ${currentLanguage}`);

      // Temporarily disable language detection during TTS to prevent drift
      if (originalDetectionEnabled) {
        setVoiceState(prev => ({ ...prev, isAutoDetecting: false }));
        console.log('🔒 Language detection disabled during TTS to prevent drift');
      }

      // Process each chunk sequentially
      for (let i = 0; i < textChunks.length; i++) {
        // Check if TTS is still enabled before processing chunk
        if (!voiceStateRef.current.isTTSEnabled) {
          console.log('🛑 TTS was disabled during processing, stopping playback');
          break;
        }
        
        const chunk = textChunks[i];
        console.log(`🎙️ Speaking chunk ${i + 1}/${textChunks.length}: "${chunk.substring(0, 50)}..."`);

        const formData = new FormData();
        formData.append('text', chunk); // Use cleaned and chunked text
        // Don't send voice_id to use backend default (TxGEqnHWrfWFTfGW9XjX - James voice)
        formData.append('output_format', 'mp3_44100_128');
        formData.append('stability', '0.5');
        formData.append('similarity_boost', '0.5');
        formData.append('style', '0.0');
        formData.append('use_speaker_boost', 'true');

        const response = await fetch('/api/voice/tts/synthesize', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${tokenRef.current}`
          },
          body: formData
        });

        if (!response.ok) {
          throw new Error(`TTS API error: ${response.status}`);
        }

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);

        setCurrentAudio(audio);

        // Wait for this chunk to finish before starting the next one
        await new Promise<void>((resolve, reject) => {
          // Check if TTS was disabled before starting playback
          if (!voiceStateRef.current.isTTSEnabled) {
            console.log('🛑 TTS disabled before chunk playback, skipping');
            URL.revokeObjectURL(audioUrl);
            resolve();
            return;
          }
          
          audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            resolve();
          };

          audio.onerror = () => {
            URL.revokeObjectURL(audioUrl);
            console.error('Audio playback error for chunk', i + 1);
            reject(new Error('Audio playback failed'));
          };

          // Improved audio play with proper error handling
          audio.play().catch(playError => {
            // Check if this was an intentional interruption
            if (playError.name === 'AbortError' && audio.dataset.intentionallyStopped) {
              console.log('Audio playback intentionally stopped for chunk', i + 1);
              URL.revokeObjectURL(audioUrl);
              resolve(); // Don't treat as error
            } else if (playError.name === 'AbortError') {
              // Handle unintentional abort (browser interruption, etc.)
              console.log('TTS interrupted (this is normal when starting new speech)');
              URL.revokeObjectURL(audioUrl);
              resolve(); // Don't treat as error
            } else {
              console.error('Audio playback error:', playError);
              URL.revokeObjectURL(audioUrl);
              reject(playError);
            }
          });
        });

        // Small pause between chunks
        if (i < textChunks.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 200));
        }
      }

      // All chunks completed successfully
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      setCurrentAudio(null);
      
      // Re-enable language detection if it was enabled before TTS
      if (originalDetectionEnabled) {
        setVoiceState(prev => ({ ...prev, isAutoDetecting: true }));
        console.log('🔓 Language detection re-enabled after TTS completion');
      }
      
      // Re-enable STT if it was enabled before TTS started
      if (sttWasEnabledRef.current) {
        console.log('🎤 Restarting STT after successful TTS completion');
        try {
          // Add a small delay to ensure TTS cleanup is complete
          await new Promise(resolve => setTimeout(resolve, 500));
          await startSTTRef.current();
        } catch (error) {
          console.error('Failed to restart STT after TTS:', error);
          // Don't propagate this error, TTS was successful
        }
      }

    } catch (error) {
      // Enhanced error logging with context
      const textChunks = chunkTextForTTS(text, 800); // Get chunks for context
      const errorContext = {
        chunkIndex: 0, // Error occurred during setup or processing
        totalChunks: textChunks?.length || 0,
        textLength: text.length,
        isSTTEnabled: sttWasEnabledRef.current,
        currentLanguage: voiceStateRef.current.detectedLanguage || languageCodeRef.current || 'en',
        errorType: (error as Error)?.name || 'Unknown'
      };
      
      console.error('TTS error with context:', error, errorContext);
      
      // Create more specific error messages for debugging
      let errorMessage = "TTS playback failed";
      if ((error as Error)?.name === 'AbortError') {
        errorMessage = "TTS interrupted (this is normal when starting new speech)";
        console.log(errorMessage); // Log as info, not error
      } else if ((error as Error)?.message?.includes('STT connection') || (error as Error)?.message?.includes('connection')) {
        errorMessage = "TTS interrupted due to microphone connection issue";
      } else if ((error as Error)?.message?.includes('long output')) {
        errorMessage = "Long TTS output was interrupted";
      }
      
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      setCurrentAudio(null);
      
      // Re-enable language detection even on error
      if (originalDetectionEnabled) {
        setVoiceState(prev => ({ ...prev, isAutoDetecting: true }));
        console.log('🔓 Language detection re-enabled after TTS error');
      }
      
      // Re-enable STT if it was enabled before TTS started (even on error)
      if (sttWasEnabledRef.current) {
        console.log('🎤 Attempting to restart STT after TTS error');
        try {
          // Add a small delay to ensure cleanup is complete
          await new Promise(resolve => setTimeout(resolve, 500));
          await startSTTRef.current();
        } catch (sttError) {
          console.error('Failed to restart STT after TTS error:', sttError);
        }
      }
      
      toast({
        title: "Text-to-Speech Error",
        description: error instanceof Error ? error.message : "Failed to generate speech",
        variant: "destructive"
      });
    }
  }, [currentAudio, toast]); // Minimal dependencies - everything else uses refs

  // Stop speaking
  const stopSpeaking = useCallback(async () => {
    if (currentAudio) {
      currentAudio.pause();
      setCurrentAudio(null);
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      
      // Re-enable STT if it was enabled before TTS started
      if (sttWasEnabledRef.current) {
        try {
          await startSTTRef.current();
        } catch (error) {
          console.error('Failed to restart STT after stopping TTS:', error);
        }
      }
    }
  }, [currentAudio]); // Use ref for startSTT

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (currentAudio) {
        currentAudio.pause();
        setCurrentAudio(null);
      }
      stopSTT();
    };
  }, [currentAudio, stopSTT]);

  return {
    ...voiceState,
    toggleSTT,
    toggleTTS,
    speakText,
    stopSpeaking,
    currentAudio,
    setManualOverride,
    sessionLanguageLock,
    resetLanguageLock,
    clearDetectionAccumulation
  };
};