import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Brain, Globe, Signal, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface LanguageDetectionIndicatorProps {
  detectedLanguage: string | null;
  confidence: number;
  isAutoDetecting: boolean;
  isManualOverride: boolean;
  className?: string;
}

// Map language codes to display names
const LANGUAGE_NAMES: { [key: string]: string } = {
  'en': 'English',
  'en-US': 'English (US)',
  'en-GB': 'English (UK)',
  'en-AU': 'English (Australia)',
  'en-IN': 'English (India)',
  'es': 'Spanish',
  'es-ES': 'Spanish (Spain)',
  'es-MX': 'Spanish (Mexico)',
  'fr': 'French',
  'fr-FR': 'French (France)',
  'fr-CA': 'French (Canada)',
  'de': 'German',
  'de-DE': 'German',
  'de-CH': 'German (Switzerland)',
  'it': 'Italian',
  'it-IT': 'Italian',
  'pt': 'Portuguese',
  'pt-BR': 'Portuguese (Brazil)',
  'pt-PT': 'Portuguese (Portugal)',
  'nl': 'Dutch',
  'nl-NL': 'Dutch',
  'ru': 'Russian',
  'ru-RU': 'Russian',
  'zh': 'Chinese',
  'zh-CN': 'Chinese (Simplified)',
  'zh-TW': 'Chinese (Traditional)',
  'ja': 'Japanese',
  'ja-JP': 'Japanese',
  'ko': 'Korean',
  'ko-KR': 'Korean',
  'hi': 'Hindi',
  'hi-IN': 'Hindi',
  'pl': 'Polish',
  'pl-PL': 'Polish',
  'tr': 'Turkish',
  'tr-TR': 'Turkish',
  'sv': 'Swedish',
  'sv-SE': 'Swedish',
  'no': 'Norwegian',
  'no-NO': 'Norwegian',
  'da': 'Danish',
  'da-DK': 'Danish',
  'fi': 'Finnish',
  'fi-FI': 'Finnish',
  'uk': 'Ukrainian',
  'uk-UA': 'Ukrainian',
  'id': 'Indonesian',
  'id-ID': 'Indonesian',
  'ms': 'Malay',
  'ms-MY': 'Malay',
  'vi': 'Vietnamese',
  'vi-VN': 'Vietnamese',
  'th': 'Thai',
  'th-TH': 'Thai',
  'el': 'Greek',
  'el-GR': 'Greek',
  'cs': 'Czech',
  'cs-CZ': 'Czech',
  'sk': 'Slovak',
  'sk-SK': 'Slovak',
  'hu': 'Hungarian',
  'hu-HU': 'Hungarian',
  'ro': 'Romanian',
  'ro-RO': 'Romanian',
};

// Get confidence level category
const getConfidenceLevel = (confidence: number): 'high' | 'medium' | 'low' => {
  if (confidence >= 0.8) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
};

// Get confidence display color
const getConfidenceColor = (confidence: number, isManualOverride: boolean): string => {
  if (isManualOverride) return 'bg-blue-100 text-blue-800 border-blue-200';
  
  const level = getConfidenceLevel(confidence);
  switch (level) {
    case 'high':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'medium':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    case 'low':
      return 'bg-red-100 text-red-800 border-red-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

// Get confidence icon
const getConfidenceIcon = (confidence: number, isManualOverride: boolean) => {
  if (isManualOverride) {
    return <Globe className="h-3 w-3" />;
  }
  
  const level = getConfidenceLevel(confidence);
  switch (level) {
    case 'high':
      return <CheckCircle2 className="h-3 w-3" />;
    case 'medium':
      return <Signal className="h-3 w-3" />;
    case 'low':
      return <AlertTriangle className="h-3 w-3" />;
    default:
      return <Brain className="h-3 w-3" />;
  }
};

export function LanguageDetectionIndicator({
  detectedLanguage,
  confidence,
  isAutoDetecting,
  isManualOverride,
  className = ''
}: LanguageDetectionIndicatorProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  // If auto-detecting but no language detected yet
  if (isAutoDetecting && !detectedLanguage) {
    return (
      <div className={`flex items-center space-x-1 ${className}`}>
        <Badge variant="outline" className="bg-gray-50 text-gray-600 border-gray-300">
          <Brain className="h-3 w-3 mr-1 animate-pulse" />
          Detecting...
        </Badge>
      </div>
    );
  }

  // If no language detected and not auto-detecting
  if (!detectedLanguage) {
    return null;
  }

  const languageName = LANGUAGE_NAMES[detectedLanguage] || detectedLanguage;
  const confidenceLevel = getConfidenceLevel(confidence);
  const badgeColor = getConfidenceColor(confidence, isManualOverride);
  const icon = getConfidenceIcon(confidence, isManualOverride);

  const tooltipContent = isManualOverride 
    ? `Language manually set to ${languageName}`
    : `Auto-detected ${languageName} (${(confidence * 100).toFixed(0)}% confidence)`;

  return (
    <div className={`relative flex items-center space-x-1 ${className}`}>
      <div 
        className="flex items-center space-x-1"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <Badge 
          variant="outline" 
          className={`transition-colors duration-200 cursor-help ${badgeColor}`}
        >
          {icon}
          <span className="ml-1 text-xs font-medium">
            {languageName}
          </span>
          {!isManualOverride && (
            <span className="ml-1 text-xs opacity-75">
              ({(confidence * 100).toFixed(0)}%)
            </span>
          )}
        </Badge>
        
        {/* Status indicator */}
        {isAutoDetecting && (
          <Brain className="h-3 w-3 text-blue-500 animate-pulse" />
        )}
      </div>

      {/* Custom tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50">
          <div className="bg-gray-900 text-white text-xs rounded-md px-2 py-1 whitespace-nowrap shadow-lg">
            <div className="space-y-1">
              <p className="font-medium">{tooltipContent}</p>
              {!isManualOverride && (
                <div className="text-xs space-y-1 opacity-90">
                  <p>Confidence: {confidenceLevel} ({(confidence * 100).toFixed(1)}%)</p>
                  {confidenceLevel === 'low' && (
                    <p className="text-amber-300">Consider manual language selection for better accuracy</p>
                  )}
                </div>
              )}
            </div>
            {/* Tooltip arrow */}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
          </div>
        </div>
      )}
    </div>
  );
}