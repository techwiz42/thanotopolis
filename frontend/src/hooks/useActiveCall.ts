// src/hooks/useActiveCall.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { telephonyService, PhoneCall, CallMessage } from '@/services/telephony';
import { useTelephonyStreaming } from '@/services/voice/TelephonyStreamingService';

interface ActiveCallState {
  call: PhoneCall | null;
  messages: CallMessage[];
  isStreamActive: boolean;
  currentLanguage: string;
  error: string | null;
}

interface UseActiveCallOptions {
  /** Auto-start streaming when call becomes active */
  autoStartStreaming?: boolean;
  /** Polling interval for call updates (ms) */
  pollingInterval?: number;
  /** Callback when new message is received */
  onNewMessage?: (message: CallMessage) => void;
  /** Callback when call status changes */
  onCallStatusChange?: (status: string, call: PhoneCall) => void;
}

/**
 * Hook for managing active phone calls with real-time streaming
 */
export const useActiveCall = (callId: string, options: UseActiveCallOptions = {}) => {
  const { token } = useAuth();
  const {
    autoStartStreaming = true,
    pollingInterval = 5000,
    onNewMessage,
    onCallStatusChange
  } = options;

  // State
  const [state, setState] = useState<ActiveCallState>({
    call: null,
    messages: [],
    isStreamActive: false,
    currentLanguage: '',
    error: null
  });

  // Refs
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastMessageCountRef = useRef<number>(0);

  // Update state helper
  const updateState = useCallback((updates: Partial<ActiveCallState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  // Telephony streaming hook
  const telephonyStream = useTelephonyStreaming({
    token: token || undefined,
    callId,
    languageCode: 'auto',
    model: 'nova-2',
    onTranscription: (text, isFinal, sender) => {
      console.log(`📞 Live ${sender} transcript:`, text);
      
      // Add transcript message to state
      if (isFinal && text.trim()) {
        const newMessage: CallMessage = {
          id: `live-${Date.now()}-${Math.random()}`,
          call_id: callId,
          content: text,
          sender: {
            identifier: sender === 'customer' ? 'customer' : 'agent',
            type: sender === 'customer' ? 'customer' : 'agent',
            name: sender === 'customer' ? 'Customer' : 'Agent'
          },
          timestamp: new Date().toISOString(),
          message_type: 'transcript',
          metadata: {
            is_automated: sender === 'agent',
            confidence_score: 0.9,
            language: state.currentLanguage
          },
          created_at: new Date().toISOString()
        };

        setState(prev => ({
          ...prev,
          messages: [...prev.messages, newMessage]
        }));

        onNewMessage?.(newMessage);
      }
    },
    onTTSAudio: (audioBlob) => {
      console.log('📞 Received TTS audio for phone call');
      // The backend handles playing audio to the phone call
      // This is just for logging/monitoring
    },
    onConnectionChange: (isConnected) => {
      console.log('📞 Telephony stream connection:', isConnected);
      updateState({ isStreamActive: isConnected });
    },
    onError: (error) => {
      console.error('📞 Telephony stream error:', error);
      updateState({ error });
    },
    onLanguageDetected: (language, confidence) => {
      console.log('📞 Language detected:', language, confidence);
      updateState({ currentLanguage: language });
    },
    onCallStatusChange: (status) => {
      console.log('📞 Call status changed:', status);
      if (state.call) {
        const updatedCall = { ...state.call, status: status as any };
        updateState({ call: updatedCall });
        onCallStatusChange?.(status, updatedCall);
      }
    }
  });

  // Load call data
  const loadCall = useCallback(async () => {
    if (!token || !callId) return;

    try {
      const call = await telephonyService.getCall(callId, token);
      updateState({ call, error: null });

      // Load messages
      try {
        const messages = await telephonyService.getCallMessages(callId, token);
        updateState({ messages });
        lastMessageCountRef.current = messages.length;
      } catch (msgError) {
        console.warn('📞 Failed to load call messages:', msgError);
      }

      return call;
    } catch (error: any) {
      console.error('📞 Error loading call:', error);
      updateState({ error: error.message || 'Failed to load call' });
      throw error;
    }
  }, [token, callId]);

  // Poll for call updates
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return;

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const call = await telephonyService.getCall(callId, token!);
        updateState({ call });

        // Check for new messages
        const messages = await telephonyService.getCallMessages(callId, token!);
        if (messages.length > lastMessageCountRef.current) {
          const newMessagesCount = messages.length - lastMessageCountRef.current;
          console.log(`📞 Found ${newMessagesCount} new messages`);
          
          // Get the new messages
          const newMessages = messages.slice(-newMessagesCount);
          newMessages.forEach(msg => onNewMessage?.(msg));
          
          updateState({ messages });
          lastMessageCountRef.current = messages.length;
        }

        // Stop polling if call is completed
        if (call.status === 'completed' || call.status === 'failed') {
          stopPolling();
          telephonyStream.stopTelephonyStream();
        }
      } catch (error) {
        console.error('📞 Error polling call updates:', error);
      }
    }, pollingInterval);
  }, [callId, token, pollingInterval, onNewMessage, telephonyStream]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  // Start monitoring the call
  const startMonitoring = useCallback(async () => {
    try {
      const call = await loadCall();
      
      if (!call) return;

      // Start streaming for active calls
      if (autoStartStreaming && (call.status === 'answered' || call.status === 'in_progress')) {
        await telephonyStream.startTelephonyStream();
      }

      // Start polling for updates
      startPolling();
      
    } catch (error) {
      console.error('📞 Error starting call monitoring:', error);
    }
  }, [loadCall, autoStartStreaming, telephonyStream, startPolling]);

  // Stop monitoring the call
  const stopMonitoring = useCallback(() => {
    stopPolling();
    telephonyStream.stopTelephonyStream();
  }, [stopPolling, telephonyStream]);

  // Send agent response
  const sendAgentResponse = useCallback(async (message: string) => {
    if (!state.call) return;

    try {
      // Send via streaming service for real-time TTS
      telephonyStream.sendAgentMessage(message);

      // Also add to call messages via API
      const newMessage = await telephonyService.addCallMessage(
        callId,
        {
          content: message,
          sender: {
            identifier: 'agent',
            type: 'agent',
            name: 'Agent'
          },
          timestamp: new Date().toISOString(),
          message_type: 'transcript',
          metadata: {
            is_automated: true,
            language: state.currentLanguage
          }
        },
        token!
      );

      // Update local state
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, newMessage]
      }));

      onNewMessage?.(newMessage);

    } catch (error) {
      console.error('📞 Error sending agent response:', error);
      throw error;
    }
  }, [state.call, state.currentLanguage, callId, token, telephonyStream, onNewMessage]);

  // Initialize when callId or token changes
  useEffect(() => {
    if (callId && token) {
      startMonitoring();
    }

    return () => {
      stopMonitoring();
    };
  }, [callId, token]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMonitoring();
    };
  }, []);

  return {
    // State
    call: state.call,
    messages: state.messages,
    isStreamActive: state.isStreamActive,
    currentLanguage: state.currentLanguage,
    error: state.error,
    
    // Stream state
    telephonyConnected: telephonyStream.isConnected,
    
    // Actions
    startMonitoring,
    stopMonitoring,
    sendAgentResponse,
    refreshCall: loadCall,
    
    // Stream actions
    startStream: telephonyStream.startTelephonyStream,
    stopStream: telephonyStream.stopTelephonyStream,
  };
};