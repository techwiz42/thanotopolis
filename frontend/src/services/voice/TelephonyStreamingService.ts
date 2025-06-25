// src/services/voice/TelephonyStreamingService.ts
import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { telephonyErrorHandler, TelephonyErrorType, TelephonyErrorSeverity } from '../telephony/TelephonyErrorHandler';

/**
 * Type for telephony streaming options
 */
export interface TelephonyStreamingOptions {
  /** Authentication token for the WebSocket connection */
  token?: string;
  /** Call ID for this phone call */
  callId?: string;
  /** Language code for speech recognition */
  languageCode?: string;
  /** Model to use (nova-2, nova, etc.) */
  model?: string;
  /** Callback when transcription is received */
  onTranscription?: (text: string, isFinal: boolean, sender: 'customer' | 'agent') => void;
  /** Callback when TTS audio is received */
  onTTSAudio?: (audioBlob: Blob) => void;
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
  /** Callback when call status changes */
  onCallStatusChange?: (status: 'ringing' | 'answered' | 'in_progress' | 'completed' | 'failed') => void;
}

/**
 * Telephony streaming service for real-time phone call audio processing
 * Separate from web chat to handle phone-specific audio streams
 */
export const useTelephonyStreaming = (options: TelephonyStreamingOptions = {}) => {
  // Default options
  const defaultOptions: Required<TelephonyStreamingOptions> = {
    token: '',
    callId: '',
    languageCode: 'auto',
    model: 'nova-2',
    onTranscription: () => {},
    onTTSAudio: () => {},
    onSpeechStart: () => {},
    onUtteranceEnd: () => {},
    onConnectionChange: () => {},
    onError: () => {},
    onLanguageDetected: () => {},
    onCallStatusChange: () => {},
  };

  // Merge options with memoization to prevent recreation
  const opts = useMemo(() => ({ ...defaultOptions, ...options }), [
    options.token,
    options.callId,
    options.languageCode,
    options.model,
    options.onTranscription,
    options.onTTSAudio,
    options.onSpeechStart,
    options.onUtteranceEnd,
    options.onConnectionChange,
    options.onError,
    options.onLanguageDetected,
    options.onCallStatusChange
  ]);

  // States
  const [isConnected, setIsConnected] = useState(false);
  const [callStatus, setCallStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [currentLanguage, setCurrentLanguage] = useState<string>('');

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isStoppingRef = useRef<boolean>(false);

  // Update connection state
  const updateConnectionState = useCallback((connected: boolean) => {
    setIsConnected(connected);
    if (opts.onConnectionChange) {
      opts.onConnectionChange(connected);
    }
  }, [opts]);

  // Handle WebSocket messages for telephony
  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      
      console.log('📞 Telephony WebSocket Message:', {
        type: data.type,
        callId: data.call_id,
        status: data.status,
        hasAudio: !!data.audio_data,
        hasTranscript: !!data.transcript
      });
      
      switch (data.type) {
        case 'telephony_connected':
          console.log('📞 Telephony streaming connected for call:', data.call_id);
          updateConnectionState(true);
          break;
          
        case 'call_status_update':
          console.log('📞 Call status update:', data.status);
          setCallStatus(data.status);
          opts.onCallStatusChange(data.status);
          break;
          
        case 'customer_transcript':
          // Handle customer speech transcription
          if (data.transcript) {
            console.log('🎤 Customer transcript:', data.transcript.substring(0, 50) + '...');
            
            // Language detection for customer speech
            if (data.detected_language) {
              const confidence = data.language_confidence || 0;
              console.log('🌍 Customer language detected:', data.detected_language, confidence);
              setCurrentLanguage(data.detected_language);
              opts.onLanguageDetected(data.detected_language, confidence);
            }
            
            opts.onTranscription(data.transcript, data.is_final || false, 'customer');
          }
          break;
          
        case 'agent_tts_audio':
          // Handle TTS audio from agent response
          if (data.audio_data) {
            console.log('🔊 Received TTS audio for phone call');
            
            // Convert base64 audio to blob
            try {
              const audioBytes = atob(data.audio_data);
              const audioArray = new Uint8Array(audioBytes.length);
              for (let i = 0; i < audioBytes.length; i++) {
                audioArray[i] = audioBytes.charCodeAt(i);
              }
              
              const audioBlob = new Blob([audioArray], { type: 'audio/mpeg' });
              opts.onTTSAudio(audioBlob);
            } catch (error) {
              console.error('Error processing TTS audio:', error);
            }
          }
          break;
          
        case 'agent_transcript':
          // Handle agent response transcription (for logging)
          if (data.transcript) {
            console.log('🤖 Agent transcript:', data.transcript.substring(0, 50) + '...');
            opts.onTranscription(data.transcript, data.is_final || false, 'agent');
          }
          break;
          
        case 'speech_start':
          console.log('🎤 Speech started on phone call');
          opts.onSpeechStart();
          break;
          
        case 'utterance_end':
          console.log('🎤 Utterance ended on phone call');
          opts.onUtteranceEnd();
          break;
          
        case 'telephony_error':
          console.error('📞 Telephony error:', data.message);
          setError(data.message);
          opts.onError(data.message);
          break;
          
        case 'pong':
          // Heartbeat response
          break;
          
        default:
          console.log('📞 Unknown telephony message type:', data.type);
      }
    } catch (e) {
      console.error('Error parsing telephony WebSocket message:', e);
    }
  }, [opts, updateConnectionState]);

  // Connect to telephony WebSocket
  const connectTelephonyWebSocket = useCallback(async (): Promise<boolean> => {
    try {
      const authToken = opts.token;
      const callId = opts.callId;
      
      if (!authToken) {
        throw new Error('No authentication token provided');
      }
      
      if (!callId) {
        throw new Error('No call ID provided');
      }

      // Telephony-specific WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const backendHost = process.env.NEXT_PUBLIC_API_URL ? new URL(process.env.NEXT_PUBLIC_API_URL).host : 'localhost:8000';
      const params = new URLSearchParams({
        token: authToken,
        call_id: callId,
        language: opts.languageCode,
        model: opts.model
      });
      const wsUrl = `${protocol}//${backendHost}/api/ws/telephony/stream?${params.toString()}`;
      
      console.log('📞 Connecting to telephony WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      
      // Set up event handlers
      ws.onopen = async () => {
        console.log('📞 Telephony WebSocket opened successfully');
        
        // Send telephony initialization message
        const initMessage = {
          type: 'init_telephony_stream',
          call_id: callId,
          language: opts.languageCode,
          model: opts.model
        };
        
        console.log('📞 Sending telephony init message:', initMessage);
        ws.send(JSON.stringify(initMessage));
      };
      
      ws.onmessage = handleWebSocketMessage;
      
      ws.onerror = (event) => {
        console.error('📞 Telephony WebSocket error:', {
          isTrusted: event.isTrusted,
          type: event.type,
          eventPhase: event.eventPhase,
        });
        updateConnectionState(false);
      };
      
      ws.onclose = (event) => {
        console.log(`📞 Telephony WebSocket closed: ${event.code} - ${event.reason}`);
        console.log('📞 Close event details:', { 
          wasClean: event.wasClean, 
          code: event.code, 
          reason: event.reason,
          isConnected: isConnected,
          isStopping: isStoppingRef.current,
          callId: callId
        });
        updateConnectionState(false);
        
        // Auto-reconnect for active calls
        if (isConnected && !isStoppingRef.current && callStatus !== 'completed') {
          const reconnectDelay = event.code === 1006 ? 2000 : 1000;
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`📞 Attempting to reconnect telephony for call ${callId}...`);
            connectTelephonyWebSocket();
          }, reconnectDelay);
        }
      };
      
      wsRef.current = ws;
      
      // Wait for connection to open
      return new Promise((resolve) => {
        let resolved = false;
        
        const handleOpen = () => {
          console.log('📞 Telephony WebSocket opened successfully');
          if (!resolved) {
            resolved = true;
            resolve(true);
          }
        };
        
        const handleError = () => {
          console.log('📞 Telephony WebSocket connection failed');
          if (!resolved) {
            resolved = true;
            resolve(false);
          }
        };
        
        const handleClose = () => {
          console.log('📞 Telephony WebSocket closed during connection');
          if (!resolved) {
            resolved = true;
            resolve(false);
          }
        };
        
        ws.addEventListener('open', handleOpen, { once: true });
        ws.addEventListener('error', handleError, { once: true });
        ws.addEventListener('close', handleClose, { once: true });
        
        setTimeout(() => {
          if (!resolved) {
            resolved = true;
            console.log('📞 Telephony WebSocket connection timeout');
            resolve(false);
          }
        }, 5000);
      });
      
    } catch (error) {
      console.error('📞 Failed to connect telephony WebSocket:', error);
      return false;
    }
  }, [opts.token, opts.callId, opts.languageCode, opts.model, isConnected, callStatus, handleWebSocketMessage, updateConnectionState]);

  // Start telephony streaming
  const startTelephonyStream = useCallback(async () => {
    console.log('📞 Starting telephony stream for call:', opts.callId);
    
    if (isConnected && wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('📞 Already connected to telephony stream, skipping');
      return;
    }
    
    isStoppingRef.current = false;
    setError(null);
    
    try {
      const connected = await connectTelephonyWebSocket();
      if (!connected) {
        throw new Error('Failed to connect to telephony streaming service');
      }
      
      console.log('📞 Telephony stream started successfully');
      
    } catch (error) {
      console.error('📞 Error starting telephony stream:', error);
      
      let errorMessage = 'Failed to start telephony stream';
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      setError(errorMessage);
      opts.onError(errorMessage);
      
      // Log error with telephony error handler
      telephonyErrorHandler.logError(
        TelephonyErrorType.STT,
        errorMessage,
        'TelephonyStreamingService',
        {
          severity: TelephonyErrorSeverity.MEDIUM,
          callId: opts.callId,
          details: { languageCode: opts.languageCode, model: opts.model }
        }
      );
    }
  }, [opts.callId, isConnected, connectTelephonyWebSocket, opts]);

  // Stop telephony streaming
  const stopTelephonyStream = useCallback(() => {
    if (isStoppingRef.current || !isConnected) {
      console.log('📞 Telephony stream already stopping or stopped');
      return;
    }
    
    console.log('📞 Stopping telephony stream for call:', opts.callId);
    isStoppingRef.current = true;
    
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Send stop message
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        const stopMessage = {
          type: 'stop_telephony_stream',
          call_id: opts.callId
        };
        wsRef.current.send(JSON.stringify(stopMessage));
      } catch (e) {
        console.error('📞 Error sending stop message:', e);
      }
    }
    
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setCallStatus('');
    setCurrentLanguage('');
    
    if (opts.onConnectionChange) {
      opts.onConnectionChange(false);
    }
    
    isStoppingRef.current = false;
  }, [opts.callId, isConnected, opts.onConnectionChange]);

  // Send message to agent (triggers TTS response)
  const sendAgentMessage = useCallback((message: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('📞 Cannot send agent message: WebSocket not connected');
      return;
    }
    
    const agentMessage = {
      type: 'agent_message',
      call_id: opts.callId,
      message: message,
      language: currentLanguage || opts.languageCode
    };
    
    console.log('📞 Sending agent message:', agentMessage);
    wsRef.current.send(JSON.stringify(agentMessage));
  }, [opts.callId, opts.languageCode, currentLanguage]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  return {
    // States
    isConnected,
    callStatus,
    currentLanguage,
    error,
    
    // Actions
    startTelephonyStream,
    stopTelephonyStream,
    sendAgentMessage,
  };
};