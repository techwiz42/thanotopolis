// src/services/telephony/TelephonyTTSSTTProcessor.ts
import { telephonyWebSocketManager, TelephonyWebSocketEvent } from './TelephonyWebSocketManager';
import { twilioAudioService } from './TwilioAudioService';
import { voiceConfigService } from '../voice/voiceConfig';

export interface TelephonyTranscriptEvent {
  callId: string;
  transcript: string;
  isFinal: boolean;
  sender: 'customer' | 'agent';
  language?: string;
  confidence?: number;
  timestamp: string;
}

export interface TelephonyTTSEvent {
  callId: string;
  text: string;
  language?: string;
  voiceId?: string;
  timestamp: string;
}

export interface TelephonyLanguageDetection {
  callId: string;
  language: string;
  confidence: number;
  method: 'speech' | 'text' | 'manual';
  timestamp: string;
}

/**
 * Telephony-specific TTS/STT processor that handles phone call audio
 * Completely separate from web chat TTS/STT to avoid interference
 */
export class TelephonyTTSSTTProcessor {
  private activeProcessors: Map<string, {
    callId: string;
    language: string;
    isProcessing: boolean;
    lastActivity: number;
  }> = new Map();

  private languageDetection: Map<string, {
    detectedLanguage: string;
    confidence: number;
    lastUpdate: number;
  }> = new Map();

  private eventHandlers: {
    onTranscript?: (event: TelephonyTranscriptEvent) => void;
    onTTSComplete?: (callId: string, success: boolean) => void;
    onLanguageDetected?: (event: TelephonyLanguageDetection) => void;
    onError?: (callId: string, error: string) => void;
  } = {};

  constructor() {
    this.setupEventHandlers();
  }

  /**
   * Set up event handlers for telephony WebSocket
   */
  private setupEventHandlers(): void {
    // Handle customer speech transcripts
    telephonyWebSocketManager.on('customer_transcript', (data: TelephonyWebSocketEvent) => {
      this.handleCustomerTranscript(data);
    });

    // Handle agent TTS audio
    telephonyWebSocketManager.on('agent_tts_audio', (data: TelephonyWebSocketEvent) => {
      this.handleAgentTTSAudio(data);
    });

    // Handle agent transcripts (for logging)
    telephonyWebSocketManager.on('agent_transcript', (data: TelephonyWebSocketEvent) => {
      this.handleAgentTranscript(data);
    });

    // Handle telephony errors
    telephonyWebSocketManager.on('telephony_error', (data: TelephonyWebSocketEvent) => {
      this.handleTelephonyError(data);
    });

    console.log('📞 TelephonyTTSSTT: Event handlers initialized');
  }

  /**
   * Register event handlers
   */
  setEventHandlers(handlers: {
    onTranscript?: (event: TelephonyTranscriptEvent) => void;
    onTTSComplete?: (callId: string, success: boolean) => void;
    onLanguageDetected?: (event: TelephonyLanguageDetection) => void;
    onError?: (callId: string, error: string) => void;
  }): void {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };
  }

  /**
   * Start processing for a call
   */
  async startProcessing(callId: string, language: string = 'auto'): Promise<void> {
    if (this.activeProcessors.has(callId)) {
      console.log('📞 TelephonyTTSSTT: Processing already active for call:', callId);
      return;
    }

    console.log('📞 TelephonyTTSSTT: Starting processing for call:', callId);

    this.activeProcessors.set(callId, {
      callId,
      language,
      isProcessing: true,
      lastActivity: Date.now()
    });

    // Initialize language detection
    this.languageDetection.set(callId, {
      detectedLanguage: language === 'auto' ? 'en' : language,
      confidence: 0,
      lastUpdate: Date.now()
    });

    // Start transcription on telephony WebSocket
    telephonyWebSocketManager.startTranscription(callId, language);

    // Initialize Twilio audio stream
    try {
      const callSid = await this.getCallSid(callId);
      await twilioAudioService.startCallAudioStream(callId, callSid);
    } catch (error) {
      console.error('📞 TelephonyTTSSTT: Failed to start Twilio audio:', error);
      this.eventHandlers.onError?.(callId, `Failed to start audio: ${error}`);
    }
  }

  /**
   * Stop processing for a call
   */
  async stopProcessing(callId: string): Promise<void> {
    console.log('📞 TelephonyTTSSTT: Stopping processing for call:', callId);

    const processor = this.activeProcessors.get(callId);
    if (processor) {
      processor.isProcessing = false;
    }

    // Stop transcription
    telephonyWebSocketManager.stopTranscription(callId);

    // Stop Twilio audio stream
    try {
      await twilioAudioService.stopCallAudioStream(callId);
    } catch (error) {
      console.error('📞 TelephonyTTSSTT: Error stopping Twilio audio:', error);
    }

    // Clean up
    this.activeProcessors.delete(callId);
    this.languageDetection.delete(callId);
  }

  /**
   * Process agent message for TTS
   */
  async processAgentMessage(callId: string, message: string, language?: string): Promise<void> {
    const processor = this.activeProcessors.get(callId);
    if (!processor?.isProcessing) {
      throw new Error(`No active processor for call ${callId}`);
    }

    console.log('📞 TelephonyTTSSTT: Processing agent message for TTS:', message.substring(0, 50) + '...');

    try {
      // Get current language for the call
      const currentLanguage = language || 
        this.languageDetection.get(callId)?.detectedLanguage || 
        processor.language || 
        'en';

      // Send message to backend via WebSocket for TTS processing
      const sent = telephonyWebSocketManager.sendAgentMessage(callId, message, currentLanguage);
      
      if (!sent) {
        throw new Error('Failed to send agent message via WebSocket');
      }

      console.log('📞 TelephonyTTSSTT: Agent message sent to backend for TTS processing');

      // Notify completion
      this.eventHandlers.onTTSComplete?.(callId, true);

      // Create agent transcript event
      const agentTranscript: TelephonyTranscriptEvent = {
        callId,
        transcript: message,
        isFinal: true,
        sender: 'agent',
        language: currentLanguage,
        confidence: 1.0,
        timestamp: new Date().toISOString()
      };

      this.eventHandlers.onTranscript?.(agentTranscript);

    } catch (error) {
      console.error('📞 TelephonyTTSSTT: Agent message processing failed:', error);
      this.eventHandlers.onTTSComplete?.(callId, false);
      this.eventHandlers.onError?.(callId, `TTS failed: ${error}`);
      throw error;
    }
  }

  /**
   * Generate TTS audio for telephony (separate from web chat TTS)
   */
  private async generateTTSAudio(text: string, language: string): Promise<Blob> {
    console.log('📞 TelephonyTTSSTT: Generating TTS audio for telephony');

    try {
      // Get voice configuration for telephony
      const voiceId = await voiceConfigService.getVoiceId(''); // Use default or call-specific token

      const formData = new FormData();
      formData.append('text', text);
      formData.append('voice_id', voiceId);
      formData.append('output_format', 'mp3_22050_32'); // Lower quality for telephony
      formData.append('stability', '0.5'); // More stable for phone calls
      formData.append('similarity_boost', '0.8');
      formData.append('style', '0.0');
      formData.append('use_speaker_boost', 'true');
      formData.append('model_id', 'eleven_monolingual_v1'); // Optimized for telephony

      // Use separate TTS endpoint for telephony to avoid conflicts
      const response = await fetch('/api/voice/telephony/tts', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        // Fallback to regular TTS endpoint if telephony-specific doesn't exist
        const fallbackResponse = await fetch('/api/voice/tts/synthesize', {
          method: 'POST',
          body: formData
        });

        if (!fallbackResponse.ok) {
          throw new Error(`TTS API error: ${fallbackResponse.status}`);
        }

        return await fallbackResponse.blob();
      }

      return await response.blob();

    } catch (error) {
      console.error('📞 TelephonyTTSSTT: TTS generation failed:', error);
      throw error;
    }
  }

  /**
   * Handle customer transcript from telephony WebSocket
   */
  private handleCustomerTranscript(data: TelephonyWebSocketEvent): void {
    if (!data.call_id || !data.transcript) return;

    const processor = this.activeProcessors.get(data.call_id);
    if (!processor?.isProcessing) return;

    console.log('📞 TelephonyTTSSTT: Customer transcript:', data.transcript.substring(0, 50) + '...');

    // Update activity timestamp
    processor.lastActivity = Date.now();

    // Detect language if provided
    if (data.detected_language && data.language_confidence) {
      this.updateLanguageDetection(data.call_id, data.detected_language, data.language_confidence, 'speech');
    }

    // Create transcript event
    const transcriptEvent: TelephonyTranscriptEvent = {
      callId: data.call_id,
      transcript: data.transcript,
      isFinal: data.is_final || data.speech_final || false,
      sender: 'customer',
      language: data.detected_language,
      confidence: data.confidence,
      timestamp: data.timestamp || new Date().toISOString()
    };

    this.eventHandlers.onTranscript?.(transcriptEvent);
  }

  /**
   * Handle agent TTS audio from telephony WebSocket
   */
  private handleAgentTTSAudio(data: TelephonyWebSocketEvent): void {
    if (!data.call_id || !data.audio_data) return;
    
    const callId = data.call_id; // Ensure type safety

    console.log('📞 TelephonyTTSSTT: Received agent TTS audio for call:', data.call_id);

    try {
      // Convert base64 audio to blob
      const audioBytes = atob(data.audio_data);
      const audioArray = new Uint8Array(audioBytes.length);
      for (let i = 0; i < audioBytes.length; i++) {
        audioArray[i] = audioBytes.charCodeAt(i);
      }

      const audioBlob = new Blob([audioArray], { type: 'audio/mpeg' });

      // Send to Twilio for phone playback
      twilioAudioService.sendTTSToCall(callId, audioBlob)
        .then(() => {
          this.eventHandlers.onTTSComplete?.(callId, true);
        })
        .catch((error) => {
          console.error('📞 TelephonyTTSSTT: Failed to send TTS to call:', error);
          this.eventHandlers.onTTSComplete?.(callId, false);
        });

    } catch (error) {
      console.error('📞 TelephonyTTSSTT: Error processing agent TTS audio:', error);
      this.eventHandlers.onTTSComplete?.(callId, false);
    }
  }

  /**
   * Handle agent transcript (for logging)
   */
  private handleAgentTranscript(data: TelephonyWebSocketEvent): void {
    if (!data.call_id || !data.transcript) return;
    
    const callId = data.call_id; // Ensure type safety

    console.log('📞 TelephonyTTSSTT: Agent transcript logged:', data.transcript.substring(0, 50) + '...');

    const transcriptEvent: TelephonyTranscriptEvent = {
      callId,
      transcript: data.transcript,
      isFinal: data.is_final || true,
      sender: 'agent',
      language: data.detected_language,
      confidence: data.confidence || 1.0,
      timestamp: data.timestamp || new Date().toISOString()
    };

    this.eventHandlers.onTranscript?.(transcriptEvent);
  }

  /**
   * Handle telephony errors
   */
  private handleTelephonyError(data: TelephonyWebSocketEvent): void {
    if (!data.call_id) return;
    
    const callId = data.call_id; // Ensure type safety

    console.error('📞 TelephonyTTSSTT: Telephony error for call:', callId, data.message);
    this.eventHandlers.onError?.(callId, data.message || 'Unknown telephony error');
  }

  /**
   * Update language detection for a call
   */
  private updateLanguageDetection(callId: string, language: string, confidence: number, method: 'speech' | 'text' | 'manual'): void {
    const current = this.languageDetection.get(callId);
    
    // Only update if confidence is higher or significantly different
    if (!current || confidence > current.confidence || 
        (language !== current.detectedLanguage && confidence > 0.7)) {
      
      this.languageDetection.set(callId, {
        detectedLanguage: language,
        confidence,
        lastUpdate: Date.now()
      });

      console.log(`📞 TelephonyTTSSTT: Language updated for call ${callId}: ${language} (${confidence})`);

      // Notify language detection
      const detectionEvent: TelephonyLanguageDetection = {
        callId,
        language,
        confidence,
        method,
        timestamp: new Date().toISOString()
      };

      this.eventHandlers.onLanguageDetected?.(detectionEvent);

      // Update processor language
      const processor = this.activeProcessors.get(callId);
      if (processor) {
        processor.language = language;
      }
    }
  }

  /**
   * Get call SID for a call ID (placeholder - implement based on your system)
   */
  private async getCallSid(callId: string): Promise<string> {
    // This should get the Twilio call SID from your backend
    // For now, return a placeholder
    return `CA${callId.replace(/-/g, '').substring(0, 32)}`;
  }

  /**
   * Get processing status for a call
   */
  getProcessingStatus(callId: string): {
    isActive: boolean;
    language: string;
    lastActivity: number;
    detectedLanguage?: string;
    languageConfidence?: number;
  } | null {
    const processor = this.activeProcessors.get(callId);
    const language = this.languageDetection.get(callId);

    if (!processor) return null;

    return {
      isActive: processor.isProcessing,
      language: processor.language,
      lastActivity: processor.lastActivity,
      detectedLanguage: language?.detectedLanguage,
      languageConfidence: language?.confidence
    };
  }

  /**
   * Get all active call processors
   */
  getActiveCalls(): string[] {
    return Array.from(this.activeProcessors.keys());
  }

  /**
   * Clean up inactive processors
   */
  cleanupInactive(timeoutMs: number = 300000): void { // 5 minutes timeout
    const now = Date.now();
    const toRemove: string[] = [];

    Array.from(this.activeProcessors.entries()).forEach(([callId, processor]) => {
      if (now - processor.lastActivity > timeoutMs) {
        toRemove.push(callId);
      }
    });

    for (const callId of toRemove) {
      console.log('📞 TelephonyTTSSTT: Cleaning up inactive processor for call:', callId);
      this.stopProcessing(callId);
    }
  }

  /**
   * Destroy the processor and clean up all resources
   */
  destroy(): void {
    console.log('📞 TelephonyTTSSTT: Destroying processor');

    // Stop all active processors
    const callIds = Array.from(this.activeProcessors.keys());
    for (const callId of callIds) {
      this.stopProcessing(callId);
    }

    // Remove event handlers
    telephonyWebSocketManager.removeAllListeners();
    this.eventHandlers = {};
  }
}

// Singleton instance for telephony TTS/STT processing
export const telephonyTTSSTTProcessor = new TelephonyTTSSTTProcessor();