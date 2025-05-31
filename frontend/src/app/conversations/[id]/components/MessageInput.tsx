// src/app/conversations/[id]/components/MessageInput.tsx
import React, { useState, useCallback, useEffect, useRef, ChangeEvent, DragEvent } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send, EyeOff, Paperclip, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';
import { useToast } from '@/components/ui/use-toast';
import { MessageMetadata } from '@/app/conversations/[id]/types/message.types';

export interface MessageInputProps {
  onSendMessage: (message: string, metadata?: MessageMetadata) => void;
  onTypingStatus?: (isTyping: boolean) => void;
  disabled?: boolean;
  conversationId: string;
  isPrivacyEnabled?: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({ 
  onSendMessage,
  onTypingStatus,
  disabled = false,
  conversationId,
  isPrivacyEnabled
}: MessageInputProps) => {
  const [message, setMessage] = useState('');
  const [messageMetadata, setMessageMetadata] = useState<MessageMetadata | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
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
            is_file: true  // Add this flag to indicate it's a file
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

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="flex flex-col gap-2">
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
          value={message}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Message input temporarily unavailable" : "Type your message..."}
          className="flex-grow min-h-[80px] max-h-[200px] resize-none pr-24 pl-4"
          disabled={disabled}
        />
        <div className="absolute right-12 bottom-2 flex items-center gap-2">
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
          {isPrivacyEnabled && (
            <div className="bg-purple-100 p-2 rounded-full">
              <EyeOff className="h-4 w-4 text-purple-600" />
            </div>
          )}
        </div>
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
