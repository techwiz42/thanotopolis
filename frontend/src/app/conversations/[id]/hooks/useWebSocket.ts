// src/app/conversations/[id]/hooks/useWebSocket.ts
import { useState, useCallback, useEffect, useRef } from 'react';
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
    const mountedRef = useRef(true);
    const unsubscribeRef = useRef<(() => void) | null>(null);

const connect = useCallback(async () => {
    if (!mountedRef.current) return;

    try {
        const participantSession = participantStorage.getSession(conversationId);
        console.log('Participant session:', participantSession);

        const connectionToken = participantSession?.token || token;
        const connectionId = participantSession?.email || userId || token;

        if (!connectionToken || !connectionId) {
            console.error('No valid connection credentials found');
            return;
        }

        await websocketService.connect(
            conversationId,
            connectionToken,
            connectionId
        );

        if (mountedRef.current) {
            setWsConnected(true);
            console.log('WebSocket connected successfully');

            const unsubscribe = websocketService.subscribe((message: WebSocketMessage) => {
                if (!mountedRef.current) return;

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
                                name: message.agent_type || message.name || '',
                                email: message.email || '',
                                type: message.agent_type ? 'agent' : 'user',
                                message_metadata: message.message_metadata || undefined
                            },
                            timestamp: message.timestamp,
                            message_metadata: message.message_metadata || undefined,
                            agent_type: message.agent_type  // Add agent_type to top level for easier access
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
        setWsConnected(false);
    }
}, [conversationId, token, userId, onMessage, onTypingStatus, onToken]);

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
        metadataStringified: JSON.stringify(messageMetadata)
    });

        if (!websocketService.isConnected) {
            console.error('Cannot send message: WebSocket not connected');
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
    }, [conversationId, userEmail]);

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
        connect();

        return () => {
            mountedRef.current = false;
            if (unsubscribeRef.current) {
                unsubscribeRef.current();
            }
        };
    }, [connect]);

    const isAllowedToParticipate = useCallback(() => {
        return wsConnected && (
            userEmail || 
            participantStorage.isParticipant(conversationId)
        );
    }, [wsConnected, userEmail, conversationId]);

    return {
        sendMessage,
        sendTypingStatus,
        isConnected: isAllowedToParticipate()
    };
};