"""
Prompt Injection Defense System for AI Security

This module provides comprehensive protection against prompt injection attacks
targeting AI agents, including voice agents and chat agents.
"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class PromptInjectionFilter:
    """Defense against prompt injection attacks"""
    
    # Comprehensive list of prompt injection patterns
    INJECTION_PATTERNS = [
        # Direct instruction manipulation
        r"ignore\s+previous\s+instructions",
        r"forget\s+everything\s+above",
        r"disregard\s+previous\s+instructions",
        r"new\s+instructions?\s*:",
        r"override\s+instructions",
        
        # System prompt attempts
        r"system\s*:",
        r"assistant\s*:",
        r"user\s*:",
        r"human\s*:",
        r"ai\s*:",
        
        # Prompt structure manipulation
        r"<\s*prompt\s*>",
        r"<\s*/\s*prompt\s*>",
        r"###\s*",
        r"---\s*",
        r"\[\s*system\s*\]",
        r"\[\s*assistant\s*\]",
        r"\[\s*user\s*\]",
        
        # Information extraction attempts
        r"print\s+your\s+instructions",
        r"print\s+your\s+system\s+prompt",
        r"print\s+your\s+prompt", 
        r"reveal\s+your\s+prompt",
        r"reveal\s+your\s+instructions",
        r"show\s+your\s+system\s+prompt",
        r"what\s+are\s+your\s+instructions",
        r"repeat\s+your\s+system\s+prompt",
        r"tell\s+me\s+your\s+instructions",
        r"what\s+is\s+your\s+prompt",
        
        # Role manipulation
        r"you\s+are\s+now\s+a",
        r"act\s+as\s+a",
        r"pretend\s+to\s+be",
        r"role[\s-]?play",
        r"simulate\s+being",
        
        # Jailbreak attempts
        r"jailbreak",
        r"dan\s+mode",
        r"developer\s+mode",
        r"evil\s+mode",
        r"unrestricted\s+mode",
        
        # Context manipulation
        r"in\s+a\s+hypothetical",
        r"let's\s+imagine",
        r"what\s+if\s+you\s+were",
        r"for\s+educational\s+purposes",
        
        # Encoding/bypass attempts
        r"base64",
        r"rot13",
        r"caesar\s+cipher",
        r"encode\s+in",
        r"decode\s+this",
        
        # Stop sequence manipulation
        r"stop\s+generation",
        r"end\s+response",
        r"\\n\\n",
        
        # Training data extraction
        r"training\s+data",
        r"dataset",
        r"memorized",
        r"exact\s+text",
        
        # Security bypass
        r"security\s+override",
        r"admin\s+access",
        r"root\s+privileges",
        r"bypass\s+restrictions",
        
        # Multi-language injection (common phrases)
        r"ignorar\s+instrucciones",  # Spanish
        r"ignorer\s+les\s+instructions",  # French
        r"instruksi\s+mengabaikan",  # Indonesian
        
        # Creative variations
        r"do\s+the\s+opposite",
        r"reverse\s+your\s+instructions",
        r"contrary\s+to\s+your\s+programming",
    ]
    
    # Suspicious character sequences
    SUSPICIOUS_SEQUENCES = [
        r'[<>{}|\[\]]{3,}',  # Multiple special characters
        r'[#*-]{5,}',        # Long sequences of formatting characters
        r'[\n\r]{3,}',       # Multiple newlines
        r'\\[a-z]{2,}',      # Escape sequences
    ]
    
    def __init__(self):
        """Initialize the filter with compiled regex patterns"""
        self.injection_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.INJECTION_PATTERNS
        ]
        
        self.suspicious_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.SUSPICIOUS_SEQUENCES
        ]
        
        self.security_keywords = [
            'jwt_secret_key', 'database_url', 'api_key', 'password', 'token',
            'secret', 'private_key', 'access_key', 'webhook', 'stripe',
            'config', 'env', 'environment'
        ]
    
    def sanitize_user_input(self, user_input: str) -> str:
        """
        Sanitize user input to remove potential prompt injection patterns
        
        Args:
            user_input: Raw user input string
            
        Returns:
            Sanitized input string with injection patterns removed/replaced
        """
        if not user_input or not isinstance(user_input, str):
            return ""
        
        sanitized = user_input
        injection_detected = False
        
        # Remove injection patterns
        for pattern in self.injection_patterns:
            if pattern.search(sanitized):
                injection_detected = True
                sanitized = pattern.sub('[FILTERED]', sanitized)
        
        # Remove suspicious character sequences
        for pattern in self.suspicious_patterns:
            sanitized = pattern.sub('', sanitized)
        
        # Limit length to prevent overflow attacks
        sanitized = sanitized[:2000]
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s{3,}', ' ', sanitized)
        
        # Log security events
        if injection_detected:
            logger.warning(
                f"Prompt injection attempt detected and filtered: {user_input[:100]}..."
            )
            from app.security.audit_logger import audit_logger
            audit_logger.log_prompt_injection_attempt(
                user_id="unknown",
                content=user_input[:200],
                detected_patterns=[
                    pattern.pattern for pattern in self.injection_patterns
                    if pattern.search(user_input)
                ]
            )
        
        return sanitized.strip()
    
    def validate_organization_data(self, org_data: str) -> str:
        """
        Validate organization-provided data for prompt safety
        This is more restrictive since org data goes into system prompts
        
        Args:
            org_data: Organization-provided text data
            
        Returns:
            Validated and sanitized organization data
        """
        if not org_data or not isinstance(org_data, str):
            return ""
        
        # More restrictive filtering for org data
        safe_data = org_data
        
        # Remove all potentially dangerous characters
        safe_data = re.sub(r'[<>{}|\[\]"\'`\\]', '', safe_data)
        
        # Remove injection patterns
        for pattern in self.injection_patterns:
            safe_data = pattern.sub('', safe_data)
        
        # Remove security-related keywords
        for keyword in self.security_keywords:
            safe_data = re.sub(
                rf'\b{re.escape(keyword)}\b',
                '[FILTERED]',
                safe_data,
                flags=re.IGNORECASE
            )
        
        # Shorter limit for org data that goes into prompts
        safe_data = safe_data[:300]
        
        # Clean up whitespace
        safe_data = re.sub(r'\s+', ' ', safe_data).strip()
        
        return safe_data
    
    def detect_injection_attempt(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect if text contains prompt injection attempts
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (is_injection_detected, list_of_detected_patterns)
        """
        if not text or not isinstance(text, str):
            return False, []
        
        detected_patterns = []
        
        for pattern in self.injection_patterns:
            if pattern.search(text):
                detected_patterns.append(pattern.pattern)
        
        return len(detected_patterns) > 0, detected_patterns
    
    def calculate_risk_score(self, text: str) -> float:
        """
        Calculate a risk score (0.0 to 1.0) for potential injection attempts
        
        Args:
            text: Text to analyze
            
        Returns:
            Risk score between 0.0 (safe) and 1.0 (high risk)
        """
        if not text or not isinstance(text, str):
            return 0.0
        
        risk_score = 0.0
        
        # Check for injection patterns
        pattern_matches = 0
        for pattern in self.injection_patterns:
            if pattern.search(text):
                pattern_matches += 1
        
        # Base risk from pattern matches
        if pattern_matches > 0:
            risk_score += min(0.8, pattern_matches * 0.2)
        
        # Additional risk factors
        
        # Length-based risk (very long inputs are suspicious)
        if len(text) > 1000:
            risk_score += 0.1
        
        # Special character density
        special_chars = len(re.findall(r'[<>{}|\[\]"\'`\\]', text))
        if special_chars > len(text) * 0.1:  # >10% special chars
            risk_score += 0.2
        
        # Multiple language detection (mixed scripts)
        if self._contains_mixed_scripts(text):
            risk_score += 0.1
        
        # Security keyword presence
        security_keywords_found = sum(
            1 for keyword in self.security_keywords
            if keyword.lower() in text.lower()
        )
        if security_keywords_found > 0:
            risk_score += min(0.3, security_keywords_found * 0.1)
        
        return min(1.0, risk_score)
    
    def _contains_mixed_scripts(self, text: str) -> bool:
        """Check if text contains mixed writing systems (potential obfuscation)"""
        scripts = set()
        for char in text:
            if '\u0000' <= char <= '\u007F':  # ASCII
                scripts.add('latin')
            elif '\u0080' <= char <= '\u00FF':  # Latin-1
                scripts.add('latin')
            elif '\u0100' <= char <= '\u017F':  # Latin Extended
                scripts.add('latin')
            elif '\u0400' <= char <= '\u04FF':  # Cyrillic
                scripts.add('cyrillic')
            elif '\u4E00' <= char <= '\u9FFF':  # CJK
                scripts.add('cjk')
            elif '\u0600' <= char <= '\u06FF':  # Arabic
                scripts.add('arabic')
        
        return len(scripts) > 1


# Global filter instance
prompt_filter = PromptInjectionFilter()