from fastapi import WebSocket, WebSocketDisconnect 
from fastapi.websockets import WebSocketState
from typing import Dict, Set, Optional, List, Union, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from app.core.buffer_manager import buffer_manager
import contextlib
import json
import asyncio
import logging
import traceback
from enum import Enum
import random
import time

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DISCONNECTED = "disconnected"

class WebSocketConnection:
    def __init__(self, websocket: WebSocket, user_identifier: str):
        self.websocket = websocket
        self.user_identifier = user_identifier
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.state = ConnectionState.PENDING
        self._accept_lock = None
        self._send_lock = None

    async def _ensure_locks(self):
        """Ensure locks are created in async context"""
        if self._accept_lock is None:
            self._accept_lock = asyncio.Lock()
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """Initialize the connection (but don't accept - connection should already be accepted)"""
        await self._ensure_locks()
        if self.state != ConnectionState.PENDING:
            return False

        async with self._accept_lock:
            if self.state != ConnectionState.PENDING:
                return False

            try:
                # Just mark as accepted since connection is already accepted
                self.state = ConnectionState.ACCEPTED
                return True
            except Exception as e:
                logger.error(f"Failed to initialize websocket: {e}")
                self.state = ConnectionState.DISCONNECTED
                return False

    async def send_text(self, message: str, max_retries: int = 5, initial_delay: float = 0.1) -> bool:
        """Thread-safe message sending with retry logic"""
        await self._ensure_locks()

        retries = 0
        delay = initial_delay

        while retries < max_retries:
            if self.state != ConnectionState.ACCEPTED:
                return False

            async with self._send_lock:
                if self.state != ConnectionState.ACCEPTED:
                    return False

                try:
                    await self.websocket.send_text(message)
                    self.last_activity = datetime.utcnow()
                    return True
                except WebSocketDisconnect:
                    logger.warning(f"WebSocket disconnected. Retrying in {delay:.2f} seconds...")
                    self.state = ConnectionState.DISCONNECTED
                except Exception as e:
                    logger.error(f"Failed to send message: {e}")

            # Exponential backoff with jitter
            jitter = random.uniform(0.8, 1.2)
            delay = min(delay * 2 * jitter, 60)  # Cap the maximum delay at 60 seconds
            await asyncio.sleep(delay)
            retries += 1

        self.state = ConnectionState.DISCONNECTED
        return False

    async def close(self, code: int = 1000, reason: str = "normal closure"):
        """Thread-safe connection closure"""
        await self._ensure_locks()
        if self.state == ConnectionState.DISCONNECTED:
            return

        async with self._accept_lock:
            if self.state == ConnectionState.DISCONNECTED:
                return

            try:
                await self.websocket.close(code=code, reason=reason)
            except Exception as e:
                logger.error(f"Error closing websocket: {e}")
            finally:
                self.state = ConnectionState.DISCONNECTED

class ConnectionHealth:
    def __init__(self):
        # Connection storage
        self.active_connections: Dict[UUID, Dict[str, WebSocketConnection]] = {}
        self.private_conversations: Set[UUID] = set()
        self.connection_health_task = None 
        # Configuration - Limits
        self.MAX_TOTAL_CONNECTIONS = 50000
        self.MAX_CONNECTIONS_PER_CONVERSATION = 250
        
        # Configuration - Timeouts
        self.HANDSHAKE_TIMEOUT = 30.0    # Initial handshake timeout
        self.LOCK_ACQUIRE_TIMEOUT = 10.0  # Lock acquisition timeout (increased)
        self.CONNECTION_TIMEOUT = 3600.0  # Overall connection lifetime timeout (increased to 1 hour)
        self.CLEANUP_TIMEOUT = 10.0      # Cleanup operation timeout
        self.MESSAGE_TIMEOUT = 95.0      # Message processing timeout (increased to match collaboration timeout)
        self.DB_OPERATION_TIMEOUT = 10.0  # Database operation timeout (increased)
        
        # Metrics
        self.metrics = {
            'total_connections': 0,
            'peak_connections': 0,
            'failed_connections': 0,
            'successful_connections': 0,
            'timeouts': {
                'handshake': 0,
                'lock_acquisition': 0,
                'message': 0,
                'cleanup': 0,
                'db': 0
            }
        }

        # Initialize these as None, will create in async context
        self._global_lock = None
        self._connection_locks = {}
        self._cleanup_task = None
        self._cleanup_task_lock = None
        self._privacy_lock = None
        self._metrics_lock = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Initialize async components safely"""
        if not self._initialized:
            self._global_lock = asyncio.Lock()
            self._cleanup_task_lock = asyncio.Lock()
            self._privacy_lock = asyncio.Lock()
            self._metrics_lock = asyncio.Lock()
            self._initialized = True
            logger.info("ConnectionHealth initialized")

    async def initialize_connection_manager(self):
        """Initialize the connection manager"""
        await buffer_manager._ensure_initialized()  # Initialize buffer first
        if not self.connection_health_task or self.connection_health_task.done():
            self.connection_health_task = asyncio.create_task(
                self.monitor_connection_health()
            )

    async def get_timeout_metrics(self):
        """Get current timeout metrics."""
        await self._ensure_initialized()
        async with self._metrics_lock:
            return self.metrics['timeouts']

    async def ensure_cleanup_task(self):
        """Ensure cleanup task is running in the current event loop"""
        await self._ensure_initialized()
        async with self._cleanup_task_lock:
            if self._cleanup_task is None or self._cleanup_task.done():
                try:
                    loop = asyncio.get_running_loop()
                    self._cleanup_task = loop.create_task(self._periodic_cleanup())
                except Exception as e:
                    logger.error(f"Failed to start cleanup task: {e}")

    async def get_conversation_lock(self, conversation_id: UUID) -> asyncio.Lock:
        """Get or create a lock for a specific conversation"""
        await self._ensure_initialized()
        async with self._global_lock:
            if conversation_id not in self._connection_locks:
                self._connection_locks[conversation_id] = asyncio.Lock()
            return self._connection_locks[conversation_id]

    async def update_timeout_metrics(self, timeout_type: str):
        """Update timeout metrics safely"""
        await self._ensure_initialized()
        async with self._metrics_lock:
            if timeout_type in self.metrics['timeouts']:
                self.metrics['timeouts'][timeout_type] += 1

    async def update_metrics(self, updates: Dict[str, int]):
        """Thread-safe metrics update"""
        await self._ensure_initialized()
        async with self._metrics_lock:
            for key, value in updates.items():
                if key in self.metrics:
                    self.metrics[key] += value
            self.metrics['peak_connections'] = max(
                self.metrics['peak_connections'],
                self.metrics['total_connections']
            )

    async def enqueue_connection(
        self,
        websocket: WebSocket,
        conversation_id: UUID,
        user_identifier: str
    ) -> Optional[str]:
        """Enhanced connection handling with starvation prevention"""
        await self._ensure_initialized()

        # Pre-generate connection ID and object outside of locks
        connection_id = str(uuid4())
        connection = WebSocketConnection(websocket, user_identifier)
        
        # STT connections get priority in high-contention scenarios
        is_stt_connection = 'streaming_stt' in user_identifier
        
        try:
            # Check global limits with timeout and retry for STT connections
            retry_count = 0
            max_retries = 3 if is_stt_connection else 1
            
            while retry_count < max_retries:
                try:
                    # Use progressively longer timeout for retries
                    timeout_multiplier = 1 + (retry_count * 0.5)
                    adjusted_timeout = self.LOCK_ACQUIRE_TIMEOUT * timeout_multiplier
                    
                    async with asyncio.timeout(adjusted_timeout):
                        async with self._global_lock:
                            # Make a temporary exception for STT connections in high load
                            if self.metrics['total_connections'] >= self.MAX_TOTAL_CONNECTIONS:
                                if is_stt_connection and self.metrics['total_connections'] < self.MAX_TOTAL_CONNECTIONS * 1.05:
                                    # Allow 5% over-provisioning for STT connections
                                    logger.warning("Allowing STT connection despite connection limit")
                                else:
                                    logger.error("Global connection limit reached")
                                    return None
                            
                            # Early initialization outside conversation lock for better performance
                            await connection.initialize()
                    break  # Successfully acquired lock and checked limits
                    
                except asyncio.TimeoutError:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(f"Timeout acquiring global lock after {retry_count} attempts")
                        await self.update_timeout_metrics('lock_acquisition')
                        return None
                    logger.warning(f"Timeout acquiring global lock (attempt {retry_count}/{max_retries})")
                    # Add a small delay between retries with jitter
                    await asyncio.sleep(0.1 * (1 + 0.5 * retry_count) * random.uniform(0.8, 1.2))
            
            # Get and acquire conversation-specific lock with similar retry logic
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Use progressively longer timeout for retries
                    timeout_multiplier = 1 + (retry_count * 0.5)
                    adjusted_timeout = self.LOCK_ACQUIRE_TIMEOUT * timeout_multiplier
                    
                    async with asyncio.timeout(adjusted_timeout):
                        conv_lock = await self.get_conversation_lock(conversation_id)
                        async with conv_lock:
                            # Check conversation-specific limits
                            conv_connections = self.active_connections.get(conversation_id, {})
                            
                            # Apply conversation limits but with temporary exception for STT
                            if len(conv_connections) >= self.MAX_CONNECTIONS_PER_CONVERSATION:
                                if is_stt_connection and len(conv_connections) < self.MAX_CONNECTIONS_PER_CONVERSATION * 1.05:
                                    # Allow 5% over-provisioning for STT connections per conversation
                                    logger.warning(f"Allowing STT connection despite limit for conversation {conversation_id}")
                                else:
                                    logger.error(f"Connection limit reached for conversation {conversation_id}")
                                    return None
                            
                            # Connection was already initialized above
                            if connection.state != ConnectionState.ACCEPTED:
                                logger.error("Connection in invalid state")
                                return None
                            
                            # Store the connection
                            if conversation_id not in self.active_connections:
                                self.active_connections[conversation_id] = {}
                            self.active_connections[conversation_id][connection_id] = connection
                            
                            # Update metrics
                            await self.update_metrics({
                                'total_connections': 1,
                                'successful_connections': 1
                            })
                            
                            logger.info(f"Connection established: {connection_id} for {user_identifier}")
                            return connection_id
                            
                except asyncio.TimeoutError:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(f"Timeout acquiring conversation lock after {retry_count} attempts")
                        await self.update_timeout_metrics('lock_acquisition')
                        return None
                    logger.warning(f"Timeout acquiring conversation lock (attempt {retry_count}/{max_retries})")
                    # Add a small delay between retries with jitter
                    await asyncio.sleep(0.1 * (1 + 0.5 * retry_count) * random.uniform(0.8, 1.2))

        except Exception as e:
            logger.error(f"Connection establishment failed: {str(e)}")
            await self.update_metrics({'failed_connections': 1})
            return None

    async def disconnect(
        self, 
        conversation_id: UUID, 
        connection_id: str,
        reason: str = "normal closure"
    ):
        """Enhanced disconnection handling"""
        await self._ensure_initialized()
        try:
            conv_lock = await self.get_conversation_lock(conversation_id)
            async with conv_lock:
                if conversation_id in self.active_connections:
                    connection = self.active_connections[conversation_id].get(connection_id)
                    if connection:
                        await connection.close(reason=reason)
                        del self.active_connections[conversation_id][connection_id]
                        await self.update_metrics({'total_connections': -1})

                        if not self.active_connections[conversation_id]:
                            del self.active_connections[conversation_id]
                            async with self._privacy_lock:
                                self.private_conversations.discard(conversation_id)

        except Exception as e:
            logger.error(f"Error during disconnection: {e}")

    async def broadcast(
        self,
        conversation_id: UUID,
        message: dict,
        exclude_id: Optional[str] = None
    ):
        """Enhanced broadcast with improved fairness and starvation prevention"""
        await self._ensure_initialized()
        try:
            # Check if conversation exists in active connections
            if conversation_id not in self.active_connections:
                return

            # Serialize message once
            message_json = json.dumps(message)
            
            # Get a copy of connections without holding the lock for too long
            connections = []
            try:
                # Use timeout to prevent indefinite blocking
                async with asyncio.timeout(self.LOCK_ACQUIRE_TIMEOUT):
                    conv_lock = await self.get_conversation_lock(conversation_id)
                    async with conv_lock:
                        if conversation_id in self.active_connections:
                            connections = list(self.active_connections[conversation_id].items())
            except asyncio.TimeoutError:
                logger.warning(f"Timeout acquiring conversation lock for broadcast to {conversation_id}")
                await self.update_timeout_metrics('lock_acquisition')
                return  # Skip this broadcast rather than blocking indefinitely
            
            # Process connections in a fair way
            failed_connections = []
            
            # Prioritize STT connections for broadcasts to ensure they're processed first
            # This prevents starvation of STT connections during high load
            stt_connections = []
            regular_connections = []
            
            # Sort connections by type - STT first, then others
            for connection_id, connection in connections:
                if connection_id == exclude_id:
                    continue
                    
                if 'streaming_stt' in connection.user_identifier:
                    stt_connections.append((connection_id, connection))
                else:
                    regular_connections.append((connection_id, connection))
            
            # Process STT connections first with slightly longer timeout
            for connection_id, connection in stt_connections:
                try:
                    async with asyncio.timeout(self.MESSAGE_TIMEOUT * 1.5):  # 50% longer timeout for STT
                        if not await connection.send_text(message_json):
                            failed_connections.append(connection_id)
                except asyncio.TimeoutError:
                    logger.error(f"Message send timeout for STT connection {connection_id}")
                    await self.update_timeout_metrics('message')
                    failed_connections.append(connection_id)
                # Yield control briefly to prevent blocking the event loop
                await asyncio.sleep(0)
            
            # Then process regular connections
            for connection_id, connection in regular_connections:
                try:
                    async with asyncio.timeout(self.MESSAGE_TIMEOUT):
                        if not await connection.send_text(message_json):
                            failed_connections.append(connection_id)
                except asyncio.TimeoutError:
                    logger.error(f"Message send timeout for connection {connection_id}")
                    await self.update_timeout_metrics('message')
                    failed_connections.append(connection_id)
                # Yield control briefly to prevent blocking the event loop
                await asyncio.sleep(0)

            # Clean up failed connections without blocking other operations
            if failed_connections:
                asyncio.create_task(self._clean_up_failed_connections(conversation_id, failed_connections))

        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            logger.error(traceback.format_exc())
    
    async def _clean_up_failed_connections(self, conversation_id: UUID, failed_connections: List[str]):
        """Cleanup failed connections as a separate task to avoid blocking broadcast"""
        for failed_id in failed_connections:
            try:
                await self.disconnect(
                    conversation_id,
                    failed_id,
                    reason="failed to send message"
                )
                # Brief pause between disconnections to prevent overwhelming resources
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Error disconnecting failed connection {failed_id}: {e}")

    async def _periodic_cleanup(self):
        """Background task to clean up stale connections with improved starvation prevention"""
        while True:
            try:
                await asyncio.sleep(10)  # Run cleanup every 10 seconds
                current_time = datetime.utcnow()
                
                # Get a copy of all conversation IDs without holding the global lock for too long
                conv_ids = []
                try:
                    async with asyncio.timeout(self.LOCK_ACQUIRE_TIMEOUT):
                        async with self._global_lock:
                            conv_ids = list(self.active_connections.keys())
                except asyncio.TimeoutError:
                    logger.warning("Timeout acquiring global lock for cleanup - will try again next cycle")
                    continue
                
                # Process each conversation individually - this prevents global lock starvation
                for conv_id in conv_ids:
                    try:
                        # Use a timeout when acquiring the conversation lock
                        async with asyncio.timeout(self.LOCK_ACQUIRE_TIMEOUT):
                            conv_lock = await self.get_conversation_lock(conv_id)
                            async with conv_lock:
                                # Check if conversation still exists (might have been removed by another process)
                                if conv_id not in self.active_connections:
                                    continue
                                    
                                connections = list(self.active_connections[conv_id].items())
                                
                                # Process a limited number of connections per cycle to prevent locking for too long
                                # This improves fairness by not letting one conversation monopolize cleanup resources
                                for conn_id, connection in connections[:20]:  # Process max 20 connections per conv per cycle
                                    # Skip timeout for STT connections - never time them out
                                    if 'streaming_stt' in connection.user_identifier:
                                        continue
                                    
                                    # Apply timeout for all other connections
                                    if (current_time - connection.last_activity).total_seconds() > self.CONNECTION_TIMEOUT:
                                        await self.disconnect(
                                            conv_id,
                                            conn_id,
                                            reason="connection timeout"
                                        )
                                        
                                # Yield control to event loop briefly after each conversation
                                await asyncio.sleep(0.01)
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout acquiring lock for conversation {conv_id} - will try again next cycle")
                        # Continue to next conversation rather than breaking the entire loop
                        continue
                    except Exception as conv_error:
                        logger.error(f"Error cleaning up conversation {conv_id}: {conv_error}")
                        # Continue to next conversation

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                # Sleep a bit longer after an error
                await asyncio.sleep(5)

    async def set_privacy(self, conversation_id: UUID, is_private: bool) -> None:
        """Set privacy mode for a conversation"""
        await self._ensure_initialized()
        try:
            async with self._privacy_lock:
                if is_private:
                    self.private_conversations.add(conversation_id)
                else:
                    self.private_conversations.discard(conversation_id)
            
            logger.info(f"Privacy set for conversation {conversation_id}: {'Private' if is_private else 'Public'}")
        
        except Exception as e:
            logger.error(f"Error setting privacy for conversation {conversation_id}: {e}")

    async def is_private(self, conversation_id: UUID) -> bool:
        """Check if a conversation is in private mode"""
        await self._ensure_initialized()
        async with self._privacy_lock:
            return conversation_id in self.private_conversations

    async def get_connection_metrics(self) -> dict:
        """Get current connection metrics."""
        await self._ensure_initialized()
        async with self._metrics_lock:
            metrics = {
                **self.metrics,
                'current_active_connections': sum(
                    len(connections)
                    for connections in self.active_connections.values()
                ),
                'active_conversations': len(self.active_connections)
            }
            # Use self.metrics['timeouts'] directly
            metrics['timeouts'] = self.metrics['timeouts']
            return metrics

# Global connection health manager
connection_health = ConnectionHealth()

async def initialize_connection_health():
    """Initialize the connection health manager and start background tasks"""
    await buffer_manager._ensure_initialized()  # Initialize buffer first
    await connection_health._ensure_initialized()  # Initialize connection health
    await connection_health.ensure_cleanup_task()  # Start background cleanup task
