// src/types/conversation.ts
export interface Conversation {
  id: string;
  title: string;
  description?: string;
  owner_id: string;
  organization_id: string;
  is_privacy_enabled: boolean;
  created_at: string;
  updated_at: string;
  participant_count?: number;
}

export interface ConversationListResponse {
  conversations: Conversation[];
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  content: string;
  created_at: string;
  participant_id?: string;
  agent_id?: string;
  message_info?: {
    is_owner?: boolean;
    participant_name?: string;
    participant_email?: string;
    source?: string;
    file_name?: string;
    file_type?: string;
    file_size?: number;
  };
}

export interface ParticipantResponse {
  id: string;
  conversation_id: string;
  email: string;
  name?: string;
  joined_at: string;
  is_active: boolean;
}
