// src/app/conversations/[id]/page.tsx
'use client';

import React, { useCallback, useEffect, useState, useMemo, useRef } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, ChevronLeft, UserPlus } from 'lucide-react';

import MessageList from '@/app/conversations/[id]/components/MessageList';
import MessageInput from '@/app/conversations/[id]/components/MessageInput';
// These components now exist
import { TypingIndicator } from '@/app/conversations/[id]/components/TypingIndicator';
import { StreamingIndicator } from '@/app/conversations/[id]/components/StreamingIndicator';

// These hooks now exist
import { useConversation } from '@/app/conversations/[id]/hooks/useConversation';
import { useWebSocket } from '@/app/conversations/[id]/hooks/useWebSocket';
import { useMessageLoader } from '@/app/conversations/[id]/hooks/useMessageLoader';
import { useScrollManager } from '@/app/conversations/[id]/hooks/useScrollManager';
import { useStreamingTokens } from '@/app/conversations/[id]/hooks/useStreamingTokens';
import { Message, MessageMetadata } from '@/app/conversations/[id]/types/message.types';
import { TypingStatusMessage, TokenMessage } from '@/app/conversations/[id]/types/websocket.types';
import { participantStorage } from '@/lib/participantStorage';
import { useToast } from '@/components/ui/use-toast';
import { conversationService } from '@/services/conversations';

interface TypingState {
  [identifier: string]: {
    isTyping: boolean;
    agentType?: string;
    name?: string;
    email?: string;
    isAgent: boolean;
  };
}

export default function ConversationPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, user } = useAuth();
  const { toast } = useToast();
  const conversationId = params.id as string;
  const [typingStates, setTypingStates] = useState<TypingState>({});
  const [hideAwaitingMessage, setHideAwaitingMessage] = useState<boolean>(false);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const [email, setEmail] = useState('');
  const isPrivacyEnabled: boolean = searchParams.get('privacy') === 'true';
  
  // Streaming tokens handling
  const { streamingState, handleToken, resetStreamingForAgent } = useStreamingTokens();
  
  const messageQueueRef = useRef<Message[]>([]);
  const isProcessingRef = useRef(false);
  const awaitingInputTimeoutRef = useRef<NodeJS.Timeout>();

  // Using the conversation hook
  const { conversation, error, isLoading } = useConversation(conversationId, token);

  // Using the message loader hook
  const {
    messages,
    isLoading: messagesLoading,
    addMessage
  } = useMessageLoader({
    conversationId,
    token: token || ''
  });

  // Using the scroll manager hook
  const { 
    scrollContainerRef,
    messagesEndRef, 
    scrollToBottom
  } = useScrollManager(messages);
  
  // Auto-scroll when new streaming content arrives
  useEffect(() => {
    const hasActiveStreaming = Object.values(streamingState).some(state => state.active);
    if (hasActiveStreaming) {
      const timeoutId = setTimeout(() => {
        scrollToBottom(false);
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [streamingState, scrollToBottom]);

  useEffect(() => {
    const checkAuth = async () => {
      const participantSession = participantStorage.getSession(conversationId);
      const hasAuth = !!token || !!participantSession;
      if (!hasAuth) {
        router.replace('/login');
      }
    };

    checkAuth();
  }, [conversationId, token, router]);

  const handleAddParticipant = async () => {
    if (!email) {
      toast({
        title: "Invalid Email",
        description: "Please enter a valid email address",
        variant: "destructive"
      });
      return;
    }

    if (!token) {
      toast({
        title: "Authentication Error",
        description: "You must be logged in to add participants",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await conversationService.addParticipant(conversationId, { email }, token);
    
      toast({
        title: "Participant Management",
        description: response.message,
        variant: undefined
      });
    
      setEmail('');
    } catch (error) {
      toast({
        title: "Add Participant Error",
        description: error instanceof Error 
          ? error.message 
          : "Failed to add participant",
        variant: "destructive"
      });
    }
  };

  const handleMessage = useCallback((message: Message) => {
    if (!message.sender.is_owner) {
      setHideAwaitingMessage(true);
      if (awaitingInputTimeoutRef.current) {
        clearTimeout(awaitingInputTimeoutRef.current);
      }
      
      if (message.sender.type === 'agent' && message.sender.name) {
        if (message.sender.name.toLowerCase() === 'moderator') {
          Object.keys(streamingState).forEach(agent => {
            resetStreamingForAgent(agent, message.id);
          });
        } else {
          resetStreamingForAgent(message.sender.name, message.id);
        }
        
        setTimeout(() => {
          requestAnimationFrame(() => {
            scrollToBottom(true);
          });
        }, 150);
      }
    } else {
      if (typingUsers.size === 0) {
        setHideAwaitingMessage(false);
      }
    }
    
    messageQueueRef.current.push(message);
    if (!isProcessingRef.current) {
      isProcessingRef.current = true;
      requestAnimationFrame(() => {
        const messagesToAdd = [...messageQueueRef.current];
        messageQueueRef.current = [];
        isProcessingRef.current = false;
        
        messagesToAdd.forEach(msg => {
          addMessage(msg);
        });
        
        scrollToBottom(true);
      });
    }
  }, [addMessage, resetStreamingForAgent, scrollToBottom, typingUsers.size, streamingState]);

  const handleTypingStatus = useCallback((status: TypingStatusMessage) => {
    setTypingUsers(prev => {
      const next = new Set(prev);
      if (status.is_typing) {
        next.add(status.identifier);
        setHideAwaitingMessage(true);
      } else {
        next.delete(status.identifier);
        if (next.size === 0) {
          setHideAwaitingMessage(false);
        }
      }
      return next;
    });

    setTypingStates(prev => {
      const next = { ...prev };
      if (status.is_typing) {
        next[status.identifier] = {
          isTyping: true,
          agentType: status.agent_type,
          name: status.name,
          email: status.email,
          isAgent: !!status.agent_type
        };
      } else {
        delete next[status.identifier];
      }
      return next;
    });
  }, []);

  const handleTokenMessage = useCallback((tokenMessage: TokenMessage) => {
    if (tokenMessage.token) {
      handleToken(tokenMessage);
    }
  }, [handleToken]);

  const wsConfig = useMemo(() => ({
    conversationId,
    token,
    userId: user?.id,
    userEmail: user?.email,
    onMessage: handleMessage,
    onTypingStatus: handleTypingStatus,
    onToken: handleTokenMessage
  }), [conversationId, token, user?.id, user?.email, handleMessage, handleTypingStatus, handleTokenMessage]);

  // Using the websocket hook
  const { sendMessage, sendTypingStatus, isConnected } = useWebSocket(wsConfig);

  // Debug logging for MessageInput disabled state
  useEffect(() => {
    console.log('MessageInput Debug:', {
      isConnected,
      hasUser: !!user,
      userEmail: user?.email,
      hasParticipantSession: !!participantStorage.getSession(conversationId),
      participantSession: participantStorage.getSession(conversationId),
      isDisabled: !isConnected || (!user && !participantStorage.getSession(conversationId))
    });
  }, [isConnected, user, conversationId]);

  if (isLoading || messagesLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
        <span className="ml-2 text-gray-600">Loading conversation...</span>
      </div>
    );
  }

  if (error || !conversation) {
    return (
      <div className="text-red-500 py-8 text-center">
        {error || 'Conversation not found'}
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-4">
      {/* Optional: Show conversation title */}
      <h1 className="text-2xl font-semibold">{conversation.title}</h1>
      
      {conversation.owner_id === user?.id && (
        <div className="flex items-center space-x-4 w-full">
          <Button
            variant="outline"
            onClick={() => router.push('/conversations')}
            className="flex items-center"
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back to Conversations
          </Button>

          <div className="flex space-x-2 flex-grow">
            <Input
              type="email"
              placeholder="Enter participant email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-grow"
            />
            <Button onClick={handleAddParticipant}>
              <UserPlus className="mr-2 h-4 w-4" />
              Invite Participant
            </Button>
          </div>
        </div>
      )}
      
      <div className="h-[calc(100vh-200px)]">
        <Card className="h-full">
          <CardContent className="h-full p-0">
            <div className="flex flex-col h-full">
              <div
                ref={scrollContainerRef}
                className="flex-1 min-h-0 overflow-y-auto scroll-smooth"
              >
                <MessageList messages={messages} />
                <div ref={messagesEndRef} />
              </div>

              <div className="flex-shrink-0 p-4 border-t">
                {!hideAwaitingMessage && messages.length > 0 && (
                  <div className="text-sm text-gray-500 mb-2 flex items-center">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Awaiting input...
                  </div>
                )}

                <TypingIndicator typingStates={typingStates} />
                
                {Object.entries(streamingState).map(([agentType, state]) => (
                  state.active && (
                    <StreamingIndicator
                      key={agentType}
                      agentType={agentType}
                      streamingContent={state.tokens}
                      isActive={state.active}
                    />
                  )
                ))}
                
                <MessageInput
                  onSendMessage={(content: string, metadata?: MessageMetadata) => {
                    sendMessage(content, metadata);
                    requestAnimationFrame(() => scrollToBottom(true));
                  }}
                  onTypingStatus={sendTypingStatus}
                  disabled={!isConnected || (!user && !participantStorage.getSession(conversationId))}
                  conversationId={conversationId}
                  isPrivacyEnabled={isPrivacyEnabled}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
