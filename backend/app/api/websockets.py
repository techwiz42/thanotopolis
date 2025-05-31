# backend/app/api/websockets.py
from fastapi import APIRouter, WebSocket, Depends, HTTPException
from fastapi.websockets import WebSocketDisconnect, WebSocketState
from sqlalchemy import select, update, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Set, Optional, List, Union
from uuid import UUID, uuid4
from datetime import datetime
import json
import asyncio
import logging
import traceback
from app.auth.auth import get_current_user, get_tenant_from_request
from app.core.config import settings
from app.db.database import get_db
from app.models.models import User, Tenant

logger = logging.getLogger(__name__)
router = APIRouter()

# Connection tracking
active_connections: Dict[UUID, Set[WebSocket]] = {}
connection_lock = asyncio.Lock()

class ConnectionManager:
    """Manages WebSocket connections for conversations"""
    
    def __init__(self):
        self.active_connections: Dict[UUID, Dict[str, WebSocket]] = {}
        self.user_connections: Dict[str, Set[UUID]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, conversation_id: UUID, user_email: str) -> str:
        """Register a new connection"""
        async with self.lock:
            connection_id = str(uuid4())
            
            # Initialize conversation connections if needed
            if conversation_id not in self.active_connections:
                self.active_connections[conversation_id] = {}
            
            # Add connection
            self.active_connections[conversation_id][connection_id] = websocket
            
            # Track user connections
            if user_email not in self.user_connections:
                self.user_connections[user_email] = set()
            self.user_connections[user_email].add(conversation_id)
            
            logger.info(f"Connected: {user_email} to conversation {conversation_id}")
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
            
            logger.info(f"Disconnected: {user_email} from conversation {conversation_id}")
    
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
    content: str
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
        
        # Broadcast regular message
        broadcast_message = {
            "type": "message",
            "content": content,
            "id": message_id,
            "identifier": user.email,
            "is_owner": True,
            "email": user.email,
            "timestamp": datetime.utcnow().isoformat(),
            "user_metadata": {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        }
        
        await connection_manager.broadcast(conversation_id, broadcast_message)
        
        # Here you would typically save the message to database
        # For now, we'll just log it
        logger.info(f"Message from {user.email} in conversation {conversation_id}: {content[:50]}...")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        logger.error(traceback.format_exc())
        
        # Send error message
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
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Main WebSocket endpoint for conversations"""
    connection_id = None
    user = None
    
    try:
        # Accept connection first
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for conversation {conversation_id}")
        
        # Authenticate
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
        
        # Send welcome message
        welcome_message = {
            "type": "system",
            "content": f"Welcome to conversation {conversation_id}",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_json(welcome_message)
        
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

@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for user-specific notifications"""
    try:
        await websocket.accept()
        
        # Authenticate
        user = await authenticate_websocket(token, db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
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
        try:
            await websocket.close()
        except:
            pass
