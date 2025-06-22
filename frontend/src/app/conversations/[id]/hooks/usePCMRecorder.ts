// Enhanced PCM audio recorder using Web Audio API for STT
// Based on working implementation from cyberiad_dev project
import { useRef } from 'react';

/**
 * Type for streaming STT options
 */
export interface StreamingSttOptions {
  /** Language code for speech recognition */
  languageCode?: string;
  /** Model to use (for Soniox compatibility) */
  model?: string;
  /** Callback when transcription is received */
  onTranscription?: (text: string, isFinal: boolean) => void;
  /** Callback when speech starts */
  onSpeechStart?: () => void;
  /** Callback when utterance ends */
  onUtteranceEnd?: () => void;
  /** Callback when connection status changes */
  onConnectionChange?: (isConnected: boolean) => void;
  /** Callback when error occurs */
  onError?: (error: string) => void;
}

/**
 * Enhanced PCM recorder with sophisticated audio processing
 */
export class PCMRecorder {
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private websocket: WebSocket | null = null;
  private stream: MediaStream | null = null;
  private targetSampleRate: number = 16000;
  private isStoppingRef: boolean = false;

  constructor() {
    // Don't initialize AudioContext here - wait for user interaction
  }

  async start(websocket: WebSocket): Promise<void> {
    this.websocket = websocket;
    this.isStoppingRef = false;
    
    try {
      // Request microphone access with optimized constraints for better sensitivity
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: false, // Disable noise suppression to improve sensitivity
          autoGainControl: true,
          // Increase volume sensitivity
          advanced: [
            { autoGainControl: { exact: true } },
            { echoCancellation: { exact: true } },
            { noiseSuppression: { exact: false } } // Explicitly disable noise suppression
          ]
          // Don't specify sampleRate to avoid conflicts
        }
      });

      // Don't specify sample rate - let it use the default to avoid Firefox issues
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      // Create audio nodes
      this.source = this.audioContext.createMediaStreamSource(this.stream);
      
      // Get the actual sample rate
      const actualSampleRate = this.audioContext.sampleRate;
      console.log(`AudioContext sample rate: ${actualSampleRate}Hz`);
      
      // Create script processor (buffer size, input channels, output channels)
      // Smaller buffer size for lower latency
      this.processor = this.audioContext.createScriptProcessor(512, 1, 1); // Reduced buffer size for better responsiveness
      
      // Track recent audio activity for better silence detection
      let recentAudioFramesWithActivity = 0;
      const RECENT_AUDIO_THRESHOLD = 3; // Number of frames to keep sending after detecting activity
      
      // Process audio
      this.processor.onaudioprocess = (e) => {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN || this.isStoppingRef) {
          return;
        }

        // Get audio data
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Check if there's actual audio (not silence)
        // Use a lower threshold to increase sensitivity
        let hasAudio = false;
        let maxAmplitude = 0;
        for (let i = 0; i < inputData.length; i++) {
          const amplitude = Math.abs(inputData[i]);
          maxAmplitude = Math.max(maxAmplitude, amplitude);
          if (amplitude > 0.005) { // Lower threshold for better sensitivity (was 0.01)
            hasAudio = true;
            break;
          }
        }
        
        // Update recent activity tracker
        if (hasAudio) {
          recentAudioFramesWithActivity = RECENT_AUDIO_THRESHOLD;
        } else {
          recentAudioFramesWithActivity = Math.max(0, recentAudioFramesWithActivity - 1);
        }
        
        // Process if we have audio or recent audio activity
        if (hasAudio || recentAudioFramesWithActivity > 0) {
          // If sample rate is not 16kHz, we need to downsample
          let outputData: Int16Array;
          
          if (actualSampleRate === 16000) {
            // Direct conversion without resampling
            outputData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              // Apply slight gain to boost the signal
              const boostedSample = inputData[i] * 1.5; // Boost input by 50%
              const s = Math.max(-1, Math.min(1, boostedSample));
              outputData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
          } else {
            // Improved downsampling with basic interpolation
            const ratio = actualSampleRate / 16000;
            const outputLength = Math.floor(inputData.length / ratio);
            outputData = new Int16Array(outputLength);
            
            for (let i = 0; i < outputLength; i++) {
              const inputIndexFloat = i * ratio;
              const inputIndex = Math.floor(inputIndexFloat);
              const fraction = inputIndexFloat - inputIndex;
              
              // Simple linear interpolation between samples
              let sample = inputData[inputIndex];
              if (inputIndex + 1 < inputData.length) {
                sample = sample * (1 - fraction) + inputData[inputIndex + 1] * fraction;
              }
              
              // Apply gain to boost signal
              const boostedSample = sample * 1.5; // Boost by 50%
              const s = Math.max(-1, Math.min(1, boostedSample));
              outputData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
          }
          
          // Send to WebSocket
          this.websocket.send(outputData.buffer);
        }
      };

      // Connect nodes
      this.source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      
      console.log('Enhanced PCM recording started with improved audio processing');
      
    } catch (error) {
      console.error('Error starting enhanced PCM recorder:', error);
      this.stop();
      throw error;
    }
  }

  stop(): void {
    console.log('Stopping enhanced PCM recording...');
    this.isStoppingRef = true;
    
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }
    
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    console.log('Enhanced PCM recording stopped');
  }
}

export const usePCMRecorder = () => {
  const recorderRef = useRef<PCMRecorder | null>(null);
  
  const startRecording = async (websocket: WebSocket) => {
    if (!recorderRef.current) {
      recorderRef.current = new PCMRecorder();
    }
    await recorderRef.current.start(websocket);
  };
  
  const stopRecording = () => {
    if (recorderRef.current) {
      recorderRef.current.stop();
      recorderRef.current = null;
    }
  };
  
  return { startRecording, stopRecording };
};