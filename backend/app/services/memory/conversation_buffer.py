from collections import deque
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
import logging
import json
import os
import aiofiles
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class ConversationBuffer:
    """
    Manages short-term memory for active conversations using a circular buffer.
    Provides quick access to conversation context without RAG overhead.
    """

    def __init__(self, max_size: int = 100, save_dir: str = "data/buffers"):
        """
        Initialize conversation buffer.
        
        Args:
            max_size: Maximum number of messages to store in buffer
            save_dir: Directory to save buffer persistence files
        """
        self.max_size = max_size
        # Use string keys instead of UUID objects to avoid object identity issues
        self.buffers: Dict[str, deque] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.save_dir = Path(save_dir)
        self.save_file = self.save_dir / "conversation_buffers.json"
        self._ensure_save_dir()

    def _ensure_save_dir(self):
        """Ensure the save directory exists."""
        try:
            self.save_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create save directory {self.save_dir}: {e}")
            raise

    def add_message(
        self,
        conversation_id: UUID,
        message: str,
        sender_id: str,
        sender_type: str,
        owner_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a message to the conversation buffer.
        
        Args:
            conversation_id: UUID of the conversation
            message: Content of the message
            sender_id: ID of sender (user ID, participant ID, or agent ID)
            sender_type: Type of sender ('user', 'participant', or 'agent')
            metadata: Optional additional message metadata
        """
        try:
            # Convert UUID to string to use as key
            str_id = str(conversation_id)
            
            # Debug logging - type of conversation_id
            logger.info(f"[BUFFER_DEBUG] Adding message to buffer for conversation: {str_id} (original: {conversation_id})")
            logger.info(f"[BUFFER_DEBUG] Sender: {sender_id} ({sender_type})")
            
            # Initialize buffer for new conversation
            if str_id not in self.buffers:
                logger.info(f"[BUFFER_DEBUG] Creating new buffer for conversation: {str_id}")
                self.buffers[str_id] = deque(maxlen=self.max_size)
                self.metadata[str_id] = {
                    'created_at': datetime.utcnow(),
                    'last_updated': datetime.utcnow(),
                    'message_count': 0,
                    'participants': set(),
                    'owner_id': owner_id 
                }

            # Update metadata
            meta = self.metadata[str_id]
            meta['last_updated'] = datetime.utcnow()
            meta['message_count'] += 1
            meta['participants'].add(sender_id)

            # Add message with timestamp and metadata
            message_data = {
                'content': message,
                'sender_id': sender_id,
                'sender_type': sender_type,
                'timestamp': datetime.utcnow(),
                'metadata': metadata or {}
            }
            
            self.buffers[str_id].append(message_data)
            
            logger.info(
                f"[BUFFER_DEBUG] Added message to buffer for conversation {str_id}, "
                f"buffer size: {len(self.buffers[str_id])}, "
                f"total buffers: {len(self.buffers)}"
            )

        except Exception as e:
            logger.error(f"[BUFFER_DEBUG] Error adding message to buffer: {e}")
            raise

    def get_recent_messages(
        self,
        conversation_id: UUID,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages from the buffer.
        
        Args:
            conversation_id: UUID of the conversation
            limit: Optional maximum number of messages to return (None for all messages)
        """
        # Convert UUID to string for dictionary lookup
        str_id = str(conversation_id)
        
        logger.info(f"[BUFFER_DEBUG] get_recent_messages for {str_id} (original: {conversation_id})")
        
        if str_id not in self.buffers:
            logger.warning(f"[BUFFER_DEBUG] Conversation {str_id} not found in buffers!")
            logger.info(f"[BUFFER_DEBUG] Available buffers: {list(self.buffers.keys())}")
            return []

        messages = list(self.buffers[str_id])
        logger.info(f"[BUFFER_DEBUG] Found {len(messages)} messages for conversation {str_id}")
        
        if limit is not None and limit > 0:
            messages = messages[-limit:]
            logger.info(f"[BUFFER_DEBUG] Limited to {len(messages)} messages")
            
        return messages

    def format_context(
        self,
        conversation_id: UUID,
        include_metadata: bool = False,
        limit: Optional[int] = None
    ) -> str:
        """
        Format messages as a context string.
        
        Args:
            conversation_id: UUID of the conversation
            include_metadata: Whether to include message metadata
            limit: Optional limit on number of messages (None for all messages)
        """
        # Convert UUID to string for dictionary lookup
        str_id = str(conversation_id)
        
        logger.info(f"[BUFFER_DEBUG] Formatting context for conversation: {str_id} (original: {conversation_id})")
        logger.info(f"[BUFFER_DEBUG] Current buffers available: {list(self.buffers.keys())}")
        
        messages = self.get_recent_messages(conversation_id, limit)
        
        logger.info(f"[BUFFER_DEBUG] Retrieved {len(messages)} messages for conversation {str_id}")
        
        if not messages:
            return ""
        
        context_parts = []
        
        # Add conversation metadata if requested - use string ID
        str_id = str(conversation_id)
        if include_metadata and str_id in self.metadata:
            conv_meta = self.metadata[str_id]
            meta_str = (
                f"Conversation Info:\n"
                f"Created: {conv_meta['created_at'].isoformat()}\n"
                f"Last Updated: {conv_meta['last_updated'].isoformat()}\n"
                f"Total Messages: {conv_meta['message_count']}\n"
                f"Participants: {len(conv_meta['participants'])}\n"
            )
            context_parts.append(meta_str)
            context_parts.append("-" * 50)  # Separator

        # Format each message
        for msg in messages:
            # Basic message format
            msg_parts = []
            
            # Format sender info
            sender_info = f"[{msg['sender_type'].upper()}]"
            if 'metadata' in msg and msg['metadata']:
                if 'agent_type' in msg['metadata'] and msg['sender_type'] == "agent":
                    sender_info = f"[AGENT: {msg['metadata']['agent_type']}]"
                elif 'sender_name' in msg['metadata']:
                    sender_info = f"[{msg['sender_type'].upper()}: {msg['metadata']['sender_name']}]"
                elif 'participant_name' in msg['metadata']:
                    sender_info = f"[{msg['metadata']['participant_name']}]"
            
            msg_parts.append(sender_info)
            
            # Add timestamp
            if isinstance(msg['timestamp'], datetime):
                msg_parts.append(f"({msg['timestamp'].isoformat()})")
            
            # Add message content
            msg_parts.append(msg['content'])
            
            # Add metadata if requested
            if include_metadata and msg['metadata']:
                meta_items = [
                    f"{k}: {v}"
                    for k, v in msg['metadata'].items()
                    if k not in ['agent_type', 'participant_name']  # Skip already shown metadata
                ]
                if meta_items:
                    msg_parts.append(f"[{', '.join(meta_items)}]")
            
            # Join message parts and add to context
            context_parts.append(" ".join(msg_parts))
        
        # Return full context
        context = "\n".join(context_parts)
        logger.info(f"[BUFFER_DEBUG] Formatted context length: {len(context)} characters")
        return context

    def get_buffer_size(self, conversation_id: UUID) -> int:
        """Get current size of buffer for a conversation."""
        str_id = str(conversation_id)
        if str_id not in self.buffers:
            return 0
        return len(self.buffers[str_id])

    def get_buffer_metadata(self, conversation_id: UUID) -> Optional[Dict[str, Any]]:
        """Get metadata for a conversation buffer."""
        str_id = str(conversation_id)
        return self.metadata.get(str_id)

    def clear_conversation(self, conversation_id: UUID) -> None:
        """Clear the buffer for a specific conversation."""
        str_id = str(conversation_id)
        if str_id in self.buffers:
            self.buffers[str_id].clear()
            self.metadata[str_id]['message_count'] = 0
            logger.debug(f"Cleared buffer for conversation {str_id}")

    def remove_conversation(self, conversation_id: UUID) -> None:
        """Remove a conversation from the buffer entirely."""
        str_id = str(conversation_id)
        self.buffers.pop(str_id, None)
        self.metadata.pop(str_id, None)
        logger.debug(f"Removed conversation {str_id} from buffer")

    def export_conversation(
        self,
        conversation_id: UUID,
    ) -> Dict[str, Any]:
        """
        Export all messages from a conversation buffer before clearing.
        Returns dict with messages and metadata intact.
        """
        str_id = str(conversation_id)
        if str_id not in self.buffers:
            return {'messages': [], 'metadata': {}}
            
        messages = list(self.buffers[str_id])
        metadata = self.metadata.get(str_id, {})
        
        # Convert set to list for JSON serialization
        if 'participants' in metadata:
            metadata['participants'] = list(metadata['participants'])
        
        return {
            'messages': messages,
            'metadata': metadata
        }

    async def save_to_disk(self):
        """Save current buffer state to disk."""
        try:
            # Convert buffer data to serializable format
            buffer_data = {}
            for conv_id, messages in self.buffers.items():
                metadata = self.metadata.get(conv_id, {}).copy()
                
                # Convert set to list for JSON serialization
                if 'participants' in metadata:
                    metadata['participants'] = list(metadata['participants'])
                
                buffer_data[conv_id] = {
                    'messages': list(messages),
                    'metadata': metadata
                }
            
            # Convert to JSON and save
            json_data = json.dumps(buffer_data, default=str)
            
            async with aiofiles.open(self.save_file, 'w') as f:
                await f.write(json_data)
                
            logger.info(f"Saved {len(buffer_data)} conversation buffers to {self.save_file}")
            
        except Exception as e:
            logger.error(f"Error saving buffers to disk: {e}")

    async def load_from_disk(self):
        """Load buffer state from disk."""
        try:
            if not self.save_file.exists():
                logger.info(f"No buffer file found at {self.save_file}")
                return
                
            async with aiofiles.open(self.save_file, 'r') as f:
                json_data = await f.read()
            
            buffer_data = json.loads(json_data)
            
            # Restore buffers
            for conv_id_str, data in buffer_data.items():
                try:
                    # Store using string key directly
                    messages = data['messages']
                    metadata = data['metadata']
                    
                    # Convert timestamps back to datetime
                    for msg in messages:
                        if 'timestamp' in msg:
                            msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
                    
                    if metadata.get('created_at'):
                        metadata['created_at'] = datetime.fromisoformat(metadata['created_at'])
                    if metadata.get('last_updated'):
                        metadata['last_updated'] = datetime.fromisoformat(metadata['last_updated'])
                    
                    # Convert participants back to set
                    if 'participants' in metadata:
                        metadata['participants'] = set(metadata['participants'])
                    
                    # Restore to buffer using string key
                    self.buffers[conv_id_str] = deque(messages, maxlen=self.max_size)
                    self.metadata[conv_id_str] = metadata
                    
                except Exception as e:
                    logger.error(f"Error restoring conversation {conv_id_str}: {e}")
                    continue
                
            logger.info(f"Loaded {len(buffer_data)} conversation buffers from {self.save_file}")
            
        except Exception as e:
            logger.error(f"Error loading buffers from disk: {e}")

    def cleanup_and_export(self, conversation_id: UUID) -> Dict[str, Any]:
        """Export conversation data and then remove it from the buffer."""
        exported_data = self.export_conversation(conversation_id)
        self.remove_conversation(conversation_id)
        return exported_data

    def cleanup_expired_conversations(self, max_age_hours: int = 24) -> None:
        """Remove conversations that haven't been updated in specified time."""
        current_time = datetime.utcnow()
        expired = []
        
        for conv_id, meta in self.metadata.items():
            age = current_time - meta['last_updated']
            if age.total_seconds() > (max_age_hours * 3600):
                expired.append(conv_id)
                
        for conv_id in expired:
            self.remove_conversation(conv_id)
            logger.info(f"Removed expired conversation {conv_id} from buffer")
