// src/app/conversations/[id]/components/TypingIndicator.tsx
import React from "react";
import { Loader2 } from "lucide-react";

interface TypingState {
  [identifier: string]: {
    isTyping: boolean;
    agentType?: string;
    name?: string;
    email?: string;
    isAgent: boolean;
  };
}

interface TypingIndicatorProps {
  typingStates: TypingState;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ typingStates }) => {
  const typingUsers = Object.entries(typingStates).filter(([, state]) => state.isTyping);
  
  if (typingUsers.length === 0) return null;

  return (
    <div className="flex flex-col gap-1 p-2 text-sm">
      {typingUsers.map(([identifier, state]) => (
        <div 
          key={identifier} 
          className={`flex items-center gap-2 ${state.isAgent ? 'text-green-600' : 'text-gray-500'}`}
        >
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className={state.isAgent ? 'font-medium' : ''}>
            {state.isAgent
              ? `${state.agentType} is responding...`
              : `${state.name || state.email || identifier} is typing...`}
          </span>
        </div>
      ))}
    </div>
  );
};