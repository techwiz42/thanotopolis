// src/services/voice/StreamingSpeechToTextService.ts
import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Type for streaming STT options
 */
export interface StreamingSttOptions {
  /** Authentication token for the WebSocket connection */
  token?: string;
  /** Language code for speech recognition */
  languageCode?: string;
  /** Model to use (nova-2, nova, etc.) */
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
}

/**
 * Streaming STT service using Deepgram via WebSocket
 */
export const useStreamingSpeechToText = (options: StreamingSttOptions = {}) => {
  // Default options
  const defaultOptions: Required<StreamingSttOptions> = {
    token: '',
    languageCode: 'auto', // Default to auto-detection
    model: 'nova-2', // Use nova-2 for better multilingual support
    onTranscription: () => {},
    onSpeechStart: () => {},
    onUtteranceEnd: () => {},
    onConnectionChange: () => {},
    onError: () => {},
  };

  // Merge options
  const opts = { ...defaultOptions, ...options };

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

  // Update connection state
  const updateConnectionState = useCallback((connected: boolean) => {
    setIsConnected(connected);
    opts.onConnectionChange(connected);
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
            
            // Log for debugging
            if (data.detected_language) {
              console.log(`Detected language: ${data.detected_language}`);
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
        language: opts.languageCode,
        model: opts.model
      });
      const wsUrl = `${protocol}//${backendHost}/api/ws/stt/stream?${params.toString()}`;
      
      console.log('Connecting to streaming STT WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      
      // Set up event handlers
      ws.onopen = async () => {
        console.log('STT WebSocket opened successfully');
        
        // Send start transcription control message with language configuration
        const startMessage = {
          type: 'start_transcription',
          language: opts.languageCode,
          model: opts.model
        };
        
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
      const RECENT_AUDIO_THRESHOLD = 5; // Increased frames to keep sending after detecting activity
      let lastSentTime = 0;
      const MIN_SEND_INTERVAL = 40; // Reduced for better responsiveness (was 50ms)
      let consecutiveFramesWithoutAudio = 0;
      const MAX_SILENT_FRAMES = 100; // Send heartbeat audio every N silent frames to keep connection alive
      
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
        hasAudio = rmsLevel > 0.003 || maxAmplitude > 0.005; // Lower thresholds for better sensitivity
        
        // Update activity trackers
        if (hasAudio) {
          recentAudioFramesWithActivity = RECENT_AUDIO_THRESHOLD;
          consecutiveFramesWithoutAudio = 0;
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
    console.log('startListening called, current state:', { isListening, isConnected });
    
    if (isListening) {
      console.log('Already listening, skipping');
      return;
    }
    
    isStoppingRef.current = false;
    setError(null);
    
    try {
      // Request microphone access with optimized constraints for better multilingual sensitivity
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: false, // Disable to preserve speech characteristics for language detection
          autoGainControl: true,
          sampleRate: 16000, // Explicitly request 16kHz to match Deepgram requirements
          // Optimized for multilingual support
          advanced: [
            { autoGainControl: { exact: true } },
            { echoCancellation: { exact: true } },
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
    }
  }, [isListening, connectWebSocket, processAudioStream, opts]);

  // Stop listening
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
    updateConnectionState(false);
  }, [updateConnectionState]);

  // Toggle listening
  const toggleListening = useCallback(async () => {
    if (isListening) {
      stopListening();
    } else {
      await startListening();
    }
  }, [isListening, startListening, stopListening]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isListening) {
        stopListening();
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