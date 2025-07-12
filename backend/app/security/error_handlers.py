"""
Secure Error Handlers

Provides secure error handling that prevents sensitive information
disclosure while maintaining useful error messages for legitimate users.
"""

import logging
import traceback
from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class SecureErrorHandler:
    """Handles errors securely without leaking sensitive information"""
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize secure error handler
        
        Args:
            debug_mode: Whether to include detailed error info (dev only)
        """
        self.debug_mode = debug_mode
        
        # Error messages that are safe to expose
        self.safe_error_messages = {
            400: "Bad request - please check your input",
            401: "Authentication required",
            403: "Access denied - insufficient permissions", 
            404: "Resource not found",
            405: "Method not allowed",
            408: "Request timeout",
            409: "Conflict - resource already exists",
            413: "Request payload too large",
            415: "Unsupported media type",
            422: "Invalid request data",
            429: "Too many requests - please try again later",
            500: "Internal server error",
            502: "Service temporarily unavailable",
            503: "Service unavailable", 
            504: "Request timeout"
        }
        
        # Patterns to filter from error messages
        self.sensitive_patterns = [
            'database', 'sql', 'postgresql', 'connection',
            'secret', 'key', 'token', 'password', 'credential',
            'internal', 'server', 'host', 'port', 'path',
            'traceback', 'exception', 'error in line',
            'sqlalchemy', 'fastapi', 'uvicorn', 'pydantic'
        ]
    
    async def handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions securely"""
        try:
            status_code = exc.status_code
            
            # Log the actual error details
            client_ip = self._get_client_ip(request)
            logger.warning(
                f"HTTP {status_code} error: {request.method} {request.url.path} "
                f"from {client_ip} - {str(exc.detail)}"
            )
            
            # Get safe error message
            safe_message = self.safe_error_messages.get(
                status_code, 
                "An error occurred while processing your request"
            )
            
            # For authentication/authorization errors, log security event
            if status_code in [401, 403]:
                audit_logger.log_authentication_failure(
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent", "unknown"),
                    failure_reason=f"http_{status_code}"
                )
            
            # Prepare response
            response_data = {
                "detail": safe_message,
                "status_code": status_code
            }
            
            # In debug mode, include filtered error details
            if self.debug_mode and hasattr(exc, 'detail'):
                filtered_detail = self._filter_sensitive_info(str(exc.detail))
                if filtered_detail != str(exc.detail):
                    response_data["debug_info"] = filtered_detail
            
            return JSONResponse(
                status_code=status_code,
                content=response_data
            )
            
        except Exception as e:
            logger.error(f"Error in HTTP exception handler: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    async def handle_validation_error(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle validation errors securely"""
        try:
            client_ip = self._get_client_ip(request)
            
            # Log validation error
            logger.warning(
                f"Validation error: {request.method} {request.url.path} "
                f"from {client_ip} - {len(exc.errors())} errors"
            )
            
            # Filter validation errors to prevent information leakage
            safe_errors = []
            for error in exc.errors():
                safe_error = {
                    "field": ".".join(str(loc) for loc in error.get("loc", [])),
                    "message": self._get_safe_validation_message(error.get("type", ""), error.get("msg", ""))
                }
                safe_errors.append(safe_error)
            
            response_data = {
                "detail": "Invalid request data",
                "errors": safe_errors[:10]  # Limit to 10 errors to prevent DoS
            }
            
            # In debug mode, include original error count
            if self.debug_mode:
                response_data["total_errors"] = len(exc.errors())
            
            return JSONResponse(
                status_code=422,
                content=response_data
            )
            
        except Exception as e:
            logger.error(f"Error in validation exception handler: {e}")
            return JSONResponse(
                status_code=422,
                content={"detail": "Invalid request data"}
            )
    
    async def handle_internal_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle internal server errors securely"""
        try:
            client_ip = self._get_client_ip(request)
            
            # Log the full error details internally
            logger.error(
                f"Internal server error: {request.method} {request.url.path} "
                f"from {client_ip} - {type(exc).__name__}: {str(exc)}"
            )
            
            # Log full traceback for debugging
            if self.debug_mode:
                logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Log security event for potential attack
            audit_logger.log_suspicious_activity(
                activity_type="internal_server_error",
                details={
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "error_type": type(exc).__name__,
                    "user_agent": request.headers.get("user-agent", "unknown")
                },
                ip_address=client_ip
            )
            
            # Return generic error message
            response_data = {
                "detail": "Internal server error",
                "type": "internal_error"
            }
            
            # In debug mode, include error type (but not details)
            if self.debug_mode:
                response_data["error_type"] = type(exc).__name__
            
            return JSONResponse(
                status_code=500,
                content=response_data
            )
            
        except Exception as e:
            logger.error(f"Error in internal error handler: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    async def handle_not_found(self, request: Request, exc) -> JSONResponse:
        """Handle 404 errors securely"""
        try:
            client_ip = self._get_client_ip(request)
            
            logger.warning(f"404 Not Found: {request.method} {request.url.path} from {client_ip}")
            
            # Check for suspicious patterns in the URL
            url_path = str(request.url.path).lower()
            suspicious_patterns = [
                '.php', '.asp', '.jsp', 'admin', 'wp-', 'config',
                '../', 'etc/passwd', 'proc/', 'cmd.exe'
            ]
            
            if any(pattern in url_path for pattern in suspicious_patterns):
                audit_logger.log_suspicious_activity(
                    activity_type="suspicious_404_pattern",
                    details={
                        "requested_path": str(request.url.path),
                        "method": request.method,
                        "user_agent": request.headers.get("user-agent", "unknown")
                    },
                    ip_address=client_ip
                )
            
            # Return minimal information
            response_data = {
                "detail": "Resource not found"
            }
            
            # Only include helpful information for legitimate API endpoints
            if request.url.path.startswith("/api/"):
                response_data["available_endpoints"] = {
                    "authentication": "/api/auth",
                    "conversations": "/api/conversations", 
                    "documentation": "/docs"
                }
            
            return JSONResponse(
                status_code=404,
                content=response_data
            )
            
        except Exception as e:
            logger.error(f"Error in 404 handler: {e}")
            return JSONResponse(
                status_code=404,
                content={"detail": "Resource not found"}
            )
    
    def _filter_sensitive_info(self, message: str) -> str:
        """Filter sensitive information from error messages"""
        filtered_message = message.lower()
        
        # Check for sensitive patterns
        for pattern in self.sensitive_patterns:
            if pattern in filtered_message:
                return "Error details filtered for security"
        
        # Remove file paths
        import re
        message = re.sub(r'/[a-zA-Z0-9_/.-]+\.py', '[file path]', message)
        message = re.sub(r'line \d+', '[line number]', message)
        
        return message
    
    def _get_safe_validation_message(self, error_type: str, original_message: str) -> str:
        """Get safe validation error messages"""
        safe_messages = {
            "missing": "This field is required",
            "type_error": "Invalid data type",
            "value_error": "Invalid value", 
            "assertion_error": "Value does not meet requirements",
            "length_error": "Invalid length",
            "regex_error": "Invalid format",
            "enum_error": "Invalid option selected",
            "url_error": "Invalid URL format",
            "email_error": "Invalid email format",
            "json_error": "Invalid JSON format"
        }
        
        # Return safe message or filtered original
        for error_key, safe_msg in safe_messages.items():
            if error_key in error_type:
                return safe_msg
        
        # Filter the original message
        return self._filter_sensitive_info(original_message)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"


# Global error handler instance
error_handler = SecureErrorHandler(debug_mode=False)  # Set to True only for development