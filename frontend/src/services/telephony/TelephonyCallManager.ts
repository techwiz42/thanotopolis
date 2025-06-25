// src/services/telephony/TelephonyCallManager.ts
import { EventEmitter } from 'events';
import { telephonyWebSocketManager } from './TelephonyWebSocketManager';
import { telephonyTTSSTTProcessor, TelephonyTranscriptEvent, TelephonyLanguageDetection } from './TelephonyTTSSTTProcessor';
import { twilioAudioService } from './TwilioAudioService';
import { telephonyService, PhoneCall, CallMessage } from '../telephony';

export interface CallState {
  callId: string;
  callSid: string;
  status: 'incoming' | 'ringing' | 'answered' | 'in_progress' | 'completed' | 'failed' | 'no_answer' | 'busy';
  customerNumber: string;
  organizationNumber: string;
  direction: 'inbound' | 'outbound';
  startTime: Date;
  answerTime?: Date;
  endTime?: Date;
  language?: string;
  languageConfidence?: number;
  isStreamActive: boolean;
  lastActivity: Date;
  messages: CallMessage[];
  agentConnected: boolean;
}

export interface CallRoutingRule {
  id: string;
  name: string;
  conditions: {
    timeRange?: { start: string; end: string };
    dayOfWeek?: number[];
    callerNumberPattern?: string;
    organizationNumber?: string;
  };
  action: {
    type: 'forward' | 'voicemail' | 'agent' | 'automated';
    target?: string;
    message?: string;
  };
  priority: number;
  isEnabled: boolean;
}

/**
 * Manages telephony calls, routing, and state coordination
 * Orchestrates all telephony services without interfering with web chat
 */
export class TelephonyCallManager extends EventEmitter {
  private activeCalls: Map<string, CallState> = new Map();
  private routingRules: CallRoutingRule[] = [];
  private isInitialized = false;
  private cleanupInterval: NodeJS.Timeout | null = null;
  private token: string = '';

  constructor() {
    super();
    this.setMaxListeners(50); // High limit for telephony events
  }

  /**
   * Initialize the call manager
   */
  async initialize(token: string): Promise<void> {
    if (this.isInitialized) return;

    this.token = token;
    console.log('📞 CallManager: Initializing...');

    try {
      // Set up event handlers for telephony processor
      telephonyTTSSTTProcessor.setEventHandlers({
        onTranscript: (event: TelephonyTranscriptEvent) => {
          this.handleTranscript(event);
        },
        onTTSComplete: (callId: string, success: boolean) => {
          this.handleTTSComplete(callId, success);
        },
        onLanguageDetected: (event: TelephonyLanguageDetection) => {
          this.handleLanguageDetected(event);
        },
        onError: (callId: string, error: string) => {
          this.handleProcessingError(callId, error);
        }
      });

      // Set up WebSocket event handlers
      telephonyWebSocketManager.on('call_status_update', (data) => {
        this.handleCallStatusUpdate(data);
      });

      telephonyWebSocketManager.on('telephony_connected', (callId) => {
        this.handleTelephonyConnected(callId);
      });

      telephonyWebSocketManager.on('disconnected', () => {
        this.handleTelephonyDisconnected();
      });

      // Load routing rules
      await this.loadRoutingRules();

      // Start cleanup interval
      this.cleanupInterval = setInterval(() => {
        this.cleanupCompletedCalls();
        telephonyTTSSTTProcessor.cleanupInactive();
      }, 60000); // Clean up every minute

      this.isInitialized = true;
      console.log('📞 CallManager: Initialized successfully');

    } catch (error) {
      console.error('📞 CallManager: Initialization failed:', error);
      throw error;
    }
  }

  /**
   * Handle incoming call
   */
  async handleIncomingCall(callData: {
    callId: string;
    callSid: string;
    from: string;
    to: string;
    timestamp: string;
  }): Promise<void> {
    console.log('📞 CallManager: Incoming call:', callData);

    try {
      // Create call state
      const callState: CallState = {
        callId: callData.callId,
        callSid: callData.callSid,
        status: 'incoming',
        customerNumber: callData.from,
        organizationNumber: callData.to,
        direction: 'inbound',
        startTime: new Date(callData.timestamp),
        isStreamActive: false,
        lastActivity: new Date(),
        messages: [],
        agentConnected: false
      };

      this.activeCalls.set(callData.callId, callState);

      // Apply routing rules
      const routingAction = await this.applyRoutingRules(callState);
      await this.executeRoutingAction(callState, routingAction);

      // Emit call event
      this.emit('call_incoming', callState);

      // Log call to backend
      await this.logCallToBackend(callState);

    } catch (error) {
      console.error('📞 CallManager: Error handling incoming call:', error);
      this.emit('call_error', callData.callId, error);
    }
  }

  /**
   * Start call processing (answer the call)
   */
  async startCallProcessing(callId: string, language: string = 'auto'): Promise<void> {
    const callState = this.activeCalls.get(callId);
    if (!callState) {
      throw new Error(`Call not found: ${callId}`);
    }

    console.log('📞 CallManager: Starting call processing for:', callId);

    try {
      // Update call state
      callState.status = 'answered';
      callState.answerTime = new Date();
      callState.lastActivity = new Date();
      callState.language = language;

      // Connect to telephony WebSocket
      await telephonyWebSocketManager.connect(callId, this.token, language);

      // Start TTS/STT processing
      await telephonyTTSSTTProcessor.startProcessing(callId, language);

      // Update state
      callState.isStreamActive = true;
      callState.status = 'in_progress';

      this.emit('call_answered', callState);

      // Update backend
      await this.updateCallInBackend(callState);

    } catch (error) {
      console.error('📞 CallManager: Error starting call processing:', error);
      callState.status = 'failed';
      this.emit('call_error', callId, error);
      throw error;
    }
  }

  /**
   * Send agent message to call
   */
  async sendAgentMessage(callId: string, message: string): Promise<void> {
    const callState = this.activeCalls.get(callId);
    if (!callState) {
      throw new Error(`Call not found: ${callId}`);
    }

    if (!callState.isStreamActive) {
      throw new Error(`Call stream not active: ${callId}`);
    }

    console.log('📞 CallManager: Sending agent message to call:', callId);

    try {
      // Process message through TTS/STT processor
      await telephonyTTSSTTProcessor.processAgentMessage(
        callId, 
        message, 
        callState.language
      );

      // Update activity
      callState.lastActivity = new Date();
      callState.agentConnected = true;

      // Create message record
      const messageRecord: CallMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        call_id: callId,
        content: message,
        sender: {
          identifier: 'agent',
          type: 'agent',
          name: 'Agent'
        },
        timestamp: new Date().toISOString(),
        message_type: 'transcript',
        metadata: {
          is_automated: true,
          language: callState.language
        },
        created_at: new Date().toISOString()
      };

      callState.messages.push(messageRecord);

      // Log to backend
      try {
        await telephonyService.addCallMessage(callId, {
          content: message,
          sender: messageRecord.sender,
          timestamp: messageRecord.timestamp,
          message_type: 'transcript',
          metadata: messageRecord.metadata
        }, this.token);
      } catch (backendError) {
        console.warn('📞 CallManager: Failed to log message to backend:', backendError);
      }

      this.emit('message_sent', callId, messageRecord);

    } catch (error) {
      console.error('📞 CallManager: Error sending agent message:', error);
      this.emit('message_error', callId, error);
      throw error;
    }
  }

  /**
   * End call processing
   */
  async endCall(callId: string, reason: string = 'completed'): Promise<void> {
    const callState = this.activeCalls.get(callId);
    if (!callState) {
      console.warn('📞 CallManager: Call not found for ending:', callId);
      return;
    }

    console.log('📞 CallManager: Ending call:', callId, reason);

    try {
      // Update call state
      callState.status = reason === 'completed' ? 'completed' : 'failed';
      callState.endTime = new Date();
      callState.isStreamActive = false;

      // Stop processing
      await telephonyTTSSTTProcessor.stopProcessing(callId);

      // Disconnect WebSocket
      if (telephonyWebSocketManager.currentCallId === callId) {
        telephonyWebSocketManager.disconnect();
      }

      this.emit('call_ended', callState);

      // Update backend
      await this.updateCallInBackend(callState);

      // Remove from active calls after a delay (for cleanup)
      setTimeout(() => {
        this.activeCalls.delete(callId);
      }, 60000); // Keep for 1 minute for final updates

    } catch (error) {
      console.error('📞 CallManager: Error ending call:', error);
      this.emit('call_error', callId, error);
    }
  }

  /**
   * Apply routing rules to determine action for incoming call
   */
  private async applyRoutingRules(callState: CallState): Promise<CallRoutingRule['action']> {
    const now = new Date();
    const timeString = now.toTimeString().substring(0, 5); // HH:MM format
    const dayOfWeek = now.getDay();

    // Sort rules by priority
    const sortedRules = this.routingRules
      .filter(rule => rule.isEnabled)
      .sort((a, b) => a.priority - b.priority);

    for (const rule of sortedRules) {
      let matches = true;

      // Check time range
      if (rule.conditions.timeRange) {
        const { start, end } = rule.conditions.timeRange;
        if (timeString < start || timeString > end) {
          matches = false;
        }
      }

      // Check day of week
      if (rule.conditions.dayOfWeek && !rule.conditions.dayOfWeek.includes(dayOfWeek)) {
        matches = false;
      }

      // Check caller number pattern
      if (rule.conditions.callerNumberPattern) {
        const pattern = new RegExp(rule.conditions.callerNumberPattern);
        if (!pattern.test(callState.customerNumber)) {
          matches = false;
        }
      }

      // Check organization number
      if (rule.conditions.organizationNumber && 
          rule.conditions.organizationNumber !== callState.organizationNumber) {
        matches = false;
      }

      if (matches) {
        console.log('📞 CallManager: Applied routing rule:', rule.name);
        return rule.action;
      }
    }

    // Default action: route to agent
    return {
      type: 'agent',
      message: 'Hello! How can I help you today?'
    };
  }

  /**
   * Execute routing action
   */
  private async executeRoutingAction(callState: CallState, action: CallRoutingRule['action']): Promise<void> {
    console.log('📞 CallManager: Executing routing action:', action.type);

    switch (action.type) {
      case 'agent':
        // Start automated agent processing
        await this.startCallProcessing(callState.callId, 'auto');
        
        // Send welcome message if provided
        if (action.message) {
          await this.sendAgentMessage(callState.callId, action.message);
        }
        break;

      case 'automated':
        // Start automated response system
        await this.startCallProcessing(callState.callId, 'auto');
        
        const automatedMessage = action.message || 
          'Thank you for calling. Your call is important to us. Please hold while we connect you.';
        await this.sendAgentMessage(callState.callId, automatedMessage);
        break;

      case 'voicemail':
        callState.status = 'completed';
        const voicemailMessage = action.message || 
          'Thank you for calling. Please leave a message after the tone.';
        
        // Note: In a real implementation, this would trigger voicemail recording
        console.log('📞 CallManager: Voicemail action (implementation needed)');
        break;

      case 'forward':
        if (action.target) {
          console.log('📞 CallManager: Forwarding to:', action.target);
          // Note: Implementation would forward call to target number
        }
        break;

      default:
        console.warn('📞 CallManager: Unknown routing action:', action.type);
    }
  }

  /**
   * Handle transcript from TTS/STT processor
   */
  private handleTranscript(event: TelephonyTranscriptEvent): void {
    const callState = this.activeCalls.get(event.callId);
    if (!callState) return;

    console.log('📞 CallManager: Received transcript:', event.sender, event.transcript.substring(0, 50) + '...');

    // Update activity
    callState.lastActivity = new Date();

    // Create message record
    const messageRecord: CallMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      call_id: event.callId,
      content: event.transcript,
      sender: {
        identifier: event.sender,
        type: event.sender,
        name: event.sender === 'customer' ? 'Customer' : 'Agent'
      },
      timestamp: event.timestamp,
      message_type: 'transcript',
      metadata: {
        is_automated: event.sender === 'agent',
        language: event.language,
        confidence_score: event.confidence
      },
      created_at: new Date().toISOString()
    };

    callState.messages.push(messageRecord);

    // Log to backend if final transcript
    if (event.isFinal) {
      telephonyService.addCallMessage(event.callId, {
        content: event.transcript,
        sender: messageRecord.sender,
        timestamp: messageRecord.timestamp,
        message_type: 'transcript',
        metadata: messageRecord.metadata
      }, this.token).catch(error => {
        console.warn('📞 CallManager: Failed to log transcript to backend:', error);
      });
    }

    this.emit('transcript_received', event.callId, messageRecord);
  }

  /**
   * Handle TTS completion
   */
  private handleTTSComplete(callId: string, success: boolean): void {
    console.log('📞 CallManager: TTS completed for call:', callId, success ? 'successfully' : 'with error');
    this.emit('tts_complete', callId, success);
  }

  /**
   * Handle language detection
   */
  private handleLanguageDetected(event: TelephonyLanguageDetection): void {
    const callState = this.activeCalls.get(event.callId);
    if (!callState) return;

    console.log('📞 CallManager: Language detected:', event.language, event.confidence);

    // Update call state
    callState.language = event.language;
    callState.languageConfidence = event.confidence;

    this.emit('language_detected', event.callId, event.language, event.confidence);
  }

  /**
   * Handle processing errors
   */
  private handleProcessingError(callId: string, error: string): void {
    console.error('📞 CallManager: Processing error for call:', callId, error);
    this.emit('call_error', callId, error);
  }

  /**
   * Handle call status updates from WebSocket
   */
  private handleCallStatusUpdate(data: any): void {
    const callState = this.activeCalls.get(data.call_id);
    if (!callState) return;

    console.log('📞 CallManager: Call status update:', data.call_id, data.status);

    callState.status = data.status;
    callState.lastActivity = new Date();

    this.emit('call_status_update', data.call_id, data.status);
  }

  /**
   * Handle telephony connection established
   */
  private handleTelephonyConnected(callId: string): void {
    const callState = this.activeCalls.get(callId);
    if (callState) {
      callState.isStreamActive = true;
      this.emit('stream_connected', callId);
    }
  }

  /**
   * Handle telephony disconnection
   */
  private handleTelephonyDisconnected(): void {
    console.log('📞 CallManager: Telephony disconnected');
    
    // Update all active calls
    Array.from(this.activeCalls.values()).forEach(callState => {
      if (callState.isStreamActive) {
        callState.isStreamActive = false;
        this.emit('stream_disconnected', callState.callId);
      }
    });
  }

  /**
   * Get call state
   */
  getCallState(callId: string): CallState | null {
    return this.activeCalls.get(callId) || null;
  }

  /**
   * Get all active calls
   */
  getActiveCalls(): CallState[] {
    return Array.from(this.activeCalls.values());
  }

  /**
   * Load routing rules from backend
   */
  private async loadRoutingRules(): Promise<void> {
    try {
      // Placeholder: Load from backend API
      // const rules = await telephonyService.getRoutingRules(this.token);
      
      // Default rules for now
      this.routingRules = [
        {
          id: 'business-hours',
          name: 'Business Hours Agent',
          conditions: {
            timeRange: { start: '09:00', end: '17:00' },
            dayOfWeek: [1, 2, 3, 4, 5] // Monday to Friday
          },
          action: {
            type: 'agent',
            message: 'Hello! Thank you for calling during business hours. How can I help you today?'
          },
          priority: 1,
          isEnabled: true
        },
        {
          id: 'after-hours',
          name: 'After Hours Automated',
          conditions: {},
          action: {
            type: 'automated',
            message: 'Thank you for calling. Our office is currently closed. Please leave a message or call back during business hours.'
          },
          priority: 999,
          isEnabled: true
        }
      ];

      console.log('📞 CallManager: Loaded', this.routingRules.length, 'routing rules');
    } catch (error) {
      console.error('📞 CallManager: Error loading routing rules:', error);
    }
  }

  /**
   * Log call to backend
   */
  private async logCallToBackend(callState: CallState): Promise<void> {
    try {
      // This would typically create the call record in the backend
      console.log('📞 CallManager: Logging call to backend:', callState.callId);
    } catch (error) {
      console.error('📞 CallManager: Error logging call to backend:', error);
    }
  }

  /**
   * Update call in backend
   */
  private async updateCallInBackend(callState: CallState): Promise<void> {
    try {
      // This would typically update the call record in the backend
      console.log('📞 CallManager: Updating call in backend:', callState.callId);
    } catch (error) {
      console.error('📞 CallManager: Error updating call in backend:', error);
    }
  }

  /**
   * Clean up completed calls
   */
  private cleanupCompletedCalls(): void {
    const cutoffTime = Date.now() - (24 * 60 * 60 * 1000); // 24 hours ago
    const toRemove: string[] = [];

    Array.from(this.activeCalls.entries()).forEach(([callId, callState]) => {
      if ((callState.status === 'completed' || callState.status === 'failed') &&
          callState.lastActivity.getTime() < cutoffTime) {
        toRemove.push(callId);
      }
    });

    for (const callId of toRemove) {
      console.log('📞 CallManager: Cleaning up old call:', callId);
      this.activeCalls.delete(callId);
    }
  }

  /**
   * Destroy the call manager
   */
  destroy(): void {
    console.log('📞 CallManager: Destroying...');

    // End all active calls
    const activeCalls = Array.from(this.activeCalls.keys());
    for (const callId of activeCalls) {
      this.endCall(callId, 'failed');
    }

    // Clean up interval
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }

    // Remove listeners
    this.removeAllListeners();

    this.isInitialized = false;
  }
}

// Singleton instance
export const telephonyCallManager = new TelephonyCallManager();