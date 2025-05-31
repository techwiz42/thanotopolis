// src/app/conversations/[id]/hooks/useStreamingTokens.ts
import { useState, useCallback, useRef } from 'react';
import { TokenMessage } from '@/app/conversations/[id]/types/websocket.types';

interface StreamingState {
  [agentType: string]: {
    tokens: string;
    active: boolean;
    lastMessageId?: string;
  };
}

export const useStreamingTokens = () => {
  const [streamingState, setStreamingState] = useState<StreamingState>({});
  const timeoutRefs = useRef<{ [agentType: string]: NodeJS.Timeout }>({});

  const handleToken = useCallback((tokenMessage: TokenMessage) => {
    const { agent_type, token, message_id } = tokenMessage;
    
    // Clear any existing timeout for this agent
    if (timeoutRefs.current[agent_type]) {
      clearTimeout(timeoutRefs.current[agent_type]);
    }

    setStreamingState(prev => ({
      ...prev,
      [agent_type]: {
        tokens: (prev[agent_type]?.tokens || '') + token,
        active: true,
        lastMessageId: message_id
      }
    }));

    // Set a timeout to mark streaming as inactive if no new tokens arrive
    timeoutRefs.current[agent_type] = setTimeout(() => {
      setStreamingState(prev => ({
        ...prev,
        [agent_type]: {
          ...prev[agent_type],
          active: false
        }
      }));
    }, 1000); // 1 second timeout
  }, []);

  const resetStreamingForAgent = useCallback((agentType: string, messageId?: string) => {
    // Clear timeout if exists
    if (timeoutRefs.current[agentType]) {
      clearTimeout(timeoutRefs.current[agentType]);
      delete timeoutRefs.current[agentType];
    }

    setStreamingState(prev => {
      const currentState = prev[agentType];
      
      // Only reset if this is for the current message or no message ID is specified
      if (!messageId || !currentState?.lastMessageId || currentState.lastMessageId === messageId) {
        const newState = { ...prev };
        delete newState[agentType];
        return newState;
      }
      
      return prev;
    });
  }, []);

  const resetAllStreaming = useCallback(() => {
    // Clear all timeouts
    Object.values(timeoutRefs.current).forEach(timeout => clearTimeout(timeout));
    timeoutRefs.current = {};
    
    setStreamingState({});
  }, []);

  return {
    streamingState,
    handleToken,
    resetStreamingForAgent,
    resetAllStreaming
  };
};
