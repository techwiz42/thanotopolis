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

  // Check if this is a participant/user message by looking for participant_id
  if (msg.participant_id) {
    // Check for owner status in message_info
    isOwner = msg.message_info?.is_owner === true;
    senderType = 'user';
    
    // Extract participant name, fallback to email or Unknown
    senderName = msg.message_info?.participant_name || 
                 msg.message_info?.participant_email ||
                 'Unknown';
                 
    // Extract email
    senderEmail = msg.message_info?.participant_email || '';
  } 
  // Check if this is an agent message
  else if (msg.agent_id) {
    isOwner = false;
    // Set appropriate sender type based on agent type
    senderType = msg.message_info?.source === 'MODERATOR' ? 'moderator' : 'agent';
    // Use agent type or fallback to 'Agent'
    senderName = msg.message_info?.source || 'Agent';
  }

  const transformed: Message = {
    id: msg.id,
    content: msg.content,
    timestamp: msg.created_at,
    sender: {
      identifier: senderEmail || msg.participant_id || msg.agent_id || 'unknown',
      is_owner: isOwner,
      name: senderName,
      email: senderEmail,
      type: senderType
    },
    message_info: {
      // Copy message_info fields or create empty object
      ...(msg.message_info || {}),
      is_file: Boolean(msg.message_info?.file_name),
      file_name: msg.message_info?.file_name,
      file_type: msg.message_info?.file_type,
      file_size: msg.message_info?.file_size
    }
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

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const addMessage = useCallback((message: Message) => {
    setMessages(prev => {
      // Check for duplicates using the message ID
      const isDuplicate = prev.some(m => m.id === message.id);
      if (isDuplicate) {
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

    loadMessages();
  }, [conversationId, loadMessages]);

  return {
    messages,
    isLoading,
    addMessage
  };
};
