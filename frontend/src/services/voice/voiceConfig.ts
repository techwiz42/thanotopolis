import { api } from '../api';

export interface VoiceConfig {
  tts: {
    voice_id: string;
    model: string;
    output_format: string;
    optimize_streaming_latency: number;
  };
  stt: {
    model: string;
    language: string;
  };
  timestamp: string;
}

class VoiceConfigService {
  private config: VoiceConfig | null = null;
  private configPromise: Promise<VoiceConfig> | null = null;
  private lastFetch: number = 0;
  private readonly CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  async getConfig(token: string): Promise<VoiceConfig> {
    const now = Date.now();
    
    // Return cached config if still valid
    if (this.config && (now - this.lastFetch) < this.CACHE_DURATION) {
      return this.config;
    }

    // Return existing promise if one is in flight
    if (this.configPromise) {
      return this.configPromise;
    }

    // Fetch new config
    this.configPromise = this.fetchConfig(token);
    
    try {
      this.config = await this.configPromise;
      this.lastFetch = now;
      return this.config;
    } finally {
      this.configPromise = null;
    }
  }

  private async fetchConfig(token: string): Promise<VoiceConfig> {
    try {
      const response = await api.get('/voice/config', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      return response.data as VoiceConfig;
    } catch (error) {
      console.error('Failed to fetch voice config:', error);
      throw error;
    }
  }

  // Get just the voice ID quickly
  async getVoiceId(token: string): Promise<string> {
    const config = await this.getConfig(token);
    return config.tts.voice_id;
  }

  // Clear cache to force refresh
  clearCache(): void {
    this.config = null;
    this.configPromise = null;
    this.lastFetch = 0;
  }
}

export const voiceConfigService = new VoiceConfigService();