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

    def get_context(self, conversation_id: UUID, include_metadata: bool = False) -> str:
        """Get formatted context from conversation buffer."""
        logger.info(f"[BUFFER_DEBUG] Retrieving context for conversation: {conversation_id}")
        context = self.conversation_buffer.format_context(conversation_id, include_metadata)
        logger.info(f"[BUFFER_DEBUG] Retrieved context length: {len(context)} characters")
        if not context:
            logger.warning(f"[BUFFER_DEBUG] No context found for conversation {conversation_id}")
            # Log buffer state
            logger.info(f"[BUFFER_DEBUG] Current buffer keys: {list(self.conversation_buffer.buffers.keys())}")
        return context

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
