"""
Secure WebSocket Authentication

Provides secure WebSocket authentication using headers instead of URL parameters
to prevent token exposure in logs and browser history.
"""

import logging
from typing import Optional
from fastapi import WebSocket, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.auth.auth import AuthService
from app.db.database import get_db_context
from app.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


async def authenticate_websocket_secure(websocket: WebSocket) -> Optional[User]:
    """
    Secure WebSocket authentication via headers
    
    Args:
        websocket: WebSocket connection object
        
    Returns:
        User object if authentication successful, None otherwise
    """
    try:
        # Get authorization header
        auth_header = None
        client_ip = "unknown"
        
        # Extract headers from WebSocket
        for name, value in websocket.headers.items():
            if name.lower() == "authorization":
                auth_header = value
            elif name.lower() == "x-forwarded-for":
                client_ip = value.split(',')[0].strip()
            elif name.lower() == "x-real-ip":
                client_ip = value
        
        # Get client IP from scope if not found in headers
        if client_ip == "unknown" and hasattr(websocket, 'client'):
            client_ip = websocket.client.host if websocket.client else "unknown"
        
        # Validate authorization header format
        if not auth_header:
            logger.warning(f"WebSocket connection missing authorization header from IP: {client_ip}")
            audit_logger.log_websocket_auth_failure(
                ip_address=client_ip,
                reason="missing_authorization_header"
            )
            await websocket.close(code=4001, reason="Missing authorization header")
            return None
        
        if not auth_header.startswith("Bearer "):
            logger.warning(f"WebSocket connection invalid authorization header format from IP: {client_ip}")
            audit_logger.log_websocket_auth_failure(
                ip_address=client_ip,
                reason="invalid_auth_header_format"
            )
            await websocket.close(code=4001, reason="Invalid authorization header format")
            return None
        
        # Extract token
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        if not token:
            logger.warning(f"WebSocket connection empty token from IP: {client_ip}")
            audit_logger.log_websocket_auth_failure(
                ip_address=client_ip,
                reason="empty_token"
            )
            await websocket.close(code=4001, reason="Empty authentication token")
            return None
        
        # Validate token
        try:
            payload = AuthService.decode_token(token)
        except Exception as e:
            logger.warning(f"WebSocket token validation failed from IP: {client_ip} - {str(e)}")
            audit_logger.log_websocket_auth_failure(
                ip_address=client_ip,
                reason=f"token_validation_failed: {str(e)}"
            )
            await websocket.close(code=4001, reason="Invalid authentication token")
            return None
        
        # Get user from database
        async with get_db_context() as db:
            try:
                result = await db.execute(
                    select(User).where(User.id == payload.sub)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"WebSocket user not found for token from IP: {client_ip}")
                    audit_logger.log_websocket_auth_failure(
                        ip_address=client_ip,
                        reason="user_not_found"
                    )
                    await websocket.close(code=4001, reason="User not found")
                    return None
                
                if not user.is_active:
                    logger.warning(f"WebSocket inactive user attempted connection from IP: {client_ip}")
                    audit_logger.log_websocket_auth_failure(
                        ip_address=client_ip,
                        reason="user_inactive"
                    )
                    await websocket.close(code=4001, reason="User account inactive")
                    return None
                
                logger.info(f"WebSocket authentication successful for user {user.email} from IP: {client_ip}")
                return user
                
            except Exception as e:
                logger.error(f"WebSocket database error during authentication from IP: {client_ip} - {str(e)}")
                audit_logger.log_websocket_auth_failure(
                    ip_address=client_ip,
                    reason=f"database_error: {str(e)}"
                )
                await websocket.close(code=4001, reason="Authentication service unavailable")
                return None
                
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        # Try to get IP for logging
        try:
            client_ip = websocket.client.host if hasattr(websocket, 'client') and websocket.client else "unknown"
        except:
            client_ip = "unknown"
        
        audit_logger.log_websocket_auth_failure(
            ip_address=client_ip,
            reason=f"authentication_exception: {str(e)}"
        )
        
        try:
            await websocket.close(code=4001, reason="Authentication failed")
        except:
            pass  # Connection might already be closed
        
        return None


async def authenticate_websocket_with_conversation(
    websocket: WebSocket, 
    conversation_id: str
) -> Optional[User]:
    """
    Secure WebSocket authentication with conversation validation
    
    Args:
        websocket: WebSocket connection object
        conversation_id: UUID string of the conversation
        
    Returns:
        User object if authentication and authorization successful, None otherwise
    """
    # First authenticate the user
    user = await authenticate_websocket_secure(websocket)
    if not user:
        return None
    
    # TODO: Add conversation access validation here
    # This would check if the user has permission to access the specific conversation
    # For now, we'll just return the authenticated user
    
    return user


def get_websocket_client_info(websocket: WebSocket) -> dict:
    """
    Extract client information from WebSocket connection
    
    Args:
        websocket: WebSocket connection object
        
    Returns:
        Dictionary containing client information
    """
    info = {
        "ip_address": "unknown",
        "user_agent": "unknown",
        "origin": "unknown"
    }
    
    try:
        # Extract from headers
        for name, value in websocket.headers.items():
            name_lower = name.lower()
            if name_lower == "x-forwarded-for":
                info["ip_address"] = value.split(',')[0].strip()
            elif name_lower == "x-real-ip" and info["ip_address"] == "unknown":
                info["ip_address"] = value
            elif name_lower == "user-agent":
                info["user_agent"] = value
            elif name_lower == "origin":
                info["origin"] = value
        
        # Get IP from connection if not found in headers
        if info["ip_address"] == "unknown" and hasattr(websocket, 'client') and websocket.client:
            info["ip_address"] = websocket.client.host
            
    except Exception as e:
        logger.warning(f"Failed to extract WebSocket client info: {e}")
    
    return info


# Legacy function for backward compatibility (deprecated)
async def authenticate_websocket(token: str, db: AsyncSession) -> Optional[User]:
    """
    DEPRECATED: Legacy WebSocket authentication function
    
    This function is deprecated and should not be used for new implementations.
    Use authenticate_websocket_secure() instead which provides header-based authentication.
    
    Args:
        token: JWT token string
        db: Database session
        
    Returns:
        User object if authentication successful, None otherwise
    """
    logger.warning("Using deprecated authenticate_websocket function. Use authenticate_websocket_secure instead.")
    
    try:
        if not token:
            return None
        
        # Validate token
        payload = AuthService.decode_token(token)
        
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == payload.sub)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return None
        
        return user
        
    except Exception as e:
        logger.error(f"Legacy WebSocket authentication error: {e}")
        return None