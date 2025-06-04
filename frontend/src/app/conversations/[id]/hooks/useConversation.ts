// src/app/conversations/[id]/hooks/useConversation.ts
import { useState, useEffect } from 'react';
import { conversationService, ConversationResponse } from '@/services/conversations';
import { Conversation } from '@/types/conversation';
import { participantStorage } from '@/lib/participantStorage';

// Map ConversationResponse to Conversation
const mapToConversation = (response: ConversationResponse): Conversation => {
  return {
    id: response.id,
    title: response.title,
    description: response.description,
    owner_id: response.owner_id,
    organization_id: response.tenant_id, // Map tenant_id to organization_id
    is_privacy_enabled: false, // Default value
    created_at: response.created_at,
    updated_at: response.updated_at || response.created_at,
    participant_count: response.participants?.length || 0
  };
};

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
          setConversation(mapToConversation(response.data));
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
