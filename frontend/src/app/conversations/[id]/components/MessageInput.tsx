// src/app/conversations/[id]/components/MessageInput.tsx
import React, { useState, useCallback, useEffect, useRef, ChangeEvent, DragEvent } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send, Paperclip, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useVoice } from '@/contexts/VoiceContext';
import { api } from '@/services/api';
import { useToast } from '@/components/ui/use-toast';
import { MessageMetadata } from '@/app/conversations/[id]/types/message.types';
// No longer need to import VoiceInput since it's handled at the page level

export interface MessageInputProps {
  onSendMessage: (message: string, metadata?: MessageMetadata) => void;
  onTypingStatus?: (isTyping: boolean) => void;
  disabled?: boolean;
  conversationId: string;
}

const MessageInput: React.FC<MessageInputProps> = ({ 
  onSendMessage,
  onTypingStatus,
  disabled = false,
  conversationId
}: MessageInputProps) => {
  const [message, setMessage] = useState('');
  const [messageMetadata, setMessageMetadata] = useState<MessageMetadata | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isVoiceInput, setIsVoiceInput] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'connecting' | 'recording' | 'error'>('idle');
  
  const typingTimeoutRef = useRef<NodeJS.Timeout>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { token, user } = useAuth();
  const { inputEnabled } = useVoice();
  const { toast } = useToast();

  // Debug logging
  useEffect(() => {
    console.log('MessageInput - Voice input enabled globally:', inputEnabled);
    console.log('MessageInput - Token available:', !!token);
    console.log('MessageInput - Component disabled:', disabled);
    
    if (inputEnabled) {
      // Add a CSS class to indicate voice input is enabled globally
      textareaRef.current?.classList.add('voice-enabled');
    } else {
      textareaRef.current?.classList.remove('voice-enabled');
    }
  }, [inputEnabled, token, disabled]);

  const processFile = async (file: File) => {
    if (!file) return;

    try {
        console.log('Processing file:', {
            name: file.name,
            size: file.size,
            type: file.type
        });

        setIsProcessingFile(true);

        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post<{ 
            text: string; 
            metadata: { 
                filename: string; 
                mime_type: string; 
                size: number;
                text_length?: number;
                chunk_count?: number;
            } 
        }>('/parse-document', formData, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        console.log('File processing response:', response.data);

        // Prepare message metadata
        const fileMetadata: MessageMetadata = {
            filename: response.data.metadata.filename,
            mime_type: response.data.metadata.mime_type,
            size: response.data.metadata.size,
            text_length: response.data.metadata.text_length,
            chunk_count: response.data.metadata.chunk_count,
            is_file: true
        };

        // Format the file content with simple text display
        const formattedFileContent = `File: ${response.data.metadata.filename}\n\n${response.data.text}`;

        // Combine existing message with file content if there is a message
        const finalMessage = message.trim() 
            ? `${message.trim()}\n\n${formattedFileContent}`
            : formattedFileContent;

        // Send message with metadata and clear input
        onSendMessage(finalMessage, fileMetadata);
        setMessage('');
        setMessageMetadata(null);

        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }

        toast({
            title: "File Processed",
            description: `Successfully processed ${response.data.metadata.filename}`,
            variant: "default"
        });

    } catch (error) {
        console.error('Error processing file:', error);
        toast({
            title: "Error Processing File",
            description: error instanceof Error ? error.message : "Failed to process the file",
            variant: "destructive"
        });
    } finally {
        setIsProcessingFile(false);
        setIsDragging(false);
    }
};

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (disabled) {
      setIsDragging(false);
      return;
    }

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await processFile(files[0]); // Process only the first file
    }
    setIsDragging(false);
  };

  const handleSend = useCallback(() => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage) return;

    console.log('Sending message:', trimmedMessage);

    // Send message with existing metadata if any
    onSendMessage(trimmedMessage, messageMetadata || undefined);
    
    setMessage('');
    setMessageMetadata(null);
    setInterimTranscript('');
    
    if (onTypingStatus && isTyping) {
      setIsTyping(false);
      onTypingStatus(false);
    }
  }, [message, messageMetadata, onSendMessage, onTypingStatus, isTyping]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const updateTypingStatus = useCallback((isCurrentlyTyping: boolean) => {
    if (isTyping !== isCurrentlyTyping) {
      setIsTyping(isCurrentlyTyping);
      if (onTypingStatus) {
        onTypingStatus(isCurrentlyTyping);
      }
    }
  }, [isTyping, onTypingStatus]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newMessage = e.target.value;
    setMessage(newMessage);
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    if (newMessage.length > 0) {
      updateTypingStatus(true);
      typingTimeoutRef.current = setTimeout(() => {
        updateTypingStatus(false);
      }, 2000);
    } else {
      updateTypingStatus(false);
    }
  }, [updateTypingStatus]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  // Handle voice transcription
  const handleVoiceTranscription = useCallback((text: string, isFinal: boolean) => {
    console.log('Voice transcription received:', { text, isFinal });
    
    if (isFinal) {
      // Final transcription - add to message
      const currentText = message.trim();
      const newText = currentText ? `${currentText} ${text}` : text;
      console.log('Setting final message:', newText);
      setMessage(newText);
      setInterimTranscript('');
      setIsVoiceInput(false);
      
      // Focus textarea after voice input
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
      
      toast({
        title: "Voice Input Complete",
        description: `Transcribed: "${text}"`,
        duration: 2000
      });
    } else {
      // Interim transcription - show as preview
      console.log('Setting interim transcript:', text);
      setInterimTranscript(text);
      setIsVoiceInput(true);
    }
  }, [message, toast]);

  // Handle voice input status changes
  const handleVoiceStatusChange = useCallback((status: 'idle' | 'connecting' | 'recording' | 'error') => {
    console.log('Voice status changed:', status);
    setVoiceStatus(status);
    
    if (status === 'recording') {
      updateTypingStatus(true);
      setIsVoiceInput(true);
    } else if (status === 'idle') {
      updateTypingStatus(false);
      setIsVoiceInput(false);
      setInterimTranscript('');
    } else if (status === 'error') {
      setIsVoiceInput(false);
      setInterimTranscript('');
      toast({
        title: "Voice Input Error",
        description: "There was an issue with voice input. Please try again.",
        variant: "destructive"
      });
    }
  }, [updateTypingStatus, toast]);

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  // Combine message text with interim transcript for display
  const displayText = isVoiceInput && interimTranscript ? 
    `${message}${message ? ' ' : ''}${interimTranscript}` : 
    message;

  // Show voice status indicator
  const getVoiceStatusText = () => {
    switch (voiceStatus) {
      case 'connecting': return 'Connecting to voice service...';
      case 'recording': return 'Listening...';
      case 'error': return 'Voice input error';
      default: return '';
    }
  };

  return (
    <div className="flex flex-col gap-2">
      {/* Debug info in development */}
      {process.env.NODE_ENV === 'development' && (
        <div className="text-xs text-gray-400 bg-gray-50 p-2 rounded">
          Voice Debug: Enabled={inputEnabled ? 'Y' : 'N'} | Status={voiceStatus} | Token={token ? 'Y' : 'N'}
        </div>
      )}

      {/* Main input section */}
      <div 
        className={`flex gap-2 relative ${isDragging ? 'drop-target' : ''}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {isDragging && (
          <div className="absolute inset-0 bg-blue-50 border-2 border-dashed border-blue-300 rounded-lg z-10 flex items-center justify-center">
            <div className="text-blue-500 font-medium">Drop file here to upload</div>
          </div>
        )}
        
        <Textarea
          ref={textareaRef}
          value={displayText}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled 
              ? "Message input temporarily unavailable" 
              : voiceStatus === 'recording'
              ? "Listening... (speak now)"
              : "Type your message or use voice input..."
          }
          className={`flex-grow min-h-[80px] max-h-[200px] resize-none pr-32 pl-4 ${
            inputEnabled ? 'voice-enabled border-green-200' : ''
          } ${isVoiceInput ? 'border-green-300 bg-green-50' : ''}`}
          disabled={disabled}
        />
        
        {/* Button controls */}
        <div className="absolute right-12 bottom-2 flex items-center gap-2">
          {/* File upload button */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            style={{ display: 'none' }}
            aria-label="Upload file"
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isProcessingFile}
            className="p-2 hover:bg-gray-100 rounded-full"
          >
            {isProcessingFile ? (
              <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
            ) : (
              <Paperclip className="h-4 w-4 text-gray-500" />
            )}
          </Button>
        </div>
        
        {/* Send button */}
        <Button 
          onClick={handleSend}
          disabled={!message.trim() || disabled}
          className="absolute bottom-2 right-2"
          size="sm"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>

      {/* Voice status indicators */}
      {voiceStatus !== 'idle' && (
        <div className={`text-sm px-3 py-1 rounded border ${
          voiceStatus === 'recording' ? 'text-green-600 bg-green-50 border-green-200' :
          voiceStatus === 'connecting' ? 'text-blue-600 bg-blue-50 border-blue-200' :
          voiceStatus === 'error' ? 'text-red-600 bg-red-50 border-red-200' :
          'text-gray-600 bg-gray-50 border-gray-200'
        }`}>
          <span className="font-medium">{getVoiceStatusText()}</span>
          {voiceStatus === 'recording' && (
            <span className="ml-2 inline-block w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
          )}
        </div>
      )}

      {/* Interim transcript display */}
      {isVoiceInput && interimTranscript && (
        <div className="text-sm text-green-600 bg-green-50 px-3 py-1 rounded border border-green-200">
          <span className="font-medium">Transcribing:</span> "{interimTranscript}"
        </div>
      )}

      <style jsx global>{`
        .drop-target {
          position: relative;
        }
        
        .drop-target::after {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: 0.5rem;
          pointer-events: none;
          z-index: 10;
        }
        
        .voice-enabled {
          border-color: #86efac;
          background-color: #f0fdf4;
        }
        
        .voice-enabled::placeholder {
          color: #059669;
        }
      `}</style>
    </div>
  );
};

export default MessageInput;
