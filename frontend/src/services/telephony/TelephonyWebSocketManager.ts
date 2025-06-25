// src/services/telephony/TelephonyWebSocketManager.ts
import { EventEmitter } from 'events';

export interface TelephonyWebSocketEvent {
  type: 'telephony_connected' | 'call_status_update' | 'customer_transcript' | 'agent_tts_audio' | 
        'agent_transcript' | 'speech_start' | 'utterance_end' | 'telephony_error' | 'pong';
  call_id?: string;
  status?: string;
  transcript?: string;
  is_final?: boolean;
  speech_final?: boolean;
  detected_language?: string;
  language_confidence?: number;
  confidence?: number;
  audio_data?: string; // base64 encoded audio
  message?: string;
  timestamp?: string;
  metadata?: Record<string, any>;
}

/**
 * Manages WebSocket connections specifically for telephony without interfering with web chat
 */
export class TelephonyWebSocketManager extends EventEmitter {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isIntentionallyClosed = false;
  private connectionParams: {
    callId: string;
    token: string;
    language: string;
    model: string;
  } | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private connectionTimeout: NodeJS.Timeout | null = null;

  constructor() {
    super();
    this.setMaxListeners(20); // Increase max listeners for telephony events
  }

  /**
   * Connect to telephony WebSocket (separate from web chat WebSocket)
   */
  async connect(callId: string, token: string, language: string = 'auto', model: string = 'nova-2'): Promise<boolean> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('📞 TelephonyWS: Already connected');
      return true;
    }

    this.connectionParams = { callId, token, language, model };
    this.isIntentionallyClosed = false;

    try {
      await this.createConnection();
      return true;
    } catch (error) {
      console.error('📞 TelephonyWS: Connection failed:', error);
      this.emit('error', error);
      return false;
    }
  }

  private async createConnection(): Promise<void> {
    if (!this.connectionParams) {
      throw new Error('No connection parameters set');
    }

    const { callId, token, language, model } = this.connectionParams;

    // Use separate telephony WebSocket URL to avoid conflicts with web chat
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const backendHost = process.env.NEXT_PUBLIC_API_URL ? 
      new URL(process.env.NEXT_PUBLIC_API_URL).host : 
      'localhost:8000';
    
    const params = new URLSearchParams({
      token,
      language,
      model,
      client_type: 'telephony' // Distinguish from web chat clients
    });

    const wsUrl = `${protocol}//${backendHost}/api/ws/telephony/stream/${callId}?${params.toString()}`;
    
    console.log('📞 TelephonyWS: Connecting to:', wsUrl);

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);

        // Connection timeout
        this.connectionTimeout = setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            console.error('📞 TelephonyWS: Connection timeout');
            this.ws?.close();
            reject(new Error('Connection timeout'));
          }
        }, 10000);

        this.ws.onopen = () => {
          console.log('📞 TelephonyWS: Connected successfully');
          
          if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
          }

          this.reconnectAttempts = 0;
          this.setupHeartbeat();

          // Send initialization message
          this.sendMessage({
            type: 'init_telephony_stream',
            call_id: callId,
            language,
            model,
            client_type: 'telephony'
          });

          this.emit('connected', callId);
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data: TelephonyWebSocketEvent = JSON.parse(event.data);
            console.log('📞 TelephonyWS: Received:', data.type, data.call_id);
            
            // Emit specific event types for telephony handling
            this.emit('message', data);
            this.emit(data.type, data);
          } catch (error) {
            console.error('📞 TelephonyWS: Message parse error:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('📞 TelephonyWS: Error:', error);
          
          if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
          }

          this.emit('error', error);
          reject(error);
        };

        this.ws.onclose = (event) => {
          console.log('📞 TelephonyWS: Closed:', event.code, event.reason);
          
          if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
          }

          this.cleanup();
          this.emit('disconnected', event.code, event.reason);

          // Auto-reconnect if not intentionally closed
          if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

      } catch (error) {
        if (this.connectionTimeout) {
          clearTimeout(this.connectionTimeout);
          this.connectionTimeout = null;
        }
        reject(error);
      }
    });
  }

  private setupHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendMessage({ type: 'ping' });
      }
    }, 30000); // 30 second heartbeat
  }

  private cleanup(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
    
    console.log(`📞 TelephonyWS: Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    setTimeout(async () => {
      if (!this.isIntentionallyClosed && this.connectionParams) {
        try {
          await this.createConnection();
        } catch (error) {
          console.error('📞 TelephonyWS: Reconnect failed:', error);
        }
      }
    }, delay);
  }

  /**
   * Send message to telephony WebSocket
   */
  sendMessage(message: any): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('📞 TelephonyWS: Send error:', error);
        return false;
      }
    }
    
    console.warn('📞 TelephonyWS: Cannot send message, connection not open');
    return false;
  }

  /**
   * Send agent message for TTS processing
   */
  sendAgentMessage(callId: string, message: string, language?: string): boolean {
    return this.sendMessage({
      type: 'agent_message',
      call_id: callId,
      message,
      language: language || 'auto',
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Update call status
   */
  updateCallStatus(callId: string, status: string): boolean {
    return this.sendMessage({
      type: 'update_call_status',
      call_id: callId,
      status,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Start transcription for a call
   */
  startTranscription(callId: string, language?: string): boolean {
    return this.sendMessage({
      type: 'start_transcription',
      call_id: callId,
      language: language || 'auto',
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Stop transcription for a call
   */
  stopTranscription(callId: string): boolean {
    return this.sendMessage({
      type: 'stop_transcription',
      call_id: callId,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Disconnect from telephony WebSocket
   */
  disconnect(): void {
    console.log('📞 TelephonyWS: Disconnecting...');
    this.isIntentionallyClosed = true;
    
    if (this.connectionParams) {
      this.sendMessage({
        type: 'stop_telephony_stream',
        call_id: this.connectionParams.callId
      });
    }

    this.cleanup();

    if (this.ws) {
      this.ws.close(1000, 'Intentional disconnect');
      this.ws = null;
    }

    this.connectionParams = null;
    this.emit('disconnected', 1000, 'Intentional disconnect');
  }

  /**
   * Get connection state
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get current call ID
   */
  get currentCallId(): string | null {
    return this.connectionParams?.callId || null;
  }

  /**
   * Destroy the manager and cleanup all resources
   */
  destroy(): void {
    this.disconnect();
    this.removeAllListeners();
  }
}

// Singleton instance for telephony WebSocket management
export const telephonyWebSocketManager = new TelephonyWebSocketManager();