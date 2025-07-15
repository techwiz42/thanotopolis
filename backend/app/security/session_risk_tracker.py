"""
Session-Based Risk Tracking System

Monitors risk patterns across conversation sessions to detect
sophisticated multi-turn attacks like echo chamber and crescendo attacks.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RiskEvent:
    """Record of a single risk event in a session"""
    timestamp: datetime
    risk_score: float
    event_type: str
    patterns_detected: List[str]
    content_sample: str


@dataclass 
class SessionRiskProfile:
    """Risk profile for a conversation session"""
    session_id: str
    created_at: datetime
    risk_events: deque = field(default_factory=lambda: deque(maxlen=100))
    cumulative_risk: float = 0.0
    high_risk_count: int = 0
    injection_attempts: int = 0
    last_activity: datetime = field(default_factory=datetime.now)
    is_blocked: bool = False
    block_reason: Optional[str] = None


class SessionRiskTracker:
    """Track and analyze risk patterns across conversation sessions"""
    
    def __init__(
        self,
        high_risk_threshold: float = 0.7,
        session_timeout_minutes: int = 30,
        max_sessions: int = 10000,
        echo_threshold: int = 3,
        crescendo_window: int = 5
    ):
        self.sessions: Dict[str, SessionRiskProfile] = {}
        self.high_risk_threshold = high_risk_threshold
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_sessions = max_sessions
        self.echo_threshold = echo_threshold
        self.crescendo_window = crescendo_window
        
        # Pattern tracking for echo chamber detection
        self.pattern_history = defaultdict(lambda: deque(maxlen=10))
        
    def track_risk_event(
        self,
        session_id: str,
        risk_score: float,
        event_type: str,
        patterns_detected: List[str],
        content_sample: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Track a risk event and analyze session patterns
        
        Returns:
            Tuple of (should_block, block_reason)
        """
        # Get or create session
        session = self._get_or_create_session(session_id)
        
        # Record the event
        event = RiskEvent(
            timestamp=datetime.now(),
            risk_score=risk_score,
            event_type=event_type,
            patterns_detected=patterns_detected,
            content_sample=content_sample[:100]
        )
        session.risk_events.append(event)
        session.last_activity = datetime.now()
        
        # Update risk metrics
        session.cumulative_risk += risk_score
        if risk_score >= self.high_risk_threshold:
            session.high_risk_count += 1
        if event_type == "prompt_injection":
            session.injection_attempts += 1
        
        # Check for attack patterns
        should_block, reason = self._analyze_attack_patterns(session_id)
        
        if should_block:
            session.is_blocked = True
            session.block_reason = reason
            logger.warning(
                f"Session {session_id} blocked due to: {reason}. "
                f"Cumulative risk: {session.cumulative_risk:.2f}, "
                f"Injection attempts: {session.injection_attempts}"
            )
            
        return should_block, reason
    
    def _analyze_attack_patterns(
        self, 
        session_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Analyze session for sophisticated attack patterns"""
        session = self.sessions[session_id]
        
        # Check for immediate high-risk conditions
        if session.injection_attempts >= 5:
            return True, "Multiple injection attempts detected"
        
        if session.cumulative_risk >= 5.0:
            return True, "Cumulative risk threshold exceeded"
        
        # Check for echo chamber attack
        echo_detected, echo_reason = self._detect_echo_chamber(session)
        if echo_detected:
            return True, echo_reason
        
        # Check for crescendo attack
        crescendo_detected, crescendo_reason = self._detect_crescendo(session)
        if crescendo_detected:
            return True, crescendo_reason
        
        return False, None
    
    def _detect_echo_chamber(
        self, 
        session: SessionRiskProfile
    ) -> Tuple[bool, Optional[str]]:
        """Detect echo chamber attack patterns"""
        if len(session.risk_events) < self.echo_threshold:
            return False, None
        
        # Analyze pattern repetition
        recent_events = list(session.risk_events)[-10:]
        pattern_counts = defaultdict(int)
        
        for event in recent_events:
            for pattern in event.patterns_detected:
                pattern_counts[pattern] += 1
        
        # Check for repeated patterns
        for pattern, count in pattern_counts.items():
            if count >= self.echo_threshold:
                return True, f"Echo chamber attack detected: '{pattern}' repeated {count} times"
        
        # Check for semantic similarity (similar risk events in sequence)
        if len(recent_events) >= 5:
            similar_count = 0
            for i in range(1, len(recent_events)):
                if abs(recent_events[i].risk_score - recent_events[i-1].risk_score) < 0.1:
                    similar_count += 1
            
            if similar_count >= 4:
                return True, "Echo chamber attack: Repetitive similar risk patterns"
        
        return False, None
    
    def _detect_crescendo(
        self, 
        session: SessionRiskProfile
    ) -> Tuple[bool, Optional[str]]:
        """Detect crescendo attack patterns"""
        if len(session.risk_events) < self.crescendo_window:
            return False, None
        
        # Get recent events
        recent_events = list(session.risk_events)[-self.crescendo_window:]
        
        # Check for escalating risk scores
        risk_scores = [event.risk_score for event in recent_events]
        
        # Calculate if scores are generally increasing
        increasing_count = 0
        for i in range(1, len(risk_scores)):
            if risk_scores[i] > risk_scores[i-1]:
                increasing_count += 1
        
        # If 80% of transitions are increasing, it's likely a crescendo
        if increasing_count >= (len(risk_scores) - 1) * 0.8:
            start_risk = risk_scores[0]
            end_risk = risk_scores[-1]
            if end_risk > start_risk * 1.5:  # 50% increase
                return True, f"Crescendo attack detected: Risk escalated from {start_risk:.2f} to {end_risk:.2f}"
        
        # Check for escalating injection sophistication
        injection_events = [e for e in recent_events if e.event_type == "prompt_injection"]
        if len(injection_events) >= 3:
            # Check if patterns are becoming more complex
            pattern_lengths = [len(e.patterns_detected) for e in injection_events]
            if pattern_lengths == sorted(pattern_lengths):  # Monotonically increasing
                return True, "Crescendo attack: Escalating injection complexity"
        
        return False, None
    
    def _get_or_create_session(self, session_id: str) -> SessionRiskProfile:
        """Get existing session or create new one"""
        # Clean up old sessions if needed
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_old_sessions()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionRiskProfile(
                session_id=session_id,
                created_at=datetime.now()
            )
        
        return self.sessions[session_id]
    
    def _cleanup_old_sessions(self):
        """Remove inactive sessions"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, session in self.sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
        
        # If still over limit, remove oldest sessions
        if len(self.sessions) >= self.max_sessions:
            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1].last_activity
            )
            for session_id, _ in sorted_sessions[:len(self.sessions) - self.max_sessions + 1000]:
                del self.sessions[session_id]
    
    def get_session_status(self, session_id: str) -> Dict[str, any]:
        """Get current risk status for a session"""
        session = self.sessions.get(session_id)
        if not session:
            return {
                "exists": False,
                "is_blocked": False,
                "risk_level": "unknown"
            }
        
        risk_level = "low"
        if session.cumulative_risk >= 3.0:
            risk_level = "critical"
        elif session.cumulative_risk >= 2.0:
            risk_level = "high"
        elif session.cumulative_risk >= 1.0:
            risk_level = "medium"
        
        return {
            "exists": True,
            "is_blocked": session.is_blocked,
            "block_reason": session.block_reason,
            "risk_level": risk_level,
            "cumulative_risk": session.cumulative_risk,
            "injection_attempts": session.injection_attempts,
            "high_risk_count": session.high_risk_count,
            "event_count": len(session.risk_events),
            "session_duration": (datetime.now() - session.created_at).total_seconds()
        }
    
    def is_session_blocked(self, session_id: str) -> bool:
        """Check if a session is blocked"""
        session = self.sessions.get(session_id)
        return session.is_blocked if session else False


# Global instance
session_risk_tracker = SessionRiskTracker()