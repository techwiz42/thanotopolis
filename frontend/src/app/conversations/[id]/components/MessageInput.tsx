// src/app/conversations/[id]/components/MessageInput.tsx
import React, { useState, useCallback, useEffect, useRef, ChangeEvent, DragEvent } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send, Paperclip, Loader2, Mic } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';
import { useToast } from '@/components/ui/use-toast';
import { MessageMetadata } from '@/app/conversations/[id]/types/message.types';
import { VoiceInput } from '@/components/voice/VoiceInput';

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
  const [showVoiceInput, setShowVoiceInput] = useState(false);
  const [voiceInputStatus, setVoiceInputStatus] = useState<'idle' | 'connecting' | 'recording' | 'error'>('idle');
  const [interimTranscript, setInterimTranscript] = useState('');
  
  const typingTimeoutRef = useRef<NodeJS.Timeout>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { token, user } = useAuth();
  const { toast } = useToast();

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
    if (isFinal) {
      // Add the finalized transcription to the message
      const currentText = message.trim();
      const newText = currentText 
        ? `${currentText} ${text}` 
        : text;
      
      setMessage(newText);
      setInterimTranscript('');
      
      // Update typing status
      updateTypingStatus(true);
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      typingTimeoutRef.current = setTimeout(() => {
        updateTypingStatus(false);
      }, 2000);
      
    } else {
      // Show interim transcription
      setInterimTranscript(text);
    }
  }, [message, updateTypingStatus]);

  // Handle voice input status changes
  const handleVoiceStatusChange = useCallback((status: 'idle' | 'connecting' | 'recording' | 'error') => {
    setVoiceInputStatus(status);
    
    // Auto-hide voice input when recording stops
    if (status === 'idle' && showVoiceInput) {
      const timer = setTimeout(() => {
        setShowVoiceInput(false);
      }, 2000);
      
      return () => clearTimeout(timer);
    }
  }, [showVoiceInput]);

  // Toggle voice input visibility
  const toggleVoiceInput = useCallback(() => {
    setShowVoiceInput(!showVoiceInput);
    if (!showVoiceInput) {
      setInterimTranscript('');
    }
  }, [showVoiceInput]);

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  // Calculate the display text (including interim transcription)
  const displayText = interimTranscript 
    ? `${message}${message && !message.endsWith(' ') ? ' ' : ''}${interimTranscript}`
    : message;

  const getVoiceButtonColor = () => {
    if (disabled) return 'text-gray-400';
    if (voiceInputStatus === 'error') return 'text-red-500';
    if (voiceInputStatus === 'recording') return 'text-red-500';
    if (voiceInputStatus === 'connecting') return 'text-yellow-500';
    if (showVoiceInput) return 'text-blue-500';
    return 'text-gray-500';
  };

  return (
    <div className="flex flex-col gap-2">
      {/* Voice input section */}
      {showVoiceInput && (
        <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-3">
            <VoiceInput
              onTranscription={handleVoiceTranscription}
              onStatusChange={handleVoiceStatusChange}
              disabled={disabled}
            />
            <div className="flex flex-col">
              <span className="text-sm font-medium">
                {voiceInputStatus === 'idle' && 'Voice Input Ready'}
                {voiceInputStatus === 'connecting' && 'Connecting...'}
                {voiceInputStatus === 'recording' && 'Listening...'}
                {voiceInputStatus === 'error' && 'Voice Input Error'}
              </span>
              {interimTranscript && (
                <span className="text-xs text-gray-600 italic">
                  "{interimTranscript}"
                </span>
              )}
            </div>
          </div>
          <Button
            onClick={toggleVoiceInput}
            variant="ghost"
            size="sm"
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </Button>
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
              : showVoiceInput 
                ? "Type or speak your message..."
                : "Type your message..."
          }
          className={`flex-grow min-h-[80px] max-h-[200px] resize-none pr-24 pl-4 ${
            interimTranscript ? 'text-gray-700' : ''
          }`}
          disabled={disabled}
        />
        
        {/* Button controls */}
        <div className="absolute right-12 bottom-2 flex items-center gap-2">
          {/* Voice input toggle button */}
          <Button
            onClick={toggleVoiceInput}
            variant="ghost"
            size="sm"
            disabled={disabled}
            className={`p-2 hover:bg-gray-100 rounded-full ${getVoiceButtonColor()}`}
            title={showVoiceInput ? "Hide voice input" : "Show voice input"}
          >
            <Mic className={`h-4 w-4 ${voiceInputStatus === 'recording' ? 'animate-pulse' : ''}`} />
          </Button>
          
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
      `}</style>
    </div>
  );
};

export default MessageInput;
