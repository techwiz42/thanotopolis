// src/contexts/VoiceContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface VoiceSettings {
  inputEnabled: boolean;
  outputEnabled: boolean;
  autoPlayResponses: boolean;
  selectedVoice: string;
  speakingRate: number;
  pitch: number;
  volume: number;
  preprocessText: boolean;
}

interface VoiceContextType extends VoiceSettings {
  setInputEnabled: (enabled: boolean) => void;
  setOutputEnabled: (enabled: boolean) => void;
  setAutoPlayResponses: (enabled: boolean) => void;
  setSelectedVoice: (voiceId: string) => void;
  setSpeakingRate: (rate: number) => void;
  setPitch: (pitch: number) => void;
  setVolume: (volume: number) => void;
  setPreprocessText: (enabled: boolean) => void;
  updateSettings: (settings: Partial<VoiceSettings>) => void;
  resetSettings: () => void;
}

const defaultSettings: VoiceSettings = {
  inputEnabled: false,
  outputEnabled: false,
  autoPlayResponses: false,
  selectedVoice: '',
  speakingRate: 0.95,
  pitch: -1.0,
  volume: 80,
  preprocessText: true
};

const VoiceContext = createContext<VoiceContextType | undefined>(undefined);

export const useVoice = (): VoiceContextType => {
  const context = useContext(VoiceContext);
  if (!context) {
    throw new Error('useVoice must be used within a VoiceProvider');
  }
  return context;
};

interface VoiceProviderProps {
  children: ReactNode;
}

export const VoiceProvider: React.FC<VoiceProviderProps> = ({ children }) => {
  const [settings, setSettings] = useState<VoiceSettings>(defaultSettings);

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

  const setInputEnabled = (enabled: boolean) => {
    setSettings(prev => ({ ...prev, inputEnabled: enabled }));
  };

  const setOutputEnabled = (enabled: boolean) => {
    setSettings(prev => ({ ...prev, outputEnabled: enabled }));
  };

  const setAutoPlayResponses = (enabled: boolean) => {
    setSettings(prev => ({ ...prev, autoPlayResponses: enabled }));
  };

  const setSelectedVoice = (voiceId: string) => {
    setSettings(prev => ({ ...prev, selectedVoice: voiceId }));
  };

  const setSpeakingRate = (rate: number) => {
    setSettings(prev => ({ ...prev, speakingRate: rate }));
  };

  const setPitch = (pitch: number) => {
    setSettings(prev => ({ ...prev, pitch: pitch }));
  };

  const setVolume = (volume: number) => {
    setSettings(prev => ({ ...prev, volume: volume }));
  };

  const setPreprocessText = (enabled: boolean) => {
    setSettings(prev => ({ ...prev, preprocessText: enabled }));
  };

  const updateSettings = (newSettings: Partial<VoiceSettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  };

  const resetSettings = () => {
    setSettings(defaultSettings);
  };

  const value: VoiceContextType = {
    ...settings,
    setInputEnabled,
    setOutputEnabled,
    setAutoPlayResponses,
    setSelectedVoice,
    setSpeakingRate,
    setPitch,
    setVolume,
    setPreprocessText,
    updateSettings,
    resetSettings
  };

  return (
    <VoiceContext.Provider value={value}>
      {children}
    </VoiceContext.Provider>
  );
};
