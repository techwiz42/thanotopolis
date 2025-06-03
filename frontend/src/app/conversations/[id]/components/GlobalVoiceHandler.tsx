import React, { useEffect, useRef, useState } from 'react';
import { useVoice } from '@/contexts/VoiceContext';
import { VoiceInput } from '@/components/voice/VoiceInput';
import { useToast } from '@/components/ui/use-toast';

interface GlobalVoiceHandlerProps {
  conversationId: string;
}

/**
 * GlobalVoiceHandler - A component that handles voice input for the entire conversation.
 * It activates automatically when voice input is enabled from the top controls.
 */
export const GlobalVoiceHandler: React.FC<GlobalVoiceHandlerProps> = ({ 
  conversationId 
}) => {
  const { inputEnabled } = useVoice();
  const { toast } = useToast();
  const messageInputRef = useRef<HTMLTextAreaElement | null>(null);
  const [transcriptionBuffer, setTranscriptionBuffer] = useState('');

  // Find the message input element whenever inputEnabled changes
  useEffect(() => {
    if (inputEnabled) {
      // Find the textarea in the message input component
      const textarea = document.querySelector('textarea[placeholder*="Type your message"]') as HTMLTextAreaElement;
      if (textarea) {
        messageInputRef.current = textarea;
        console.log('Found message input textarea:', textarea);
      } else {
        console.error('Could not find message input textarea');
      }
    }
  }, [inputEnabled]);

  // Handle transcriptions from the voice input component
  const handleTranscription = (text: string, isFinal: boolean) => {
    console.log('Global voice handler received transcription:', { text, isFinal });
    
    if (!messageInputRef.current) {
      console.warn('No message input reference available for transcription');
      return;
    }
    
    if (isFinal) {
      // Get the current input value
      const currentValue = messageInputRef.current.value;
      
      // Combine existing text with the final transcription
      const newValue = currentValue 
        ? `${currentValue.trim()} ${text}` 
        : text;
      
      // Set the value and trigger an input event to update React state
      messageInputRef.current.value = newValue;
      messageInputRef.current.dispatchEvent(new Event('input', { bubbles: true }));
      
      // Clear buffer
      setTranscriptionBuffer('');
      
      // Notify user
      toast({
        title: "Voice Input Complete",
        description: `Added: "${text}"`,
        duration: 2000
      });
    } else {
      // Store interim transcription in buffer
      setTranscriptionBuffer(text);
      
      // Show a visual indication in the textarea (optional)
      // This approach avoids modifying the actual input value for interim results
      // messageInputRef.current.style.backgroundColor = '#f0f9ff';
    }
  };

  // Handle voice status changes
  const handleStatusChange = (status: 'idle' | 'connecting' | 'recording' | 'error') => {
    console.log('Global voice handler status changed:', status);
    
    if (status === 'error') {
      toast({
        title: "Voice Input Error",
        description: "There was an issue with voice input. Please try again.",
        variant: "destructive"
      });
    }
  };

  // Only render the voice input component when voice input is enabled
  if (!inputEnabled) {
    return null;
  }

  return (
    <div style={{ display: 'none' }}>
      <VoiceInput 
        onTranscription={handleTranscription}
        onStatusChange={handleStatusChange}
        disabled={false}
      />
      
      {/* Hidden debug info */}
      <div data-debug="voice-handler" className="hidden">
        Voice Handler Active | Buffer: {transcriptionBuffer}
      </div>
    </div>
  );
};