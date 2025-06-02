import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Mic, Volume2, VolumeX } from 'lucide-react';
import { useVoice } from '@/contexts/VoiceContext';
import { useToast } from '@/components/ui/use-toast';

interface VoiceControlsProps {
  className?: string;
}

export const VoiceControls: React.FC<VoiceControlsProps> = ({ 
  className = '' 
}) => {
  const { 
    inputEnabled, 
    setInputEnabled, 
    outputEnabled, 
    setOutputEnabled 
  } = useVoice();
  const { toast } = useToast();

  const [serviceStatus, setServiceStatus] = useState<{
    stt: { available: boolean; error?: string };
    tts: { available: boolean; error?: string };
  }>({
    stt: { available: true },
    tts: { available: true }
  });

  const toggleInputEnabled = () => {
    if (!serviceStatus.stt.available && !inputEnabled) {
      toast({
        title: "Voice Input Unavailable",
        description: serviceStatus.stt.error || "Voice input service is currently unavailable",
        variant: "destructive"
      });
      return;
    }
    
    setInputEnabled(!inputEnabled);
    toast({
      title: `Voice Input ${!inputEnabled ? 'Enabled' : 'Disabled'}`,
      description: !inputEnabled 
        ? "You can now use your microphone for voice input" 
        : "Voice input has been disabled",
      variant: "default"
    });
  };

  const toggleOutputEnabled = () => {
    if (!serviceStatus.tts.available && !outputEnabled) {
      toast({
        title: "Voice Output Unavailable",
        description: serviceStatus.tts.error || "Voice output service is currently unavailable",
        variant: "destructive"
      });
      return;
    }
    
    setOutputEnabled(!outputEnabled);
    toast({
      title: `Voice Output ${!outputEnabled ? 'Enabled' : 'Disabled'}`,
      description: !outputEnabled 
        ? "Agent responses can now be spoken aloud" 
        : "Voice output has been disabled",
      variant: "default"
    });
  };

  // Check service status on component mount
  useEffect(() => {
    // This could be expanded to actually check service status with API calls
    // For now, we're assuming services are available
  }, []);

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <Button
        onClick={toggleInputEnabled}
        variant={inputEnabled ? "default" : "outline"}
        size="sm"
        className={`flex items-center gap-1 ${
          inputEnabled 
            ? "bg-green-600 hover:bg-green-700 text-white font-medium shadow-md border-green-700 ring-2 ring-green-300"
            : ""
        }`}
        title={inputEnabled ? "Disable voice input" : "Enable voice input"}
      >
        <Mic className={`h-4 w-4 ${inputEnabled ? "text-white" : ""}`} />
        {inputEnabled ? "Voice Input ON" : "Voice Input Off"}
      </Button>
      
      <Button
        onClick={toggleOutputEnabled}
        variant={outputEnabled ? "default" : "outline"}
        size="sm"
        className={`flex items-center gap-1 ${
          outputEnabled 
            ? "bg-green-600 hover:bg-green-700 text-white font-medium shadow-md border-green-700 ring-2 ring-green-300" 
            : ""
        }`}
        title={outputEnabled ? "Disable voice output" : "Enable voice output"}
      >
        {outputEnabled ? (
          <>
            <Volume2 className="h-4 w-4 text-white" />
            Voice Output ON
          </>
        ) : (
          <>
            <VolumeX className="h-4 w-4" />
            Voice Output Off
          </>
        )}
      </Button>
    </div>
  );
};

export default VoiceControls;