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
    [key: string]: unknown;
  };
}
