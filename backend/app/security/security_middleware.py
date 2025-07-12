"""
Security Middleware for FastAPI Application

Provides comprehensive security headers, request size limiting,
and other security-related middleware functionality.
"""

import logging
import time
from typing import Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all HTTP responses"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Security headers configuration
        self.security_headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Force HTTPS connections
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' wss: ws: https:; "
                "media-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            ),
            
            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Prevent DNS prefetching
            "X-DNS-Prefetch-Control": "off",
            
            # Disable features that could be misused
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            )
        }
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        try:
            # Process the request
            response = await call_next(request)
            
            # Add security headers
            for header, value in self.security_headers.items():
                response.headers[header] = value
            
            # Add custom headers based on response type
            if hasattr(response, 'media_type'):
                if response.media_type == "application/json":
                    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                    response.headers["Pragma"] = "no-cache"
                    response.headers["Expires"] = "0"
            
            return response
            
        except Exception as e:
            logger.error(f"Security headers middleware error: {e}")
            # Don't fail the request due to header issues
            return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request payload size to prevent DoS attacks"""
    
    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        """Check request size before processing"""
        try:
            # Check Content-Length header
            content_length = request.headers.get("content-length")
            if content_length:
                content_length = int(content_length)
                if content_length > self.max_size:
                    client_ip = self._get_client_ip(request)
                    logger.warning(f"Request size limit exceeded: {content_length} bytes from IP: {client_ip}")
                    
                    # Log security event
                    audit_logger.log_suspicious_activity(
                        activity_type="oversized_request",
                        details={
                            "content_length": content_length,
                            "max_allowed": self.max_size,
                            "endpoint": str(request.url),
                            "method": request.method
                        },
                        ip_address=client_ip
                    )
                    
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": "Request payload too large",
                            "max_size_mb": self.max_size // (1024 * 1024)
                        }
                    )
            
            return await call_next(request)
            
        except ValueError:
            # Invalid Content-Length header
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header"}
            )
        except Exception as e:
            logger.error(f"Request size limit middleware error: {e}")
            return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    """Audit security-related requests and responses"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Sensitive endpoints to monitor
        self.monitored_endpoints = {
            "/api/auth/login",
            "/api/auth/register", 
            "/api/auth/refresh",
            "/api/admin/",
            "/api/billing/",
            "/api/users/",
            "/api/tenants/"
        }
        
        # Suspicious patterns in requests
        self.suspicious_patterns = [
            "script", "javascript:", "vbscript:", "onload=", "onerror=",
            "eval(", "alert(", "confirm(", "prompt(",
            "../", "..\\", "/etc/passwd", "/proc/", "cmd.exe",
            "union select", "drop table", "delete from", "insert into"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Monitor and audit security-relevant requests"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        try:
            # Check for suspicious patterns in URL
            url_str = str(request.url)
            if any(pattern in url_str.lower() for pattern in self.suspicious_patterns):
                audit_logger.log_suspicious_activity(
                    activity_type="suspicious_url_pattern",
                    details={
                        "url": url_str,
                        "method": request.method,
                        "user_agent": request.headers.get("user-agent", "unknown")
                    },
                    ip_address=client_ip
                )
            
            # Process the request
            response = await call_next(request)
            
            # Audit authentication failures
            if (str(request.url.path) in self.monitored_endpoints and 
                response.status_code in [401, 403]):
                
                audit_logger.log_authentication_failure(
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent", "unknown")
                )
            
            # Monitor slow responses (potential DoS)
            response_time = time.time() - start_time
            if response_time > 10.0:  # Responses taking over 10 seconds
                audit_logger.log_suspicious_activity(
                    activity_type="slow_response",
                    details={
                        "response_time": response_time,
                        "endpoint": str(request.url.path),
                        "method": request.method,
                        "status_code": response.status_code
                    },
                    ip_address=client_ip
                )
            
            return response
            
        except Exception as e:
            # Log any unhandled exceptions
            audit_logger.log_suspicious_activity(
                activity_type="request_processing_error",
                details={
                    "error": str(e),
                    "endpoint": str(request.url.path) if hasattr(request, 'url') else "unknown",
                    "method": request.method if hasattr(request, 'method') else "unknown"
                },
                ip_address=client_ip
            )
            raise
    
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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Basic rate limiting middleware"""
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, Dict[str, Any]] = {}
        self.cleanup_interval = 60  # Clean up old entries every minute
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting based on IP address"""
        try:
            client_ip = self._get_client_ip(request)
            current_time = time.time()
            
            # Clean up old entries periodically
            if current_time - self.last_cleanup > self.cleanup_interval:
                self._cleanup_old_entries(current_time)
                self.last_cleanup = current_time
            
            # Initialize or update request count for this IP
            if client_ip not in self.request_counts:
                self.request_counts[client_ip] = {
                    "count": 1,
                    "window_start": current_time
                }
            else:
                ip_data = self.request_counts[client_ip]
                
                # Reset window if more than a minute has passed
                if current_time - ip_data["window_start"] > 60:
                    ip_data["count"] = 1
                    ip_data["window_start"] = current_time
                else:
                    ip_data["count"] += 1
                
                # Check rate limit
                if ip_data["count"] > self.requests_per_minute:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    
                    # Log rate limit violation
                    audit_logger.log_rate_limit_exceeded(
                        user_id="unknown",
                        endpoint=str(request.url.path),
                        ip_address=client_ip
                    )
                    
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit exceeded",
                            "retry_after": 60
                        },
                        headers={"Retry-After": "60"}
                    )
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            return await call_next(request)
    
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
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove old rate limiting entries"""
        expired_ips = [
            ip for ip, data in self.request_counts.items()
            if current_time - data["window_start"] > 120  # Remove entries older than 2 minutes
        ]
        
        for ip in expired_ips:
            del self.request_counts[ip]