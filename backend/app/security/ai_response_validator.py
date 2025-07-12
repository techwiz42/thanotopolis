"""
AI Response Validation System

This module validates AI-generated responses to prevent system information
leakage, inappropriate content, and security violations.
"""

import re
import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


class AIResponseValidator:
    """Validate AI responses for security and appropriateness"""
    
    # Patterns that should never appear in AI responses
    FORBIDDEN_PATTERNS = [
        # System information
        r"system\s+prompt",
        r"my\s+instructions",
        r"i\s+was\s+told\s+to",
        r"the\s+system\s+says",
        r"according\s+to\s+my\s+instructions",
        r"my\s+programming\s+tells\s+me",
        
        # Security credentials
        r"jwt_secret_key",
        r"database_url",
        r"api_key",
        r"access_key",
        r"secret_key",
        r"private_key",
        r"webhook_secret",
        r"stripe_secret",
        
        # Environment variables
        r"env\s*\(",
        r"getenv",
        r"environment\s+variable",
        r"\.env",
        
        # Database information
        r"postgresql://",
        r"mysql://",
        r"mongodb://",
        r"redis://",
        r"database\s+schema",
        r"table\s+structure",
        
        # File paths and system info
        r"/app/",
        r"/backend/",
        r"/home/",
        r"/var/",
        r"/etc/",
        r"\.py$",
        r"\.env$",
        r"config\.py",
        
        # Technical implementation details
        r"fastapi",
        r"uvicorn",
        r"sqlalchemy",
        r"alembic",
        r"pydantic",
        r"langchain",
        
        # Security tokens
        r"bearer\s+[a-zA-Z0-9\-_]+",
        r"jwt\s+[a-zA-Z0-9\-_\.]+",
        r"token\s*:\s*[a-zA-Z0-9\-_]+",
        
        # Internal endpoints
        r"/api/internal",
        r"/admin/",
        r"localhost:",
        r"127\.0\.0\.1",
        
        # Code snippets
        r"import\s+[a-zA-Z_]",
        r"from\s+[a-zA-Z_]",
        r"def\s+[a-zA-Z_]",
        r"class\s+[a-zA-Z_]",
        
        # Prompt injection indicators in responses
        r"as\s+an\s+ai\s+language\s+model,\s+i\s+cannot",
        r"i\s+cannot\s+provide\s+that\s+information",
        r"i\s+don't\s+have\s+access\s+to",
        
        # Error messages that leak info
        r"traceback",
        r"exception\s+occurred",
        r"error\s+in\s+line",
        r"stack\s+trace",
    ]
    
    # Patterns that indicate inappropriate responses
    INAPPROPRIATE_PATTERNS = [
        # Harmful content
        r"how\s+to\s+hack",
        r"exploit\s+vulnerability",
        r"ddos\s+attack",
        r"sql\s+injection",
        r"cross[\s-]site\s+scripting",
        
        # Personal attacks
        r"you\s+are\s+stupid",
        r"that's\s+dumb",
        r"idiot",
        r"moron",
        
        # Discriminatory content
        r"racial\s+slur",
        r"hate\s+speech",
        
        # Medical/legal advice disclaimers missing
        r"medical\s+advice",
        r"legal\s+advice",
        r"financial\s+advice",
        
        # Inappropriate personal questions
        r"what\s+is\s+your\s+age",
        r"are\s+you\s+single",
        r"personal\s+relationship",
    ]
    
    # Business context keywords that should be present
    BUSINESS_CONTEXT_KEYWORDS = [
        'cemetery', 'burial', 'funeral', 'memorial', 'grave', 'plot',
        'service', 'arrangement', 'cremation', 'headstone', 'monument',
        'visitation', 'viewing', 'obituary', 'celebration of life',
        'appointment', 'meeting', 'consultation', 'planning', 'pricing',
        'payment', 'contract', 'family', 'loved one', 'deceased'
    ]
    
    def __init__(self):
        """Initialize the validator with compiled patterns"""
        self.forbidden_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.FORBIDDEN_PATTERNS
        ]
        
        self.inappropriate_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.INAPPROPRIATE_PATTERNS
        ]
    
    def validate_response(self, response: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate AI response for security issues and appropriateness
        
        Args:
            response: AI-generated response text
            context: Context information (conversation_id, user_id, agent_type, etc.)
            
        Returns:
            Tuple of (is_valid, filtered_response_or_fallback)
        """
        if not response or not isinstance(response, str):
            return False, "I apologize, but I cannot provide a response at this time."
        
        # Check for forbidden system information
        forbidden_found = []
        for pattern in self.forbidden_patterns:
            if pattern.search(response):
                forbidden_found.append(pattern.pattern)
        
        if forbidden_found:
            logger.warning(f"Blocked AI response containing forbidden patterns: {forbidden_found}")
            from app.security.audit_logger import audit_logger
            audit_logger.log_ai_response_blocked(
                agent_type=context.get('agent_type', 'unknown'),
                response=response[:200],
                reason=f"Forbidden patterns: {forbidden_found}"
            )
            return False, self._get_fallback_response(context)
        
        # Check for inappropriate content
        inappropriate_found = []
        for pattern in self.inappropriate_patterns:
            if pattern.search(response):
                inappropriate_found.append(pattern.pattern)
        
        if inappropriate_found:
            logger.warning(f"Blocked inappropriate AI response: {inappropriate_found}")
            from app.security.audit_logger import audit_logger
            audit_logger.log_ai_response_blocked(
                agent_type=context.get('agent_type', 'unknown'),
                response=response[:200],
                reason=f"Inappropriate content: {inappropriate_found}"
            )
            return False, self._get_fallback_response(context)
        
        # Check response length
        if len(response) > 3000:
            logger.warning("Blocked excessively long AI response")
            return False, "I apologize, but my response was too long. Could you please be more specific about what you'd like to know?"
        
        # Validate response is contextually appropriate
        if not self._is_response_contextually_appropriate(response, context):
            logger.warning("Blocked contextually inappropriate AI response")
            return False, self._get_contextual_fallback_response(context)
        
        # Check for potential prompt injection in response (AI echoing injection attempts)
        if self._contains_injection_echo(response):
            logger.warning("Blocked AI response echoing prompt injection")
            return False, "I'm here to help with your inquiry. Could you please rephrase your question?"
        
        # Response passed all validation checks
        return True, response
    
    def _is_response_contextually_appropriate(self, response: str, context: Dict[str, Any]) -> bool:
        """
        Check if response is appropriate for the business context
        
        Args:
            response: AI response text
            context: Conversation context
            
        Returns:
            True if response is contextually appropriate
        """
        # Check if response is related to cemetery/funeral services
        conversation_type = context.get('conversation_type', '')
        agent_type = context.get('agent_type', '')
        
        # For telephony and cemetery-related conversations, ensure business relevance
        if conversation_type == 'telephony' or 'cemetery' in agent_type.lower():
            # Response should contain business-relevant keywords or be general assistance
            response_lower = response.lower()
            
            # Allow general courtesy responses
            courtesy_phrases = [
                'how can i help', 'how may i assist', 'thank you', 'you\'re welcome',
                'i understand', 'i apologize', 'certainly', 'of course',
                'let me help', 'i\'m here to help', 'please', 'sorry'
            ]
            
            if any(phrase in response_lower for phrase in courtesy_phrases):
                return True
            
            # Check for business context
            business_context_found = any(
                keyword in response_lower for keyword in self.BUSINESS_CONTEXT_KEYWORDS
            )
            
            # Allow responses that are asking for clarification
            clarification_phrases = [
                'could you please', 'can you tell me', 'what would you like',
                'which', 'when', 'where', 'how', 'what type'
            ]
            
            if any(phrase in response_lower for phrase in clarification_phrases):
                return True
            
            # If it's a substantial response without business context, flag it
            if len(response) > 100 and not business_context_found:
                return False
        
        return True
    
    def _contains_injection_echo(self, response: str) -> bool:
        """Check if AI response is echoing prompt injection attempts"""
        injection_echo_patterns = [
            r"ignore\s+previous",
            r"system\s+prompt",
            r"instructions",
            r"as\s+an\s+ai",
            r"i\s+cannot\s+ignore",
            r"my\s+instructions",
            r"programmed\s+to"
        ]
        
        for pattern in injection_echo_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        return False
    
    def _get_fallback_response(self, context: Dict[str, Any]) -> str:
        """Get appropriate fallback response based on context"""
        conversation_type = context.get('conversation_type', '')
        
        if conversation_type == 'telephony':
            return (
                "I apologize, but I need to transfer you to one of our staff members "
                "who can better assist you with your inquiry. Please hold while I connect you."
            )
        else:
            return (
                "I apologize, but I cannot provide that information. "
                "How else can I help you today?"
            )
    
    def _get_contextual_fallback_response(self, context: Dict[str, Any]) -> str:
        """Get contextually appropriate fallback response"""
        conversation_type = context.get('conversation_type', '')
        
        if conversation_type == 'telephony':
            return (
                "I'm here to help you with information about our cemetery services, "
                "including burial plots, memorial services, and arrangements. "
                "What specific information can I provide for you today?"
            )
        else:
            return (
                "I'm here to assist you with your cemetery and memorial service needs. "
                "What would you like to know about our services?"
            )
    
    def calculate_safety_score(self, response: str, context: Dict[str, Any]) -> float:
        """
        Calculate a safety score for the response (0.0 to 1.0)
        
        Args:
            response: AI response text
            context: Conversation context
            
        Returns:
            Safety score where 1.0 is completely safe, 0.0 is unsafe
        """
        if not response:
            return 0.0
        
        safety_score = 1.0
        
        # Check for forbidden patterns
        forbidden_count = sum(
            1 for pattern in self.forbidden_patterns
            if pattern.search(response)
        )
        safety_score -= forbidden_count * 0.4
        
        # Check for inappropriate patterns
        inappropriate_count = sum(
            1 for pattern in self.inappropriate_patterns
            if pattern.search(response)
        )
        safety_score -= inappropriate_count * 0.3
        
        # Length penalty for very long responses
        if len(response) > 2000:
            safety_score -= 0.2
        
        # Context appropriateness
        if not self._is_response_contextually_appropriate(response, context):
            safety_score -= 0.3
        
        # Injection echo check
        if self._contains_injection_echo(response):
            safety_score -= 0.4
        
        return max(0.0, safety_score)


# Global validator instance
response_validator = AIResponseValidator()