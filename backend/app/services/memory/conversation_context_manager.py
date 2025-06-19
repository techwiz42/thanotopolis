import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ConversationContextManager:
    """
    Manages conversation context for agents, including token counting,
    formatting, and summarization.
    """
    
    def __init__(self, max_tokens: int = 4000):
        """
        Initialize the conversation context manager.
        
        Args:
            max_tokens: Maximum number of tokens to include in context
        """
        self.max_tokens = max_tokens
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Approximate token count
        """
        # Simple approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    async def format_conversation_context(
        self,
        messages: List[Dict[str, Any]],
        summarize_if_needed: bool = True
    ) -> str:
        """
        Format conversation messages into context for the agent.
        
        Args:
            messages: List of conversation messages
            summarize_if_needed: Whether to summarize if over token limit
            
        Returns:
            Formatted context string
        """
        if not messages:
            return "CONVERSATION HISTORY:\nNo previous messages."
        
        # Format messages into context string
        context_parts = ["CONVERSATION HISTORY:"]
        
        for msg in messages:
            # Format timestamp
            timestamp = msg.get('created_at')
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    timestamp_str = timestamp
            elif isinstance(timestamp, datetime):
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp_str = "Unknown time"
            
            # Format sender
            if msg.get('agent_type'):
                sender = f"[{msg['agent_type']}]"
            elif msg.get('user_id') and msg.get('user'):
                user = msg['user']
                first_name = user.get('first_name', '').strip()
                last_name = user.get('last_name', '').strip()
                full_name = f"{first_name} {last_name}".strip()
                if full_name:
                    sender = f"[{full_name}]"
                else:
                    sender = f"[USER: {user.get('username', 'unknown')}]"
            else:
                sender = "[USER]"
            
            # Format content
            content = msg.get('content', '')
            
            # Combine into formatted message
            formatted_msg = f"{sender} ({timestamp_str}): {content}"
            context_parts.append(formatted_msg)
        
        # Join into full context
        context = "\n".join(context_parts)
        
        # Check token count
        token_count = self.count_tokens(context)
        logger.info(f"Context token count: {token_count} (limit: {self.max_tokens})")
        
        # Summarize if needed
        if summarize_if_needed and token_count > self.max_tokens:
            summary = await self._summarize_messages(messages[:-10])  # Summarize all but last 10 messages
            recent_context = await self.format_conversation_context(messages[-10:], summarize_if_needed=False)
            
            # Combine summary with recent messages
            context = f"SUMMARY OF EARLIER CONVERSATION:\n{summary}\n\nRECENT CONVERSATION HISTORY:\n{recent_context.replace('CONVERSATION HISTORY:', '')}"
        
        return context
    
    async def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Summarize older messages to reduce context size.
        
        Args:
            messages: List of messages to summarize
            
        Returns:
            Summary string
        """
        # In a real implementation, this would use LLM to generate a summary
        # For now, return a simple summary based on message count and topics
        
        if not messages:
            return "No previous conversation."
        
        message_count = len(messages)
        
        # Extract users involved
        users = set()
        agents = set()
        topics = set()
        
        # Simple keyword extraction for topics
        keywords = ["funeral", "arrangement", "service", "burial", "cremation", 
                   "memorial", "grief", "support", "planning", "cost"]
        
        for msg in messages:
            if msg.get('agent_type'):
                agents.add(msg['agent_type'])
            elif msg.get('user') and msg['user'].get('username'):
                users.add(msg['user'].get('username'))
            
            # Simple keyword matching for topics
            content = msg.get('content', '').lower()
            for keyword in keywords:
                if keyword in content:
                    topics.add(keyword)
        
        # Format summary
        user_str = ", ".join(users) if users else "a user"
        agent_str = ", ".join(agents) if agents else "an assistant"
        topic_str = ", ".join(topics) if topics else "various topics"
        
        summary = f"A conversation between {user_str} and {agent_str} with {message_count} messages. "
        summary += f"The conversation covered topics including: {topic_str}."
        
        return summary