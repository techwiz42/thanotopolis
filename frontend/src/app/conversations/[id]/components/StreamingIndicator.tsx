// src/app/conversations/[id]/components/StreamingIndicator.tsx
import React, { useEffect, useRef, useMemo } from 'react';
import { formatAgentName } from './MessageItem';

interface StreamingIndicatorProps {
  agentType: string;
  streamingContent: string;
  isActive: boolean;
}

export const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({
  agentType,
  streamingContent,
  isActive
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll the streaming indicator container (not the main message area)
  useEffect(() => {
    if (containerRef.current && isActive) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [streamingContent, isActive]);

  // Clean and format the streaming content
  const cleanedContent = useMemo(() => {
    return streamingContent
      // Remove agent status indicators
      .replace(/\[\w+ is thinking\.\.\.\]/g, '')
      .replace(/\[\w+ has completed\]/g, '')
      .replace(/\[Synthesizing collaborative response\.\.\.\]/g, '')
      .replace(/\[TIMEOUT\]/g, '')
      .replace(/\[ERROR\]/g, '')
      .replace(/\[DONE\]/g, '')
      .replace(/\[END\]/g, '')
      .replace(/\[AGENT_COMPLETE\]/g, '')
      // Clean up excessive newlines
      .replace(/\n{3,}/g, '\n\n')
      // Trim whitespace
      .trim();
  }, [streamingContent]);
  
  // If no streaming is happening, don't render anything
  if (!streamingContent && !isActive) {
    return null;
  }

  // Check if content contains timeout or error message
  const isErrorState = streamingContent.includes('[TIMEOUT]') || 
                        streamingContent.includes('[ERROR]') ||
                        streamingContent.includes('took too long to respond');

  const getAvatarColor = (name: string) => {
    // Use red for error states
    if (isErrorState) {
      return 'bg-red-500';
    }
    
    const colors = ['bg-red-500', 'bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500'];
    const index = name.charCodeAt(0) % colors.length;
    return colors[index]; 
  };

  const displayName = formatAgentName(agentType);
  const initial = displayName[0];

  return (
    <div className="flex justify-start mb-4">
      <div className="rounded-lg px-4 py-3 max-w-[70%] relative text-sm bg-green-300 text-gray-900 border border-blue-300 flex flex-col">
        <div className="flex items-center gap-2 mb-1">
          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-white font-bold ${getAvatarColor(agentType)}`}>
            {initial}
          </div>
          <span className="font-medium text-xs">
            {displayName}
          </span>
          {isErrorState ? (
            <span className="text-xs text-red-600 ml-1">
              timed out
            </span>
          ) : isActive && (
            <span className="text-xs text-blue-600 ml-1 animate-pulse">
              streaming...
            </span>
          )}
        </div>
        
        <div 
          ref={containerRef}
          className="whitespace-pre-wrap break-words text-sm streaming-content"
        >
          {cleanedContent}
          {isActive && (
            <span className="typing-indicator inline-block ml-1">
              <span className="dot bg-black"></span>
              <span className="dot bg-black"></span>
              <span className="dot bg-black"></span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};