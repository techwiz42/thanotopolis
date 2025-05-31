// src/app/conversations/[id]/components/MessageList.tsx
import React from 'react';
import MessageItem, { TypingIndicatorStyles } from '@/app/conversations/[id]/components/MessageItem';
import { Message } from '@/app/conversations/[id]/types/message.types';

interface MessageListProps {
  messages: Message[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const calculateResponseTime = (currentMessage: Message, previousMessage?: Message) => {
    if (!previousMessage || currentMessage.sender.type === 'user') return undefined;
    
    const current = new Date(currentMessage.timestamp).getTime();
    const previous = new Date(previousMessage.timestamp).getTime();
    const diffMs = current - previous;
    
    if (diffMs < 1000) return `${diffMs}ms`;
    if (diffMs < 60000) return `${(diffMs / 1000).toFixed(1)}s`;
    return `${Math.floor(diffMs / 60000)}m ${Math.floor((diffMs % 60000) / 1000)}s`;
  };

  return (
    <div className="p-4">
      <TypingIndicatorStyles />
      {messages.map((message, index) => (
        <MessageItem
          key={message.id}
          message={message}
          formatDate={formatDate}
          responseTime={calculateResponseTime(message, messages[index - 1])}
        />
      ))}
    </div>
  );
};

export default MessageList;
