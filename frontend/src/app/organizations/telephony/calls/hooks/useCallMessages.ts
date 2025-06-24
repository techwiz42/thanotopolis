import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { telephonyService, CallMessage } from '@/services/telephony';
import { useToast } from '@/components/ui/use-toast';

interface UseCallMessagesProps {
  callId: string;
  autoLoad?: boolean;
}

export function useCallMessages({ callId, autoLoad = true }: UseCallMessagesProps) {
  const { token } = useAuth();
  const { toast } = useToast();
  
  const [messages, setMessages] = useState<CallMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load messages
  const loadMessages = useCallback(async () => {
    if (!token || !callId) return;

    try {
      setIsLoading(true);
      setError(null);
      
      const callMessages = await telephonyService.getCallMessages(callId, token);
      setMessages(callMessages);
      
    } catch (error: any) {
      console.error('Error loading call messages:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to load call messages';
      setError(errorMessage);
      
      // Only show toast if this isn't a "not found" error (API might not exist yet)
      if (error.response?.status !== 404) {
        toast({
          title: "Error Loading Messages",
          description: errorMessage,
          variant: "destructive"
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [token, callId, toast]);

  // Add message
  const addMessage = useCallback(async (
    message: Omit<CallMessage, 'id' | 'call_id' | 'created_at'>
  ): Promise<CallMessage | null> => {
    if (!token || !callId) return null;

    try {
      const newMessage = await telephonyService.addCallMessage(callId, message, token);
      setMessages(prev => [...prev, newMessage].sort((a, b) => 
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      ));
      return newMessage;
    } catch (error: any) {
      console.error('Error adding call message:', error);
      toast({
        title: "Error Adding Message",
        description: error.response?.data?.detail || 'Failed to add message',
        variant: "destructive"
      });
      return null;
    }
  }, [token, callId, toast]);

  // Update message
  const updateMessage = useCallback(async (
    messageId: string,
    updates: Partial<Pick<CallMessage, 'content' | 'metadata'>>
  ): Promise<CallMessage | null> => {
    if (!token || !callId) return null;

    try {
      const updatedMessage = await telephonyService.updateCallMessage(callId, messageId, updates, token);
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? updatedMessage : msg
      ));
      return updatedMessage;
    } catch (error: any) {
      console.error('Error updating call message:', error);
      toast({
        title: "Error Updating Message",
        description: error.response?.data?.detail || 'Failed to update message',
        variant: "destructive"
      });
      return null;
    }
  }, [token, callId, toast]);

  // Delete message
  const deleteMessage = useCallback(async (messageId: string): Promise<boolean> => {
    if (!token || !callId) return false;

    try {
      await telephonyService.deleteCallMessage(callId, messageId, token);
      setMessages(prev => prev.filter(msg => msg.id !== messageId));
      return true;
    } catch (error: any) {
      console.error('Error deleting call message:', error);
      toast({
        title: "Error Deleting Message",
        description: error.response?.data?.detail || 'Failed to delete message',
        variant: "destructive"
      });
      return false;
    }
  }, [token, callId, toast]);

  // Auto-load messages on mount
  useEffect(() => {
    if (autoLoad) {
      loadMessages();
    }
  }, [loadMessages, autoLoad]);

  // Utility getters
  const sortedMessages = telephonyService.sortMessagesByTimestamp(messages);
  const messagesByType = telephonyService.groupMessagesByType(messages);
  const transcriptMessages = messages.filter(msg => msg.message_type === 'transcript');
  const systemMessages = messages.filter(msg => msg.message_type === 'system');
  const summaryMessage = messages.find(msg => msg.message_type === 'summary');
  const noteMessages = messages.filter(msg => msg.message_type === 'note');

  return {
    // State
    messages,
    sortedMessages,
    messagesByType,
    transcriptMessages,
    systemMessages,
    summaryMessage,
    noteMessages,
    isLoading,
    error,
    
    // Actions
    loadMessages,
    addMessage,
    updateMessage,
    deleteMessage,
    
    // Utilities
    getTranscript: () => telephonyService.getCallTranscript(messages),
    getSummary: () => telephonyService.getCallSummary(messages),
    hasMessages: messages.length > 0
  };
}