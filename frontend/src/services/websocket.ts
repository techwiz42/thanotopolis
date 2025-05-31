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
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this.conversationId = conversationId;
    this.token = token;
    this.userId = userId;

    // Build the correct WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_WS_HOST || window.location.hostname;
    const port = process.env.NEXT_PUBLIC_WS_PORT || (window.location.protocol === 'https:' ? '443' : '8000');
    
    // Construct base WebSocket URL
    let wsBaseUrl: string;
    if (process.env.NEXT_PUBLIC_WS_URL) {
      wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL;
    } else {
      wsBaseUrl = `${protocol}//${host}:${port}`;
    }
    
    const organization = localStorage.getItem('organization') || '';
    
    // Build query parameters
    const queryParams = new URLSearchParams({
      token: token,
      user_id: userId,
      ...(organization && { tenant_id: organization })
    });
    
    // Construct the correct URL path to match backend: /api/ws/conversations/{id}
    const url = `${wsBaseUrl}/api/ws/conversations/${conversationId}?${queryParams.toString()}`;

    console.log('Connecting to WebSocket:', url);

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          console.log('WebSocket connected successfully');
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
          if (event.code !== 1000) { // 1000 is normal closure
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
    } else {
      console.error('Max reconnection attempts reached or missing connection info');
    }
  }

  disconnect(): void {
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
    if (this.ws) {
      this.ws.close(1000, 'User disconnected'); // Normal closure
      this.ws = null;
    }
    this.messageHandlers.clear();
  }

  subscribe(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  private notifyHandlers(message: WebSocketMessage): void {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
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
      console.warn('Cannot send typing status: WebSocket is not connected');
      return;
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
