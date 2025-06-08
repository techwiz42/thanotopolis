import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Globe } from 'lucide-react';

interface LanguageSelectorProps {
  value: string;
  onChange: (language: string) => void;
  disabled?: boolean;
  className?: string;
}

// Language codes in standard locale format (e.g., fr-FR)
// The backend will map these to Deepgram's expected format (e.g., fr)
// Based on confirmed Deepgram Nova-2 support
const SUPPORTED_LANGUAGES = [
  // English variants (Nova-3 & Nova-2 supported)
  { code: 'en-US', name: 'English (US)' },
  { code: 'en-GB', name: 'English (UK)' },
  { code: 'en-AU', name: 'English (Australia)' },
  { code: 'en-IN', name: 'English (India)' },
  
  // Spanish (Nova-3 & Nova-2 supported)
  { code: 'es-ES', name: 'Spanish (Spain)' },
  { code: 'es-MX', name: 'Spanish (Mexico)' },
  
  // Other languages (Nova-2 supported)
  { code: 'fr-FR', name: 'French (France)' },
  { code: 'fr-CA', name: 'French (Canada)' },
  { code: 'de-DE', name: 'German' },
  { code: 'de-CH', name: 'German (Switzerland)' },
  { code: 'it-IT', name: 'Italian' },
  { code: 'pt-BR', name: 'Portuguese (Brazil)' },
  { code: 'pt-PT', name: 'Portuguese (Portugal)' },
  { code: 'nl-NL', name: 'Dutch' },
  { code: 'ru-RU', name: 'Russian' },
  { code: 'zh-CN', name: 'Chinese (Mandarin, Simplified)' },
  { code: 'zh-TW', name: 'Chinese (Traditional)' },
  { code: 'ja-JP', name: 'Japanese' },
  { code: 'ko-KR', name: 'Korean' },
  { code: 'hi-IN', name: 'Hindi' },
  { code: 'pl-PL', name: 'Polish' },
  { code: 'tr-TR', name: 'Turkish' },
  { code: 'sv-SE', name: 'Swedish' },
  { code: 'no-NO', name: 'Norwegian' },
  { code: 'da-DK', name: 'Danish' },
  { code: 'fi-FI', name: 'Finnish' },
  { code: 'uk-UA', name: 'Ukrainian' },
  { code: 'id-ID', name: 'Indonesian' },
  { code: 'ms-MY', name: 'Malay' },
  { code: 'vi-VN', name: 'Vietnamese' },
  { code: 'th-TH', name: 'Thai' },
  { code: 'el-GR', name: 'Greek' },
  { code: 'cs-CZ', name: 'Czech' },
  { code: 'sk-SK', name: 'Slovak' },
  { code: 'hu-HU', name: 'Hungarian' },
  { code: 'ro-RO', name: 'Romanian' },
  
  // Note: Removed Arabic (ar-SA) and Hebrew (he-IL) as they're not in Nova-2 docs
  // Note: Removed some Baltic languages not confirmed in Nova-2 docs
];

export function LanguageSelector({ value, onChange, disabled, className }: LanguageSelectorProps) {
  // Find the current language name for display
  const currentLanguage = SUPPORTED_LANGUAGES.find(lang => lang.code === value);
  
  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <Globe className="h-4 w-4 text-gray-700" />
      <Select
        value={value}
        onValueChange={onChange}
        disabled={disabled}
      >
        <SelectTrigger className="w-48 bg-white border-gray-300 text-gray-900">
          <SelectValue placeholder="Select language" />
        </SelectTrigger>
        <SelectContent className="bg-white border border-gray-200 shadow-lg max-h-60 overflow-y-auto">
          {SUPPORTED_LANGUAGES.map((lang) => (
            <SelectItem key={lang.code} value={lang.code} className="bg-white hover:bg-gray-100">
              {lang.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}