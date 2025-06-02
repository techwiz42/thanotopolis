# app/core/buffer_manager.py

import asyncio
import logging
from typing import Dict, Optional, List, Any
from uuid import UUID
from datetime import datetime, timedelta
import json
import tiktoken
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

class ConversationBuffer:
    """Manages conversation context with automatic summarization"""
    
    def __init__(self, conversation_id: UUID, max_tokens: int = 20000):
        self.conversation_id = conversation_id
        self.max_tokens = max_tokens
        self.messages: List[Dict[str, Any]] = []
        self.summary: Optional[str] = None
        self.last_updated = datetime.utcnow()
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self._lock = asyncio.Lock()
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback estimate: roughly 4 characters per token
            return len(text) // 4
        
    def add_message(
        self, 
        message: str, 
        sender_id: str, 
        sender_type: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a message to the buffer"""
        msg_data = {
            "content": message,
            "sender_id": sender_id,
            "sender_type": sender_type,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.messages.append(msg_data)
        self.last_updated = datetime.utcnow()
        
        # Check if we need to summarize (async)
        asyncio.create_task(self._check_and_summarize())
        
    async def _check_and_summarize(self):
        """Check if buffer needs summarization"""
        async with self._lock:
            try:
                current_context = self.get_formatted_context()
                token_count = self.count_tokens(current_context)
                
                if token_count > self.max_tokens:
                    await self._summarize_older_messages()
            except Exception as e:
                logger.error(f"Error checking buffer size: {e}")
    
    async def _summarize_older_messages(self):
        """Summarize older messages to keep buffer size manageable"""
        if len(self.messages) <= 20:  # Don't summarize if we have few messages
            return
            
        try:
            # Keep last 20 messages, summarize the rest
            messages_to_summarize = self.messages[:-20]
            recent_messages = self.messages[-20:]
            
            if not messages_to_summarize:
                return
                
            # Create summary of older messages
            summary_text = await self._create_summary(messages_to_summarize)
            
            # Update buffer with summary + recent messages
            self.summary = summary_text
            self.messages = recent_messages
            
            logger.info(f"Summarized {len(messages_to_summarize)} older messages for conversation {self.conversation_id}")
            
        except Exception as e:
            logger.error(f"Error summarizing buffer: {e}")
    
    async def _create_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Create summary of messages"""
        try:
            from openai import AsyncOpenAI
            from app.core.config import settings
            
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Format messages for summarization
            formatted_messages = []
            for msg in messages:
                sender_type = msg['sender_type']
                sender_id = msg['sender_id']
                content = msg['content']
                
                if sender_type == 'agent':
                    formatted_messages.append(f"[{sender_id}]: {content}")
                elif sender_type == 'user':
                    formatted_messages.append(f"[USER]: {content}")
                else:
                    formatted_messages.append(f"[{sender_type.upper()}]: {content}")
            
            conversation_text = "\n".join(formatted_messages)
            
            summary_prompt = f"""Summarize this conversation segment, preserving key information for context:

{conversation_text}

Focus on:
- Main topics and themes discussed
- Important decisions or outcomes
- Agent responses and recommendations
- Any ongoing issues or follow-ups needed
- Essential context for continuing the conversation

Provide a concise but comprehensive summary."""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a conversation summarizer. Preserve essential context while being concise."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error creating summary: {e}")
            return f"[Summary of {len(messages)} messages - details unavailable due to error]"
    
    def get_formatted_context(self) -> str:
        """Get formatted conversation context"""
        context_parts = []
        
        # Add summary if it exists
        if self.summary:
            context_parts.append("CONVERSATION SUMMARY:")
            context_parts.append(self.summary)
            context_parts.append("\nRECENT CONVERSATION:")
        else:
            context_parts.append("CONVERSATION HISTORY:")
        
        # Add recent messages
        for msg in self.messages:
            sender_type = msg['sender_type']
            sender_id = msg['sender_id']
            content = msg['content']
            timestamp = msg['timestamp']
            
            if sender_type == 'agent':
                line = f"[{timestamp}] [{sender_id}]: {content}"
            elif sender_type == 'user':
                line = f"[{timestamp}] [USER]: {content}"
            else:
                line = f"[{timestamp}] [{sender_type.upper()}]: {content}"
                
            context_parts.append(line)
        
        return "\n".join(context_parts)
    
    async def load_from_database(self, db: Any):
        """Load conversation history from database"""
        async with self._lock:
            try:
                from app.models.models import Message, User, Participant
                
                # Query for all messages
                query = (
                    select(Message)
                    .options(
                        selectinload(Message.user),
                        selectinload(Message.participant)
                    )
                    .where(Message.conversation_id == self.conversation_id)
                    .order_by(Message.created_at)
                )

                result = await db.execute(query)
                messages = result.scalars().all()
                
                # Convert to buffer format
                self.messages = []
                for msg in messages:
                    sender_type = "system"
                    sender_id = "system"
                    
                    # Parse additional_data for metadata
                    metadata = {}
                    if msg.additional_data:
                        try:
                            if isinstance(msg.additional_data, str):
                                metadata = json.loads(msg.additional_data)
                            else:
                                metadata = msg.additional_data
                        except:
                            pass
                    
                    if msg.agent_type:
                        sender_type = "agent"
                        sender_id = msg.agent_type
                    elif msg.user_id:
                        sender_type = "user"
                        if msg.user:
                            sender_id = f"{msg.user.first_name} {msg.user.last_name}".strip() or msg.user.username
                        else:
                            sender_id = "user"
                    elif msg.participant_id:
                        sender_type = "participant"
                        if msg.participant:
                            sender_id = msg.participant.name or msg.participant.identifier
                        else:
                            sender_id = "participant"
                    
                    msg_data = {
                        "content": msg.content,
                        "sender_id": sender_id,
                        "sender_type": sender_type,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat(),
                        "metadata": metadata
                    }
                    self.messages.append(msg_data)
                
                # Check if we need to summarize immediately
                await self._check_and_summarize()
                
                logger.info(f"Loaded {len(messages)} messages from database for conversation {self.conversation_id}")
                
            except Exception as e:
                logger.error(f"Error loading from database: {e}")
                logger.error(f"Traceback: {e.__traceback__}")

class BufferManager:
    """Buffer manager with automatic context management and summarization"""
    
    def __init__(self, max_tokens: int = 20000, cleanup_interval: int = 3600):
        self.buffers: Dict[UUID, ConversationBuffer] = {}
        self.max_tokens = max_tokens
        self.cleanup_interval = cleanup_interval
        self._cleanup_task = None
        self._lock = asyncio.Lock()
        
        # Start cleanup task
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start periodic cleanup of old buffers"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodically clean up old buffers"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_buffers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in buffer cleanup: {e}")
    
    async def _cleanup_old_buffers(self):
        """Remove buffers that haven't been used recently"""
        cutoff_time = datetime.utcnow() - timedelta(hours=6)
        
        async with self._lock:
            to_remove = []
            for conv_id, buffer in self.buffers.items():
                if buffer.last_updated < cutoff_time:
                    to_remove.append(conv_id)
            
            for conv_id in to_remove:
                del self.buffers[conv_id]
                logger.info(f"Cleaned up buffer for conversation {conv_id}")
    
    async def get_or_create_buffer(
        self, 
        conversation_id: UUID, 
        db: Optional[Any] = None
    ) -> ConversationBuffer:
        """Get existing buffer or create new one"""
        async with self._lock:
            if conversation_id not in self.buffers:
                buffer = ConversationBuffer(conversation_id, self.max_tokens)
                
                # Load from database if available
                if db:
                    await buffer.load_from_database(db)
                
                self.buffers[conversation_id] = buffer
                logger.info(f"Created new buffer for conversation {conversation_id}")
            
            return self.buffers[conversation_id]
    
    async def add_message(
        self,
        conversation_id: UUID,
        message: str,
        sender_id: str,
        sender_type: str,
        owner_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None
    ):
        """Add message to conversation buffer"""
        try:
            buffer = await self.get_or_create_buffer(conversation_id, db)
            buffer.add_message(message, sender_id, sender_type, metadata)
            
            logger.debug(f"Added message to buffer for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error adding message to buffer: {e}")
    
    async def get_context(
        self, 
        conversation_id: UUID, 
        db: Optional[Any] = None
    ) -> Optional[str]:
        """Get formatted conversation context"""
        try:
            buffer = await self.get_or_create_buffer(conversation_id, db)
            return buffer.get_formatted_context()
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return None
    
    async def resume_conversation(
        self,
        conversation_id: UUID,
        db: Any
    ) -> Optional[str]:
        """Resume a conversation by loading full history and creating proper context"""
        try:
            # Create new buffer and load from database
            buffer = ConversationBuffer(conversation_id, self.max_tokens)
            await buffer.load_from_database(db)
            
            # Store in our buffers
            async with self._lock:
                self.buffers[conversation_id] = buffer
            
            context = buffer.get_formatted_context()
            logger.info(f"Resumed conversation {conversation_id} with {len(buffer.messages)} messages")
            
            return context
            
        except Exception as e:
            logger.error(f"Error resuming conversation {conversation_id}: {e}")
            return None
    
    async def clear_conversation(self, conversation_id: UUID):
        """Clear a conversation from the buffer"""
        async with self._lock:
            if conversation_id in self.buffers:
                del self.buffers[conversation_id]
                logger.info(f"Cleared buffer for conversation {conversation_id}")
    
    async def update_conversation_context(
        self,
        conversation_id: UUID,
        db: Any,
        force_reload: bool = False
    ) -> Optional[str]:
        """Update conversation context from database"""
        try:
            if force_reload or conversation_id not in self.buffers:
                # Force reload from database
                return await self.resume_conversation(conversation_id, db)
            else:
                # Just return existing context
                buffer = self.buffers[conversation_id]
                return buffer.get_formatted_context()
                
        except Exception as e:
            logger.error(f"Error updating conversation context: {e}")
            return None
    
    def get_buffer_info(self, conversation_id: UUID) -> Optional[Dict[str, Any]]:
        """Get information about a specific buffer"""
        if conversation_id in self.buffers:
            buffer = self.buffers[conversation_id]
            context = buffer.get_formatted_context()
            return {
                "conversation_id": str(conversation_id),
                "message_count": len(buffer.messages),
                "has_summary": buffer.summary is not None,
                "last_updated": buffer.last_updated.isoformat(),
                "token_count": buffer.count_tokens(context),
                "max_tokens": buffer.max_tokens
            }
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer manager statistics"""
        total_messages = sum(len(buffer.messages) for buffer in self.buffers.values())
        summarized_buffers = sum(1 for buffer in self.buffers.values() if buffer.summary)
        
        # Calculate average token count
        token_counts = []
        for buffer in self.buffers.values():
            try:
                context = buffer.get_formatted_context()
                token_counts.append(buffer.count_tokens(context))
            except:
                pass
        
        avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0
        
        return {
            "active_buffers": len(self.buffers),
            "total_messages": total_messages,
            "summarized_buffers": summarized_buffers,
            "max_tokens": self.max_tokens,
            "cleanup_interval": self.cleanup_interval,
            "average_token_count": round(avg_tokens, 2),
            "max_token_count": max(token_counts) if token_counts else 0,
            "min_token_count": min(token_counts) if token_counts else 0
        }
    
    async def get_conversation_summary(
        self,
        conversation_id: UUID,
        db: Optional[Any] = None
    ) -> Optional[str]:
        """Get just the summary of a conversation if it exists"""
        try:
            buffer = await self.get_or_create_buffer(conversation_id, db)
            return buffer.summary
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return None
    
    async def force_summarize_conversation(
        self,
        conversation_id: UUID,
        db: Optional[Any] = None
    ) -> bool:
        """Force summarization of a conversation"""
        try:
            buffer = await self.get_or_create_buffer(conversation_id, db)
            if len(buffer.messages) > 5:  # Only summarize if we have enough messages
                await buffer._summarize_older_messages()
                return True
            return False
        except Exception as e:
            logger.error(f"Error forcing summarization: {e}")
            return False
    
    async def export_conversation_context(
        self,
        conversation_id: UUID,
        db: Optional[Any] = None,
        include_metadata: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Export conversation context for analysis or backup"""
        try:
            buffer = await self.get_or_create_buffer(conversation_id, db)
            
            export_data = {
                "conversation_id": str(conversation_id),
                "last_updated": buffer.last_updated.isoformat(),
                "message_count": len(buffer.messages),
                "has_summary": buffer.summary is not None,
                "formatted_context": buffer.get_formatted_context()
            }
            
            if include_metadata:
                export_data.update({
                    "summary": buffer.summary,
                    "messages": buffer.messages,
                    "token_count": buffer.count_tokens(buffer.get_formatted_context()),
                    "max_tokens": buffer.max_tokens
                })
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting conversation context: {e}")
            return None
    
    async def import_conversation_context(
        self,
        conversation_id: UUID,
        context_data: Dict[str, Any]
    ) -> bool:
        """Import conversation context from export data"""
        try:
            async with self._lock:
                buffer = ConversationBuffer(conversation_id, self.max_tokens)
                
                if "messages" in context_data:
                    buffer.messages = context_data["messages"]
                
                if "summary" in context_data:
                    buffer.summary = context_data["summary"]
                
                if "last_updated" in context_data:
                    try:
                        buffer.last_updated = datetime.fromisoformat(context_data["last_updated"])
                    except:
                        buffer.last_updated = datetime.utcnow()
                
                self.buffers[conversation_id] = buffer
                logger.info(f"Imported conversation context for {conversation_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error importing conversation context: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the buffer manager"""
        try:
            stats = self.get_stats()
            
            # Check for potential issues
            issues = []
            
            if stats["active_buffers"] > 1000:
                issues.append("High number of active buffers")
            
            if stats["average_token_count"] > self.max_tokens * 0.8:
                issues.append("Average token count approaching limit")
            
            if not self._cleanup_task or self._cleanup_task.done():
                issues.append("Cleanup task not running")
                self._start_cleanup_task()  # Restart if needed
            
            return {
                "status": "healthy" if not issues else "warning",
                "issues": issues,
                "stats": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def __del__(self):
        """Cleanup when the manager is destroyed"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

# Create singleton instance
buffer_manager = BufferManager()
