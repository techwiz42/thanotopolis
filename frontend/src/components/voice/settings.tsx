// src/components/voice/VoiceSettings.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';
import { Play, Volume2, Mic, TestTube } from 'lucide-react';

interface Voice {
  id: string;
  name: string;
  gender: string;
  quality: string;
}

interface VoiceSettingsState {
  inputEnabled: boolean;
  outputEnabled: boolean;
  autoPlayResponses: boolean;
  selectedVoice: string;
  speakingRate: number;
  pitch: number;
  volume: number;
  preprocessText: boolean;
}

export const VoiceSettings: React.FC = () => {
  const [settings, setSettings] = useState<VoiceSettingsState>({
    inputEnabled: false,
    outputEnabled: false,
    autoPlayResponses: false,
    selectedVoice: '',
    speakingRate: 0.95,
    pitch: -1.0,
    volume: 80,
    preprocessText: true
  });
  
  const [voices, setVoices] = useState<Voice[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTestingVoice, setIsTestingVoice] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<{
    stt: { available: boolean; error?: string };
    tts: { available: boolean; error?: string };
  }>({
    stt: { available: false },
    tts: { available: false }
  });

  const { token } = useAuth();
  const { toast } = useToast();

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = localStorage.getItem('voiceSettings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setSettings(prev => ({ ...prev, ...parsed }));
      } catch (error) {
        console.error('Error loading voice settings:', error);
      }
    }
  }, []);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('voiceSettings', JSON.stringify(settings));
  }, [settings]);

  const loadVoicesAndStatus = useCallback(async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      // Load TTS voices and status
      const [voicesResponse, ttsStatusResponse, sttStatusResponse] = await Promise.allSettled([
        api.get('/voice/tts/voices', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        api.get('/voice/tts/status'),
        api.get('/voice/stt/status')
      ]);

      // Handle voices
      if (voicesResponse.status === 'fulfilled') {
        const responseData = voicesResponse.value.data as any;
        setVoices(responseData.voices || []);
        if (!settings.selectedVoice && responseData.default_voice) {
          setSettings(prev => ({ 
            ...prev, 
            selectedVoice: responseData.default_voice 
          }));
        }
      }

      // Handle TTS status
      const ttsResponseData = ttsStatusResponse.status === 'fulfilled' ? (ttsStatusResponse.value.data as any) : null;
      const ttsAvailable = ttsResponseData?.api_key_configured === true;
      const ttsError = ttsStatusResponse.status === 'rejected' ? 
                      (ttsStatusResponse.reason as Error).message : 
                      !ttsAvailable ? 'API key not configured' : undefined;

      // Handle STT status  
      const sttResponseData = sttStatusResponse.status === 'fulfilled' ? (sttStatusResponse.value.data as any) : null;
      const sttAvailable = sttResponseData?.api_key_configured === true;
      const sttError = sttStatusResponse.status === 'rejected' ? 
                      (sttStatusResponse.reason as Error).message : 
                      !sttAvailable ? 'API key not configured' : undefined;

      setServiceStatus({
        tts: { available: ttsAvailable, error: ttsError },
        stt: { available: sttAvailable, error: sttError }
      });

    } catch (error) {
      console.error('Error loading voice data:', error);
      toast({
        title: "Error Loading Voice Settings",
        description: "Failed to load voice configuration",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  }, [token, settings.selectedVoice, toast]);

  // Load available voices and service status
  useEffect(() => {
    loadVoicesAndStatus();
  }, [loadVoicesAndStatus]);

  const testVoice = async () => {
    if (!settings.selectedVoice || !serviceStatus.tts.available) return;

    setIsTestingVoice(true);
    try {
      const testText = "Hello! This is a test of the selected voice settings. How does this sound?";
      
      // Use fetch directly for binary data
      const response = await fetch('/api/voice/synthesize', {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: testText,
          voice_id: settings.selectedVoice,
          speaking_rate: settings.speakingRate,
          pitch: settings.pitch,
          volume_gain_db: (settings.volume / 100) * 16 - 8, // Convert 0-100 to -8 to +8 dB
          preprocess_text: settings.preprocessText
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      // Play the audio
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        setIsTestingVoice(false);
      };
      
      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        setIsTestingVoice(false);
        toast({
          title: "Playback Error",
          description: "Failed to play test audio",
          variant: "destructive"
        });
      };

      await audio.play();

    } catch (error) {
      console.error('Error testing voice:', error);
      setIsTestingVoice(false);
      toast({
        title: "Voice Test Failed",
        description: "Could not test the selected voice",
        variant: "destructive"
      });
    }
  };

  const resetToDefaults = () => {
    setSettings({
      inputEnabled: false,
      outputEnabled: false,
      autoPlayResponses: false,
      selectedVoice: voices.find(v => v.quality === 'studio')?.id || voices[0]?.id || '',
      speakingRate: 0.95,
      pitch: -1.0,
      volume: 80,
      preprocessText: true
    });
    
    toast({
      title: "Settings Reset",
      description: "Voice settings have been reset to defaults",
    });
  };

  const getQualityBadgeColor = (quality: string) => {
    switch (quality) {
      case 'studio': return 'bg-purple-100 text-purple-800';
      case 'neural2': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Service Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TestTube className="w-5 h-5" />
            Service Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4" />
                <span className="font-medium">Speech Input</span>
              </div>
              <Badge variant={serviceStatus.stt.available ? "default" : "destructive"}>
                {serviceStatus.stt.available ? "Available" : "Unavailable"}
              </Badge>
            </div>
            
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4" />
                <span className="font-medium">Speech Output</span>
              </div>
              <Badge variant={serviceStatus.tts.available ? "default" : "destructive"}>
                {serviceStatus.tts.available ? "Available" : "Unavailable"}
              </Badge>
            </div>
          </div>
          
          {(serviceStatus.stt.error || serviceStatus.tts.error) && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">
                <strong>Configuration Issues:</strong>
              </p>
              {serviceStatus.stt.error && (
                <p className="text-sm text-yellow-700">• Speech Input: {serviceStatus.stt.error}</p>
              )}
              {serviceStatus.tts.error && (
                <p className="text-sm text-yellow-700">• Speech Output: {serviceStatus.tts.error}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* General Voice Settings */}
      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <label className="font-medium">Enable Voice Input</label>
              <p className="text-sm text-gray-600">Allow microphone input for conversations</p>
            </div>
            <Switch
              checked={settings.inputEnabled}
              onCheckedChange={(checked) => 
                setSettings(prev => ({ ...prev, inputEnabled: checked }))
              }
              disabled={!serviceStatus.stt.available}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="font-medium">Enable Voice Output</label>
              <p className="text-sm text-gray-600">Allow text-to-speech for agent responses</p>
            </div>
            <Switch
              checked={settings.outputEnabled}
              onCheckedChange={(checked) => 
                setSettings(prev => ({ ...prev, outputEnabled: checked }))
              }
              disabled={!serviceStatus.tts.available}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="font-medium">Auto-play Agent Responses</label>
              <p className="text-sm text-gray-600">Automatically speak agent responses aloud</p>
            </div>
            <Switch
              checked={settings.autoPlayResponses}
              onCheckedChange={(checked) => 
                setSettings(prev => ({ ...prev, autoPlayResponses: checked }))
              }
              disabled={!serviceStatus.tts.available || !settings.outputEnabled}
            />
          </div>
        </CardContent>
      </Card>

      {/* Voice Output Settings */}
      {serviceStatus.tts.available && (
        <Card>
          <CardHeader>
            <CardTitle>Voice Output Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Voice Selection */}
            <div>
              <label className="font-medium mb-2 block">Voice Selection</label>
              <div className="flex gap-2">
                <Select
                  value={settings.selectedVoice}
                  onValueChange={(value) => 
                    setSettings(prev => ({ ...prev, selectedVoice: value }))
                  }
                >
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="Select a voice..." />
                  </SelectTrigger>
                  <SelectContent>
                    {voices.map((voice) => (
                      <SelectItem key={voice.id} value={voice.id}>
                        <div className="flex items-center gap-2">
                          <span>{voice.name}</span>
                          <Badge className={getQualityBadgeColor(voice.quality)}>
                            {voice.quality}
                          </Badge>
                          <Badge variant="outline">
                            {voice.gender}
                          </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Button
                  onClick={testVoice}
                  disabled={!settings.selectedVoice || isTestingVoice}
                  size="sm"
                >
                  {isTestingVoice ? (
                    <div className="w-4 h-4 border border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Speaking Rate */}
            <div>
              <label className="font-medium mb-2 block">
                Speaking Rate: {settings.speakingRate.toFixed(2)}x
              </label>
              <Slider
                value={[settings.speakingRate]}
                onValueChange={(value) => 
                  setSettings(prev => ({ ...prev, speakingRate: value[0] }))
                }
                min={0.25}
                max={4.0}
                step={0.05}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Slow (0.25x)</span>
                <span>Normal (1.0x)</span>
                <span>Fast (4.0x)</span>
              </div>
            </div>

            {/* Pitch */}
            <div>
              <label className="font-medium mb-2 block">
                Pitch: {settings.pitch > 0 ? '+' : ''}{settings.pitch.toFixed(1)}
              </label>
              <Slider
                value={[settings.pitch]}
                onValueChange={(value) => 
                  setSettings(prev => ({ ...prev, pitch: value[0] }))
                }
                min={-20}
                max={20}
                step={0.5}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Lower (-20)</span>
                <span>Normal (0)</span>
                <span>Higher (+20)</span>
              </div>
            </div>

            {/* Volume */}
            <div>
              <label className="font-medium mb-2 block">
                Volume: {settings.volume}%
              </label>
              <Slider
                value={[settings.volume]}
                onValueChange={(value) => 
                  setSettings(prev => ({ ...prev, volume: value[0] }))
                }
                min={0}
                max={100}
                step={5}
                className="w-full"
              />
            </div>

            {/* Text Preprocessing */}
            <div className="flex items-center justify-between">
              <div>
                <label className="font-medium">Enhanced Text Processing</label>
                <p className="text-sm text-gray-600">
                  Apply natural speech patterns and pronunciation improvements
                </p>
              </div>
              <Switch
                checked={settings.preprocessText}
                onCheckedChange={(checked) => 
                  setSettings(prev => ({ ...prev, preprocessText: checked }))
                }
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex gap-4">
        <Button
          onClick={resetToDefaults}
          variant="outline"
          disabled={isLoading}
        >
          Reset to Defaults
        </Button>
        
        <Button
          onClick={loadVoicesAndStatus}
          variant="outline"
          disabled={isLoading}
        >
          {isLoading ? 'Refreshing...' : 'Refresh Status'}
        </Button>
      </div>
    </div>
  );
};