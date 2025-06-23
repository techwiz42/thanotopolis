// src/app/conversations/[id]/utils/voiceUtils.ts

/**
 * Voice utility functions for the conversation page
 */

/**
 * Check if the browser supports the required Web APIs for voice functionality
 */
export const checkVoiceSupport = () => {
  const support = {
    mediaDevices: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
    webSocket: !!window.WebSocket,
    audioContext: !!(window.AudioContext || (window as any).webkitAudioContext),
    mediaRecorder: !!window.MediaRecorder,
    audioElement: !!window.Audio
  };

  const isSupported = Object.values(support).every(Boolean);

  return {
    isSupported,
    support,
    missingFeatures: Object.entries(support)
      .filter(([_, supported]) => !supported)
      .map(([feature]) => feature)
  };
};

/**
 * Clean text content for TTS by removing or replacing problematic characters
 */
export const cleanTextForTTS = (text: string): string => {
  return text
    // Remove markdown-style formatting
    .replace(/[*_`]/g, '')
    // Replace newlines with pauses
    .replace(/\n+/g, '. ')
    // Remove URLs (they don't speak well)
    .replace(/https?:\/\/[^\s]+/g, '[link]')
    // Handle temperature and degree symbols
    .replace(/(\d+)\s*°C/g, '$1 degrees Celsius')
    .replace(/(\d+)\s*°F/g, '$1 degrees Fahrenheit')
    .replace(/(\d+)\s*°/g, '$1 degrees')
    .replace(/°C/g, ' degrees Celsius')
    .replace(/°F/g, ' degrees Fahrenheit')
    .replace(/°/g, ' degrees')
    // Replace common symbols with speakable text
    .replace(/&/g, ' and ')
    .replace(/@/g, ' at ')
    .replace(/#/g, ' hashtag ')
    .replace(/\$/g, ' dollars ')
    .replace(/%/g, ' percent ')
    .replace(/\+/g, ' plus ')
    .replace(/=/g, ' equals ')
    // Handle common abbreviations
    .replace(/\bvs\b/gi, 'versus')
    .replace(/\betc\b/gi, 'etcetera')
    .replace(/\be\.g\.\b/gi, 'for example')
    .replace(/\bi\.e\.\b/gi, 'that is')
    // Remove excessive whitespace
    .replace(/\s+/g, ' ')
    .trim();
};

/**
 * Estimate speaking time for text (rough approximation)
 */
export const estimateSpeakingTime = (text: string, wordsPerMinute: number = 150): number => {
  const words = text.trim().split(/\s+/).length;
  return Math.round((words / wordsPerMinute) * 60 * 1000); // Return milliseconds
};

/**
 * Check if text is suitable for TTS (not too long, has actual content)
 */
export const isTextSuitableForTTS = (text: string, maxLength: number = 1000): boolean => {
  const cleaned = cleanTextForTTS(text);
  return cleaned.length > 0 && cleaned.length <= maxLength;
};

/**
 * Split long text into chunks suitable for TTS while preserving sentence boundaries
 */
export const chunkTextForTTS = (text: string, maxChunkLength: number = 800): string[] => {
  const cleaned = cleanTextForTTS(text);
  
  if (cleaned.length <= maxChunkLength) {
    return [cleaned];
  }

  const chunks: string[] = [];
  const sentences = cleaned.split(/(?<=[.!?])\s+/);
  let currentChunk = '';

  for (const sentence of sentences) {
    // If adding this sentence would exceed the limit, save current chunk and start new one
    if (currentChunk.length + sentence.length + 1 > maxChunkLength && currentChunk.length > 0) {
      chunks.push(currentChunk.trim());
      currentChunk = sentence;
    } else {
      currentChunk += (currentChunk.length > 0 ? ' ' : '') + sentence;
    }
  }

  // Add the last chunk if it has content
  if (currentChunk.trim().length > 0) {
    chunks.push(currentChunk.trim());
  }

  // If we still have chunks that are too long, split by words as fallback
  const finalChunks: string[] = [];
  for (const chunk of chunks) {
    if (chunk.length <= maxChunkLength) {
      finalChunks.push(chunk);
    } else {
      // Split long chunk by words
      const words = chunk.split(' ');
      let wordChunk = '';
      for (const word of words) {
        if (wordChunk.length + word.length + 1 > maxChunkLength && wordChunk.length > 0) {
          finalChunks.push(wordChunk.trim());
          wordChunk = word;
        } else {
          wordChunk += (wordChunk.length > 0 ? ' ' : '') + word;
        }
      }
      if (wordChunk.trim().length > 0) {
        finalChunks.push(wordChunk.trim());
      }
    }
  }

  return finalChunks.length > 0 ? finalChunks : [cleaned.substring(0, maxChunkLength)];
};

/**
 * Generate WebSocket URL for voice services
 */
export const generateVoiceWebSocketUrl = (token: string, service: 'stt' | 'tts' = 'stt'): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const endpoint = service === 'stt' ? 'streaming-stt' : 'streaming-tts';
  
  return `${protocol}//${host}/api/ws/voice/${endpoint}?token=${encodeURIComponent(token)}`;
};

/**
 * Audio constraints for microphone recording optimized for speech recognition
 */
export const getOptimalAudioConstraints = (): MediaStreamConstraints => {
  return {
    audio: {
      sampleRate: 16000,
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      // Request specific sample rate for Deepgram
      sampleSize: 16
    },
    video: false
  };
};

/**
 * Check microphone permission status
 */
export const checkMicrophonePermission = async (): Promise<{
  state: 'granted' | 'denied' | 'prompt' | 'unknown';
  canRequest: boolean;
}> => {
  try {
    if (!navigator.permissions) {
      return { state: 'unknown', canRequest: true };
    }

    const permission = await navigator.permissions.query({ name: 'microphone' as PermissionName });
    return {
      state: permission.state as 'granted' | 'denied' | 'prompt',
      canRequest: permission.state !== 'denied'
    };
  } catch (error) {
    console.warn('Could not check microphone permission:', error);
    return { state: 'unknown', canRequest: true };
  }
};

/**
 * Convert MediaRecorder blob to appropriate format for streaming
 */
export const convertAudioBlob = async (blob: Blob): Promise<ArrayBuffer> => {
  try {
    return await blob.arrayBuffer();
  } catch (error) {
    console.error('Error converting audio blob:', error);
    throw error;
  }
};

/**
 * Debounce function for handling rapid voice events
 */
export const debounce = <T extends (...args: any[]) => void>(
  func: T,
  delay: number
): ((...args: Parameters<T>) => void) => {
  let timeoutId: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

/**
 * Voice activity detection (basic implementation)
 */
export class VoiceActivityDetector {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;
  private threshold: number = 30;
  private isActive: boolean = false;

  constructor(threshold: number = 30) {
    this.threshold = threshold;
  }

  async initialize(stream: MediaStream): Promise<void> {
    try {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      
      const source = this.audioContext.createMediaStreamSource(stream);
      source.connect(this.analyser);
      
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    } catch (error) {
      console.error('Failed to initialize voice activity detection:', error);
    }
  }

  getVoiceActivity(): boolean {
    if (!this.analyser || !this.dataArray) return false;

    this.analyser.getByteFrequencyData(this.dataArray);
    
    // Calculate average volume
    const average = this.dataArray.reduce((sum, value) => sum + value, 0) / this.dataArray.length;
    
    this.isActive = average > this.threshold;
    return this.isActive;
  }

  destroy(): void {
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.analyser = null;
    this.dataArray = null;
  }
}
