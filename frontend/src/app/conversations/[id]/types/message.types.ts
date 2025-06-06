// src/app/conversations/[id]/types/message.types.ts

export interface MessageSender {
  identifier: string;
  is_owner: boolean;
  name?: string;
  email?: string;
  type: 'user' | 'agent' | 'moderator' | 'system';
  message_metadata?: MessageMetadata;
}

export interface MessageMetadata {
  filename?: string;
  mime_type?: string;
  size?: number;
  text_length?: number;
  chunk_count?: number;
  is_file?: boolean;
  file_name?: string;
  file_type?: string;
  file_size?: number;
  is_private?: boolean;
  is_streaming?: boolean;
  [key: string]: unknown;
}

export interface Message {
  id: string;
  content: string;
  sender: MessageSender;
  timestamp: string;
  message_metadata?: MessageMetadata;
  message_info?: MessageMetadata;
  agent_type?: string;
  is_streaming?: boolean;
  streaming_content?: string;
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
