# In app/core/buffer_manager.py

import asyncio
import logging
from typing import Dict, Optional, Any
from uuid import UUID
from datetime import datetime
from app.core.config import settings
from app.services.memory.conversation_buffer import ConversationBuffer

logger = logging.getLogger(__name__)

class BufferManager:
    def __init__(self):
        self.conversation_buffer = ConversationBuffer(save_dir=settings.BUFFER_SAVE_DIR)
        self._buffer_loaded = False
        self._buffer_lock = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Initialize async components safely"""
        if not self._initialized:
            logger.info("[BUFFER_DEBUG] Initializing BufferManager")
            self._buffer_lock = asyncio.Lock()
            if not self._buffer_loaded:
                logger.info("[BUFFER_DEBUG] Loading conversation buffer from disk")
                await self.conversation_buffer.load_from_disk()
                self._buffer_loaded = True
            self._initialized = True
            logger.info("[BUFFER_DEBUG] BufferManager initialized")

    async def add_message(
        self,
        conversation_id: UUID,
        message: str,
        sender_id: str,
        sender_type: str,
        owner_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a message to the conversation buffer."""
        await self._ensure_initialized()
        try:
            async with self._buffer_lock:
                self.conversation_buffer.add_message(
                    conversation_id=conversation_id,
                    message=message,
                    sender_id=sender_id,
                    sender_type=sender_type,
                    owner_id=owner_id,
                    metadata=metadata
                )
                logger.debug(f"Stored message in buffer for conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to store message in buffer: {e}")
            raise

    async def get_context(self, conversation_id: UUID, include_metadata: bool = False) -> str:
        """Get formatted context from conversation buffer."""
        await self._ensure_initialized()
        logger.info(f"[BUFFER_DEBUG] Retrieving context for conversation: {conversation_id}")
        
        # Ensure the conversation exists in the buffer
        str_id = str(conversation_id)
        if str_id not in self.conversation_buffer.buffers:
            logger.warning(f"[BUFFER_DEBUG] Conversation {conversation_id} not found in buffer, checking database")
            # Try to load messages from database
            await self._load_messages_from_db(conversation_id)
        
        context = self.conversation_buffer.format_context(conversation_id, include_metadata)
        logger.info(f"[BUFFER_DEBUG] Retrieved context length: {len(context)} characters")
        if not context:
            logger.warning(f"[BUFFER_DEBUG] No context found for conversation {conversation_id}")
            # Log buffer state
            logger.info(f"[BUFFER_DEBUG] Current buffer keys: {list(self.conversation_buffer.buffers.keys())}")
            # Try one more time with database reload forced
            await self._load_messages_from_db(conversation_id, force=True)
            context = self.conversation_buffer.format_context(conversation_id, include_metadata)
            logger.info(f"[BUFFER_DEBUG] After forced reload, context length: {len(context)} characters")
        return context
        
    async def _load_messages_from_db(self, conversation_id: UUID, force: bool = False):
        """Load messages from database into buffer when not found in memory."""
        try:
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select
            from app.db.database import get_db
            from app.models.models import Message, User, Conversation, Participant
            
            # Clear existing buffer if forcing reload
            if force:
                str_id = str(conversation_id)
                if str_id in self.conversation_buffer.buffers:
                    self.conversation_buffer.clear_conversation(conversation_id)
                    logger.info(f"[BUFFER_DEBUG] Forced buffer clear for conversation {conversation_id}")
            
            # Get database session
            db = await anext(get_db())
            
            # Query for messages in this conversation
            query = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            
            result = await db.execute(query)
            messages = result.scalars().all()
            
            if not messages:
                logger.warning(f"[BUFFER_DEBUG] No messages found in database for conversation {conversation_id}")
                return
                
            logger.info(f"[BUFFER_DEBUG] Found {len(messages)} messages in database for conversation {conversation_id}")
            
            # Get owner ID from conversation record
            owner_id = None
            try:
                conv_query = select(Conversation).where(Conversation.id == conversation_id)
                conv_result = await db.execute(conv_query)
                conversation = conv_result.scalar_one_or_none()
                if conversation:
                    owner_id = conversation.created_by_user_id
                    logger.info(f"[BUFFER_DEBUG] Found conversation owner: {owner_id}")
            except Exception as e:
                logger.error(f"[BUFFER_DEBUG] Error getting conversation owner: {e}")
            
            # Cache user data to avoid repeated queries
            user_cache = {}
            participant_cache = {}
            
            # Add messages to buffer
            for msg in messages:
                sender_type = "system"
                sender_id = "system"
                sender_name = "System"
                
                # User message
                if msg.user_id:
                    sender_type = "user"
                    sender_id = str(msg.user_id)
                    
                    # Get user name if not in cache
                    if sender_id not in user_cache:
                        try:
                            user_query = select(User).where(User.id == msg.user_id)
                            user_result = await db.execute(user_query)
                            user = user_result.scalar_one_or_none()
                            if user:
                                name = f"{user.first_name} {user.last_name}".strip() or user.username
                                user_cache[sender_id] = name
                                sender_name = name
                            else:
                                user_cache[sender_id] = "Unknown User"
                                sender_name = "Unknown User"
                        except Exception as e:
                            logger.error(f"[BUFFER_DEBUG] Error getting user data: {e}")
                            user_cache[sender_id] = "Unknown User"
                            sender_name = "Unknown User"
                    else:
                        sender_name = user_cache[sender_id]
                
                # Agent message
                elif msg.agent_type:
                    sender_type = "agent"  # This MUST be "agent" for frontend to recognize it correctly
                    sender_id = msg.agent_type
                    sender_name = msg.agent_type
                    
                    # Ensure agent_type is always in metadata for agent messages
                    if not metadata:
                        metadata = {}
                    metadata["agent_type"] = msg.agent_type
                    metadata["message_type"] = "agent"  # Also set message_type consistently
                
                # Participant message
                elif msg.participant_id:
                    sender_type = "participant"
                    sender_id = str(msg.participant_id)
                    
                    # Get participant name if not in cache
                    if sender_id not in participant_cache:
                        try:
                            part_query = select(Participant).where(Participant.id == msg.participant_id)
                            part_result = await db.execute(part_query)
                            participant = part_result.scalar_one_or_none()
                            if participant:
                                name = participant.name or participant.identifier
                                participant_cache[sender_id] = name
                                sender_name = name
                            else:
                                participant_cache[sender_id] = "Unknown Participant"
                                sender_name = "Unknown Participant"
                        except Exception as e:
                            logger.error(f"[BUFFER_DEBUG] Error getting participant data: {e}")
                            participant_cache[sender_id] = "Unknown Participant"
                            sender_name = "Unknown Participant"
                    else:
                        sender_name = participant_cache[sender_id]
                
                # Parse message metadata if available
                metadata = None
                if msg.additional_data:
                    try:
                        if isinstance(msg.additional_data, str):
                            metadata = json.loads(msg.additional_data)
                        else:
                            metadata = msg.additional_data
                    except Exception:
                        metadata = None
                
                # Ensure we have metadata object
                if not metadata:
                    metadata = {}
                
                # Add sender info to metadata
                metadata["sender_name"] = sender_name
                metadata["sender_type"] = sender_type  # Explicitly add sender_type to ensure consistency
                if msg.agent_type:
                    metadata["agent_type"] = msg.agent_type
                
                # Add message to buffer
                await self.add_message(
                    conversation_id=conversation_id,
                    message=msg.content,
                    sender_id=sender_id,
                    sender_type=sender_type,
                    owner_id=owner_id or msg.user_id,  # Use conversation owner or message user_id
                    metadata=metadata
                )
            
            logger.info(f"[BUFFER_DEBUG] Successfully loaded {len(messages)} messages from database for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"[BUFFER_DEBUG] Error loading messages from database: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def save_state(self):
        """Save current buffer state to disk."""
        await self._ensure_initialized()
        try:
            async with self._buffer_lock:
                await self.conversation_buffer.save_to_disk()
        except Exception as e:
            logger.error(f"Error saving buffer state: {e}")
            raise

    async def cleanup_conversation(self, conversation_id: UUID):
        """Export and clean up a conversation from the buffer."""
        await self._ensure_initialized()
        try:
            async with self._buffer_lock:
                buffer_data = self.conversation_buffer.cleanup_and_export(conversation_id)
                logger.info(f"Exported and cleaned up buffer for conversation {conversation_id}")
                return buffer_data
        except Exception as e:
            logger.error(f"Error cleaning up conversation buffer: {e}")
            raise

    async def cleanup_expired_conversations(self, max_age_hours: int = 24):
        """Clean up expired conversations from the buffer."""
        await self._ensure_initialized()
        try:
            async with self._buffer_lock:
                self.conversation_buffer.cleanup_expired_conversations(max_age_hours)
        except Exception as e:
            logger.error(f"Error cleaning up expired conversations: {e}")
            raise
    
    async def delete_conversation(self, conversation_id: UUID):
        async with self._buffer_lock:
            self.conversation_buffer.remove_conversation(conversation_id)

    def get_buffer_metrics(self) -> dict:
        """Get current buffer metrics."""
        return {
            'total_conversations': len(self.conversation_buffer.buffers),
            'total_messages': sum(
                len(buffer) 
                for buffer in self.conversation_buffer.buffers.values()
            )
        }

# Global buffer manager instance
buffer_manager = BufferManager()
