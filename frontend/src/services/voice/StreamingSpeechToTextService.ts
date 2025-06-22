// src/services/voice/StreamingSpeechToTextService.ts
import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { advancedLanguageDetection, LanguageDetectionResult } from './AdvancedLanguageDetection';

// Simple client-side language detection fallback
function detectLanguageFallback(text: string): { language: string | null, confidence: number } {
  if (!text || text.length < 5) return { language: null, confidence: 0 };
  
  const lowerText = text.toLowerCase();
  
  // Simple pattern-based detection (very basic but better than nothing)
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
    },
    'de': {
      words: ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'des', 'auf', 'für', 'ist', 'im', 'dem', 'nicht', 'ein', 'eine', 'als', 'auch', 'es', 'an', 'werden', 'aus', 'er', 'hat', 'dass', 'sie', 'nach', 'wird', 'bei', 'einer', 'um', 'am', 'sind', 'noch', 'wie', 'einem', 'über', 'einen', 'so', 'zum', 'war', 'haben', 'nur', 'oder', 'aber', 'vor', 'zur', 'bis', 'mehr', 'durch', 'man', 'sein', 'wurde', 'sei', 'in'],
      endings: ['ung', 'heit', 'keit', 'schaft', 'tum'],
      chars: ['ä', 'ö', 'ü', 'ß']
    },
    'it': {
      words: ['il', 'di', 'che', 'e', 'la', 'per', 'un', 'in', 'con', 'del', 'da', 'a', 'al', 'le', 'si', 'gli', 'una', 'o', 'anche', 'come', 'ma', 'se', 'nel', 'non', 'più', 'sono', 'molto', 'bene', 'ciao', 'grazie', 'dove', 'come'],
      endings: ['zione', 'mente', 'ezza', 'ità'],
      chars: ['à', 'è', 'é', 'ì', 'ò', 'ù']
    },
    'pt': {
      words: ['o', 'de', 'a', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela', 'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'suas', 'numa', 'pelos', 'pelas', 'esse', 'eles', 'estão', 'você', 'tinha', 'foram', 'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha', 'têm', 'numa', 'pelos', 'pelas', 'olá', 'obrigado', 'onde', 'como'],
      endings: ['ção', 'mente', 'dade', 'ismo'],
      chars: ['ã', 'õ', 'á', 'à', 'é', 'ê', 'í', 'ó', 'ô', 'ú', 'ç']
    }
  };
  
  const scores: { [key: string]: number } = {};
  
  for (const [lang, data] of Object.entries(patterns)) {
    let score = 0;
    
    // Check for common words
    const words = lowerText.split(/\s+/);
    for (const word of words) {
      if (data.words.includes(word)) {
        score += 2;
      }
    }
    
    // Check for characteristic endings
    for (const ending of data.endings) {
      const regex = new RegExp(ending + '\\b', 'g');
      const matches = lowerText.match(regex);
      if (matches) {
        score += matches.length * 1.5;
      }
    }
    
    // Check for characteristic characters
    for (const char of data.chars) {
      const regex = new RegExp(char, 'g');
      const matches = lowerText.match(regex);
      if (matches) {
        score += matches.length * 1;
      }
    }
    
    scores[lang] = score;
  }
  
  // Default to English if no other language has a strong signal
  scores['en'] = Math.max(1, scores['en'] || 0);
  
  // Find the highest scoring language
  const sortedLangs = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  const topLang = sortedLangs[0];
  
  if (topLang[1] > 0) {
    const confidence = Math.min(0.9, topLang[1] / (text.length / 5)); // Normalize by text length
    return { 
      language: topLang[0], 
      confidence: Math.max(0.1, confidence) 
    };
  }
  
  return { language: 'en', confidence: 0.6 }; // Default fallback
}

/**
 * Type for streaming STT options
 */
export interface StreamingSttOptions {
  /** Authentication token for the WebSocket connection */
  token?: string;
  /** Language code for speech recognition */
  languageCode?: string;
  /** Model to use (removed for Soniox compatibility) */
  model?: string;
  /** Callback when transcription is received */
  onTranscription?: (text: string, isFinal: boolean) => void;
  /** Callback when speech starts */
  onSpeechStart?: () => void;
  /** Callback when utterance ends */
  onUtteranceEnd?: () => void;
  /** Callback when connection status changes */
  onConnectionChange?: (isConnected: boolean) => void;
  /** Callback when error occurs */
  onError?: (error: string) => void;
  /** Callback when language is detected */
  onLanguageDetected?: (language: string, confidence: number) => void;
}

/**
 * Streaming STT service using Soniox via WebSocket
 */
export const useStreamingSpeechToText = (options: StreamingSttOptions = {}) => {
  // Default options
  const defaultOptions: Required<StreamingSttOptions> = {
    token: '',
    languageCode: 'auto', // Default to auto-detection
    model: 'soniox-auto', // Use Soniox auto model
    onTranscription: () => {},
    onSpeechStart: () => {},
    onUtteranceEnd: () => {},
    onConnectionChange: () => {},
    onError: () => {},
    onLanguageDetected: () => {},
  };

  // Merge options with memoization to prevent recreation
  const opts = useMemo(() => ({ ...defaultOptions, ...options }), [
    options.token,
    options.languageCode, 
    options.model,
    options.onTranscription,
    options.onSpeechStart,
    options.onUtteranceEnd,
    options.onConnectionChange,
    options.onError,
    options.onLanguageDetected
  ]);

  // States
  const [isListening, setIsListening] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isStoppingRef = useRef<boolean>(false);
  const isStartingRef = useRef<boolean>(false);
  
  // Advanced language detection
  const audioBufferRef = useRef<Float32Array[]>([]);
  const lastDetectionRef = useRef<number>(0);

  // Update connection state - use ref to avoid dependency on opts
  const updateConnectionState = useCallback((connected: boolean) => {
    setIsConnected(connected);
    if (opts.onConnectionChange) {
      opts.onConnectionChange(connected);
    }
  }, [opts]);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connected':
          console.log('STT streaming connected');
          updateConnectionState(true);
          break;
          
        case 'transcription_ready':
          console.log('STT ready to receive audio');
          break;
          
        case 'transcript':
          if (data.transcript) {
            // Pass both is_final and speech_final flags
            const isFinal = data.is_final || false;
            const speechFinal = data.speech_final || false;
            
            // Debug: Log all received data to see what we're getting
            console.log('📨 Raw WebSocket Data:', {
              type: data.type,
              transcript: data.transcript?.substring(0, 50) + '...',
              detected_language: data.detected_language,
              language_confidence: data.language_confidence,
              confidence: data.confidence,
              is_final: data.is_final,
              speech_final: data.speech_final,
              alternatives: data.alternatives,
              allKeys: Object.keys(data)
            });
            
            // Enhanced language detection with detailed logging
            if (data.detected_language) {
              const languageConfidence = data.language_confidence || 0;
              const transcriptConfidence = data.confidence || 0;
              const textLength = data.transcript ? data.transcript.length : 0;
              
              console.log(`🌍 Language Detection:`, {
                language: data.detected_language,
                languageConfidence: languageConfidence,
                transcriptConfidence: transcriptConfidence,
                textLength: textLength,
                transcript: data.transcript?.substring(0, 50) + '...',
                isFinal: isFinal,
                speechFinal: speechFinal,
                rawData: {
                  language_confidence: data.language_confidence,
                  confidence: data.confidence,
                  alternatives: data.alternatives
                }
              });
              
              // Enhanced confidence calculation
              let finalConfidence = languageConfidence;
              
              // Boost confidence for longer text samples (more reliable)
              if (textLength > 10) {
                finalConfidence = Math.min(1.0, finalConfidence * 1.1);
              }
              if (textLength > 30) {
                finalConfidence = Math.min(1.0, finalConfidence * 1.1);
              }
              
              // Consider transcript confidence as well
              if (transcriptConfidence > 0) {
                finalConfidence = (finalConfidence + transcriptConfidence) / 2;
              }
              
              // Only trigger detection for meaningful confidence levels
              if (finalConfidence >= 0.3) {
                opts.onLanguageDetected(data.detected_language, finalConfidence);
              } else {
                console.log(`⚠️ Skipping low confidence detection: ${finalConfidence}`);
              }
            } else if (isFinal || speechFinal) {
              // Fallback: Client-side language detection if backend doesn't provide it
              console.log('🔍 No backend language detection, trying client-side fallback...');
              const fallbackDetection = detectLanguageFallback(data.transcript);
              if (fallbackDetection.language && fallbackDetection.confidence > 0.5) {
                console.log('🎯 Fallback detection:', fallbackDetection);
                opts.onLanguageDetected(fallbackDetection.language, fallbackDetection.confidence);
              }
            }
            
            // For now, treat speech_final as the main final indicator
            opts.onTranscription(data.transcript, isFinal || speechFinal);
          }
          break;
          
        case 'transcription_stopped':
          console.log('STT transcription stopped');
          break;
          
        case 'error':
          console.error('STT error:', data.message);
          setError(data.message);
          opts.onError(data.message);
          break;
          
        case 'pong':
          // Heartbeat response
          break;
      }
    } catch (e) {
      console.error('Error parsing WebSocket message:', e);
    }
  }, [opts, updateConnectionState]);

  // Connect to WebSocket
  const connectWebSocket = useCallback(async (): Promise<boolean> => {
    try {
      // Get authentication token from options
      const authToken = opts.token;
      if (!authToken) {
        throw new Error('No authentication token provided');
      }

      // Determine WebSocket URL with language and model parameters
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const backendHost = process.env.NEXT_PUBLIC_API_URL ? new URL(process.env.NEXT_PUBLIC_API_URL).host : 'localhost:8000';
      const params = new URLSearchParams({
        token: authToken,
        language: opts.languageCode
      });
      
      // Only add model parameter if it's specified and not the default Soniox model
      if (opts.model && opts.model !== 'soniox-auto') {
        params.set('model', opts.model);
      }
      const wsUrl = `${protocol}//${backendHost}/api/ws/stt/stream?${params.toString()}`;
      
      console.log('Connecting to streaming STT WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      
      // Set up event handlers
      ws.onopen = async () => {
        console.log('STT WebSocket opened successfully');
        
        // Send start transcription control message with language configuration
        const startMessage: any = {
          type: 'start_transcription',
          language: opts.languageCode
        };
        
        // Only include model if it's not the default Soniox model
        if (opts.model && opts.model !== 'soniox-auto') {
          startMessage.model = opts.model;
        }
        
        console.log('Sending start transcription message:', startMessage);
        ws.send(JSON.stringify(startMessage));
      };
      
      ws.onmessage = handleWebSocketMessage;
      
      ws.onerror = (event) => {
        // Safely log error without accessing potentially problematic properties
        console.error('WebSocket error:', {
          isTrusted: event.isTrusted,
          type: event.type,
          eventPhase: event.eventPhase,
          // Avoid accessing event.target directly as it may have browser-specific implementations
        });
        updateConnectionState(false);
      };
      
      ws.onclose = (event) => {
        console.log(`STT WebSocket closed: ${event.code} - ${event.reason}`);
        console.log('Close event details:', { 
          wasClean: event.wasClean, 
          code: event.code, 
          reason: event.reason,
          isListening: isListening,
          isStopping: isStoppingRef.current,
          language: opts.languageCode
        });
        updateConnectionState(false);
        
        // Auto-reconnect with exponential backoff for connection stability
        if (isListening && !isStoppingRef.current) {
          // Increase reconnection delay for language-specific issues
          const reconnectDelay = event.code === 1006 ? 2000 : 1000; // 1006 = abnormal closure
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Attempting to reconnect for language ${opts.languageCode}...`);
            connectWebSocket();
          }, reconnectDelay);
        }
      };
      
      wsRef.current = ws;
      
      // Wait for connection to open
      return new Promise((resolve) => {
        let resolved = false;
        
        // Handle connection success
        const handleOpen = () => {
          console.log('WebSocket opened successfully');
          if (!resolved) {
            resolved = true;
            resolve(true);
          }
        };
        
        // Handle connection failure
        const handleError = () => {
          console.log('WebSocket connection failed');
          if (!resolved) {
            resolved = true;
            resolve(false);
          }
        };
        
        // Handle connection close
        const handleClose = () => {
          console.log('WebSocket closed during connection');
          if (!resolved) {
            resolved = true;
            resolve(false);
          }
        };
        
        // Set up one-time listeners
        ws.addEventListener('open', handleOpen, { once: true });
        ws.addEventListener('error', handleError, { once: true });
        ws.addEventListener('close', handleClose, { once: true });
        
        // Timeout after 5 seconds
        setTimeout(() => {
          if (!resolved) {
            resolved = true;
            console.log('WebSocket connection timeout');
            resolve(false);
          }
        }, 5000);
      });
      
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      return false;
    }
  }, [opts.languageCode, opts.model, opts.token, isListening, handleWebSocketMessage, updateConnectionState]);

  // Process audio using Web Audio API
  const processAudioStream = useCallback((stream: MediaStream) => {
    try {
      // Don't specify sample rate - let it use the default to avoid Firefox issues
      audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      
      // Get the actual sample rate
      const actualSampleRate = audioContextRef.current.sampleRate;
      console.log(`AudioContext sample rate: ${actualSampleRate}Hz`);
      
      // Create processor node (using deprecated ScriptProcessorNode for compatibility)
      // Use 1024 buffer size for better balance between latency and performance
      processorRef.current = audioContextRef.current.createScriptProcessor(1024, 1, 1);
      
      // Enhanced audio activity tracking for multilingual support
      let recentAudioFramesWithActivity = 0;
      const RECENT_AUDIO_THRESHOLD = 10; // Increased to capture more initial audio
      let lastSentTime = 0;
      const MIN_SEND_INTERVAL = 20; // Reduced for better initial syllable capture
      let consecutiveFramesWithoutAudio = 0;
      const MAX_SILENT_FRAMES = 100; // Send heartbeat audio every N silent frames to keep connection alive
      let isFirstAudioFrame = true; // Track first audio detection
      
      processorRef.current.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return;
        }
        
        // Get audio data
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Check if there's actual audio (not silence)
        // Lower threshold for better sensitivity to different languages/accents
        let hasAudio = false;
        let maxAmplitude = 0;
        let rmsLevel = 0;
        
        // Calculate both peak and RMS for better audio detection
        for (let i = 0; i < inputData.length; i++) {
          const amplitude = Math.abs(inputData[i]);
          maxAmplitude = Math.max(maxAmplitude, amplitude);
          rmsLevel += amplitude * amplitude;
        }
        rmsLevel = Math.sqrt(rmsLevel / inputData.length);
        
        // Use RMS for better noise detection - critical for different languages
        // Lower thresholds for first frames to capture initial syllables
        const rmsThreshold = isFirstAudioFrame ? 0.001 : 0.003;
        const amplitudeThreshold = isFirstAudioFrame ? 0.003 : 0.005;
        hasAudio = rmsLevel > rmsThreshold || maxAmplitude > amplitudeThreshold;
        
        // Update activity trackers
        if (hasAudio) {
          recentAudioFramesWithActivity = RECENT_AUDIO_THRESHOLD;
          consecutiveFramesWithoutAudio = 0;
          if (isFirstAudioFrame) {
            isFirstAudioFrame = false; // Reset after first audio detection
            console.log('First audio detected, using lower thresholds');
          }
        } else {
          recentAudioFramesWithActivity = Math.max(0, recentAudioFramesWithActivity - 1);
          consecutiveFramesWithoutAudio++;
        }
        
        // Send audio data to maintain connection stability
        const shouldSendAudio = hasAudio || 
                               recentAudioFramesWithActivity > 0 || 
                               (consecutiveFramesWithoutAudio % MAX_SILENT_FRAMES === 0 && consecutiveFramesWithoutAudio > 0);
        
        if (shouldSendAudio) {
          // Throttle sending to avoid overwhelming the service
          const now = Date.now();
          if (now - lastSentTime < MIN_SEND_INTERVAL) {
            return;
          }
          lastSentTime = now;
          
          // If sample rate is not 16kHz, we need to downsample
          let outputData: Int16Array;
          
          if (actualSampleRate === 16000) {
            // Direct conversion without resampling
            outputData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              // Apply slight gain to boost the signal
              const boostedSample = inputData[i] * 1.5; // Boost input by 50%
              const s = Math.max(-1, Math.min(1, boostedSample));
              outputData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
          } else {
            // Improved downsampling with basic interpolation
            const ratio = actualSampleRate / 16000;
            const outputLength = Math.floor(inputData.length / ratio);
            outputData = new Int16Array(outputLength);
            
            for (let i = 0; i < outputLength; i++) {
              const inputIndexFloat = i * ratio;
              const inputIndex = Math.floor(inputIndexFloat);
              const fraction = inputIndexFloat - inputIndex;
              
              // Simple linear interpolation between samples
              let sample = inputData[inputIndex];
              if (inputIndex + 1 < inputData.length) {
                sample = sample * (1 - fraction) + inputData[inputIndex + 1] * fraction;
              }
              
              // Apply gain to boost signal
              const boostedSample = sample * 1.5; // Boost by 50%
              const s = Math.max(-1, Math.min(1, boostedSample));
              outputData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
          }
          
          // Send to WebSocket
          wsRef.current.send(outputData.buffer);
        }
      };
      
      // Connect nodes
      source.connect(processorRef.current);
      processorRef.current.connect(audioContextRef.current.destination);
      
    } catch (error) {
      console.error('Error processing audio stream:', error);
      throw error;
    }
  }, []);

  // Start listening
  const startListening = useCallback(async () => {
    console.log('startListening called, current state:', { isListening, isConnected, isStarting: isStartingRef.current });
    
    // Force reset listening state if there's inconsistency
    if (isListening && !wsRef.current) {
      console.log('Inconsistent state detected: isListening=true but no WebSocket. Resetting...');
      setIsListening(false);
      updateConnectionState(false);
    }
    
    if (isListening && wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('Already listening with active connection, skipping');
      return;
    }
    
    if (isStartingRef.current) {
      console.log('Already starting listening, skipping');
      return;
    }
    
    isStartingRef.current = true;
    isStoppingRef.current = false;
    setError(null);
    
    try {
      // Get available audio input devices
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter(device => device.kind === 'audioinput');
      
      console.log('Available audio input devices:', audioInputs.map(d => ({ 
        deviceId: d.deviceId, 
        label: d.label 
      })));

      // Request microphone access with optimized constraints for better multilingual sensitivity
      // Note: echoCancellation disabled to allow computer audio (like Google Translate) to be detected
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: false, // Allow computer audio to be detected
          noiseSuppression: false, // Disable to preserve speech characteristics for language detection
          autoGainControl: true,
          sampleRate: 16000, // Explicitly request 16kHz to match Soniox requirements
          // Optimized for multilingual support
          advanced: [
            { autoGainControl: { exact: true } },
            { echoCancellation: { exact: false } }, // Allow computer audio
            { noiseSuppression: { exact: false } }, // Critical for non-English languages
            { sampleRate: { exact: 16000 } } // Ensure consistent sample rate
          ]
        }
      });
      
      streamRef.current = stream;
      
      // Connect to WebSocket
      const connected = await connectWebSocket();
      if (!connected) {
        throw new Error('Failed to connect to streaming service');
      }
      
      // Process audio
      processAudioStream(stream);
      
      setIsListening(true);
      console.log('Started listening');
      
    } catch (error) {
      console.error('Error starting listening:', error);
      
      let errorMessage = 'Failed to start listening';
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          errorMessage = 'Microphone access denied';
        } else if (error.name === 'NotFoundError') {
          errorMessage = 'No microphone found';
        } else {
          errorMessage = error.message;
        }
      }
      
      setError(errorMessage);
      opts.onError(errorMessage);
      
      // Clean up
      stopListening();
    } finally {
      isStartingRef.current = false;
    }
  }, [isListening, connectWebSocket, processAudioStream, opts]);

  // Stop listening - remove dependency on updateConnectionState to avoid loops
  const stopListening = useCallback(() => {
    console.log('stopListening called, current state:', { isListening, isConnected });
    console.log('Stack trace:', new Error().stack);
    isStoppingRef.current = true;
    
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Send stop transcription message before closing
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        const stopMessage = {
          type: 'stop_transcription'
        };
        wsRef.current.send(JSON.stringify(stopMessage));
      } catch (e) {
        console.error('Error sending stop message:', e);
      }
    }
    
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    // Stop audio processing
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    // Stop media stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    setIsListening(false);
    setIsConnected(false);
    // Call connection change callback directly to avoid dependency loop
    if (opts.onConnectionChange) {
      opts.onConnectionChange(false);
    }
    isStartingRef.current = false;
  }, [opts.onConnectionChange]);

  // Toggle listening
  const toggleListening = useCallback(async () => {
    if (isListening) {
      stopListening();
    } else {
      await startListening();
    }
  }, [isListening, startListening, stopListening]);

  // Cleanup on unmount - use refs to avoid stale closures
  useEffect(() => {
    return () => {
      // Use direct cleanup instead of relying on stopListening
      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      // Close WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      // Stop audio processing
      if (processorRef.current) {
        processorRef.current.disconnect();
        processorRef.current = null;
      }
      
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      
      // Stop media stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
    };
  }, []);

  return {
    // States
    isListening,
    isConnected,
    error,
    
    // Actions
    startListening,
    stopListening,
    toggleListening,
  };
};