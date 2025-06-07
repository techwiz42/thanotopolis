// PCM audio recorder using Web Audio API for STT
import { useRef } from 'react';

export class PCMRecorder {
  private audioContext: AudioContext;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private websocket: WebSocket | null = null;
  private stream: MediaStream | null = null;
  private targetSampleRate: number = 16000;

  constructor() {
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  }

  async start(websocket: WebSocket): Promise<void> {
    this.websocket = websocket;
    
    // Get microphone stream - don't specify sample rate, let browser decide
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });

    // Create audio nodes
    this.source = this.audioContext.createMediaStreamSource(this.stream);
    
    // Create script processor (buffer size, input channels, output channels)
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    
    // Log actual sample rates for debugging
    console.log(`Audio context sample rate: ${this.audioContext.sampleRate}Hz`);
    console.log(`Target sample rate: ${this.targetSampleRate}Hz`);
    
    // Process audio
    this.processor.onaudioprocess = (e) => {
      if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
        return;
      }

      const inputData = e.inputBuffer.getChannelData(0);
      const inputSampleRate = this.audioContext.sampleRate;
      
      // Resample if needed
      let processedData = inputData;
      if (inputSampleRate !== this.targetSampleRate) {
        processedData = this.resample(inputData, inputSampleRate, this.targetSampleRate);
      }
      
      // Convert float32 to int16 PCM
      const pcm = new Int16Array(processedData.length);
      for (let i = 0; i < processedData.length; i++) {
        const s = Math.max(-1, Math.min(1, processedData[i]));
        pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      
      // Send raw PCM data
      this.websocket.send(pcm.buffer);
    };

    // Connect nodes
    this.source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
    
    console.log(`PCM recording started - resampling from ${this.audioContext.sampleRate}Hz to ${this.targetSampleRate}Hz`);
  }

  stop(): void {
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    console.log('PCM recording stopped');
  }

  private resample(inputData: Float32Array, inputSampleRate: number, outputSampleRate: number): Float32Array {
    if (inputSampleRate === outputSampleRate) {
      return inputData;
    }
    
    const ratio = inputSampleRate / outputSampleRate;
    const outputLength = Math.floor(inputData.length / ratio);
    const output = new Float32Array(outputLength);
    
    for (let i = 0; i < outputLength; i++) {
      const inputIndex = i * ratio;
      const index = Math.floor(inputIndex);
      const fraction = inputIndex - index;
      
      if (index + 1 < inputData.length) {
        // Linear interpolation
        output[i] = inputData[index] * (1 - fraction) + inputData[index + 1] * fraction;
      } else {
        output[i] = inputData[index];
      }
    }
    
    return output;
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