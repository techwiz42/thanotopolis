// src/services/websocket.ts

import { WebSocketMessage } from '@/app/conversations/[id]/types/websocket.types';
import { MessageMetadata } from '@/app/conversations/[id]/types/message.types';

type MessageHandler = (message: WebSocketMessage) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private conversationId: string | null = null;
  private token: string | null = null;
  private userId: string | null = null;

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  async connect(conversationId: string, token: string, userId: string): Promise<void> {
    // Check if already connected to the same conversation
    if (this.ws?.readyState === WebSocket.OPEN && this.conversationId === conversationId) {
      console.log('WebSocket already connected to this conversation');
      return;
    }

    // If connecting or already connected, skip
    if (this.ws?.readyState === WebSocket.CONNECTING) {
      console.log('WebSocket connection already in progress');
      return;
    }

    // If connected to a different conversation, disconnect first
    if (this.ws?.readyState === WebSocket.OPEN && this.conversationId !== conversationId) {
      console.log('Disconnecting from previous conversation');
      this.disconnect();
    }

    this.conversationId = conversationId;
    this.token = token;
    this.userId = userId;

    // Fix the WebSocket URL construction
    let wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    
    // Remove any trailing /ws from the base URL to avoid duplication
    if (wsBaseUrl.endsWith('/ws')) {
      wsBaseUrl = wsBaseUrl.slice(0, -3);
    }
    
    const organization = localStorage.getItem('organization') || '';
    
    // Include organization in WebSocket connection params
    const queryParams = new URLSearchParams({
      token: token,
      user_id: userId,
      ...(organization && { tenant_id: organization })
    });
    
    // Fixed: Use the correct path structure
    const url = `${wsBaseUrl}/api/ws/conversations/${conversationId}?${queryParams.toString()}`;

    console.log('Connecting to WebSocket:', url);

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WebSocketMessage;
            console.log('WebSocket message received:', message);
            this.notifyHandlers(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          // Only reconnect if not a normal closure
          if (event.code !== 1000 && event.code !== 1001) {
            this.handleReconnect();
          }
        };
      } catch (error) {
        console.error('Error creating WebSocket:', error);
        reject(error);
      }
    });
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts && this.conversationId && this.token && this.userId) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      
      setTimeout(() => {
        this.connect(this.conversationId!, this.token!, this.userId!).catch(console.error);
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  disconnect(): void {
    if (this.ws) {
      // Remove event listeners before closing
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.conversationId = null;
    this.token = null;
    this.userId = null;
    this.reconnectAttempts = 0;
    // Clear handlers on disconnect
    this.messageHandlers.clear();
  }

  subscribe(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  private notifyHandlers(message: WebSocketMessage): void {
    this.messageHandlers.forEach(handler => handler(message));
  }

  sendMessage(content: string, senderEmail: string, metadata?: MessageMetadata): void {
    if (!this.isConnected) {
      throw new Error('WebSocket is not connected');
    }

    const message = {
      type: 'message',
      content,
      sender_email: senderEmail,
      message_metadata: metadata,
    };

    console.log('Sending WebSocket message:', message);
    this.ws!.send(JSON.stringify(message));
  }

  sendTypingStatus(isTyping: boolean, senderEmail: string): void {
    if (!this.isConnected) {
      throw new Error('WebSocket is not connected');
    }

    const message = {
      type: 'typing_status',
      is_typing: isTyping,
      sender_email: senderEmail,
    };

    this.ws!.send(JSON.stringify(message));
  }
}

export const websocketService = new WebSocketService();
