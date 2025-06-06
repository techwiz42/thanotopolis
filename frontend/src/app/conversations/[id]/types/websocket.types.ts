// src/app/conversations/[id]/types/websocket.types.ts

import { MessageMetadata } from './message.types';

export interface BaseWebSocketMessage {
  type: string;
}

export interface MessageWebSocketMessage extends BaseWebSocketMessage {
  type: 'message';
  id?: string;
  content: string;
  identifier: string;
  is_owner?: boolean;
  agent_type?: string;
  name?: string;
  email?: string;
  timestamp: string;
  message_metadata?: MessageMetadata;
}

export interface TypingStatusMessage extends BaseWebSocketMessage {
  type: 'typing_status';
  identifier: string;
  is_typing: boolean;
  agent_type?: string;
  name?: string;
  email?: string;
}

export interface TokenMessage extends BaseWebSocketMessage {
  type: 'token';
  token: string;
  agent_type: string;
  message_id?: string;
}

export interface ErrorMessage extends BaseWebSocketMessage {
  type: 'error';
  message: string;
}

export type WebSocketMessage = 
  | MessageWebSocketMessage 
  | TypingStatusMessage 
  | TokenMessage 
  | ErrorMessage;
