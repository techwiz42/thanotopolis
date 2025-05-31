// src/app/conversations/[id]/hooks/useScrollManager.ts
'use client';

import { useRef, useCallback, useEffect } from 'react';
import { Message } from '../types/message.types';

interface UseScrollManagerReturn {
    scrollContainerRef: React.RefObject<HTMLDivElement>;
    messagesEndRef: React.RefObject<HTMLDivElement>;
    handleNewMessage: () => void;
    scrollToBottom: (force?: boolean) => void;
    initialScrollComplete: boolean;
}

export const useScrollManager = (messages: Message[]): UseScrollManagerReturn => {
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const lastMessageCountRef = useRef(0);
    const isScrollingRef = useRef(false);
    const initialScrollRef = useRef(false);

    const scrollToBottom = useCallback((force: boolean = false) => {
        if (!scrollContainerRef.current) return;
        
        if (isScrollingRef.current && !force) return;
        
        // Add a check for user interaction - don't auto-scroll if user is scrolled up
        const scrollContainer = scrollContainerRef.current;
        const isScrolledUp = scrollContainer.scrollTop < 
            (scrollContainer.scrollHeight - scrollContainer.clientHeight - 100);
        
        // If user has manually scrolled up and this is not a forced scroll, don't scroll to bottom
        if (isScrolledUp && !force) return;
        
        isScrollingRef.current = true;
        
        const performScroll = () => {
            if (!scrollContainer) return;
            
            const scrollTarget = scrollContainer.scrollHeight;
            
            scrollContainer.scrollTo({
                top: scrollTarget,
                behavior: force ? "auto" : 'smooth'
            });

            setTimeout(() => {
                if (!scrollContainer) return;
                const currentScroll = scrollContainer.scrollTop;
                const maxScroll = scrollContainer.scrollHeight - scrollContainer.clientHeight;
                
                if (Math.abs(currentScroll - maxScroll) > 2) {
                    scrollContainer.scrollTo({
                        top: scrollContainer.scrollHeight,
                        behavior: 'auto'
                    });
                }
                
                isScrollingRef.current = false;
            }, 300);
        };

        requestAnimationFrame(performScroll);
    }, []);

    useEffect(() => {
        if (messages.length > 0 && !initialScrollRef.current) {
            const timer = setTimeout(() => {
                scrollToBottom(true);
                initialScrollRef.current = true;
            }, 150);
            
            return () => clearTimeout(timer);
        }
    }, [messages, scrollToBottom]);

    useEffect(() => {
        const currentCount = messages.length;
        if (currentCount > lastMessageCountRef.current) {
            lastMessageCountRef.current = currentCount;
            scrollToBottom(true);
        }
    }, [messages, scrollToBottom]);

    return {
        scrollContainerRef,
        messagesEndRef,
        handleNewMessage: () => scrollToBottom(true),
        scrollToBottom: () => scrollToBottom(true),
        initialScrollComplete: initialScrollRef.current
    };
};
