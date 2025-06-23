// src/app/conversations/[id]/hooks/useWebSocket.ts
import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { websocketService } from '@/services/websocket';
import { Message, MessageMetadata } from '../types/message.types';
import { WebSocketMessage, TypingStatusMessage, TokenMessage } from '../types/websocket.types';
import { participantStorage } from '@/lib/participantStorage';

interface UseWebSocketProps {
    conversationId: string;
    token: string | null;
    userId: string | undefined;
    userEmail: string | undefined;
    onMessage: (message: Message) => void;
    onTypingStatus: (status: TypingStatusMessage) => void;
    onToken: (token: TokenMessage) => void;
}

export const useWebSocket = ({
    conversationId,
    token,
    userId,
    userEmail,
    onMessage,
    onTypingStatus,
    onToken
}: UseWebSocketProps) => {
    const [wsConnected, setWsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);
    const mountedRef = useRef(true);
    const unsubscribeRef = useRef<(() => void) | null>(null);
    const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const retryCountRef = useRef(0);
    const maxRetries = 3;
    const connectingRef = useRef(false);
    const connectedConversationRef = useRef<string | null>(null);
    const lastParticipationStatusRef = useRef<string>('');

    const connect = useCallback(async () => {
        if (!mountedRef.current) return;
        
        // Prevent multiple simultaneous connection attempts
        if (connectingRef.current) {
            console.log('Connection already in progress, skipping...');
            return;
        }
        
        // Check if already connected to this conversation
        if (websocketService.isConnected && connectedConversationRef.current === conversationId) {
            console.log('Already connected to this conversation via service');
            setWsConnected(true);
            return;
        }
        
        connectingRef.current = true;

        try {
            console.log('=== WebSocket Connection Attempt ===');
            console.log('Conversation ID:', conversationId);
            console.log('Has Token:', !!token);
            console.log('User ID:', userId);
            console.log('User Email:', userEmail);

            const participantSession = participantStorage.getSession(conversationId);
            console.log('Participant session:', participantSession);

            // Determine connection credentials
            const connectionToken = participantSession?.token || token;
            const connectionId = participantSession?.email || userId || userEmail || token;

            console.log('Connection Token Available:', !!connectionToken);
            console.log('Connection ID Available:', !!connectionId);

            if (!connectionToken || !connectionId) {
                const error = 'No valid connection credentials found';
                console.error(error);
                setConnectionError(error);
                setWsConnected(false);
                return;
            }

            // Clear any previous errors
            setConnectionError(null);

            await websocketService.connect(
                conversationId,
                connectionToken,
                connectionId
            );

            if (mountedRef.current) {
                setWsConnected(true);
                connectedConversationRef.current = conversationId;
                retryCountRef.current = 0; // Reset retry count on successful connection
                console.log('WebSocket connected successfully');

                const unsubscribe = websocketService.subscribe((message: WebSocketMessage) => {
                    if (!mountedRef.current) return;

                    console.log('WebSocket message received:', message.type, message);

                    switch (message.type) {
                        case 'message': {
                            // Preserve HTML content from agents
                            const messageContent = message.content;

                            // If this is from DOCUMENTSEARCH agent and contains HTML, make sure it's preserved
                            if (message.agent_type === 'DOCUMENTSEARCH' && /<[a-z][\s\S]*>/i.test(message.content)) {
                                console.log('Preserving HTML format in document search message');
                                // Ensure no accidental markdown-style links
                                // This ensures the backend HTML is preserved exactly as-is
                            }

                            const transformedMessage: Message = {
                                id: message.id || crypto.randomUUID(),
                                content: messageContent,
                                sender: {
                                    identifier: message.identifier,
                                    is_owner: message.is_owner || false,
                                    name: message.agent_type || message.sender_name || message.name || '',
                                    email: message.email || '',
                                    type: message.sender_type === 'agent' || message.agent_type ? 'agent' : 'user',
                                    message_metadata: message.agent_metadata || message.message_metadata || undefined
                                },
                                timestamp: message.timestamp,
                                message_metadata: message.agent_metadata || message.message_metadata || undefined,
                                agent_type: message.agent_type,  // Add agent_type to top level for easier access
                                is_history: message.is_history
                            };
                            onMessage(transformedMessage);
                            break;
                        }
                        case 'typing_status': {
                            onTypingStatus(message);
                            break;
                        }
                        case 'token': {
                            if (onToken) {
                                onToken(message);
                            }
                            break;
                        }
                    }
                });

                unsubscribeRef.current = unsubscribe;
            }
        } catch (error) {
            console.error('WebSocket connection error:', error);
            setConnectionError(error instanceof Error ? error.message : 'Connection failed');
            setWsConnected(false);
            connectedConversationRef.current = null;

            // Retry logic with exponential backoff
            if (retryCountRef.current < maxRetries && mountedRef.current) {
                retryCountRef.current++;
                const retryDelay = Math.pow(2, retryCountRef.current) * 1000; // 2s, 4s, 8s
                console.log(`Retrying connection in ${retryDelay}ms (attempt ${retryCountRef.current}/${maxRetries})`);
                
                retryTimeoutRef.current = setTimeout(() => {
                    if (mountedRef.current) {
                        connect();
                    }
                }, retryDelay);
            }
        } finally {
            connectingRef.current = false;
        }
    }, [conversationId, token, userId, userEmail, onMessage, onTypingStatus, onToken]);

    const sendMessage = useCallback((
        content: string, 
        messageMetadata?: MessageMetadata
    ) => {
        console.log('useWebSocket sendMessage FULL CONTEXT:', {
            content,
            messageMetadata,
            contentType: typeof content,
            metadataType: typeof messageMetadata,
            metadataKeys: messageMetadata ? Object.keys(messageMetadata) : null,
            metadataStringified: JSON.stringify(messageMetadata),
            wsConnected,
            isServiceConnected: websocketService.isConnected
        });

        if (!websocketService.isConnected) {
            console.error('Cannot send message: WebSocket not connected');
            // Try to reconnect if not connected
            if (!wsConnected) {
                console.log('Attempting to reconnect...');
                connect();
            }
            return;
        }

        const participantSession = participantStorage.getSession(conversationId);
        const senderEmail = userEmail || participantSession?.email;

        if (!senderEmail) {
            console.error('No sender email available');
            return;
        }

        try {
            console.log('Sending message with details:', {
                content,
                senderEmail,
                messageMetadata,
                isParticipant: !!participantSession
            });

            websocketService.sendMessage(
                content, 
                senderEmail, 
                messageMetadata
            );
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }, [conversationId, userEmail, wsConnected, connect]);

    const sendTypingStatus = useCallback((isTyping: boolean) => {
        if (!websocketService.isConnected) {
            console.error('Cannot send typing status: WebSocket not connected');
            return;
        }

        const participantSession = participantStorage.getSession(conversationId);
        const senderEmail = userEmail || participantSession?.email;

        if (!senderEmail) {
            console.error('No sender email available for typing status');
            return;
        }

        try {
            websocketService.sendTypingStatus(isTyping, senderEmail);
        } catch (error) {
            console.error('Error sending typing status:', error);
        }
    }, [conversationId, userEmail]);

    useEffect(() => {
        mountedRef.current = true;
        
        // Only connect if we have the necessary credentials
        if (conversationId && (token || participantStorage.getSession(conversationId))) {
            connect();
        }

        return () => {
            mountedRef.current = false;
            connectingRef.current = false;
            connectedConversationRef.current = null;
            if (retryTimeoutRef.current) {
                clearTimeout(retryTimeoutRef.current);
            }
            if (unsubscribeRef.current) {
                unsubscribeRef.current();
                unsubscribeRef.current = null;
            }
            // Disconnect the websocket when component unmounts
            websocketService.disconnect();
        };
    }, [conversationId]); // Remove connect from dependencies to prevent loops

    // Enhanced participation check - memoized to prevent excessive logging
    const isAllowedToParticipate = useMemo(() => {
        // Check if we have valid authentication
        const hasValidAuth = !!token || !!participantStorage.getSession(conversationId);
        
        // Check if we have user identification
        const hasUserIdentification = !!userEmail || !!participantStorage.isParticipant(conversationId);
        
        const result = wsConnected && hasValidAuth && hasUserIdentification;
        
        // Only log when participation status actually changes
        const currentStatus = `${wsConnected}-${hasValidAuth}-${hasUserIdentification}`;
        if (currentStatus !== lastParticipationStatusRef.current) {
            console.log('=== Participation Status Changed ===');
            console.log('WebSocket Connected:', wsConnected);
            console.log('Has Valid Auth:', hasValidAuth);
            console.log('Has User Identification:', hasUserIdentification);
            console.log('Connection Error:', connectionError);
            console.log('Can Participate:', result);
            lastParticipationStatusRef.current = currentStatus;
        }
        
        return result;
    }, [wsConnected, token, userEmail, conversationId, connectionError]);

    // Debug logging - only when connection state changes significantly
    useEffect(() => {
        if (connectionError || !wsConnected) {
            const debugInfo = {
                wsConnected,
                hasToken: !!token,
                hasUserId: !!userId,
                hasUserEmail: !!userEmail,
                hasParticipantSession: !!participantStorage.getSession(conversationId),
                connectionError,
                canParticipate: isAllowedToParticipate,
                websocketServiceConnected: websocketService.isConnected
            };
            
            console.log('=== WebSocket Connection Debug ===', debugInfo);
        }
    }, [wsConnected, connectionError, isAllowedToParticipate, conversationId]);

    return {
        sendMessage,
        sendTypingStatus,
        isConnected: isAllowedToParticipate,
        connectionError,
        wsConnected
    };
};
