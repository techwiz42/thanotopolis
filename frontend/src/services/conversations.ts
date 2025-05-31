// src/services/conversations.ts
import { api } from './api';
import { Conversation, ConversationListResponse, MessageResponse, ParticipantResponse } from '@/types/conversation';

interface CreateConversationData {
  title: string;
  description?: string;
  is_privacy_enabled?: boolean;
}

interface AddParticipantData {
  email: string;
}

interface ConversationResponse<T> {
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
  getConversation: async (conversationId: string, token: string): Promise<ConversationResponse<Conversation>> => {
    const response = await api.get<ConversationResponse<Conversation>>(`/api/conversations/${conversationId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  // Create a new conversation
  createConversation: async (data: CreateConversationData, token: string): Promise<ConversationResponse<Conversation>> => {
    const response = await api.post<ConversationResponse<Conversation>>('/api/conversations', data, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  // Get messages for a conversation
  getMessages: async (conversationId: string, token: string): Promise<ConversationResponse<MessageResponse[]>> => {
    const response = await api.get<ConversationResponse<MessageResponse[]>>(`/api/conversations/${conversationId}/messages`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  // Add a participant to a conversation
  addParticipant: async (conversationId: string, data: AddParticipantData, token: string): Promise<ConversationResponse<ParticipantResponse>> => {
    const response = await api.post<ConversationResponse<ParticipantResponse>>(
      `/api/conversations/${conversationId}/participants`, 
      data,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    return response.data;
  },

  // Get participants for a conversation
  getParticipants: async (conversationId: string, token: string): Promise<ConversationResponse<ParticipantResponse[]>> => {
    const response = await api.get<ConversationResponse<ParticipantResponse[]>>(`/api/conversations/${conversationId}/participants`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  // Remove a participant from a conversation
  removeParticipant: async (conversationId: string, participantId: string, token: string): Promise<ConversationResponse<void>> => {
    const response = await api.delete<ConversationResponse<void>>(
      `/api/conversations/${conversationId}/participants/${participantId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    return response.data;
  },

  // Update conversation details
  updateConversation: async (conversationId: string, data: Partial<CreateConversationData>, token: string): Promise<ConversationResponse<Conversation>> => {
    const response = await api.put<ConversationResponse<Conversation>>(
      `/api/conversations/${conversationId}`,
      data,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    return response.data;
  },

  // Delete a conversation
  deleteConversation: async (conversationId: string, token: string): Promise<ConversationResponse<void>> => {
    const response = await api.delete<ConversationResponse<void>>(
      `/api/conversations/${conversationId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    return response.data;
  },

  // Add agents to conversation (placeholder for future implementation)
  addAgentsToConversation: async (conversationId: string, token: string): Promise<ConversationResponse<void>> => {
    // TODO: Implement based on your agent management system
    // This might involve:
    // 1. Getting available agents from an API
    // 2. Adding each agent to the conversation
    // Example:
    // const agents = await api.get('/api/agents/available');
    // for (const agent of agents.data) {
    //   await api.post(`/api/conversations/${conversationId}/agents`, { agent_id: agent.id }, {
    //     headers: { Authorization: `Bearer ${token}` }
    //   });
    // }
    return { data: undefined, message: 'Agent addition not yet implemented' };
  }
};
