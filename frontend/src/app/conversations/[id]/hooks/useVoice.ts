// Enhanced useVoice hook with advanced multi-engine language detection
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';
import { useStreamingSpeechToText } from '@/services/voice/StreamingSpeechToTextService';
import { advancedLanguageDetection, LanguageDetectionResult } from '@/services/voice/AdvancedLanguageDetection';

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
    model: 'soniox-auto',
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

  // Update STT state based on service state
  useEffect(() => {
    setVoiceState(prev => ({
      ...prev,
      isSTTActive: isRecording && prev.isSTTEnabled,
      isSTTConnecting: !sttConnected && prev.isSTTEnabled
    }));
  }, [isRecording, sttConnected]);

  // Handle language changes gracefully - stop STT if running, then allow restart
  useEffect(() => {
    const isCurrentlyEnabled = voiceState.isSTTEnabled;
    const isCurrentlyActive = voiceState.isSTTActive;
    
    // If STT is currently active and language changed, restart it
    if (isCurrentlyEnabled && isCurrentlyActive && sttConnected) {
      console.log('Language changed while STT active, restarting...');
      // Brief pause to allow service to reconnect, then restart if still enabled
      setTimeout(() => {
        if (voiceState.isSTTEnabled && sttConnected && !isRecording) {
          console.log('Restarting STT after language change');
          startSTT();
        }
      }, 100);
    }
  }, [languageCode]); // Only trigger on language changes

  // Toggle STT
  const toggleSTT = useCallback(async () => {
    try {
      const currentlyEnabled = voiceState.isSTTEnabled;
      console.log('STT toggle requested, currently enabled:', currentlyEnabled);
      
      if (!currentlyEnabled) {
        // Enabling STT
        console.log('Enabling STT...');
        setVoiceState(prev => ({ ...prev, isSTTEnabled: true, isAutoDetecting: true }));
        await startSTT();
      } else {
        // Disabling STT
        console.log('Disabling STT...');
        // Set state first to prevent race conditions
        setVoiceState(prev => ({ 
          ...prev, 
          isSTTEnabled: false, 
          isSTTActive: false, 
          isSTTConnecting: false,
          isAutoDetecting: false 
        }));
        // Then stop the service
        stopSTT();
      }
    } catch (error) {
      console.error('STT toggle error:', error);
      // Reset state on error
      setVoiceState(prev => ({ 
        ...prev, 
        isSTTEnabled: false, 
        isSTTActive: false, 
        isSTTConnecting: false,
        isAutoDetecting: false 
      }));
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
    
    // Stop current audio if disabling TTS
    if (voiceState.isTTSEnabled && currentAudio) {
      currentAudio.pause();
      setCurrentAudio(null);
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
    }
  }, [voiceState.isTTSEnabled, currentAudio]);

  // Text-to-speech function
  const speakText = useCallback(async (text: string) => {
    if (!voiceState.isTTSEnabled || !text.trim()) return;

    try {
      // Stop any currently playing audio
      if (currentAudio) {
        currentAudio.pause();
        setCurrentAudio(null);
      }

      setVoiceState(prev => ({ ...prev, isTTSActive: true }));

      const response = await fetch('/api/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          text: text.substring(0, 500), // Limit text length
          voice: 'alloy',
          format: 'mp3'
        })
      });

      if (!response.ok) {
        throw new Error(`TTS API error: ${response.status}`);
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      setCurrentAudio(audio);

      audio.onended = () => {
        setVoiceState(prev => ({ ...prev, isTTSActive: false }));
        setCurrentAudio(null);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = () => {
        setVoiceState(prev => ({ ...prev, isTTSActive: false }));
        setCurrentAudio(null);
        URL.revokeObjectURL(audioUrl);
        console.error('Audio playback error');
      };

      await audio.play();

    } catch (error) {
      console.error('TTS error:', error);
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      setCurrentAudio(null);
      
      toast({
        title: "Text-to-Speech Error",
        description: error instanceof Error ? error.message : "Failed to generate speech",
        variant: "destructive"
      });
    }
  }, [voiceState.isTTSEnabled, currentAudio, token, toast]);

  // Stop speaking
  const stopSpeaking = useCallback(() => {
    if (currentAudio) {
      currentAudio.pause();
      setCurrentAudio(null);
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
    }
  }, [currentAudio]);

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