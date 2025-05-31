# Conversation Hooks Implementation Guide

This document outlines the missing hooks that need to be implemented for the conversation feature to work properly.

## Missing Hooks

The following hooks need to be created in the `/src/app/conversations/[id]/hooks/` directory:

1. `useConversation.ts`
2. `useWebSocket.ts`
3. `useMessageLoader.ts`
4. `useScrollManager.ts`

## Missing Components

The following components need to be created in the `/src/app/conversations/[id]/components/` directory:

1. `TypingIndicator.tsx`
2. `StreamingIndicator.tsx`

## Hook Implementation Details

### 1. useConversation.ts

Purpose: Fetches and manages conversation data.

```typescript
// src/app/conversations/[id]/hooks/useConversation.ts
import { useState, useEffect } from 'react';
import { conversationService } from '@/services/conversations';
import { Conversation } from '@/types/conversation';

export const useConversation = (conversationId: string, token?: string | null) => {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConversation = async () => {
      if (!conversationId) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const data = await conversationService.getConversation(conversationId, token || '');
        setConversation(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load conversation');
        setConversation(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConversation();
  }, [conversationId, token]);

  return { conversation, isLoading, error };
};
```

### 2. useWebSocket.ts

Purpose: Manages WebSocket connection for real-time messaging.

```typescript
// src/app/conversations/[id]/hooks/useWebSocket.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { websocketService } from '@/services/websocket';
import { Message, MessageMetadata } from '@/app/conversations/[id]/types/message.types';
import { TypingStatusMessage, TokenMessage } from '@/app/conversations/[id]/types/websocket.types';
import { participantStorage } from '@/lib/participantStorage';

interface WebSocketConfig {
  conversationId: string;
  token?: string | null;
  userId?: string;
  userEmail?: string;
  onMessage: (message: Message) => void;
  onTypingStatus: (status: TypingStatusMessage) => void;
  onToken: (token: TokenMessage) => void;
}

export const useWebSocket = (config: WebSocketConfig) => {
  const { 
    conversationId, 
    token, 
    userId, 
    userEmail,
    onMessage, 
    onTypingStatus,
    onToken
  } = config;
  
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    // Get participant session if user is not logged in
    const participantSession = !token ? participantStorage.getSession(conversationId) : null;
    if (!token && !participantSession) return;

    const ws = websocketService.connect({
      conversationId,
      token: token || undefined,
      participantToken: participantSession?.token,
      onOpen: () => setIsConnected(true),
      onMessage: (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'message') {
            onMessage(data.message);
          } else if (data.type === 'typing_status') {
            onTypingStatus(data.status);
          } else if (data.type === 'token') {
            onToken(data.token_data);
          }
        } catch (err) {
          console.error('WebSocket message error:', err);
        }
      },
      onClose: () => {
        setIsConnected(false);
        // Try to reconnect after delay
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      },
      onError: (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      }
    });

    wsRef.current = ws;
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [conversationId, token, onMessage, onTypingStatus, onToken]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  const sendMessage = useCallback((content: string, metadata?: MessageMetadata) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    
    const message = {
      type: 'message',
      content,
      metadata: metadata || undefined,
      user_id: userId,
      email: userEmail
    };
    
    wsRef.current.send(JSON.stringify(message));
  }, [userId, userEmail]);

  const sendTypingStatus = useCallback((isTyping: boolean) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    
    const status = {
      type: 'typing_status',
      is_typing: isTyping,
      user_id: userId,
      email: userEmail
    };
    
    wsRef.current.send(JSON.stringify(status));
  }, [userId, userEmail]);

  return {
    isConnected,
    sendMessage,
    sendTypingStatus
  };
};
```

### 3. useMessageLoader.ts

Purpose: Loads and manages message history.

```typescript
// src/app/conversations/[id]/hooks/useMessageLoader.ts
import { useState, useEffect, useCallback } from 'react';
import { conversationService } from '@/services/conversations';
import { Message } from '@/app/conversations/[id]/types/message.types';

interface MessageLoaderProps {
  conversationId: string;
  token: string;
  limit?: number;
}

export const useMessageLoader = ({ conversationId, token, limit = 50 }: MessageLoaderProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadMessages = async () => {
      if (!conversationId || !token) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const data = await conversationService.getMessages(conversationId, token, limit);
        setMessages(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load messages');
        setMessages([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadMessages();
  }, [conversationId, token, limit]);

  const addMessage = useCallback((message: Message) => {
    setMessages(prev => {
      // Check if message already exists to avoid duplicates
      const exists = prev.some(m => m.id === message.id);
      if (exists) return prev;
      
      return [...prev, message];
    });
  }, []);

  return {
    messages,
    isLoading,
    error,
    addMessage
  };
};
```

### 4. useScrollManager.ts

Purpose: Manages scrolling behavior in the message list.

```typescript
// src/app/conversations/[id]/hooks/useScrollManager.ts
import { useRef, useCallback, useEffect } from 'react';
import { Message } from '@/app/conversations/[id]/types/message.types';

export const useScrollManager = (messages: Message[]) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  
  const scrollToBottom = useCallback((smooth = true) => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: smooth ? 'smooth' : 'auto',
        block: 'end'
      });
    }
  }, []);

  // Check if user is near bottom of scroll container
  const checkIfNearBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    
    const { scrollTop, scrollHeight, clientHeight } = container;
    const scrollBottom = scrollHeight - scrollTop - clientHeight;
    
    // Consider "near bottom" if within 100px of bottom
    isNearBottomRef.current = scrollBottom < 100;
  }, []);

  // Set up scroll event listener
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      checkIfNearBottom();
    };

    container.addEventListener('scroll', handleScroll);
    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [checkIfNearBottom]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messages.length > 0 && isNearBottomRef.current) {
      scrollToBottom();
    }
  }, [messages.length, scrollToBottom]);

  return {
    scrollContainerRef,
    messagesEndRef,
    scrollToBottom,
    isNearBottom: () => isNearBottomRef.current
  };
};
```

## Component Implementation Details

### 1. TypingIndicator.tsx

Purpose: Shows who is currently typing.

```typescript
// src/app/conversations/[id]/components/TypingIndicator.tsx
import React from 'react';
import { Loader2 } from 'lucide-react';

interface TypingState {
  [identifier: string]: {
    isTyping: boolean;
    agentType?: string;
    name?: string;
    email?: string;
    isAgent: boolean;
  };
}

interface TypingIndicatorProps {
  typingStates: TypingState;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ typingStates }) => {
  const typingUsers = Object.values(typingStates).filter(state => state.isTyping);
  
  if (typingUsers.length === 0) {
    return null;
  }

  // Format the typing indicator text based on who is typing
  const formatTypingText = () => {
    if (typingUsers.length === 1) {
      const user = typingUsers[0];
      const name = user.name || user.email || (user.isAgent ? user.agentType : 'Someone');
      return `${name} is typing...`;
    } else if (typingUsers.length === 2) {
      const names = typingUsers.map(user => 
        user.name || user.email || (user.isAgent ? user.agentType : 'Someone')
      );
      return `${names.join(' and ')} are typing...`;
    } else {
      return 'Multiple people are typing...';
    }
  };

  return (
    <div className="text-xs text-gray-500 mb-2 flex items-center">
      <Loader2 className="mr-2 h-3 w-3 animate-spin" />
      {formatTypingText()}
    </div>
  );
};
```

### 2. StreamingIndicator.tsx

Purpose: Shows real-time streaming content before it's finalized as a message.

```typescript
// src/app/conversations/[id]/components/StreamingIndicator.tsx
import React from 'react';
import { Loader2 } from 'lucide-react';

interface StreamingIndicatorProps {
  agentType: string;
  streamingContent: string;
  isActive: boolean;
}

export const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({ 
  agentType, 
  streamingContent, 
  isActive 
}) => {
  if (!isActive || !streamingContent) {
    return null;
  }

  const formatAgentName = (type: string) => {
    // Format the agent type to be more user-friendly
    return type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ');
  };

  return (
    <div className="bg-gray-50 rounded-lg p-3 mb-3 animate-pulse">
      <div className="flex items-center mb-1">
        <span className="font-medium text-sm text-gray-700">
          {formatAgentName(agentType)}
        </span>
        <Loader2 className="ml-2 h-3 w-3 animate-spin text-blue-500" />
      </div>
      <div className="text-gray-600 whitespace-pre-wrap">
        {streamingContent}
      </div>
    </div>
  );
};
```

## Implementation Notes

When implementing these hooks and components:

1. Ensure the API and WebSocket services are properly set up
2. Check that the types in `message.types.ts` and `websocket.types.ts` match what's expected
3. Test each hook and component individually before integrating
4. Add proper error handling and loading states

## Type Definitions

Make sure these types are defined in your type files:

### Message.types.ts

```typescript
export interface MessageMetadata {
  filename?: string;
  mime_type?: string;
  size?: number;
  text_length?: number;
  chunk_count?: number;
  is_file?: boolean;
}

export interface MessageSender {
  id: string;
  name?: string;
  email?: string;
  type: 'user' | 'agent' | 'system';
  is_owner: boolean;
}

export interface Message {
  id: string;
  conversation_id: string;
  content: string;
  timestamp: string;
  sender: MessageSender;
  metadata?: MessageMetadata;
}
```

### WebSocket.types.ts

```typescript
export interface TypingStatusMessage {
  identifier: string;
  is_typing: boolean;
  agent_type?: string;
  name?: string;
  email?: string;
}

export interface TokenMessage {
  agent_type: string;
  token: string;
  message_id?: string;
}
```