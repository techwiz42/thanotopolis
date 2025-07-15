"""
Adaptive Rate Limiting System

Implements risk-based rate limiting that becomes more restrictive
as session risk increases, protecting against automated attacks.
"""

import time
import logging
from typing import Dict, Optional, Tuple, List
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class RateLimitWindow:
    """Track requests within a time window"""
    requests: deque
    high_risk_requests: int = 0
    blocked_requests: int = 0


class AdaptiveRateLimiter:
    """
    Risk-aware rate limiting that adapts based on session behavior
    """
    
    def __init__(self):
        # Base rate limits (requests per minute)
        self.base_limits = {
            "low": 60,      # 1 per second
            "medium": 30,   # 1 per 2 seconds  
            "high": 10,     # 1 per 6 seconds
            "critical": 5,  # 1 per 12 seconds
            "blocked": 0    # No requests allowed
        }
        
        # Window tracking
        self.windows: Dict[str, RateLimitWindow] = defaultdict(
            lambda: RateLimitWindow(requests=deque())
        )
        
        # Cooldown periods after violations
        self.cooldowns: Dict[str, datetime] = {}
        self.cooldown_duration = timedelta(minutes=5)
        
        # Burst allowances
        self.burst_allowance = {
            "low": 5,
            "medium": 3,
            "high": 2,
            "critical": 1,
            "blocked": 0
        }
        
    async def check_rate_limit(
        self,
        session_id: str,
        risk_level: str = "low",
        risk_score: float = 0.0
    ) -> Tuple[bool, Optional[Dict[str, any]]]:
        """
        Check if request should be allowed based on rate limits
        
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = datetime.now()
        
        # Check if session is in cooldown
        if session_id in self.cooldowns:
            if current_time < self.cooldowns[session_id]:
                remaining_cooldown = (self.cooldowns[session_id] - current_time).total_seconds()
                return False, {
                    "reason": "cooldown_period",
                    "remaining_seconds": int(remaining_cooldown),
                    "message": f"Session in cooldown for {int(remaining_cooldown)} seconds"
                }
            else:
                # Cooldown expired
                del self.cooldowns[session_id]
        
        # Get window for session
        window = self.windows[session_id]
        
        # Clean old requests (older than 1 minute)
        cutoff_time = current_time - timedelta(minutes=1)
        while window.requests and window.requests[0] < cutoff_time:
            window.requests.popleft()
        
        # Get appropriate limit
        limit = self.base_limits.get(risk_level, self.base_limits["low"])
        burst = self.burst_allowance.get(risk_level, self.burst_allowance["low"])
        
        # Adjust limit based on risk score
        if risk_score > 0.8:
            limit = int(limit * 0.5)  # Half the limit for very high risk
        elif risk_score > 0.6:
            limit = int(limit * 0.7)  # 70% of limit for high risk
        
        # Check if request would exceed limit
        request_count = len(window.requests)
        
        # Check burst limit (requests in last 5 seconds)
        burst_cutoff = current_time - timedelta(seconds=5)
        burst_count = sum(1 for req in window.requests if req > burst_cutoff)
        
        if request_count >= limit:
            # Rate limit exceeded
            window.blocked_requests += 1
            
            # If multiple violations, apply cooldown
            if window.blocked_requests >= 3:
                self.cooldowns[session_id] = current_time + self.cooldown_duration
                logger.warning(
                    f"Session {session_id} placed in cooldown after "
                    f"{window.blocked_requests} rate limit violations"
                )
            
            return False, {
                "reason": "rate_limit_exceeded",
                "limit": limit,
                "window": "1 minute",
                "current_count": request_count,
                "message": f"Rate limit exceeded: {request_count}/{limit} requests per minute"
            }
        
        if burst_count >= burst:
            # Burst limit exceeded
            return False, {
                "reason": "burst_limit_exceeded",
                "limit": burst,
                "window": "5 seconds",
                "current_count": burst_count,
                "message": f"Burst limit exceeded: {burst_count}/{burst} requests in 5 seconds"
            }
        
        # Request allowed - record it
        window.requests.append(current_time)
        if risk_score >= 0.7:
            window.high_risk_requests += 1
        
        # Calculate remaining allowance
        remaining = limit - request_count - 1
        reset_time = (window.requests[0] + timedelta(minutes=1)).timestamp() if window.requests else 0
        
        return True, {
            "allowed": True,
            "limit": limit,
            "remaining": remaining,
            "reset_at": reset_time,
            "burst_remaining": burst - burst_count - 1,
            "risk_adjusted": risk_score > 0.6
        }
    
    def get_session_stats(self, session_id: str) -> Dict[str, any]:
        """Get rate limiting statistics for a session"""
        window = self.windows.get(session_id)
        if not window:
            return {"session_exists": False}
        
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=1)
        active_requests = [req for req in window.requests if req > cutoff_time]
        
        is_cooled_down = session_id in self.cooldowns and current_time < self.cooldowns[session_id]
        
        return {
            "session_exists": True,
            "current_requests": len(active_requests),
            "high_risk_requests": window.high_risk_requests,
            "blocked_requests": window.blocked_requests,
            "is_cooled_down": is_cooled_down,
            "cooldown_remaining": (
                (self.cooldowns[session_id] - current_time).total_seconds()
                if is_cooled_down else 0
            )
        }
    
    def apply_penalty(self, session_id: str, penalty_minutes: int = 10):
        """Apply a manual penalty/cooldown to a session"""
        self.cooldowns[session_id] = datetime.now() + timedelta(minutes=penalty_minutes)
        logger.info(f"Applied {penalty_minutes} minute penalty to session {session_id}")
    
    def clear_session(self, session_id: str):
        """Clear all rate limit data for a session"""
        if session_id in self.windows:
            del self.windows[session_id]
        if session_id in self.cooldowns:
            del self.cooldowns[session_id]
    
    async def cleanup_old_sessions(self):
        """Periodic cleanup of old session data"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        # Clean up windows with no recent activity
        for session_id, window in self.windows.items():
            if not window.requests or all(
                req < current_time - timedelta(minutes=30) for req in window.requests
            ):
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.windows[session_id]
        
        # Clean up expired cooldowns
        expired_cooldowns = [
            sid for sid, expiry in self.cooldowns.items()
            if expiry < current_time
        ]
        for session_id in expired_cooldowns:
            del self.cooldowns[session_id]
        
        if sessions_to_remove or expired_cooldowns:
            logger.info(
                f"Cleaned up {len(sessions_to_remove)} inactive sessions "
                f"and {len(expired_cooldowns)} expired cooldowns"
            )


# Global instance
adaptive_rate_limiter = AdaptiveRateLimiter()


# Background cleanup task
async def rate_limiter_cleanup_task():
    """Background task to clean up old rate limit data"""
    while True:
        try:
            await adaptive_rate_limiter.cleanup_old_sessions()
        except Exception as e:
            logger.error(f"Error in rate limiter cleanup: {e}")
        await asyncio.sleep(300)  # Run every 5 minutes