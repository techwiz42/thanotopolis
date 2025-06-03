// src/app/conversations/[id]/hooks/useConversation.ts
import { useState, useEffect, useCallback } from 'react';
import { conversationService } from '@/services/conversations';
import { Conversation } from '@/types/conversation';
import { participantStorage } from '@/lib/participantStorage';

export const useConversation = (conversationId: string, token?: string | null) => {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchConversation = async () => {
      try {
        // Determine authentication method
        const participantSession = participantStorage.getSession(conversationId);
        const authToken = participantSession?.token || token;

        console.log('Conversation Fetch Details:', {
          conversationId,
          hasParticipantSession: !!participantSession,
          hasToken: !!token,
          authTokenPresent: !!authToken
        });

        if (!authToken) {
          throw new Error('No authentication available');
        }

        const response = await conversationService.getConversation(conversationId, authToken);
        
        console.log('Conversation Fetch Result:', {
          conversation: response.data,
          hasData: !!response.data
        });

        // Add null check before setting conversation
        if (response.data) {
          // Type assertion to ensure compatibility with Conversation interface
          const conversationData: Conversation = {
            ...response.data,
            organization_id: response.data.tenant_id || '',
            is_privacy_enabled: response.data.status === 'private' || false,
            updated_at: response.data.updated_at || response.data.created_at // Ensure updated_at is never undefined
          };
          setConversation(conversationData);
        } else {
          setError('No conversation data found');
        }
      } catch (err) {
        console.error('Conversation Fetch Error:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch conversation');
      } finally {
        setIsLoading(false);
      }
    };

    fetchConversation();
  }, [conversationId, token]);

  return { conversation, error, isLoading };
};
