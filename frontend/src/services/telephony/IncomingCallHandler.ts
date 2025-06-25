// src/services/telephony/IncomingCallHandler.ts
import { telephonyCallManager, CallState } from './TelephonyCallManager';
import { telephonyService } from '../telephony';
import { telephonyErrorHandler, TelephonyErrorType, TelephonyErrorSeverity } from './TelephonyErrorHandler';

/**
 * Handles incoming phone calls and automatically triggers appropriate responses
 * This bridges the gap between call reception and TTS response generation
 */
export class IncomingCallHandler {
  private isInitialized = false;
  private token = '';
  private defaultWelcomeMessage = 'Hello! Thank you for calling. How can I help you today?';

  constructor() {
    this.setupEventHandlers();
  }

  /**
   * Initialize the incoming call handler
   */
  async initialize(token: string): Promise<void> {
    if (this.isInitialized) return;

    this.token = token;
    console.log('📞 IncomingCallHandler: Initializing...');

    try {
      // Initialize call manager if not already done
      await telephonyCallManager.initialize(token);

      // Load default welcome message from telephony config
      try {
        const config = await telephonyService.getTelephonyConfig(token);
        if (config.welcome_message) {
          this.defaultWelcomeMessage = config.welcome_message;
        }
      } catch (error) {
        console.warn('📞 IncomingCallHandler: Could not load welcome message from config:', error);
      }

      this.isInitialized = true;
      console.log('📞 IncomingCallHandler: Initialized with welcome message:', this.defaultWelcomeMessage);

    } catch (error) {
      telephonyErrorHandler.logError(
        TelephonyErrorType.CONFIGURATION,
        'Failed to initialize incoming call handler',
        'IncomingCallHandler',
        {
          severity: TelephonyErrorSeverity.HIGH,
          error: error as Error
        }
      );
      throw error;
    }
  }

  /**
   * Set up event handlers for call manager events
   */
  private setupEventHandlers(): void {
    // Handle incoming calls
    telephonyCallManager.on('call_incoming', async (callState: CallState) => {
      console.log('📞 IncomingCallHandler: Incoming call detected:', callState.callId);
      await this.handleIncomingCall(callState);
    });

    // Handle call answered events
    telephonyCallManager.on('call_answered', async (callState: CallState) => {
      console.log('📞 IncomingCallHandler: Call answered:', callState.callId);
      await this.handleCallAnswered(callState);
    });

    // Handle call status updates
    telephonyCallManager.on('call_status_update', async (callId: string, status: string) => {
      console.log('📞 IncomingCallHandler: Call status update:', callId, status);
      
      if (status === 'answered' || status === 'in_progress') {
        const callState = telephonyCallManager.getCallState(callId);
        if (callState) {
          await this.ensureWelcomeMessageSent(callState);
        }
      }
    });

    console.log('📞 IncomingCallHandler: Event handlers set up');
  }

  /**
   * Handle an incoming call
   */
  private async handleIncomingCall(callState: CallState): Promise<void> {
    try {
      console.log('📞 IncomingCallHandler: Processing incoming call:', callState.callId);

      // Start call processing immediately
      await telephonyCallManager.startCallProcessing(callState.callId, 'auto');
      
      console.log('📞 IncomingCallHandler: Call processing started for:', callState.callId);

    } catch (error) {
      console.error('📞 IncomingCallHandler: Error handling incoming call:', error);
      
      telephonyErrorHandler.logError(
        TelephonyErrorType.CALL_MANAGEMENT,
        'Failed to process incoming call',
        'IncomingCallHandler',
        {
          severity: TelephonyErrorSeverity.HIGH,
          callId: callState.callId,
          error: error as Error,
          details: {
            customerNumber: callState.customerNumber,
            organizationNumber: callState.organizationNumber
          }
        }
      );
    }
  }

  /**
   * Handle when a call is answered
   */
  private async handleCallAnswered(callState: CallState): Promise<void> {
    try {
      console.log('📞 IncomingCallHandler: Call answered, sending welcome message:', callState.callId);
      
      // Send welcome message
      await this.sendWelcomeMessage(callState);

    } catch (error) {
      console.error('📞 IncomingCallHandler: Error sending welcome message:', error);
      
      telephonyErrorHandler.logError(
        TelephonyErrorType.TTS,
        'Failed to send welcome message',
        'IncomingCallHandler',
        {
          severity: TelephonyErrorSeverity.MEDIUM,
          callId: callState.callId,
          error: error as Error
        }
      );
    }
  }

  /**
   * Send welcome message to caller
   */
  private async sendWelcomeMessage(callState: CallState): Promise<void> {
    // Check if welcome message was already sent
    const hasWelcomeMessage = callState.messages.some(msg => 
      msg.sender.type === 'agent' && 
      msg.message_type === 'transcript' &&
      msg.metadata?.is_automated === true
    );

    if (hasWelcomeMessage) {
      console.log('📞 IncomingCallHandler: Welcome message already sent for call:', callState.callId);
      return;
    }

    console.log('📞 IncomingCallHandler: Sending welcome message to call:', callState.callId);
    
    try {
      await telephonyCallManager.sendAgentMessage(callState.callId, this.defaultWelcomeMessage);
      console.log('📞 IncomingCallHandler: Welcome message sent successfully');
      
    } catch (error) {
      console.error('📞 IncomingCallHandler: Failed to send welcome message:', error);
      throw error;
    }
  }

  /**
   * Ensure welcome message is sent (failsafe)
   */
  private async ensureWelcomeMessageSent(callState: CallState): Promise<void> {
    // Small delay to allow for call setup
    setTimeout(async () => {
      try {
        await this.sendWelcomeMessage(callState);
      } catch (error) {
        console.error('📞 IncomingCallHandler: Failsafe welcome message failed:', error);
      }
    }, 2000); // 2 second delay
  }

  /**
   * Update welcome message
   */
  setWelcomeMessage(message: string): void {
    this.defaultWelcomeMessage = message;
    console.log('📞 IncomingCallHandler: Welcome message updated:', message);
  }

  /**
   * Manually trigger incoming call (for testing)
   */
  async simulateIncomingCall(customerNumber: string, organizationNumber: string): Promise<string> {
    if (!this.isInitialized) {
      throw new Error('IncomingCallHandler not initialized');
    }

    console.log('📞 IncomingCallHandler: Creating test call via backend API');

    try {
      // Create real call record via backend API
      const testCallResponse = await telephonyService.createTestCall(customerNumber, this.token);
      
      console.log('📞 IncomingCallHandler: Test call created:', testCallResponse);

      // Now handle the call on the frontend with the real call ID
      await telephonyCallManager.handleIncomingCall({
        callId: testCallResponse.call_id,
        callSid: testCallResponse.call_sid,
        from: testCallResponse.customer_number,
        to: testCallResponse.organization_number,
        timestamp: new Date().toISOString()
      });

      return testCallResponse.call_id;
    } catch (error) {
      console.error('📞 IncomingCallHandler: Error simulating call:', error);
      throw error;
    }
  }

  /**
   * Get handler status
   */
  getStatus(): {
    initialized: boolean;
    welcomeMessage: string;
    activeCalls: number;
  } {
    return {
      initialized: this.isInitialized,
      welcomeMessage: this.defaultWelcomeMessage,
      activeCalls: telephonyCallManager.getActiveCalls().length
    };
  }

  /**
   * Destroy the handler
   */
  destroy(): void {
    console.log('📞 IncomingCallHandler: Destroying...');
    telephonyCallManager.removeAllListeners();
    this.isInitialized = false;
  }
}

// Singleton instance
export const incomingCallHandler = new IncomingCallHandler();