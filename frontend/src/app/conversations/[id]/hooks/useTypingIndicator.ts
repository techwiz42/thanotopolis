// src/app/conversations/[id]/hooks/useTypingIndicator.ts
import { useState, useCallback } from 'react';
import { TypingStatusMessage } from '@/app/conversations/[id]/types/websocket.types';

interface UseTypingIndicatorReturn {
  typingUsers: Set<string>;
  handleTypingStatus: (message: TypingStatusMessage) => void;
}

export const useTypingIndicator = (): UseTypingIndicatorReturn => {
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());

  const handleTypingStatus = useCallback((message: TypingStatusMessage) => {
    setTypingUsers(currentUsers => {
      const nextUsers = new Set(currentUsers);
      if (message.is_typing) {
        nextUsers.add(message.identifier);
      } else {
        nextUsers.delete(message.identifier);
      }
      return nextUsers;
    });
  }, []);

  return {
    typingUsers,
    handleTypingStatus
  };
};