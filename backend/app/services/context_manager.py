# context_manager.py
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.domain.models import Message, ThreadAgent, ThreadParticipant
import logging

logger = logging.getLogger(__name__)

class ContextManager:
    def __init__(self, history_limit: int = 20):
        self.history_limit = history_limit

    async def get_conversation_context(
        self,
        db: AsyncSession,
        thread_id: UUID,
        exclude_message_id: Optional[UUID] = None
    ) -> str:
        """
        Get the conversation context for a thread, limited to the last N messages.
        
        Args:
            db: Database session
            thread_id: UUID of the thread
            exclude_message_id: Optional message ID to exclude (e.g., current message)
            
        Returns:
            Formatted string of conversation context
        """
        try:
            # Build query for last N messages
            query = (
                select(Message)
                .where(Message.thread_id == thread_id)
            )
            
            # Exclude specific message if provided
            if exclude_message_id:
                query = query.where(Message.id != exclude_message_id)
                
            # Order by creation time desc and limit
            query = (
                query
                .order_by(desc(Message.created_at))
                .limit(self.history_limit)
            )
            
            # Execute query
            result = await db.execute(query)
            messages = result.scalars().all()
            
            # Reverse messages to get chronological order
            messages = list(reversed(messages))
            
            # Format messages
            formatted_messages = []
            for msg in messages:
                # Determine sender
                if msg.agent_id:
                    # Agent message
                    sender = f"[{msg.message_metadata.get('agent_type', 'AGENT')} Agent]"
                else:
                    # Human message
                    sender = f"[{msg.message_metadata.get('participant_name', 'User')}]"
                
                # Format message
                formatted_msg = f"{sender} {msg.content}"
                formatted_messages.append(formatted_msg)
            
            return "\n".join(formatted_messages)
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return ""

    async def format_context_for_agent(
        self,
        db: AsyncSession,
        thread_id: UUID,
        current_message_id: Optional[UUID] = None
    ) -> str:
        """
        Get formatted conversation context ready for agent consumption.
        
        Args:
            db: Database session
            thread_id: UUID of the thread
            current_message_id: Optional ID of current message to exclude from context
            
        Returns:
            Formatted string containing conversation context
        """
        return await self.get_conversation_context(
            db,
            thread_id,
            exclude_message_id=current_message_id
        )

# Create singleton instance
context_manager = ContextManager()
