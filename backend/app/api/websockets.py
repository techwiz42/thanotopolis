# backend/app/api/websockets.py
from fastapi import APIRouter, WebSocket, Depends, HTTPException
from fastapi.websockets import WebSocketDisconnect, WebSocketState
from sqlalchemy import select, update, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from typing import Dict, Set, Optional, List, Union, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime
import json
import asyncio
import logging
import traceback

from app.auth.auth import get_current_user, get_tenant_from_request
from app.core.config import settings
from app.core.buffer_manager import buffer_manager
from app.db.database import get_db, get_db_context
from app.models.models import (
    User, Tenant, Message, Conversation, ConversationAgent, 
    ConversationUser, MessageType
    )
from app.agents.tenant_aware_agent_manager import tenant_aware_agent_manager as agent_manager
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Connection tracking with limits
active_connections: Dict[UUID, Set[WebSocket]] = {}
connection_lock = asyncio.Lock()

# Connection limits for scalability
MAX_CONNECTIONS_PER_CONVERSATION = 50
MAX_TOTAL_CONNECTIONS = 500

# Connection statistics
connection_stats = {
    "total": 0,
    "by_conversation": {},
    "by_user": {},
    "last_cleanup": None
}

async def process_conversation(
    conversation_id: UUID,
    message_id: UUID,
    default_agent_type: str,
    db: AsyncSession,
    owner_id: Optional[UUID] = None,
    user: Optional[User] = None
) -> Optional[Tuple[str, str]]:
    """
    Process a conversation message through the MODERATOR agent.
    
    All messages are routed to the MODERATOR agent, which will select
    the appropriate specialist agent(s) and coordinate collaboration as needed.
    
    Args:
        conversation_id: The conversation UUID
        message_id: The message UUID to process
        default_agent_type: Default agent type (should be "MODERATOR")
        db: Database session
        owner_id: Optional owner ID of the message
        
    Returns:
        Tuple of (agent_type, response_content) or None if processing fails
    """
    try:
        # Get the message content from the database
        message_query = select(Message).where(Message.id == message_id)
        message_result = await db.execute(message_query)
        message = message_result.scalar_one_or_none()
        
        if not message:
            logger.error(f"Message {message_id} not found")
            return None
            
        message_content = message.content
        
        # Get the conversation
        conversation_query = select(Conversation).where(Conversation.id == conversation_id)
        conversation_result = await db.execute(conversation_query)
        conversation = conversation_result.scalar_one_or_none()
        
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found")
            return None
        
        # If no owner_id was provided, try to get it from the message
        if owner_id is None and message.user_id is not None:
            owner_id = message.user_id
        
        # Process the conversation using the agent manager
        # Use tenant-aware processing if user is provided
        if user and hasattr(agent_manager, 'process_conversation_with_tenant_context'):
            agent_type, response = await agent_manager.process_conversation_with_tenant_context(
                message=message_content,
                user=user,
                db=db,
                thread_id=str(conversation_id),
                owner_id=owner_id,
                response_callback=None
            )
        else:
            # Fallback to regular processing
            agent_type, response = await agent_manager.process_conversation(
                message=message_content,
                conversation_agents=[],  # Ignored - agents discovered dynamically
                agents_config={},       # Ignored - agents use default config
                mention=None,           # Ignored - no mention routing
                db=db,
                thread_id=str(conversation_id),  # thread_id is used as alias for conversation_id
                owner_id=owner_id,      # owner_id is required for proper context handling
                response_callback=None  # No streaming for regular websocket messages
            )
        
        return agent_type, response
        
    except Exception as e:
        logger.error(f"Error processing conversation {conversation_id}: {e}")
        logger.error(traceback.format_exc())
        # Print additional information for debugging
        if 'owner_id' in locals() and owner_id is None:
            logger.error("owner_id is None - this might be causing the error")
        return None

async def can_accept_connection(conversation_id: UUID) -> bool:
    """Check if we can accept a new connection based on limits."""
    async with connection_lock:
        # Count total connections
        total = sum(len(sockets) for sockets in active_connections.values())
        if total >= MAX_TOTAL_CONNECTIONS:
            logger.warning(f"Total connection limit reached: {total}/{MAX_TOTAL_CONNECTIONS}")
            return False
        
        # Check per-conversation limit
        conversation_sockets = active_connections.get(conversation_id, set())
        if len(conversation_sockets) >= MAX_CONNECTIONS_PER_CONVERSATION:
            logger.warning(f"Conversation {conversation_id} connection limit reached: {len(conversation_sockets)}/{MAX_CONNECTIONS_PER_CONVERSATION}")
            return False
        
        return True

async def cleanup_stale_connections():
    """Remove disconnected WebSockets and update stats."""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            
            async with connection_lock:
                cleaned = 0
                total_before = sum(len(sockets) for sockets in active_connections.values())
                
                # Check each conversation's connections
                for conv_id, sockets in list(active_connections.items()):
                    active = set()
                    for ws in sockets:
                        try:
                            # Check if WebSocket is still connected
                            if hasattr(ws, 'client_state') and ws.client_state == WebSocketState.CONNECTED:
                                active.add(ws)
                            else:
                                cleaned += 1
                        except:
                            cleaned += 1
                    
                    if active:
                        active_connections[conv_id] = active
                    else:
                        # Remove empty conversation
                        del active_connections[conv_id]
                
                # Update stats
                total_after = sum(len(sockets) for sockets in active_connections.values())
                connection_stats["total"] = total_after
                connection_stats["by_conversation"] = {
                    str(conv_id): len(sockets) 
                    for conv_id, sockets in active_connections.items()
                }
                connection_stats["last_cleanup"] = datetime.utcnow().isoformat()
                
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} stale connections. Total: {total_before} -> {total_after}")
                    
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

# Start cleanup task on module load
cleanup_task = None

def start_cleanup_task():
    """Start the cleanup task if not already running."""
    global cleanup_task
    if cleanup_task is None or cleanup_task.done():
        cleanup_task = asyncio.create_task(cleanup_stale_connections())
        logger.info("Started WebSocket cleanup task")

class ConnectionManager:
    """Manages WebSocket connections for conversations"""
    
    def __init__(self):
        self.active_connections: Dict[UUID, Dict[str, WebSocket]] = {}
        self.user_connections: Dict[str, Set[UUID]] = {}
        self.connection_timestamps: Dict[str, datetime] = {}
        self.lock = asyncio.Lock()
        self.max_connections_per_user = 10  # Prevent abuse
        self.connection_timeout = 300  # 5 minutes without activity
    
    async def connect(self, websocket: WebSocket, conversation_id: UUID, user_email: str) -> str:
        """Register a new connection"""
        async with self.lock:
            # Check connection limits per user
            user_connection_count = sum(
                len(conversations) for email, conversations in self.user_connections.items() 
                if email == user_email
            )
            
            if user_connection_count >= self.max_connections_per_user:
                logger.warning(f"User {user_email} has reached connection limit: {user_connection_count}")
                raise HTTPException(status_code=429, detail="Too many connections")
            
            connection_id = str(uuid4())
            
            # Initialize conversation connections if needed
            if conversation_id not in self.active_connections:
                self.active_connections[conversation_id] = {}
            
            # Add connection
            self.active_connections[conversation_id][connection_id] = websocket
            self.connection_timestamps[connection_id] = datetime.utcnow()
            
            # Track user connections
            if user_email not in self.user_connections:
                self.user_connections[user_email] = set()
            self.user_connections[user_email].add(conversation_id)
            
            logger.info(f"Connected: {user_email} to conversation {conversation_id} (total connections: {len(self.connection_timestamps)})")
            return connection_id
    
    async def disconnect(self, conversation_id: UUID, connection_id: str, user_email: str):
        """Remove a connection"""
        async with self.lock:
            # Remove from conversation connections
            if conversation_id in self.active_connections:
                self.active_connections[conversation_id].pop(connection_id, None)
                
                # Clean up empty conversations
                if not self.active_connections[conversation_id]:
                    del self.active_connections[conversation_id]
            
            # Remove from user connections
            if user_email in self.user_connections:
                self.user_connections[user_email].discard(conversation_id)
                
                # Clean up empty user entries
                if not self.user_connections[user_email]:
                    del self.user_connections[user_email]
            
            # Clean up connection timestamp
            self.connection_timestamps.pop(connection_id, None)
            
            logger.info(f"Disconnected: {user_email} from conversation {conversation_id} (total connections: {len(self.connection_timestamps)})")
    
    async def broadcast(self, conversation_id: UUID, message: dict):
        """Broadcast message to all connections in a conversation"""
        if conversation_id in self.active_connections:
            # Send to all connections in parallel
            tasks = []
            for conn_id, websocket in self.active_connections[conversation_id].items():
                tasks.append(self._send_message(websocket, message, conn_id))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_message(self, websocket: WebSocket, message: dict, conn_id: str):
        """Send a message to a specific websocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to connection {conn_id}: {e}")
    
    async def send_to_user(self, user_email: str, message: dict):
        """Send message to all connections of a specific user"""
        if user_email in self.user_connections:
            tasks = []
            for conversation_id in self.user_connections[user_email]:
                tasks.append(self.broadcast(conversation_id, message))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def cleanup_stale_connections(self):
        """Remove connections that have been inactive for too long"""
        async with self.lock:
            current_time = datetime.utcnow()
            stale_connections = []
            
            for conn_id, timestamp in self.connection_timestamps.items():
                if (current_time - timestamp).total_seconds() > self.connection_timeout:
                    stale_connections.append(conn_id)
            
            for conn_id in stale_connections:
                logger.info(f"Cleaning up stale connection: {conn_id}")
                # Find and remove the stale connection
                for conversation_id, connections in self.active_connections.items():
                    if conn_id in connections:
                        connections.pop(conn_id, None)
                        if not connections:
                            del self.active_connections[conversation_id]
                        break
                
                self.connection_timestamps.pop(conn_id, None)
            
            if stale_connections:
                logger.info(f"Cleaned up {len(stale_connections)} stale connections")
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        total_connections = len(self.connection_timestamps)
        total_conversations = len(self.active_connections)
        total_users = len(self.user_connections)
        
        return {
            "total_connections": total_connections,
            "total_conversations": total_conversations,
            "total_users": total_users,
            "max_connections_per_user": self.max_connections_per_user
        }
    
    def get_stats(self) -> dict:
        """Alias for get_connection_stats for compatibility"""
        return self.get_connection_stats()

# Create singleton instance
connection_manager = ConnectionManager()

async def authenticate_websocket(token: str, db: AsyncSession) -> Optional[User]:
    """Authenticate a WebSocket connection"""
    try:
        # This is a simplified version - you'd use your actual auth system
        from app.auth.auth import AuthService
        payload = AuthService.decode_token(token)
        user_id = payload.sub
        
        if not user_id:
            return None
        
        result = await db.execute(
            select(User).filter(User.id == user_id)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None

def _help_message() -> dict:
    """Generate help message"""
    help_text = """Available Commands:
    - Type your message to broadcast to all participants
    - Start with '?' to see this help message
    - Use '/status' to see connection status
    - Use '/users' to see active participants"""
    
    return {
        "type": "message",
        "content": help_text,
        "id": str(uuid4()),
        "identifier": "system",
        "is_owner": False,
        "email": "system@thanotopolis.local",
        "timestamp": datetime.utcnow().isoformat()
    }

async def _handle_typing_status(
    conversation_id: UUID,
    user: User,
    is_typing: bool
) -> None:
    """Broadcast typing status"""
    await connection_manager.broadcast(
        conversation_id,
        {
            "type": "typing_status",
            "identifier": user.email,
            "is_owner": True,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def _handle_user_message(
    db: AsyncSession,
    conversation_id: UUID,
    user: User,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Process and broadcast user message"""
    try:
        # Generate message ID
        message_id = str(uuid4())
        
        # Handle special commands
        if content.startswith('?'):
            await connection_manager.broadcast(conversation_id, _help_message())
            return
        
        if content == '/status':
            status_message = {
                "type": "message",
                "content": f"Connection active. Conversation: {conversation_id}",
                "id": str(uuid4()),
                "identifier": "system",
                "is_owner": False,
                "email": "system@thanotopolis.local",
                "timestamp": datetime.utcnow().isoformat()
            }
            await connection_manager.broadcast(conversation_id, status_message)
            return
        
        if content == '/users':
            # Get active users in conversation
            active_users = []
            if conversation_id in connection_manager.active_connections:
                active_users = list(connection_manager.active_connections[conversation_id].keys())
            
            users_message = {
                "type": "message",
                "content": f"Active connections: {len(active_users)}",
                "id": str(uuid4()),
                "identifier": "system",
                "is_owner": False,
                "email": "system@thanotopolis.local",
                "timestamp": datetime.utcnow().isoformat()
            }
            await connection_manager.broadcast(conversation_id, users_message)
            return
        
        # Check if conversation exists first
        from sqlalchemy import select
        conversation_query = select(Conversation).where(Conversation.id == conversation_id)
        conversation_result = await db.execute(conversation_query)
        conversation = conversation_result.scalar_one_or_none()
        
        if not conversation:
            # If conversation doesn't exist, just broadcast without saving to DB
            logger.warning(f"Conversation {conversation_id} not found - message will not be saved to database")
            user_broadcast_message = {
                "type": "message",
                "content": content,
                "id": message_id,
                "identifier": user.email,
                "is_owner": True,
                "email": user.email,
                "sender_name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "sender_type": "user",
                "timestamp": datetime.utcnow().isoformat(),
                "user_metadata": {
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }
            }
            await connection_manager.broadcast(conversation_id, user_broadcast_message)
            return
            
        # Save the user message to database
        user_message = Message(
            id=UUID(message_id),
            conversation_id=conversation_id,
            user_id=user.id,
            content=content,
            message_type=MessageType.TEXT,
            additional_data=json.dumps(metadata) if metadata else None
        )
        db.add(user_message)
        
        # Update conversation timestamp
        from sqlalchemy import update as sql_update
        await db.execute(
            sql_update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=func.now())
        )
        
        await db.commit()
        await db.refresh(user_message)
        
        # Broadcast user message to all participants
        user_broadcast_message = {
            "type": "message",
            "content": content,
            "id": message_id,
            "identifier": user.email,
            "is_owner": True,
            "email": user.email,
            "sender_name": f"{user.first_name} {user.last_name}".strip() or user.username,
            "sender_type": "user",
            "timestamp": datetime.utcnow().isoformat(),
            "user_metadata": {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        }
        
        await connection_manager.broadcast(conversation_id, user_broadcast_message)
        
        # Add message to buffer for context
        await buffer_manager.add_message(
            conversation_id=conversation_id,
            message=content,
            sender_id=str(user.id),
            sender_type="user",
            owner_id=user.id,
            metadata=metadata
        )
        
        # All messages are processed by MODERATOR by default
        agent_type = "MODERATOR"
        
        # Check if conversation has a specific MODERATOR configuration
        moderator_query = select(ConversationAgent).where(
            ConversationAgent.conversation_id == conversation_id,
            ConversationAgent.agent_type == "MODERATOR",
            ConversationAgent.is_active == True
        )
        moderator_result = await db.execute(moderator_query)
        moderator_config = moderator_result.scalar_one_or_none()
        
        # If no MODERATOR is explicitly configured, add one
        if not moderator_config:
            # Get the MODERATOR agent record from database
            from app.models.models import Agent
            moderator_agent_result = await db.execute(
                select(Agent).where(Agent.agent_type == "MODERATOR")
            )
            moderator_agent_record = moderator_agent_result.scalar_one_or_none()
            
            if not moderator_agent_record:
                # Create the MODERATOR agent record if it doesn't exist
                moderator_agent_record = Agent(
                    agent_type="MODERATOR",
                    name="Moderator Agent",
                    description="Conversation moderator and agent coordinator",
                    is_free_agent=True,
                    owner_tenant_id=None,
                    configuration_template={},
                    capabilities=["agent_selection", "conversation_routing"],
                    is_active=True
                )
                db.add(moderator_agent_record)
                await db.flush()  # Get the ID without committing
            
            new_moderator = ConversationAgent(
                conversation_id=conversation_id,
                agent_id=moderator_agent_record.id,  # Link to actual agent record
                agent_type="MODERATOR",
                is_active=True,
                configuration=None
            )
            db.add(new_moderator)
            await db.commit()
        
        # Only process with agent if conversation exists
        if conversation:
            # Process with agent
            # Use the message's user_id as owner_id since conversation doesn't have owner_id
            owner_id = user.id  # Use the current user ID as the owner ID
            logger.info(f"Processing conversation with owner_id: {owner_id}")
            agent_response = await process_conversation(conversation_id, UUID(message_id), agent_type, db, owner_id=owner_id, user=user)
            
            if agent_response:
                response_agent_type, response_content = agent_response
                
                # Save agent response to database
                agent_message_id = str(uuid4())
                agent_message = Message(
                    id=UUID(agent_message_id),
                    conversation_id=conversation_id,
                    agent_type=response_agent_type,
                    content=response_content,
                    message_type=MessageType.TEXT,
                    # Store agent metadata in additional_data for proper retrieval later
                    additional_data=json.dumps({
                        "agent_type": response_agent_type,
                        "message_type": "agent",
                        "sender_type": "agent"
                    })
                )
                db.add(agent_message)
                await db.commit()
                await db.refresh(agent_message)
                
                # Add agent message to buffer
                await buffer_manager.add_message(
                    conversation_id=conversation_id,
                    message=response_content,
                    sender_id=response_agent_type,
                    sender_type="agent",  # This MUST be "agent" for frontend to recognize it correctly
                    owner_id=user.id,  # Use the conversation owner for context
                    metadata={
                        "agent_type": response_agent_type,
                        "message_type": "agent"  # Add message_type consistently for all agent messages
                    }
                )
                
                # Broadcast agent response to all participants
                agent_broadcast_message = {
                    "type": "message",
                    "content": response_content,
                    "id": agent_message_id,
                    "identifier": response_agent_type,
                    "is_owner": False,
                    "email": f"{response_agent_type.lower()}@thanotopolis.local",
                    "sender_name": response_agent_type,
                    "sender_type": "agent",  # This field is critical for message type recognition
                    "message_type": "agent",  # Explicitly add message_type for frontend styling
                    "agent_type": response_agent_type,  # Add agent_type directly for easier access
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_metadata": {
                        "agent_type": response_agent_type,
                        "message_type": "agent",  # Add to metadata as well for consistency
                        "sender_type": "agent"    # Ensure consistent sender_type
                    }
                }
                
                await connection_manager.broadcast(conversation_id, agent_broadcast_message)
                
                logger.info(f"Agent {response_agent_type} responded to message in conversation {conversation_id}")
        
        logger.info(f"Processed message from {user.email} in conversation {conversation_id}")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        logger.error(traceback.format_exc())
        
        # Send error message to user
        error_message = {
            "type": "error",
            "content": "Failed to process message",
            "timestamp": datetime.utcnow().isoformat()
        }
        await connection_manager.broadcast(conversation_id, error_message)

@router.websocket("/ws/conversations/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str
):
    """Main WebSocket endpoint for conversations"""
    connection_id = None
    user = None
    
    try:
        # Check connection limits before accepting
        if not await can_accept_connection(conversation_id):
            await websocket.close(code=1008, reason="Connection limit reached")
            return
        
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for conversation {conversation_id}")
        
        # Start cleanup task if needed
        start_cleanup_task()
        
        # Authenticate using a discrete database session
        from app.db.database import get_db_context
        async with get_db_context() as db:
            user = await authenticate_websocket(token, db)
            if not user:
                logger.error("WebSocket authentication failed")
                await websocket.send_json({
                    "type": "error",
                    "content": "Authentication failed",
                    "timestamp": datetime.utcnow().isoformat()
                })
                await websocket.close(code=4001, reason="Authentication failed")
                return
        
        logger.info(f"User {user.email} authenticated for WebSocket")
        
        # Register connection
        connection_id = await connection_manager.connect(websocket, conversation_id, user.email)
        
        # Add monitoring for this WebSocket connection
        monitoring_service.add_websocket_connection(
            connection_id=str(connection_id),
            user_id=str(user.id),
            tenant_id=str(user.tenant_id)
        )
        
        # Send welcome message
        welcome_message = {
            "type": "system",
            "content": f"Welcome to conversation {conversation_id}",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_json(welcome_message)
        
        # Fetch and send previous messages using a discrete database session
        try:
            # Get recent messages from the database
            from sqlalchemy import select
            from app.models.models import Message
            
            async with get_db_context() as db:
                # Query for all messages with no limit
                logger.info(f"Fetching all messages for conversation {conversation_id}")
                message_query = (
                    select(Message)
                    .options(
                        joinedload(Message.user),
                        joinedload(Message.participant)
                    )
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at)
                    # No limit - retrieve all messages
                )
                message_result = await db.execute(message_query)
                messages = message_result.scalars().all()
                logger.info(f"Found {len(messages)} messages for conversation {conversation_id}")
            
            # Send historical messages to the newly connected client
            for msg in messages:
                # Determine sender type and metadata
                sender_type = "system"
                sender_name = "System"
                
                # Parse message metadata from additional_data if available
                metadata = None
                if msg.additional_data:
                    try:
                        import json
                        if isinstance(msg.additional_data, str):
                            metadata = json.loads(msg.additional_data)
                        else:
                            metadata = msg.additional_data
                    except:
                        pass
                
                # Use message_metadata property which handles JSON parsing
                if not metadata and msg.message_metadata:
                    metadata = msg.message_metadata
                
                # Check if this is an agent message based on agent_type OR metadata OR sender_type
                if (msg.agent_type or 
                    (metadata and (metadata.get("agent_type") or metadata.get("sender_type") == "agent")) or
                    (not msg.user_id and not msg.participant_id)):  # If not user or participant, likely an agent
                    
                    # This is an agent message, ensure it's recognized as such
                    sender_type = "agent"  # This MUST be "agent" for frontend to recognize it correctly
                    
                    # Determine agent type from available sources
                    agent_type = None
                    if msg.agent_type:
                        agent_type = msg.agent_type
                    elif metadata and metadata.get("agent_type"):
                        agent_type = metadata.get("agent_type")
                    else:
                        # Default agent type if we can't determine it
                        agent_type = "ASSISTANT"
                    
                    sender_name = agent_type
                    
                    # Log detection of agent message for debugging
                    logger.info(f"Detected agent message id={msg.id}, agent_type={agent_type}, metadata={metadata}")
                    
                    # We'll add message_type field explicitly for agent messages
                    message_data = {
                        "type": "message",
                        "content": msg.content,
                        "id": str(msg.id),
                        "sender_name": agent_type,
                        "sender_type": "agent",  # Critical field - must be "agent"
                        "message_type": "agent", # Explicitly identify as agent message
                        "timestamp": msg.created_at.isoformat(),
                        "is_history": True,
                        "agent_type": agent_type,
                        "identifier": agent_type,
                        "is_owner": False,
                        "email": f"{agent_type.lower()}@thanotopolis.local",
                        "agent_metadata": {
                            "agent_type": agent_type,
                            "message_type": "agent",
                            "sender_type": "agent"  # Ensure consistent sender_type
                        }
                    }
                    
                    # Include any additional metadata from the message
                    if metadata and isinstance(metadata, dict):
                        message_data["agent_metadata"].update(metadata)
                    
                    # Send message to this client only and continue to the next message
                    await websocket.send_json(message_data)
                    continue
                elif msg.user_id:
                    sender_type = "user"
                    sender_name = "Unknown User"
                    # Get user info if available
                    if msg.user_id == user.id:
                        sender_name = f"{user.first_name} {user.last_name}".strip() or user.username
                        user_email = user.email
                    elif msg.user:
                        sender_name = f"{msg.user.first_name} {msg.user.last_name}".strip() or msg.user.username
                        user_email = msg.user.email
                    else:
                        # Query for user info if not loaded through joinedload
                        # Note: This runs inside the existing db context above
                        from app.models.models import User
                        user_query = select(User).where(User.id == msg.user_id)
                        user_result = await db.execute(user_query)
                        msg_user = user_result.scalar_one_or_none()
                        if msg_user:
                            sender_name = f"{msg_user.first_name} {msg_user.last_name}".strip() or msg_user.username
                            user_email = msg_user.email
                        else:
                            user_email = "user@thanotopolis.local"
                
                elif msg.participant_id:
                    sender_type = "participant"
                    if msg.participant:
                        sender_name = msg.participant.name or msg.participant.identifier
                    else:
                        # Note: This runs inside the existing db context above
                        from app.models.models import Participant
                        part_query = select(Participant).where(Participant.id == msg.participant_id)
                        part_result = await db.execute(part_query)
                        participant = part_result.scalar_one_or_none()
                        sender_name = participant.name or participant.identifier if participant else "Unknown Participant"
                
                # Note: metadata already parsed above, no need to parse again
                
                # Prepare message data based on sender type
                message_data = {
                    "type": "message",
                    "content": msg.content,
                    "id": str(msg.id),
                    "sender_name": sender_name,
                    "sender_type": sender_type,
                    "timestamp": msg.created_at.isoformat(),
                    "is_history": True  # Flag to indicate this is a historical message
                }
                
                # Ensure consistent message type field for frontend
                if sender_type == "agent":
                    message_data["message_type"] = "agent"
                
                # Add type-specific data
                if sender_type == "user":
                    message_data["identifier"] = user_email if msg.user_id == user.id else (
                        msg.user.email if msg.user else user_email
                    )
                    message_data["email"] = message_data["identifier"]
                    message_data["is_owner"] = msg.user_id == user.id
                    
                    # Add user metadata
                    if msg.user_id == user.id:
                        message_data["user_metadata"] = {
                            "username": user.username,
                            "first_name": user.first_name,
                            "last_name": user.last_name
                        }
                    elif msg.user:
                        message_data["user_metadata"] = {
                            "username": msg.user.username,
                            "first_name": msg.user.first_name,
                            "last_name": msg.user.last_name
                        }
                
                elif sender_type == "agent":
                    # Set all required fields for agent messages
                    message_data["identifier"] = msg.agent_type
                    message_data["is_owner"] = False
                    message_data["email"] = f"{msg.agent_type.lower()}@thanotopolis.local"
                    message_data["message_type"] = "agent"  # Critical for frontend rendering
                    message_data["sender_type"] = "agent"   # Ensure consistent sender_type - THIS IS CRUCIAL
                    message_data["agent_type"] = msg.agent_type
                    
                    # Initialize agent metadata with required fields
                    agent_metadata = {"agent_type": msg.agent_type, "message_type": "agent"}
                    
                    # Include additional metadata from message if available
                    if metadata and isinstance(metadata, dict):
                        agent_metadata.update(metadata)
                    
                    # Set the agent_metadata field with complete metadata
                    message_data["agent_metadata"] = agent_metadata
                
                # Send message to this client only
                await websocket.send_json(message_data)
                
            logger.info(f"Sent {len(messages)} historical messages to user {user.email}")
            
        except Exception as e:
            logger.error(f"Error fetching historical messages: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Notify others of new participant
        join_message = {
            "type": "user_joined",
            "email": user.email,
            "username": user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        await connection_manager.broadcast(conversation_id, join_message)
        
        # Message handling loop
        while True:
            try:
                # Receive message with timeout
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=300.0  # 5 minute timeout
                )
                
                message_type = message.get("type")
                
                if message_type == "message":
                    content = message.get("content")
                    if content:
                        # Use discrete database session for message handling
                        async with get_db_context() as db:
                            await _handle_user_message(db, conversation_id, user, content)
                
                elif message_type == "typing_status":
                    is_typing = message.get("is_typing", False)
                    await _handle_typing_status(conversation_id, user, is_typing)
                
                elif message_type == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            except asyncio.TimeoutError:
                # Send ping to check if connection is alive
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except:
                    # Connection is dead
                    break
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for {user.email}")
                break
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                logger.error(traceback.format_exc())
                break
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        logger.error(traceback.format_exc())
    
    finally:
        # Clean up
        if connection_id and user:
            await connection_manager.disconnect(conversation_id, connection_id, user.email)
            
            # Remove from monitoring
            monitoring_service.remove_websocket_connection(str(connection_id))
            
            # Notify others of departure
            leave_message = {
                "type": "user_left",
                "email": user.email,
                "username": user.username if user else "Unknown",
                "timestamp": datetime.utcnow().isoformat()
            }
            await connection_manager.broadcast(conversation_id, leave_message)
        
        try:
            await websocket.close()
        except:
            pass
        
        logger.info(f"WebSocket connection closed for conversation {conversation_id}")

@router.get("/conversations/{conversation_id}/active-users")
async def get_active_users(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get list of active users in a conversation"""
    active_count = 0
    if conversation_id in connection_manager.active_connections:
        active_count = len(connection_manager.active_connections[conversation_id])
    
    return {
        "conversation_id": str(conversation_id),
        "active_connections": active_count,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/websocket/stats")
async def get_websocket_stats(
    current_user: User = Depends(get_current_user)
):
    """Get WebSocket connection statistics"""
    stats = connection_manager.get_connection_stats()
    stats["timestamp"] = datetime.utcnow().isoformat()
    return stats

@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str
):
    """WebSocket endpoint for user-specific notifications"""
    connection_id = None
    user = None
    
    try:
        await websocket.accept()
        
        # Authenticate using discrete database session
        async with get_db_context() as db:
            user = await authenticate_websocket(token, db)
            if not user:
                await websocket.close(code=4001, reason="Authentication failed")
                return
        
        # Add monitoring for this notification WebSocket
        import uuid
        connection_id = str(uuid.uuid4())
        monitoring_service.add_websocket_connection(
            connection_id=connection_id,
            user_id=str(user.id),
            tenant_id=str(user.tenant_id)
        )
        
        # Simple notification loop
        while True:
            try:
                # Wait for any message (keepalive)
                await websocket.receive_text()
                
                # Send notification count or other user-specific data
                await websocket.send_json({
                    "type": "notification_update",
                    "count": 0,  # You'd fetch actual notification count
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Notification WebSocket error: {e}")
                break
    
    finally:
        # Remove from monitoring
        if connection_id:
            monitoring_service.remove_websocket_connection(connection_id)
        
        try:
            await websocket.close()
        except:
            pass

@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    async with connection_lock:
        # Update current stats
        connection_stats["total"] = sum(len(sockets) for sockets in active_connections.values())
        connection_stats["by_conversation"] = {
            str(conv_id): len(sockets) 
            for conv_id, sockets in active_connections.items()
        }
        
        # Get ConnectionManager stats too
        cm_stats = connection_manager.get_stats()
        
        return {
            "active_connections": connection_stats,
            "connection_manager": cm_stats,
            "limits": {
                "max_total": MAX_TOTAL_CONNECTIONS,
                "max_per_conversation": MAX_CONNECTIONS_PER_CONVERSATION
            },
            "cleanup_task_running": cleanup_task is not None and not cleanup_task.done()
        }
