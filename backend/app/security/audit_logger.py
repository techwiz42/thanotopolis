"""
Security Audit Logging System

Comprehensive security event logging for the Thanotopolis platform.
Tracks security incidents, prompt injection attempts, authentication failures,
and other security-related events.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Create security logs directory
SECURITY_LOGS_DIR = Path("/home/peter/thanotopolis_dev/logs/security")
SECURITY_LOGS_DIR.mkdir(parents=True, exist_ok=True)


class SecurityAuditLogger:
    """Comprehensive security event logging"""
    
    def __init__(self):
        """Initialize security audit logger"""
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Add file handler for security events
            log_file = SECURITY_LOGS_DIR / "security_audit.log"
            handler = logging.FileHandler(log_file)
            
            # Detailed formatter for security events
            formatter = logging.Formatter(
                '%(asctime)s - SECURITY - %(levelname)s - %(message)s - '
                '[PID:%(process)d] [Thread:%(thread)d]'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
            # Also add console handler for immediate visibility
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def log_prompt_injection_attempt(
        self, 
        user_id: str, 
        content: str, 
        session_id: Optional[str] = None,
        detected_patterns: Optional[List[str]] = None,
        risk_score: Optional[float] = None
    ):
        """Log potential prompt injection attempts"""
        event_data = {
            "event_type": "PROMPT_INJECTION_ATTEMPT",
            "user_id": user_id,
            "session_id": session_id,
            "content_sample": content[:200] if content else "",
            "content_length": len(content) if content else 0,
            "detected_patterns": detected_patterns or [],
            "risk_score": risk_score,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(
            f"PROMPT_INJECTION_ATTEMPT - User: {user_id} - "
            f"Session: {session_id} - Risk: {risk_score} - "
            f"Patterns: {detected_patterns} - Content: {content[:50]}..."
        )
        
        # Write detailed event to separate file
        self._write_security_event("prompt_injection", event_data)
    
    def log_ai_response_blocked(
        self, 
        agent_type: str, 
        response: str, 
        reason: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log blocked AI responses"""
        event_data = {
            "event_type": "AI_RESPONSE_BLOCKED",
            "agent_type": agent_type,
            "user_id": user_id,
            "session_id": session_id,
            "response_sample": response[:200] if response else "",
            "response_length": len(response) if response else 0,
            "block_reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(
            f"AI_RESPONSE_BLOCKED - Agent: {agent_type} - "
            f"User: {user_id} - Reason: {reason} - "
            f"Response: {response[:50]}..."
        )
        
        self._write_security_event("ai_response_blocked", event_data)
    
    def log_authentication_failure(
        self, 
        ip_address: str, 
        user_agent: str,
        username: Optional[str] = None,
        failure_reason: str = "invalid_credentials"
    ):
        """Log authentication failures"""
        event_data = {
            "event_type": "AUTH_FAILURE",
            "ip_address": ip_address,
            "user_agent": user_agent,
            "username": username,
            "failure_reason": failure_reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(
            f"AUTH_FAILURE - IP: {ip_address} - "
            f"Username: {username} - Reason: {failure_reason} - "
            f"UserAgent: {user_agent[:100]}"
        )
        
        self._write_security_event("auth_failure", event_data)
    
    def log_rate_limit_exceeded(
        self, 
        user_id: str, 
        endpoint: str, 
        ip_address: str,
        limit_type: str = "request_rate"
    ):
        """Log rate limiting events"""
        event_data = {
            "event_type": "RATE_LIMIT_EXCEEDED",
            "user_id": user_id,
            "endpoint": endpoint,
            "ip_address": ip_address,
            "limit_type": limit_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(
            f"RATE_LIMIT_EXCEEDED - User: {user_id} - "
            f"Endpoint: {endpoint} - IP: {ip_address} - "
            f"Type: {limit_type}"
        )
        
        self._write_security_event("rate_limit", event_data)
    
    def log_websocket_auth_failure(
        self, 
        ip_address: str, 
        reason: str,
        conversation_id: Optional[str] = None
    ):
        """Log WebSocket authentication failures"""
        event_data = {
            "event_type": "WEBSOCKET_AUTH_FAILURE",
            "ip_address": ip_address,
            "conversation_id": conversation_id,
            "failure_reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(
            f"WEBSOCKET_AUTH_FAILURE - IP: {ip_address} - "
            f"Conversation: {conversation_id} - Reason: {reason}"
        )
        
        self._write_security_event("websocket_auth", event_data)
    
    def log_suspicious_activity(
        self, 
        activity_type: str, 
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log general suspicious activity"""
        event_data = {
            "event_type": "SUSPICIOUS_ACTIVITY",
            "activity_type": activity_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(
            f"SUSPICIOUS_ACTIVITY - Type: {activity_type} - "
            f"User: {user_id} - IP: {ip_address} - "
            f"Details: {details}"
        )
        
        self._write_security_event("suspicious", event_data)
    
    def log_ai_safety_incident(
        self,
        incident_type: str,
        agent_type: str,
        safety_score: float,
        details: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Log AI safety incidents"""
        event_data = {
            "event_type": "AI_SAFETY_INCIDENT",
            "incident_type": incident_type,
            "agent_type": agent_type,
            "safety_score": safety_score,
            "user_id": user_id,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.error(
            f"AI_SAFETY_INCIDENT - Type: {incident_type} - "
            f"Agent: {agent_type} - Score: {safety_score} - "
            f"User: {user_id}"
        )
        
        self._write_security_event("ai_safety", event_data)
    
    def log_agent_behavior_anomaly(
        self,
        agent_type: str,
        deviation_score: float,
        baseline_data: Dict[str, Any],
        current_data: Dict[str, Any]
    ):
        """Log agent behavior anomalies"""
        event_data = {
            "event_type": "AGENT_BEHAVIOR_ANOMALY",
            "agent_type": agent_type,
            "deviation_score": deviation_score,
            "baseline_data": baseline_data,
            "current_data": current_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.error(
            f"AGENT_BEHAVIOR_ANOMALY - Agent: {agent_type} - "
            f"Deviation: {deviation_score}"
        )
        
        self._write_security_event("agent_anomaly", event_data)
    
    def log_security_policy_violation(
        self,
        policy_type: str,
        violation_details: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log security policy violations"""
        event_data = {
            "event_type": "SECURITY_POLICY_VIOLATION",
            "policy_type": policy_type,
            "violation_details": violation_details,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.error(
            f"SECURITY_POLICY_VIOLATION - Policy: {policy_type} - "
            f"User: {user_id} - Details: {violation_details}"
        )
        
        self._write_security_event("policy_violation", event_data)
    
    def _write_security_event(self, event_category: str, event_data: Dict[str, Any]):
        """Write detailed security event to category-specific file"""
        try:
            event_file = SECURITY_LOGS_DIR / f"{event_category}_events.jsonl"
            
            with open(event_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data, default=str) + '\n')
                
        except Exception as e:
            # Log to main security log if detailed logging fails
            self.logger.error(f"Failed to write security event to file: {e}")
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security event summary for the last N hours"""
        try:
            from datetime import datetime, timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            summary = {
                "period_hours": hours,
                "events": {
                    "prompt_injection_attempts": 0,
                    "ai_responses_blocked": 0,
                    "auth_failures": 0,
                    "rate_limit_violations": 0,
                    "websocket_auth_failures": 0,
                    "ai_safety_incidents": 0
                },
                "top_risk_patterns": [],
                "most_active_ips": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Count events from log files
            for event_file in SECURITY_LOGS_DIR.glob("*_events.jsonl"):
                if event_file.exists():
                    with open(event_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                event = json.loads(line.strip())
                                event_time = datetime.fromisoformat(
                                    event['timestamp'].replace('Z', '+00:00')
                                )
                                if event_time >= cutoff_time:
                                    event_type = event.get('event_type', '')
                                    if event_type == 'PROMPT_INJECTION_ATTEMPT':
                                        summary['events']['prompt_injection_attempts'] += 1
                                    elif event_type == 'AI_RESPONSE_BLOCKED':
                                        summary['events']['ai_responses_blocked'] += 1
                                    elif event_type == 'AUTH_FAILURE':
                                        summary['events']['auth_failures'] += 1
                                    elif event_type == 'RATE_LIMIT_EXCEEDED':
                                        summary['events']['rate_limit_violations'] += 1
                                    elif event_type == 'WEBSOCKET_AUTH_FAILURE':
                                        summary['events']['websocket_auth_failures'] += 1
                                    elif event_type == 'AI_SAFETY_INCIDENT':
                                        summary['events']['ai_safety_incidents'] += 1
                            except (json.JSONDecodeError, KeyError, ValueError):
                                continue
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate security summary: {e}")
            return {"error": "Failed to generate summary"}


# Global audit logger instance
audit_logger = SecurityAuditLogger()