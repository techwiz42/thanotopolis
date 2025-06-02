import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface VoiceContextType {
  inputEnabled: boolean;
  outputEnabled: boolean;
  autoPlayResponses: boolean;
  setInputEnabled: (enabled: boolean) => void;
  setOutputEnabled: (enabled: boolean) => void;
  setAutoPlayResponses: (enabled: boolean) => void;
  voiceId: string;
  setVoiceId: (id: string) => void;
  speakingRate: number;
  setSpeakingRate: (rate: number) => void;
  pitch: number;
  setPitch: (pitch: number) => void;
  volume: number;
  setVolume: (volume: number) => void;
  preprocessText: boolean;
  setPreprocessText: (preprocess: boolean) => void;
}

const defaultSettings = {
  inputEnabled: false,
  outputEnabled: false,
  autoPlayResponses: false,
  voiceId: '',
  speakingRate: 0.95,
  pitch: -1.0,
  volume: 80,
  preprocessText: true
};

const VoiceContext = createContext<VoiceContextType>({
  ...defaultSettings,
  setInputEnabled: () => {},
  setOutputEnabled: () => {},
  setAutoPlayResponses: () => {},
  setVoiceId: () => {},
  setSpeakingRate: () => {},
  setPitch: () => {},
  setVolume: () => {},
  setPreprocessText: () => {}
});

export const useVoice = () => useContext(VoiceContext);

interface VoiceProviderProps {
  children: ReactNode;
}

export const VoiceProvider: React.FC<VoiceProviderProps> = ({ children }) => {
  const [inputEnabled, setInputEnabled] = useState(defaultSettings.inputEnabled);
  const [outputEnabled, setOutputEnabled] = useState(defaultSettings.outputEnabled);
  const [autoPlayResponses, setAutoPlayResponses] = useState(defaultSettings.autoPlayResponses);
  const [voiceId, setVoiceId] = useState(defaultSettings.voiceId);
  const [speakingRate, setSpeakingRate] = useState(defaultSettings.speakingRate);
  const [pitch, setPitch] = useState(defaultSettings.pitch);
  const [volume, setVolume] = useState(defaultSettings.volume);
  const [preprocessText, setPreprocessText] = useState(defaultSettings.preprocessText);

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = localStorage.getItem('voiceSettings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setInputEnabled(parsed.inputEnabled ?? defaultSettings.inputEnabled);
        setOutputEnabled(parsed.outputEnabled ?? defaultSettings.outputEnabled);
        setAutoPlayResponses(parsed.autoPlayResponses ?? defaultSettings.autoPlayResponses);
        setVoiceId(parsed.selectedVoice ?? defaultSettings.voiceId);
        setSpeakingRate(parsed.speakingRate ?? defaultSettings.speakingRate);
        setPitch(parsed.pitch ?? defaultSettings.pitch);
        setVolume(parsed.volume ?? defaultSettings.volume);
        setPreprocessText(parsed.preprocessText ?? defaultSettings.preprocessText);
      } catch (error) {
        console.error('Error loading voice settings:', error);
      }
    }
  }, []);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    const settings = {
      inputEnabled,
      outputEnabled,
      autoPlayResponses,
      selectedVoice: voiceId,
      speakingRate,
      pitch,
      volume,
      preprocessText
    };
    localStorage.setItem('voiceSettings', JSON.stringify(settings));
  }, [inputEnabled, outputEnabled, autoPlayResponses, voiceId, speakingRate, pitch, volume, preprocessText]);

  return (
    <VoiceContext.Provider
      value={{
        inputEnabled,
        outputEnabled,
        autoPlayResponses,
        setInputEnabled,
        setOutputEnabled,
        setAutoPlayResponses,
        voiceId,
        setVoiceId,
        speakingRate,
        setSpeakingRate,
        pitch,
        setPitch,
        volume,
        setVolume,
        preprocessText,
        setPreprocessText
      }}
    >
      {children}
    </VoiceContext.Provider>
  );
};