// src/app/conversations/[id]/hooks/useMessageLoader.ts
import { useState, useCallback, useEffect, useRef } from 'react';
import { Message, MessageResponse } from '../types/message.types';
import { conversationService } from '@/services/conversations';
import { participantStorage } from '@/lib/participantStorage';

interface UseMessageLoaderProps {
  conversationId: string;
  token: string;
}

interface UseMessageLoaderReturn {
  messages: Message[];
  isLoading: boolean;
  addMessage: (message: Message) => void;
}

const transformMessageResponse = (msg: MessageResponse): Message => {
  let isOwner = false;
  let senderType: 'user' | 'agent' | 'moderator' | 'system' = 'user';
  let senderName = '';
  let senderEmail = '';

  // Check if this is an agent message by looking for agent_type
  if (msg.agent_type) {
    isOwner = false;
    // Set appropriate sender type based on agent type
    senderType = msg.agent_type === 'MODERATOR' ? 'moderator' : 'agent';
    // Use agent type or fallback to 'Agent'
    senderName = msg.agent_type || 'Agent';
    senderEmail = `${msg.agent_type?.toLowerCase()}@thanotopolis.local`;
  }
  // Check if this is a user message by looking for user_id
  else if (msg.user_id) {
    // Check for owner status from sender_type or derived from context
    isOwner = msg.sender_type === 'user' || true; // Default to true for user messages
    senderType = 'user';
    
    // Use sender_name from backend or fallback
    senderName = msg.sender_name || 'User';
    senderEmail = ''; // Will be set from context if available
  }
  // Check if this is a participant message by looking for participant_id
  else if (msg.participant_id) {
    // Check for owner status in message_info or metadata
    isOwner = (msg.metadata as any)?.is_owner === true;
    senderType = 'user';
    
    // Extract participant name, fallback to email or Unknown
    senderName = msg.sender_name || 'Participant';
    senderEmail = ''; // Will be extracted from metadata if available
  }
  // Fallback to system message
  else {
    isOwner = false;
    senderType = 'system';
    senderName = 'System';
    senderEmail = 'system@thanotopolis.local';
  }

  const transformed: Message = {
    id: msg.id,
    content: msg.content,
    timestamp: msg.created_at,
    sender: {
      identifier: senderEmail || msg.user_id || msg.participant_id || msg.agent_type || 'unknown',
      is_owner: isOwner,
      name: senderName,
      email: senderEmail,
      type: senderType
    },
    message_metadata: msg.metadata,
    // Add agent_type to the message if it exists
    agent_type: msg.agent_type
  };
  
  console.log("DB Message transformed:", JSON.stringify(transformed, null, 2));
  return transformed;
};

export const useMessageLoader = ({
  conversationId,
  token,
}: UseMessageLoaderProps): UseMessageLoaderReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const mountedRef = useRef(true);
  const hasLoadedInitialMessages = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const addMessage = useCallback((message: Message) => {
    // Skip historical messages if we haven't loaded initial messages yet
    if (!hasLoadedInitialMessages.current && 'is_history' in message && message.is_history) {
      console.log('Skipping historical message during initial load');
      return;
    }
    
    setMessages(prev => {
      // Check for duplicates using the message ID
      const isDuplicate = prev.some(m => m.id === message.id);
      if (isDuplicate) {
        console.log(`Duplicate message detected: ${message.id}, skipping...`);
        return prev;
      }
      // Also check if this is a historical message that we already have
      const isHistorical = 'is_history' in message && message.is_history;
      if (isHistorical && prev.some(m => m.content === message.content && Math.abs(new Date(m.timestamp).getTime() - new Date(message.timestamp).getTime()) < 1000)) {
        console.log(`Historical duplicate detected by content match, skipping...`);
        return prev;
      }
      return [...prev, message];
    });
  }, []);

  const loadMessages = useCallback(async () => {
    if (!conversationId) {
      return;
    }

    try {
      const participantSession = participantStorage.getSession(conversationId);
      const authToken = participantSession?.token || token;

      if (!authToken) {
        console.log('No auth token available');
        return;
      }

      setIsLoading(true);

      // First get conversation details
      const conversationResponse = await conversationService.getConversation(conversationId, authToken);
      const conversation = conversationResponse.data;
      
      // Then get messages
      const messagesResponse = await conversationService.getMessages(conversationId, authToken);
      console.log("Raw messages response:", messagesResponse);

      if (!mountedRef.current) return;

      if (messagesResponse.data) {
        let transformedMessages = messagesResponse.data
          .sort((a: MessageResponse, b: MessageResponse) => 
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          )
          .map(transformMessageResponse);

        // Add description as first message if conversation has one
        if (conversation?.description) {
          transformedMessages = [{
            id: `desc-${conversationId}`,
            content: conversation.description,
            timestamp: conversation.created_at,
            sender: {
              identifier: 'system',
              is_owner: false,
              name: 'System',
              type: 'system'
            },
            message_info: {}
          }, ...transformedMessages];
        }

        setMessages(transformedMessages);
        hasLoadedInitialMessages.current = true;
      }
    } catch (error) {
      console.error('Error loading messages:', error);
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [conversationId, token]);

  useEffect(() => {
    if (!conversationId) {
      setIsLoading(false);
      return;
    }

    // Reset the flag when conversation changes
    hasLoadedInitialMessages.current = false;
    loadMessages();
  }, [conversationId, loadMessages]);

  return {
    messages,
    isLoading,
    addMessage
  };
};
