// Enhanced useVoice hook with advanced multi-engine language detection
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/components/ui/use-toast';
import { useStreamingSpeechToText } from '@/services/voice/StreamingSpeechToTextService';
import { advancedLanguageDetection, LanguageDetectionResult } from '@/services/voice/AdvancedLanguageDetection';
import { cleanTextForTTS, chunkTextForTTS } from '../utils/voiceUtils';
import { voiceConfigService } from '@/services/voice/voiceConfig';

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
  resumeTTS: () => Promise<void>;
  getTTSProgress: () => { completed: number; total: number; isActive: boolean };
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
  
  // TTS session state for resume capability
  const ttsSessionRef = useRef({
    text: '',
    lastChunkCompleted: -1,
    isActive: false,
    chunks: [] as string[]
  });
  
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
    // Skip processing if TTS is currently active to prevent audio feedback loops
    if (voiceStateRef.current.isTTSActive) {
      console.log('🚫 Skipping transcription during TTS playback to prevent feedback loop');
      return;
    }
    
    // Additional check: Skip if we have current audio playing (even if TTS state hasn't updated yet)
    if (currentAudio && !currentAudio.paused) {
      console.log('🚫 Skipping transcription during active audio playback');
      return;
    }
    
    // Skip very short transcripts that might be audio artifacts
    if (text && text.trim().length < 3) {
      console.log('🚫 Skipping very short transcript (likely audio artifact):', text);
      return;
    }
    
    // Skip empty or whitespace-only transcripts
    if (!text || !text.trim()) {
      return;
    }
    
    if (onTranscript) {
      onTranscript(text, isFinal, isFinal);
    }
    
    // Perform language detection on final transcripts
    if (isFinal && text && text.length > 8 && !userOverrideRef.current) {
      performAdvancedLanguageDetection(text);
    }
  }, [onTranscript, performAdvancedLanguageDetection, currentAudio]);

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
    isListening: isRecording,
    pauseTranscription,
    resumeTranscription
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
  const pauseTranscriptionRef = useRef(pauseTranscription);
  const resumeTranscriptionRef = useRef(resumeTranscription);
  
  // Update refs when values change
  useEffect(() => {
    tokenRef.current = token;
    voiceStateRef.current = voiceState;
    languageCodeRef.current = languageCode;
    stopSTTRef.current = stopSTT;
    startSTTRef.current = startSTT;
    pauseTranscriptionRef.current = pauseTranscription;
    resumeTranscriptionRef.current = resumeTranscription;
  }, [token, voiceState, languageCode, stopSTT, startSTT, pauseTranscription, resumeTranscription]);

  // Text-to-speech function with improved processing and chunking
  const speakText = useCallback(async (text: string) => {
    if (!voiceStateRef.current.isTTSEnabled || !text.trim()) {
      console.log('🚫 TTS skipped: enabled=', voiceStateRef.current.isTTSEnabled, 'text=', !!text.trim());
      return;
    }

    // Capture state variables at the start to avoid closure issues
    const originalDetectionEnabled = voiceStateRef.current.isAutoDetecting;

    // Track chunk progress
    const chunkProgress = {
      total: 0,
      completed: 0,
      failed: [] as number[],
      lastSuccessfulChunk: -1
    };

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

      // Temporarily pause STT transcription processing during TTS to prevent feedback
      sttWasEnabledRef.current = voiceStateRef.current.isSTTEnabled;
      if (sttWasEnabledRef.current) {
        console.log('⏸️ Temporarily pausing STT transcription during TTS to prevent feedback');
        try {
          pauseTranscriptionRef.current();
          
          // Add a small delay to ensure pause is processed
          await new Promise(resolve => setTimeout(resolve, 100));
        } catch (sttPauseError) {
          console.warn('Error pausing STT during TTS (non-critical):', sttPauseError);
        }
      }

      setVoiceState(prev => ({ ...prev, isTTSActive: true }));

      // Get current language for stable voice selection
      const currentLanguage = voiceStateRef.current.detectedLanguage || languageCodeRef.current || 'en';
      
      // Split text into manageable chunks for long messages
      const textChunks = chunkTextForTTS(text, 800);
      chunkProgress.total = textChunks.length;
      console.log(`🎙️ TTS processing ${textChunks.length} chunks for language: ${currentLanguage}`);

      // Store TTS session state
      ttsSessionRef.current = {
        text,
        lastChunkCompleted: -1,
        isActive: true,
        chunks: textChunks
      };

      // Temporarily disable language detection during TTS to prevent drift
      if (originalDetectionEnabled) {
        setVoiceState(prev => ({ ...prev, isAutoDetecting: false }));
        console.log('🔒 Language detection disabled during TTS to prevent drift');
      }

      // Process each chunk sequentially with retry logic
      for (let i = 0; i < textChunks.length; i++) {
        // Check if TTS is still enabled before processing chunk
        if (!voiceStateRef.current.isTTSEnabled) {
          console.log('🛑 TTS was disabled during processing, stopping playback');
          console.log(`📊 Progress: ${chunkProgress.completed}/${chunkProgress.total} chunks completed`);
          break;
        }
        
        const chunk = textChunks[i];
        let retryCount = 0;
        const maxRetries = 2;
        let chunkSuccessful = false;

        // Retry logic for each chunk
        while (retryCount <= maxRetries && !chunkSuccessful) {
          try {
            console.log(`🎙️ Speaking chunk ${i + 1}/${textChunks.length}${retryCount > 0 ? ` (retry ${retryCount})` : ''}: "${chunk.substring(0, 50)}..."`);

            const formData = new FormData();
            formData.append('text', chunk); // Use cleaned and chunked text
            
            // Get voice ID from backend configuration
            let voiceId: string;
            try {
              voiceId = await voiceConfigService.getVoiceId(tokenRef.current || '');
            } catch (error) {
              console.warn('Failed to get voice ID from config, using default:', error);
              voiceId = 'VSy05caiuOBJdp42Y45T'; // Fallback to default
            }
            
            // Use consistent voice settings for uniform tone
            formData.append('voice_id', voiceId);
            formData.append('output_format', 'mp3_44100_128');
            formData.append('stability', '0.4'); // More stable for consistency
            formData.append('similarity_boost', '0.75'); // Higher similarity for voice consistency
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
            
            // Ensure no other audio is playing before setting new audio
            if (currentAudio && !currentAudio.paused) {
              currentAudio.pause();
              setCurrentAudio(null);
            }

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
                chunkSuccessful = true;
                chunkProgress.completed++;
                chunkProgress.lastSuccessfulChunk = i;
                ttsSessionRef.current.lastChunkCompleted = i;
                console.log(`✅ Chunk ${i + 1}/${textChunks.length} completed successfully`);
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

          } catch (chunkError) {
            console.error(`❌ Error processing chunk ${i + 1}:`, chunkError);
            retryCount++;
            
            if (retryCount > maxRetries) {
              console.error(`🚫 Failed to process chunk ${i + 1} after ${maxRetries} retries`);
              chunkProgress.failed.push(i);
              
              // Ask user if they want to continue or stop
              const remainingChunks = textChunks.length - i - 1;
              if (remainingChunks > 0) {
                console.log(`⚠️ ${remainingChunks} chunks remaining. Continuing with next chunk...`);
              }
              break; // Move to next chunk
            } else {
              console.log(`🔄 Retrying chunk ${i + 1} in 1 second...`);
              await new Promise(resolve => setTimeout(resolve, 1000));
            }
          }
        }
      }

      // Log final progress
      console.log(`📊 TTS Complete: ${chunkProgress.completed}/${chunkProgress.total} chunks successfully played`);
      if (chunkProgress.failed.length > 0) {
        console.warn(`⚠️ Failed chunks: ${chunkProgress.failed.map(i => i + 1).join(', ')}`);
      }

      // All chunks completed successfully
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      setCurrentAudio(null);
      
      // Clear TTS session
      ttsSessionRef.current.isActive = false;
      
      // Re-enable language detection if it was enabled before TTS
      if (originalDetectionEnabled) {
        setVoiceState(prev => ({ ...prev, isAutoDetecting: true }));
        console.log('🔓 Language detection re-enabled after TTS completion');
      }
      
      // Resume STT transcription if it was enabled before TTS started
      if (sttWasEnabledRef.current) {
        console.log('▶️ Resuming STT transcription after successful TTS completion');
        try {
          // Add a delay to ensure TTS cleanup is complete and audio has stopped
          await new Promise(resolve => setTimeout(resolve, 800));
          resumeTranscriptionRef.current();
          console.log('✅ STT transcription successfully resumed after TTS completion');
        } catch (error) {
          console.error('Failed to resume STT transcription after TTS:', error);
          // Don't propagate this error, TTS was successful
        }
      }

    } catch (error) {
      // Enhanced error logging with context and chunk progress
      const textChunks = chunkTextForTTS(text, 800); // Get chunks for context
      const errorContext = {
        chunkProgress: {
          completed: chunkProgress.completed,
          total: chunkProgress.total,
          failed: chunkProgress.failed,
          lastSuccessful: chunkProgress.lastSuccessfulChunk
        },
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
      
      // Log chunk progress summary if any chunks were processed
      if (chunkProgress.completed > 0) {
        console.log(`📊 TTS partially completed: ${chunkProgress.completed}/${chunkProgress.total} chunks played before error`);
      }
      
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      setCurrentAudio(null);
      
      // Update TTS session state
      ttsSessionRef.current.isActive = false;
      
      // Re-enable language detection even on error
      if (originalDetectionEnabled) {
        setVoiceState(prev => ({ ...prev, isAutoDetecting: true }));
        console.log('🔓 Language detection re-enabled after TTS error');
      }
      
      // Resume STT transcription if it was enabled before TTS started (even on error)
      if (sttWasEnabledRef.current) {
        console.log('▶️ Attempting to resume STT transcription after TTS error');
        try {
          // Add a delay to ensure cleanup is complete
          await new Promise(resolve => setTimeout(resolve, 800));
          resumeTranscriptionRef.current();
          console.log('✅ STT transcription successfully resumed after TTS error');
        } catch (sttError) {
          console.error('Failed to resume STT transcription after TTS error:', sttError);
        }
      }
      
      // Only show toast for non-abort errors or if no chunks were played
      if ((error as Error)?.name !== 'AbortError' || chunkProgress.completed === 0) {
        toast({
          title: "Text-to-Speech Error",
          description: chunkProgress.completed > 0 
            ? `Played ${chunkProgress.completed}/${chunkProgress.total} chunks before error`
            : (error instanceof Error ? error.message : "Failed to generate speech"),
          variant: "destructive"
        });
      }
    }
  }, [currentAudio, toast]); // Minimal dependencies - everything else uses refs

  // Stop speaking
  const stopSpeaking = useCallback(async () => {
    if (currentAudio) {
      currentAudio.pause();
      setCurrentAudio(null);
      setVoiceState(prev => ({ ...prev, isTTSActive: false }));
      
      // Mark TTS session as inactive but keep progress
      ttsSessionRef.current.isActive = false;
      
      // Resume STT transcription if it was enabled before TTS started
      if (sttWasEnabledRef.current) {
        try {
          // Add delay to ensure audio has fully stopped
          await new Promise(resolve => setTimeout(resolve, 400));
          resumeTranscriptionRef.current();
          console.log('✅ STT transcription resumed after manually stopping TTS');
        } catch (error) {
          console.error('Failed to resume STT transcription after stopping TTS:', error);
        }
      }
    }
  }, [currentAudio]); // Use ref for startSTT

  // Resume TTS from last successful chunk
  const resumeTTS = useCallback(async () => {
    const session = ttsSessionRef.current;
    if (!session.chunks.length || session.lastChunkCompleted >= session.chunks.length - 1) {
      console.log('No TTS session to resume or already completed');
      return;
    }

    const startChunk = session.lastChunkCompleted + 1;
    console.log(`📢 Resuming TTS from chunk ${startChunk + 1}/${session.chunks.length}`);

    // Create a subset of chunks to process
    const remainingText = session.chunks.slice(startChunk).join(' ');
    await speakText(remainingText);
  }, [speakText]);

  // Get current TTS progress
  const getTTSProgress = useCallback(() => {
    const session = ttsSessionRef.current;
    return {
      completed: session.lastChunkCompleted + 1,
      total: session.chunks.length,
      isActive: session.isActive
    };
  }, []);

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
    clearDetectionAccumulation,
    resumeTTS,
    getTTSProgress
  };
};