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
import { LanguageSelector } from '@/app/conversations/[id]/components/LanguageSelector';
import { LanguageDetectionIndicator } from '@/app/conversations/[id]/components/LanguageDetectionIndicator';
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
  
  // Initialize language from localStorage or default to en-US
  const [selectedLanguage, setSelectedLanguage] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('stt-language') || 'en-US';
    }
    return 'en-US';
  });
  
  // Save language preference to localStorage when it changes
  const handleLanguageChange = useCallback((language: string) => {
    console.log('Language change requested:', language);
    setSelectedLanguage(language);
    if (typeof window !== 'undefined') {
      localStorage.setItem('stt-language', language);
    }
    
    // Restore focus to message input after language change
    setTimeout(() => {
      // More specific selector for the message input textarea
      const messageInput = document.querySelector('textarea[data-testid="message-input"], textarea') as HTMLTextAreaElement;
      if (messageInput) {
        messageInput.focus();
        // Ensure cursor is at the end if there's existing text
        const length = messageInput.value.length;
        messageInput.setSelectionRange(length, length);
      }
    }, 150); // Slightly longer delay to ensure STT restart is complete
  }, []);

  // Handle auto-detected language updates
  const handleLanguageAutoUpdate = useCallback((detectedLanguage: string) => {
    console.log('Auto-updating language to:', detectedLanguage);
    handleLanguageChange(detectedLanguage);
  }, [handleLanguageChange]);
  
  // Streaming tokens handling
  const { streamingState, handleToken, resetStreamingForAgent } = useStreamingTokens();
  
  const messageQueueRef = useRef<Message[]>([]);
  const isProcessingRef = useRef(false);
  const awaitingInputTimeoutRef = useRef<NodeJS.Timeout>();
  const pendingTTSRef = useRef<{ [key: string]: NodeJS.Timeout }>({});

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

  // Track accumulated transcript across utterances
  const accumulatedTranscriptRef = useRef<string>('');
  const lastFinalTranscriptRef = useRef<string>('');
  const lastInterimTranscriptRef = useRef<string>('');

  // Voice transcript handler - Accumulate utterances across speech sessions
  const handleVoiceTranscript = useCallback((transcript: string, isFinal: boolean, speechFinal?: boolean) => {
    console.log('=== Transcript Event ===', { 
      transcript: transcript.substring(0, 50) + '...', // Log first 50 chars
      isFinal, 
      speechFinal,
      timestamp: new Date().toISOString(),
      accumulated: accumulatedTranscriptRef.current.substring(0, 30) + '...'
    });
    
    if (!transcript.trim()) {
      return; // Skip empty transcripts
    }
    
    if (speechFinal && isFinal) {
      // Speech is final - this utterance is complete, add to accumulated text
      console.log('Speech final - adding to accumulated transcript');
      
      // Add this utterance to the accumulated transcript with proper spacing
      const currentAccumulated = accumulatedTranscriptRef.current.trim();
      const newTranscript = transcript.trim();
      
      if (currentAccumulated && !currentAccumulated.endsWith('.') && !currentAccumulated.endsWith('!') && !currentAccumulated.endsWith('?')) {
        // Add punctuation if missing
        accumulatedTranscriptRef.current = currentAccumulated + '. ' + newTranscript;
      } else if (currentAccumulated) {
        // Just add space
        accumulatedTranscriptRef.current = currentAccumulated + ' ' + newTranscript;
      } else {
        // First utterance
        accumulatedTranscriptRef.current = newTranscript;
      }
      
      lastFinalTranscriptRef.current = '';
      lastInterimTranscriptRef.current = '';
      setVoiceTranscript(accumulatedTranscriptRef.current);
      setPendingVoiceText('');
      
      console.log('Accumulated transcript now:', accumulatedTranscriptRef.current);
    } else if (isFinal) {
      // Final but not speech final - update current utterance  
      console.log('Final transcript (not speech final)');
      
      // Only update if different from last final
      if (transcript !== lastFinalTranscriptRef.current) {
        lastFinalTranscriptRef.current = transcript;
        
        // Show accumulated transcript plus this final utterance
        const currentAccumulated = accumulatedTranscriptRef.current.trim();
        const displayText = currentAccumulated ? 
          (currentAccumulated + (currentAccumulated.endsWith('.') || currentAccumulated.endsWith('!') || currentAccumulated.endsWith('?') ? ' ' : '. ') + transcript) :
          transcript;
        
        setVoiceTranscript(displayText);
        setPendingVoiceText('');
      }
    } else {
      // Interim transcript - show accumulated plus current interim
      if (transcript !== lastInterimTranscriptRef.current) {
        lastInterimTranscriptRef.current = transcript;
        
        // Show as pending text (will be combined on display)
        setPendingVoiceText(transcript);
      }
    }
  }, []); // No dependencies to avoid stale closures

  // Handle final voice transcript from MessageInput
  const handleVoiceTranscriptFinal = useCallback((finalTranscript: string) => {
    console.log('[ConversationPage] handleVoiceTranscriptFinal called with:', finalTranscript);
    
    // Clear the voice transcript state since it's now been committed to the message
    setVoiceTranscript('');
    setPendingVoiceText('');
    // Reset transcript tracking refs
    accumulatedTranscriptRef.current = '';
    lastFinalTranscriptRef.current = '';
    lastInterimTranscriptRef.current = '';
    
    console.log('[ConversationPage] Voice transcript state cleared');
  }, []);

  // Using the voice hook
  const {
    isSTTEnabled,
    isTTSEnabled,
    isSTTActive,
    isTTSActive,
    isSTTConnecting,
    detectedLanguage,
    languageConfidence,
    isAutoDetecting,
    isManualOverride,
    toggleSTT,
    toggleTTS,
    speakText,
    stopSpeaking,
    currentAudio,
    setManualOverride
  } = useVoice({
    conversationId,
    onTranscript: handleVoiceTranscript,
    languageCode: selectedLanguage,
    onLanguageAutoUpdate: handleLanguageAutoUpdate
  });
  
  // Use refs to avoid stale closure issues with TTS
  const currentTTSEnabledRef = useRef(isTTSEnabled);
  const currentSpeakTextRef = useRef(speakText);

  // Update refs when values change
  useEffect(() => {
    currentTTSEnabledRef.current = isTTSEnabled;
    currentSpeakTextRef.current = speakText;
    
    // Clear completed messages when TTS is disabled to allow future auto-play
    if (!isTTSEnabled) {
      completedMessagesRef.current.clear();
    }
  }, [isTTSEnabled, speakText]);
  
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

  // Track completed agent messages for TTS to prevent duplicates
  const completedMessagesRef = useRef<Set<string>>(new Set());

  // Handle NEW WebSocket messages (includes TTS for new agent responses)
  const handleNewWebSocketMessage = useCallback((message: Message) => {
    // Use refs to get current TTS state - avoid stale closure
    const currentTTSEnabled = currentTTSEnabledRef.current;
    const currentSpeakTextFn = currentSpeakTextRef.current;
    
    // Handle message processing

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
        
        // Handle TTS for NEW agent messages only (only for WebSocket messages)
        if (currentTTSEnabled && message.content.trim() && message.id) {
          // Only speak if we haven't spoken this message before
          if (!completedMessagesRef.current.has(message.id)) {
            // Mark as completed immediately to prevent duplicates
            completedMessagesRef.current.add(message.id);
            
            // Cancel any existing TTS timeout for this message
            if (pendingTTSRef.current[message.id]) {
              clearTimeout(pendingTTSRef.current[message.id]);
            }
            
            // Wait a moment for streaming to complete, then speak
            pendingTTSRef.current[message.id] = setTimeout(() => {
              // Double-check TTS is still enabled and we haven't already started playing
              if (currentTTSEnabledRef.current && !currentAudio) {
                currentSpeakTextFn(message.content);
              }
              // Clean up the timeout reference
              delete pendingTTSRef.current[message.id];
            }, 800);
            
            // Clean up after a minute
            setTimeout(() => completedMessagesRef.current.delete(message.id), 60000);
          }
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
    
    // Add message to display
    addMessage(message);
    scrollToBottom(true);
  }, [addMessage, resetStreamingForAgent, scrollToBottom, typingUsers.size, streamingState]);

  // Handle ALL messages (used for initial load and WebSocket) - NO TTS logic here
  const handleMessage = useCallback((message: Message) => {
    // Just add the message without TTS processing - this is used for initial load
    addMessage(message);
  }, [addMessage]);

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
    onMessage: handleNewWebSocketMessage, // Use the WebSocket-specific handler with TTS
    onTypingStatus: handleTypingStatus,
    onToken: handleTokenMessage
  }), [conversationId, token, user?.id, user?.email, handleNewWebSocketMessage, handleTypingStatus, handleTokenMessage]);

  // Using the websocket hook
  const { sendMessage, sendTypingStatus, isConnected, connectionError, wsConnected } = useWebSocket(wsConfig);

  // Handle sending message with voice transcript
  const handleSendMessage = useCallback((content: string, metadata?: MessageMetadata) => {
    // Clear voice transcript when sending
    setVoiceTranscript('');
    setPendingVoiceText('');
    // Reset transcript tracking refs
    accumulatedTranscriptRef.current = '';
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
        
        <div className="flex items-center space-x-4">
          {/* Language Detection Indicator - Always visible when STT is enabled */}
          {isSTTEnabled && (
            <LanguageDetectionIndicator
              detectedLanguage={detectedLanguage}
              confidence={languageConfidence}
              isAutoDetecting={isAutoDetecting}
              isManualOverride={isManualOverride}
            />
          )}
          
          {/* Language Selector - Only visible when STT is enabled */}
          {isSTTEnabled && (
            <LanguageSelector
              value={selectedLanguage}
              onChange={handleLanguageChange}
              disabled={false}
              isAutoDetected={!isManualOverride && !!detectedLanguage}
              detectedLanguage={detectedLanguage}
              onManualOverride={setManualOverride}
            />
          )}
          
          {/* Voice Controls */}
          <VoiceControls
            isSTTEnabled={isSTTEnabled}
            isTTSEnabled={isTTSEnabled}
            isSTTActive={isSTTActive}
            isTTSActive={isTTSActive}
            isSTTConnecting={isSTTConnecting}
            onToggleSTT={toggleSTT}
            onToggleTTS={toggleTTS}
          />
        </div>
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
                  onVoiceTranscriptFinal={handleVoiceTranscriptFinal}
                  isSTTEnabled={isSTTEnabled}
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
