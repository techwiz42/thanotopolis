// src/services/conversations.ts
import { api } from './api';

export interface ConversationCreateData {
  title?: string;
  description?: string;
  user_ids?: string[];
  agent_types?: string[];
  participant_ids?: string[];
  participant_emails?: string[];
}

export interface ConversationUpdateData {
  title?: string;
  description?: string;
  status?: string;
}

export interface MessageCreateData {
  content: string;
  message_type?: 'text' | 'file' | 'image' | 'system';
  metadata?: Record<string, any>;
  mention?: string;
}

export interface ConversationResponse {
  id: string;
  title: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at?: string;
  owner_id: string;
  tenant_id: string;
  created_by_user_id: string;
  users: any[];
  agents: any[];
  participants: any[];
  recent_messages: any[];
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  content: string;
  message_type: string;
  user_id?: string;
  agent_type?: string;
  participant_id?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at?: string;
  sender_name?: string;
  sender_type?: string;
}

export interface ConversationListResponse {
  id: string;
  title: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at?: string;
  last_message?: MessageResponse;
  participant_count: number;
  message_count: number;
}

export const conversationService = {
  // Conversation CRUD
  async createConversation(data: ConversationCreateData, token: string): Promise<ConversationResponse> {
    try {
      console.log('=== CREATE CONVERSATION DEBUG ===');
      console.log('Sending conversation creation request:', data);
      console.log('Token (first 20 chars):', token?.substring(0, 20) + '...');
      console.log('API base URL:', api.defaults.baseURL);
      console.log('Full URL will be:', `${api.defaults.baseURL}/conversations`);
      
      const response = await api.post<ConversationResponse>('/conversations', data, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      // TypeScript doesn't know response has a status, so we type cast it safely
      console.log('Raw API response:', response);
      console.log('Response data:', response.data);
      // Don't try to access status directly since the request() function doesn't return it
      console.log('Response headers:', response.headers);
      
      return response.data as ConversationResponse;
      
    } catch (error: any) {
      console.error('=== CONVERSATION CREATION ERROR ===');
      console.error('Error object:', error);
      console.error('Error message:', error.message);
      
      if (error.response) {
        console.error('Error response status:', error.response.status);
        console.error('Error response data:', error.response.data);
        console.error('Error response headers:', error.response.headers);
        console.error('Request URL that failed:', error.config?.url);
        console.error('Full request config:', error.config);
        
        // Check if we got HTML instead of JSON
        if (typeof error.response.data === 'string' && error.response.data.includes('<!DOCTYPE')) {
          throw new Error(`API returned HTML instead of JSON. This usually means the API endpoint doesn't exist or the server isn't running. Status: ${error.response.status}`);
        }
        
        throw new Error(error.response.data?.detail || error.response.data?.message || `API Error: ${error.response.status}`);
      } else if (error.request) {
        console.error('No response received:', error.request);
        throw new Error('No response from server - check if the backend is running');
      } else {
        console.error('Request setup error:', error.message);
        throw new Error(error.message);
      }
    }
  },

  async getConversations(token: string): Promise<ConversationListResponse[]> {
    try {
      console.log('=== GET CONVERSATIONS DEBUG ===');
      console.log('Making request to /conversations endpoint');
      console.log('Token (first 20 chars):', token?.substring(0, 20) + '...');
      console.log('API base URL:', api.defaults.baseURL);
      console.log('Full URL will be:', `${api.defaults.baseURL}/conversations`);
      
      const response = await fetch('/api/conversations', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Raw conversations response:', response);
      console.log('Response data:', data);
      console.log('Response status:', response.status || 'unknown');
      
      return data;
    } catch (error: any) {
      console.error('=== GET CONVERSATIONS ERROR ===');
      console.error('Error object:', error);
      console.error('Error message:', error.message);
      
      if (error.response) {
        console.error('Error response status:', error.response.status);
        console.error('Error response data:', error.response.data);
        console.error('Request URL that failed:', error.config?.url);
        
        // Check if we got HTML instead of JSON
        if (typeof error.response.data === 'string' && error.response.data.includes('<!DOCTYPE')) {
          throw new Error(`API returned HTML instead of JSON. This usually means the API endpoint doesn't exist or the server isn't running. Status: ${error.response.status}`);
        }
      }
      
      throw error;
    }
  },

  async getConversation(conversationId: string, token: string): Promise<{ data: ConversationResponse }> {
    try {
      const response = await api.get<ConversationResponse>(`/conversations/${conversationId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return {
        data: response.data as ConversationResponse
      };
    } catch (error) {
      console.error('Error fetching conversation:', error);
      throw error;
    }
  },

  async updateConversation(conversationId: string, data: ConversationUpdateData, token: string): Promise<ConversationResponse> {
    try {
      const response = await api.patch<ConversationResponse>(`/conversations/${conversationId}`, data, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      return response.data as ConversationResponse;
    } catch (error) {
      console.error('Error updating conversation:', error);
      throw error;
    }
  },

  async deleteConversation(conversationId: string, token: string): Promise<{ status: string; message: string }> {
    try {
      const response = await api.delete<{ status: string; message: string }>(`/conversations/${conversationId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as { status: string; message: string };
    } catch (error) {
      console.error('Error deleting conversation:', error);
      throw error;
    }
  },

  async searchConversations(query: string, token: string): Promise<ConversationListResponse[]> {
    try {
      const response = await api.get<ConversationListResponse[]>('/conversations/search', {
        params: { q: query },
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return (response.data as ConversationListResponse[]) || [];
    } catch (error) {
      console.error('Error searching conversations:', error);
      throw error;
    }
  },

  // Message operations
  async getMessages(conversationId: string, token: string, skip = 0, limit?: number): Promise<{ data: MessageResponse[] }> {
    try {
      const params: any = { skip };
      if (limit !== undefined) {
        params.limit = limit;
      }
      
      const response = await api.get<MessageResponse[]>(`/conversations/${conversationId}/messages`, {
        params,
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return {
        data: (response.data as MessageResponse[]) || []
      };
    } catch (error) {
      console.error('Error fetching messages:', error);
      throw error;
    }
  },

  async sendMessage(conversationId: string, data: MessageCreateData, token: string): Promise<MessageResponse> {
    try {
      const response = await api.post<MessageResponse>(`/conversations/${conversationId}/messages`, data, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      return response.data as MessageResponse;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  },

  async getMessage(conversationId: string, messageId: string, token: string): Promise<MessageResponse> {
    try {
      const response = await api.get<MessageResponse>(`/conversations/${conversationId}/messages/${messageId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as MessageResponse;
    } catch (error) {
      console.error('Error fetching message:', error);
      throw error;
    }
  },

  async deleteMessage(conversationId: string, messageId: string, token: string): Promise<{ status: string; message: string }> {
    try {
      const response = await api.delete<{ status: string; message: string }>(`/conversations/${conversationId}/messages/${messageId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as { status: string; message: string };
    } catch (error) {
      console.error('Error deleting message:', error);
      throw error;
    }
  },

  async clearMessages(conversationId: string, token: string): Promise<{ status: string; message: string }> {
    try {
      const response = await api.delete<{ status: string; message: string }>(`/conversations/${conversationId}/messages`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as { status: string; message: string };
    } catch (error) {
      console.error('Error clearing messages:', error);
      throw error;
    }
  },

  // Agent operations
  async addAgent(conversationId: string, agentData: { agent_type: string; configuration?: Record<string, any> }, token: string): Promise<{ id: string; agent_type: string; configuration?: Record<string, any> }> {
    try {
      const response = await api.post<{ id: string; agent_type: string; configuration?: Record<string, any> }>(`/conversations/${conversationId}/agents`, agentData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      return response.data as { id: string; agent_type: string; configuration?: Record<string, any> };
    } catch (error) {
      console.error('Error adding agent:', error);
      throw error;
    }
  },

  async getAgents(conversationId: string, token: string): Promise<Array<{ id: string; agent_type: string; configuration?: Record<string, any>; added_at: string }>> {
    try {
      const response = await api.get<Array<{ id: string; agent_type: string; configuration?: Record<string, any>; added_at: string }>>(`/conversations/${conversationId}/agents`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return (response.data as Array<{ id: string; agent_type: string; configuration?: Record<string, any>; added_at: string }>) || [];
    } catch (error) {
      console.error('Error fetching agents:', error);
      throw error;
    }
  },

  async removeAgent(conversationId: string, agentId: string, token: string): Promise<{ status: string; message: string }> {
    try {
      const response = await api.delete<{ status: string; message: string }>(`/conversations/${conversationId}/agents/${agentId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as { status: string; message: string };
    } catch (error) {
      console.error('Error removing agent:', error);
      throw error;
    }
  },

  // Participant operations (Note: Backend doesn't seem to have these endpoints, you may need to implement them)
  async addParticipant(conversationId: string, participantData: { email: string }, token: string): Promise<{ message: string }> {
    try {
      // This endpoint might not exist in your backend - you may need to implement it
      // or handle participant addition differently
      const response = await api.post<{ message: string }>(`/conversations/${conversationId}/participants`, participantData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      // We don't directly use response.data here because we're creating our own response object
      return {
        message: 'Participant added successfully'
      };
    } catch (error: any) { // Explicitly type error as any
      console.error('Error adding participant:', error);
      if (error.response?.status === 404) {
        throw new Error('Participant endpoint not implemented yet');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw error;
    }
  },

  // Utility operations
  async exportConversation(conversationId: string, token: string): Promise<{ thread_id: string; title: string; description?: string; created_at: string; messages: any[] }> {
    try {
      const response = await api.get<{ thread_id: string; title: string; description?: string; created_at: string; messages: any[] }>(`/conversations/${conversationId}/export`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as { thread_id: string; title: string; description?: string; created_at: string; messages: any[] };
    } catch (error) {
      console.error('Error exporting conversation:', error);
      throw error;
    }
  },

  async getConversationStats(conversationId: string, token: string): Promise<{ message_count: number; created_at: string; last_message_at?: string; agents_used: string[]; status: string; title: string }> {
    try {
      const response = await api.get<{ message_count: number; created_at: string; last_message_at?: string; agents_used: string[]; status: string; title: string }>(`/conversations/${conversationId}/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as { message_count: number; created_at: string; last_message_at?: string; agents_used: string[]; status: string; title: string };
    } catch (error) {
      console.error('Error fetching conversation stats:', error);
      throw error;
    }
  }
};
