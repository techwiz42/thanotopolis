// src/app/conversations/[id]/components/VoiceControls.tsx
import React from 'react';
import { Button } from '@/components/ui/button';
import { Mic, MicOff, Volume2, VolumeX, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VoiceControlsProps {
  isSTTEnabled: boolean;
  isTTSEnabled: boolean;
  isSTTActive: boolean;
  isTTSActive: boolean;
  isSTTConnecting: boolean;
  onToggleSTT: () => void;
  onToggleTTS: () => void;
  className?: string;
}

const VoiceControls: React.FC<VoiceControlsProps> = ({
  isSTTEnabled,
  isTTSEnabled,
  isSTTActive,
  isTTSActive,
  isSTTConnecting,
  onToggleSTT,
  onToggleTTS,
  className
}) => {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Speech-to-Text Control */}
      <Button
        variant={isSTTEnabled ? "default" : "outline"}
        size="sm"
        onClick={onToggleSTT}
        disabled={isSTTConnecting}
        className={cn(
          "relative",
          isSTTEnabled && "bg-orange-500 hover:bg-orange-600",
          (isSTTActive || isSTTEnabled) && "animate-pulse"
        )}
        title={isSTTEnabled ? "Disable Voice Input" : "Enable Voice Input"}
      >
        {isSTTConnecting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : isSTTEnabled ? (
          <Mic className="h-4 w-4" />
        ) : (
          <MicOff className="h-4 w-4" />
        )}
        {(isSTTActive || (isSTTEnabled && !isSTTConnecting)) && (
          <span className="absolute -top-1 -right-1 h-2 w-2 bg-orange-400 rounded-full animate-ping" />
        )}
      </Button>

      {/* Text-to-Speech Control */}
      <Button
        variant={isTTSEnabled ? "default" : "outline"}
        size="sm"
        onClick={onToggleTTS}
        className={cn(
          "relative",
          isTTSEnabled && "bg-blue-500 hover:bg-blue-600",
          isTTSActive && "animate-pulse"
        )}
        title={isTTSEnabled ? "Disable Voice Output" : "Enable Voice Output"}
      >
        {isTTSEnabled ? (
          <Volume2 className="h-4 w-4" />
        ) : (
          <VolumeX className="h-4 w-4" />
        )}
        {isTTSActive && (
          <span className="absolute -top-1 -right-1 h-2 w-2 bg-blue-400 rounded-full animate-ping" />
        )}
      </Button>

      {/* Status indicator */}
      <div className="text-xs text-gray-500">
        {isSTTEnabled && <span className="text-orange-500">●</span>}
        {isTTSEnabled && <span className="text-blue-500">●</span>}
        {!isSTTEnabled && !isTTSEnabled && <span className="text-gray-400">●</span>}
      </div>
    </div>
  );
};

export default VoiceControls;
