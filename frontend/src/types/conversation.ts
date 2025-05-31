// src/types/conversation.ts

export interface Conversation {
  id: string;
  title: string;
  description?: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  participants?: Participant[];
}

export interface Participant {
  id: string;
  conversation_id: string;
  email: string;
  name?: string;
  joined_at: string;
  is_active: boolean;
}

export interface CreateConversationRequest {
  title: string;
  description?: string;
}

export interface AddParticipantRequest {
  email: string;
}

export interface ConversationResponse {
  data: Conversation;
  message?: string;
}
