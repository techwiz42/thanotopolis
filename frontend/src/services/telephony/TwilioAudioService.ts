// src/services/telephony/TwilioAudioService.ts
import { telephonyWebSocketManager } from './TelephonyWebSocketManager';

export interface TwilioCallEvent {
  type: 'call_started' | 'call_answered' | 'call_ended' | 'audio_received' | 'audio_sent';
  callSid: string;
  callId: string;
  from: string;
  to: string;
  status: string;
  audioData?: ArrayBuffer;
  timestamp: string;
}

export interface TwilioAudioConfig {
  /** Sample rate for audio processing */
  sampleRate: number;
  /** Audio encoding format */
  encoding: 'LINEAR16' | 'MULAW' | 'ALAW';
  /** Buffer size for audio chunks */
  bufferSize: number;
  /** Enable echo cancellation */
  echoCancellation: boolean;
  /** Enable noise suppression */
  noiseSuppression: boolean;
}

/**
 * Service for integrating with Twilio for real-time phone audio streaming
 * Handles bidirectional audio between phone calls and the telephony system
 */
export class TwilioAudioService {
  private config: TwilioAudioConfig;
  private activeStreams: Map<string, MediaStream> = new Map();
  private audioContext: AudioContext | null = null;
  private processors: Map<string, ScriptProcessorNode> = new Map();
  private isInitialized = false;

  constructor(config?: Partial<TwilioAudioConfig>) {
    this.config = {
      sampleRate: 8000, // Twilio uses 8kHz for phone calls
      encoding: 'MULAW', // μ-law encoding for telephony
      bufferSize: 512, // Small buffer for low latency
      echoCancellation: true,
      noiseSuppression: false, // Preserve speech characteristics
      ...config
    };
  }

  /**
   * Initialize the audio service
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Initialize Web Audio API for audio processing
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.config.sampleRate
      });

      console.log('📞 TwilioAudio: Initialized with sample rate:', this.audioContext.sampleRate);
      this.isInitialized = true;
    } catch (error) {
      console.error('📞 TwilioAudio: Initialization failed:', error);
      throw error;
    }
  }

  /**
   * Start audio streaming for a phone call
   */
  async startCallAudioStream(callId: string, callSid: string): Promise<void> {
    if (!this.isInitialized) {
      await this.initialize();
    }

    if (this.activeStreams.has(callId)) {
      console.log('📞 TwilioAudio: Stream already active for call:', callId);
      return;
    }

    try {
      console.log('📞 TwilioAudio: Starting audio stream for call:', callId);

      // Create a dedicated audio stream for this call
      // Note: In a real implementation, this would connect to Twilio's Media Streams
      const stream = await this.createTwilioMediaStream(callSid);
      this.activeStreams.set(callId, stream);

      // Set up audio processing
      await this.setupAudioProcessing(callId, stream);

      // Notify telephony system that audio is ready
      telephonyWebSocketManager.sendMessage({
        type: 'audio_stream_ready',
        call_id: callId,
        call_sid: callSid,
        config: this.config
      });

    } catch (error) {
      console.error('📞 TwilioAudio: Failed to start audio stream:', error);
      throw error;
    }
  }

  /**
   * Create a Twilio Media Stream connection
   * Note: This is a placeholder - real implementation would use Twilio's WebRTC SDK
   */
  private async createTwilioMediaStream(callSid: string): Promise<MediaStream> {
    // In a real implementation, this would:
    // 1. Connect to Twilio's Media Streams API
    // 2. Establish WebRTC connection
    // 3. Return the actual media stream from the phone call

    console.log('📞 TwilioAudio: Creating media stream for call SID:', callSid);

    // For now, create a mock stream that represents the phone call audio
    // In production, replace this with actual Twilio Media Streams integration
    const mockStream = new MediaStream();
    
    // Add a placeholder audio track
    // Real implementation would get this from Twilio
    try {
      const audioContext = this.audioContext!;
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.frequency.setValueAtTime(0, audioContext.currentTime); // Silent oscillator
      gainNode.gain.setValueAtTime(0, audioContext.currentTime);
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // This is just a placeholder - real audio would come from Twilio
      console.log('📞 TwilioAudio: Mock stream created (replace with real Twilio integration)');
    } catch (error) {
      console.warn('📞 TwilioAudio: Mock stream creation warning:', error);
    }

    return mockStream;
  }

  /**
   * Set up audio processing for a call
   */
  private async setupAudioProcessing(callId: string, stream: MediaStream): Promise<void> {
    if (!this.audioContext) {
      throw new Error('Audio context not initialized');
    }

    try {
      const source = this.audioContext.createMediaStreamSource(stream);
      const processor = this.audioContext.createScriptProcessor(
        this.config.bufferSize,
        1, // mono input
        1  // mono output
      );

      processor.onaudioprocess = (event) => {
        this.processIncomingAudio(callId, event);
      };

      source.connect(processor);
      processor.connect(this.audioContext.destination);

      this.processors.set(callId, processor);

      console.log('📞 TwilioAudio: Audio processing setup complete for call:', callId);
    } catch (error) {
      console.error('📞 TwilioAudio: Audio processing setup failed:', error);
      throw error;
    }
  }

  /**
   * Process incoming audio from phone call
   */
  private processIncomingAudio(callId: string, event: AudioProcessingEvent): void {
    const inputBuffer = event.inputBuffer;
    const inputData = inputBuffer.getChannelData(0);

    // Check for actual audio (not silence)
    let hasAudio = false;
    let maxAmplitude = 0;

    for (let i = 0; i < inputData.length; i++) {
      const amplitude = Math.abs(inputData[i]);
      maxAmplitude = Math.max(maxAmplitude, amplitude);
      if (amplitude > 0.01) { // Threshold for detecting speech
        hasAudio = true;
      }
    }

    if (hasAudio) {
      // Convert to format expected by STT service
      const audioData = this.convertAudioForSTT(inputData);
      
      // Send to telephony WebSocket for STT processing
      telephonyWebSocketManager.sendMessage({
        type: 'audio_data',
        call_id: callId,
        audio_data: audioData,
        sample_rate: this.config.sampleRate,
        encoding: this.config.encoding,
        timestamp: new Date().toISOString()
      });
    }
  }

  /**
   * Convert audio data for STT processing
   */
  private convertAudioForSTT(inputData: Float32Array): string {
    // Convert float32 audio to the format expected by STT
    const buffer = new ArrayBuffer(inputData.length * 2);
    const view = new DataView(buffer);

    for (let i = 0; i < inputData.length; i++) {
      // Convert float32 to int16
      const sample = Math.max(-1, Math.min(1, inputData[i]));
      view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
    }

    // Convert to base64 for transmission
    const uint8Array = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binary += String.fromCharCode(uint8Array[i]);
    }
    return btoa(binary);
  }

  /**
   * Send TTS audio to phone call
   */
  async sendTTSToCall(callId: string, audioBlob: Blob): Promise<void> {
    console.log('📞 TwilioAudio: Sending TTS audio to call:', callId);

    try {
      // Convert blob to appropriate format for Twilio
      const arrayBuffer = await audioBlob.arrayBuffer();
      const audioData = this.convertAudioForTwilio(arrayBuffer);

      // In a real implementation, this would send audio to Twilio Media Streams
      await this.sendAudioToTwilio(callId, audioData);

      console.log('📞 TwilioAudio: TTS audio sent successfully');
    } catch (error) {
      console.error('📞 TwilioAudio: Failed to send TTS audio:', error);
      throw error;
    }
  }

  /**
   * Convert audio for Twilio transmission
   */
  private convertAudioForTwilio(audioBuffer: ArrayBuffer): Uint8Array {
    // Convert audio to format suitable for Twilio (μ-law encoding)
    // This is a simplified conversion - real implementation would do proper μ-law encoding
    
    const int16Array = new Int16Array(audioBuffer);
    const mulawArray = new Uint8Array(int16Array.length);

    for (let i = 0; i < int16Array.length; i++) {
      // Simplified μ-law encoding (real implementation would use proper algorithm)
      mulawArray[i] = this.linearToMulaw(int16Array[i]);
    }

    return mulawArray;
  }

  /**
   * Simple linear to μ-law conversion (replace with proper implementation)
   */
  private linearToMulaw(sample: number): number {
    // Simplified μ-law encoding
    // Real implementation should use proper ITU-T G.711 μ-law algorithm
    const sign = sample < 0 ? 0x80 : 0x00;
    const magnitude = Math.abs(sample);
    const compressed = Math.floor(magnitude / 256);
    return sign | Math.min(compressed, 0x7F);
  }

  /**
   * Send audio data to Twilio (placeholder for real implementation)
   */
  private async sendAudioToTwilio(callId: string, audioData: Uint8Array): Promise<void> {
    // In a real implementation, this would:
    // 1. Use Twilio's Media Streams API to send audio
    // 2. Handle real-time audio streaming to the phone call
    // 3. Manage audio buffering and synchronization

    console.log('📞 TwilioAudio: [PLACEHOLDER] Sending audio to Twilio for call:', callId);
    console.log('📞 TwilioAudio: Audio data size:', audioData.length, 'bytes');

    // Simulate sending to Twilio
    return new Promise((resolve) => {
      setTimeout(() => {
        console.log('📞 TwilioAudio: [SIMULATED] Audio sent to phone call');
        resolve();
      }, 100);
    });
  }

  /**
   * Stop audio streaming for a call
   */
  async stopCallAudioStream(callId: string): Promise<void> {
    console.log('📞 TwilioAudio: Stopping audio stream for call:', callId);

    // Clean up processor
    const processor = this.processors.get(callId);
    if (processor) {
      processor.disconnect();
      this.processors.delete(callId);
    }

    // Clean up stream
    const stream = this.activeStreams.get(callId);
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      this.activeStreams.delete(callId);
    }

    // Notify telephony system
    telephonyWebSocketManager.sendMessage({
      type: 'audio_stream_stopped',
      call_id: callId
    });
  }

  /**
   * Handle call status updates from Twilio
   */
  handleCallStatusUpdate(event: TwilioCallEvent): void {
    console.log('📞 TwilioAudio: Call status update:', event);

    switch (event.type) {
      case 'call_started':
        this.startCallAudioStream(event.callId, event.callSid);
        break;
      case 'call_ended':
        this.stopCallAudioStream(event.callId);
        break;
      case 'audio_received':
        // Handle incoming audio from phone
        break;
    }

    // Forward to telephony WebSocket
    telephonyWebSocketManager.sendMessage({
      type: 'twilio_event',
      event_type: event.type,
      call_id: event.callId,
      call_sid: event.callSid,
      status: event.status,
      timestamp: event.timestamp
    });
  }

  /**
   * Get active call streams
   */
  getActiveStreams(): string[] {
    return Array.from(this.activeStreams.keys());
  }

  /**
   * Check if call has active audio stream
   */
  hasActiveStream(callId: string): boolean {
    return this.activeStreams.has(callId);
  }

  /**
   * Clean up all resources
   */
  async cleanup(): Promise<void> {
    console.log('📞 TwilioAudio: Cleaning up all resources');

    // Stop all active streams
    const callIds = Array.from(this.activeStreams.keys());
    for (const callId of callIds) {
      await this.stopCallAudioStream(callId);
    }

    // Close audio context
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }

    this.isInitialized = false;
  }
}

// Singleton instance
export const twilioAudioService = new TwilioAudioService();