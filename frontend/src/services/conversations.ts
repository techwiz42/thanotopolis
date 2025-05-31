// src/services/conversations.ts
import { api } from './api';
import { Conversation, ConversationListResponse, MessageResponse, ParticipantResponse } from '@/types/conversation';

interface CreateConversationData {
  title: string;
  description?: string;
  // Removed is_privacy_enabled
}

interface AddParticipantData {
  email: string;
}

// Response wrapper for some endpoints that need it
interface ConversationResponseWrapper<T> {
  data: T;
  message?: string;
}

export const conversationService = {
  // Get all conversations for the authenticated user
  getConversations: async (token: string): Promise<ConversationListResponse> => {
    const response = await api.get<ConversationListResponse>('/api/conversations', {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  // Get a specific conversation by ID
  getConversation: async (conversationId: string, token: string): Promise<ConversationResponseWrapper<Conversation>> => {
    const response = await api.get<Conversation>(`/api/conversations/${conversationId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    // Wrap the response to match expected format
    return { data: response.data };
  },

  // Create a new conversation - backend returns conversation directly
  createConversation: async (data: CreateConversationData, token: string): Promise<Conversation> => {
    const response = await api.post<Conversation>('/api/conversations', data, {
      headers: { Authorization: `Bearer ${token}` }
    });
    // Backend returns conversation directly, not wrapped in data
    return response.data;
  },

  // Get messages for a conversation
  getMessages: async (conversationId: string, token: string): Promise<ConversationResponseWrapper<MessageResponse[]>> => {
    const response = await api.get<MessageResponse[]>(`/api/conversations/${conversationId}/messages`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return { data: response.data };
  },

  // Add a participant to a conversation
  addParticipant: async (conversationId: string, data: AddParticipantData, token: string): Promise<ConversationResponseWrapper<ParticipantResponse>> => {
    const response = await api.post<ParticipantResponse>(
      `/api/conversations/${conversationId}/participants`, 
      data,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    return { data: response.data };
  },

  // Get participants for a conversation
  getParticipants: async (conversationId: string, token: string): Promise<ConversationResponseWrapper<ParticipantResponse[]>> => {
    const response = await api.get<ParticipantResponse[]>(`/api/conversations/${conversationId}/participants`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return { data: response.data };
  },

  // Remove a participant from a conversation
  removeParticipant: async (conversationId: string, participantId: string, token: string): Promise<ConversationResponseWrapper<void>> => {
    const response = await api.delete<void>(
      `/api/conversations/${conversationId}/participants/${participantId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    return { data: response.data };
  },

  // Update conversation details
  updateConversation: async (conversationId: string, data: Partial<CreateConversationData>, token: string): Promise<Conversation> => {
    const response = await api.put<Conversation>(
      `/api/conversations/${conversationId}`,
      data,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    return response.data;
  },

  // Delete a conversation
  deleteConversation: async (conversationId: string, token: string): Promise<{status: string, message: string}> => {
    const response = await api.delete<{status: string, message: string}>(
      `/api/conversations/${conversationId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    return response.data;
  },

  // Add agents to conversation (placeholder for future implementation)
  addAgentsToConversation: async (conversationId: string, token: string): Promise<ConversationResponseWrapper<void>> => {
    // TODO: Implement based on your agent management system
    return { data: undefined, message: 'Agent addition not yet implemented' };
  }
};
