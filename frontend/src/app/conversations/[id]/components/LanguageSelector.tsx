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
  isAutoDetected?: boolean;
  detectedLanguage?: string | null;
  onManualOverride?: () => void;
}

// Language codes in standard locale format (e.g., fr-FR)
// The backend will map these to Soniox's expected format (e.g., fr)
// Based on Soniox language support
const SUPPORTED_LANGUAGES = [
  // English variants (Soniox supported)
  { code: 'en-US', name: 'English (US)' },
  { code: 'en-GB', name: 'English (UK)' },
  { code: 'en-AU', name: 'English (Australia)' },
  { code: 'en-IN', name: 'English (India)' },
  
  // Spanish (Soniox supported)
  { code: 'es-ES', name: 'Spanish (Spain)' },
  { code: 'es-MX', name: 'Spanish (Mexico)' },
  
  // Other languages (Soniox supported)
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
  
  // Note: Language support based on Soniox documentation
  // Additional languages may be available - check Soniox docs for updates
];

export function LanguageSelector({ 
  value, 
  onChange, 
  disabled, 
  className,
  isAutoDetected = false,
  detectedLanguage = null,
  onManualOverride
}: LanguageSelectorProps) {
  // Find the current language name for display
  const currentLanguage = SUPPORTED_LANGUAGES.find(lang => lang.code === value);
  
  // Handle language change with manual override notification
  const handleLanguageChange = (newLanguage: string) => {
    // If this is a manual change (different from auto-detected), notify parent
    if (isAutoDetected && detectedLanguage && newLanguage !== detectedLanguage && onManualOverride) {
      onManualOverride();
    }
    onChange(newLanguage);
  };
  
  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <Globe className={`h-4 w-4 ${isAutoDetected ? 'text-blue-600' : 'text-gray-700'}`} />
      <Select
        value={value}
        onValueChange={handleLanguageChange}
        disabled={disabled}
        onOpenChange={(open) => {
          // Don't interfere with focus when opening/closing
          if (!open) {
            // When closing, let the parent handle focus restoration
            console.log('Language selector closed');
          }
        }}
      >
        <SelectTrigger className={`w-48 bg-white text-gray-900 transition-colors ${
          isAutoDetected 
            ? 'border-blue-300 ring-1 ring-blue-100 bg-blue-50' 
            : 'border-gray-300'
        }`}>
          <SelectValue placeholder="Select language" />
        </SelectTrigger>
        <SelectContent className="bg-white border border-gray-200 shadow-lg max-h-60 overflow-y-auto">
          {/* Add auto-detect option */}
          <SelectItem value="auto" className="bg-white hover:bg-gray-100">
            <div className="flex items-center space-x-2">
              <Globe className="h-3 w-3 text-blue-600" />
              <span>Auto-detect language</span>
            </div>
          </SelectItem>
          
          {/* Separator */}
          <div className="border-t border-gray-200 my-1" />
          
          {SUPPORTED_LANGUAGES.map((lang) => (
            <SelectItem key={lang.code} value={lang.code} className="bg-white hover:bg-gray-100">
              <div className="flex items-center justify-between w-full">
                <span>{lang.name}</span>
                {isAutoDetected && detectedLanguage === lang.code && (
                  <span className="text-xs text-blue-600 ml-2">• Auto-detected</span>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}