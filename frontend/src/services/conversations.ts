// src/services/conversations.ts

import { api } from './api';
import { 
  Conversation, 
  CreateConversationRequest, 
  AddParticipantRequest,
  ConversationResponse 
} from '@/types/conversation';
import { MessageResponse } from '@/app/conversations/[id]/types/message.types';

class ConversationService {
  async getConversations(token: string): Promise<{ data: Conversation[] }> {
    return api.get<Conversation[]>('/api/conversations', {
      headers: { Authorization: `Bearer ${token}` },
    });
  }

  async getConversation(id: string, token: string): Promise<ConversationResponse> {
    return api.get<Conversation>(`/api/conversations/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  }

  async createConversation(data: CreateConversationRequest, token: string): Promise<ConversationResponse> {
    return api.post<Conversation>('/api/conversations', data, {
      headers: { Authorization: `Bearer ${token}` },
    });
  }

  async getMessages(conversationId: string, token: string): Promise<{ data: MessageResponse[] }> {
    return api.get<MessageResponse[]>(`/api/conversations/${conversationId}/messages`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  }

  async addParticipant(
    conversationId: string, 
    data: AddParticipantRequest, 
    token: string
  ): Promise<{ data: any; message: string }> {
    const response = await api.post<any>(
      `/api/conversations/${conversationId}/participants`,
      data,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    
    return {
      data: response.data,
      message: response.data.message || 'Participant added successfully',
    };
  }

  async removeParticipant(conversationId: string, participantId: string, token: string): Promise<void> {
    await api.delete(`/api/conversations/${conversationId}/participants/${participantId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  }
}

export const conversationService = new ConversationService();
