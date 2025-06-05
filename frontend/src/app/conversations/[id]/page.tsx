// src/app/conversations/[id]/page.tsx - Voice-enabled version
'use client';

import React, { useCallback, useEffect, useState, useMemo, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, ChevronLeft, UserPlus } from 'lucide-react';

import MessageList from '@/app/conversations/[id]/components/MessageList';
import MessageInput from '@/app/conversations/[id]/components/MessageInput';
import VoiceControls from '@/app/conversations/[id]/components/VoiceControls';
import { TypingIndicator } from '@/app/conversations/[id]/components/TypingIndicator';
import { StreamingIndicator } from '@/app/conversations/[id]/components/StreamingIndicator';

import { useConversation } from '@/app/conversations/[id]/hooks/useConversation';
import { useWebSocket } from '@/app/conversations/[id]/hooks/useWebSocket';
import { useMessageLoader } from '@/app/conversations/[id]/hooks/useMessageLoader';
import { useScrollManager } from '@/app/conversations/[id]/hooks/useScrollManager';
import { useStreamingTokens } from '@/app/conversations/[id]/hooks/useStreamingTokens';
import { useVoice } from '@/app/conversations/[id]/hooks/useVoice';
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
  const { token, user } = useAuth();
  const { toast } = useToast();
  const conversationId = params.id as string;
  const [typingStates, setTypingStates] = useState<TypingState>({});
  const [hideAwaitingMessage, setHideAwaitingMessage] = useState<boolean>(false);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const [email, setEmail] = useState('');
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [pendingVoiceText, setPendingVoiceText] = useState('');
  
  // Streaming tokens handling
  const { streamingState, handleToken, resetStreamingForAgent } = useStreamingTokens();
  
  const messageQueueRef = useRef<Message[]>([]);
  const isProcessingRef = useRef(false);
  const awaitingInputTimeoutRef = useRef<NodeJS.Timeout>();
  const lastFinalTranscriptRef = useRef('');

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

  // Voice transcript handler
  const handleVoiceTranscript = useCallback((transcript: string, isFinal: boolean) => {
    if (isFinal && transcript.trim() && transcript !== lastFinalTranscriptRef.current) {
      // This is a final transcript, add it to the message input
      lastFinalTranscriptRef.current = transcript;
      setVoiceTranscript(prev => {
        const newTranscript = prev.trim() ? `${prev} ${transcript}` : transcript;
        return newTranscript;
      });
      setPendingVoiceText('');
    } else if (!isFinal) {
      // This is interim text, show it as pending
      setPendingVoiceText(transcript);
    }
  }, []);

  // Using the voice hook
  const {
    isSTTEnabled,
    isTTSEnabled,
    isSTTActive,
    isTTSActive,
    isSTTConnecting,
    toggleSTT,
    toggleTTS,
    speakText,
    stopSpeaking
  } = useVoice({
    conversationId,
    onTranscript: handleVoiceTranscript
  });
  
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

  // Cleanup pending TTS timeouts on unmount
  useEffect(() => {
    return () => {
      Object.values(pendingTTSRef.current).forEach(timeout => clearTimeout(timeout));
    };
  }, []);

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

  // Track completed agent messages for TTS
  const completedMessagesRef = useRef<Set<string>>(new Set());
  const pendingTTSRef = useRef<{ [messageId: string]: NodeJS.Timeout }>({}); 

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
        
        // Schedule TTS for agent messages after ensuring streaming is complete
        if (isTTSEnabled && message.content.trim() && message.id && !completedMessagesRef.current.has(message.id)) {
          // Clear any existing timeout for this message
          if (pendingTTSRef.current[message.id]) {
            clearTimeout(pendingTTSRef.current[message.id]);
          }
          
          // Wait a bit to ensure no more tokens are coming
          pendingTTSRef.current[message.id] = setTimeout(() => {
            // Check if streaming is still active for this agent
            const agentStreamingState = streamingState[message.sender.name || ''];
            const isStillStreaming = agentStreamingState?.active && agentStreamingState?.lastMessageId === message.id;
            
            if (!isStillStreaming && !completedMessagesRef.current.has(message.id)) {
              completedMessagesRef.current.add(message.id);
              speakText(message.content);
              
              // Clean up after a while to prevent memory leak
              setTimeout(() => {
                completedMessagesRef.current.delete(message.id);
              }, 60000); // Clean up after 1 minute
            }
            
            delete pendingTTSRef.current[message.id];
          }, 1500); // Wait 1.5 seconds to ensure streaming is complete
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
  }, [addMessage, resetStreamingForAgent, scrollToBottom, typingUsers.size, streamingState, isTTSEnabled, speakText]);

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
  const { sendMessage, sendTypingStatus, isConnected, connectionError, wsConnected } = useWebSocket(wsConfig);

  // Handle sending message with voice transcript
  const handleSendMessage = useCallback((content: string, metadata?: MessageMetadata) => {
    // Clear voice transcript when sending
    setVoiceTranscript('');
    setPendingVoiceText('');
    lastFinalTranscriptRef.current = '';
    
    sendMessage(content, metadata);
    requestAnimationFrame(() => scrollToBottom(true));
  }, [sendMessage, scrollToBottom]);

  // Compute disabled state
  const isMessageInputDisabled = useMemo(() => {
    const participantSession = participantStorage.getSession(conversationId);
    const hasAuth = !!token || !!participantSession;
    const hasIdentification = !!user?.email || !!participantSession?.email;
    
    return !isConnected || !hasAuth || !hasIdentification;
  }, [isConnected, token, user?.email, conversationId]);

  // Enhanced MessageList that passes TTS functionality
  const enhancedMessages = messages;

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
      {/* Header with title and voice controls */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{conversation.title}</h1>
        
        {/* Voice Controls */}
        <VoiceControls
          isSTTEnabled={isSTTEnabled}
          isTTSEnabled={isTTSEnabled}
          isSTTActive={isSTTActive}
          isTTSActive={isTTSActive}
          isSTTConnecting={isSTTConnecting}
          onToggleSTT={toggleSTT}
          onToggleTTS={toggleTTS}
          className="ml-4"
        />
      </div>
      
      {/* Navigation and participant management */}
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
      
      {/* Show connection status for debugging */}
      {connectionError && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
          <p className="text-sm text-yellow-800">
            Connection issue: {connectionError}
          </p>
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
                <MessageList 
                  messages={enhancedMessages} 
                  isTTSEnabled={isTTSEnabled}
                  onSpeakMessage={speakText}
                  isSpeaking={isTTSActive}
                />
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
                  onSendMessage={handleSendMessage}
                  onTypingStatus={sendTypingStatus}
                  disabled={isMessageInputDisabled}
                  conversationId={conversationId}
                  voiceTranscript={voiceTranscript + (pendingVoiceText ? ` ${pendingVoiceText}` : '')}
                  isVoiceActive={isSTTActive}
                />
                
                {/* Debug info for development */}
                {process.env.NODE_ENV === 'development' && (
                  <div className="mt-2 text-xs text-gray-400 space-y-1">
                    <div>WS: {wsConnected ? '✓' : '✗'} | Connected: {isConnected ? '✓' : '✗'} | Disabled: {isMessageInputDisabled ? '✓' : '✗'}</div>
                    <div>STT: {isSTTEnabled ? '✓' : '✗'} | TTS: {isTTSEnabled ? '✓' : '✗'} | Recording: {isSTTActive ? '✓' : '✗'} | Speaking: {isTTSActive ? '✓' : '✗'}</div>
                    {voiceTranscript && <div>Voice: "{voiceTranscript}"</div>}
                    {pendingVoiceText && <div>Pending: "{pendingVoiceText}"</div>}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
