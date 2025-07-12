"""
Content Security Pipeline

Multi-stage content filtering system for AI interactions.
Provides comprehensive input sanitization and output validation
for all AI agents and communication channels.
"""

import re
import logging
from typing import Dict, Any, Tuple, Optional, List
from app.security.prompt_injection_filter import prompt_filter
from app.security.ai_response_validator import response_validator
from app.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class ContentSecurityPipeline:
    """Multi-stage content filtering for AI interactions"""
    
    def __init__(self):
        """Initialize the content security pipeline"""
        self.injection_filter = prompt_filter
        self.response_validator = response_validator
        
        # PII detection patterns
        self.pii_patterns = {
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'ssn_nodash': re.compile(r'\b\d{9}\b'),
            'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'address': re.compile(r'\b\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)\b', re.IGNORECASE)
        }
        
        # Context-specific security levels
        self.security_levels = {
            'telephony': 'high',
            'web_chat': 'medium',
            'internal': 'low'
        }
    
    async def filter_user_input(
        self, 
        user_input: str, 
        context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Filter user input before sending to AI
        
        Args:
            user_input: Raw user input string
            context: Context information (conversation_type, user_id, etc.)
            
        Returns:
            Tuple of (filtered_input, security_metadata)
        """
        if not user_input or not isinstance(user_input, str):
            return "", {"filtered": False, "security_events": []}
        
        security_metadata = {
            "original_length": len(user_input),
            "filtered": False,
            "security_events": [],
            "risk_score": 0.0,
            "pii_detected": []
        }
        
        # Stage 1: Calculate initial risk score
        risk_score = self.injection_filter.calculate_risk_score(user_input)
        security_metadata["risk_score"] = risk_score
        
        # Stage 2: Detect prompt injection attempts
        is_injection, detected_patterns = self.injection_filter.detect_injection_attempt(user_input)
        if is_injection:
            security_metadata["security_events"].append("prompt_injection_detected")
            # Log the attempt
            audit_logger.log_prompt_injection_attempt(
                user_id=context.get('user_id', 'unknown'),
                content=user_input,
                session_id=context.get('session_id'),
                detected_patterns=detected_patterns,
                risk_score=risk_score
            )
        
        # Stage 3: Basic sanitization
        sanitized = self.injection_filter.sanitize_user_input(user_input)
        if sanitized != user_input:
            security_metadata["filtered"] = True
            security_metadata["security_events"].append("content_sanitized")
        
        # Stage 4: Context-specific validation
        if context.get("conversation_type") == "telephony":
            sanitized = self._filter_telephony_context(sanitized)
            security_metadata["context_filter"] = "telephony"
        
        # Stage 5: PII detection and handling
        pii_found, masked_input = self._detect_and_handle_pii(
            sanitized, 
            context.get("conversation_type", "web_chat")
        )
        if pii_found:
            security_metadata["pii_detected"] = pii_found
            security_metadata["security_events"].append("pii_masked")
            sanitized = masked_input
        
        # Stage 6: Length and format validation
        sanitized = self._apply_length_limits(sanitized, context)
        
        # Stage 7: Final security check
        final_risk = self.injection_filter.calculate_risk_score(sanitized)
        if final_risk > 0.8:
            security_metadata["security_events"].append("high_risk_content")
            # For very high risk, replace with safe placeholder
            sanitized = "[Content filtered for security]"
            security_metadata["filtered"] = True
        
        security_metadata["final_length"] = len(sanitized)
        security_metadata["final_risk_score"] = final_risk
        
        return sanitized, security_metadata
    
    async def filter_ai_response(
        self, 
        ai_response: str, 
        context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Filter AI response before sending to user
        
        Args:
            ai_response: AI-generated response text
            context: Context information
            
        Returns:
            Tuple of (filtered_response, security_metadata)
        """
        if not ai_response or not isinstance(ai_response, str):
            fallback = "I apologize, but I cannot provide a response at this time."
            return fallback, {"filtered": True, "reason": "empty_response"}
        
        security_metadata = {
            "original_length": len(ai_response),
            "filtered": False,
            "security_events": [],
            "safety_score": 0.0
        }
        
        # Stage 1: Calculate safety score
        safety_score = self.response_validator.calculate_safety_score(ai_response, context)
        security_metadata["safety_score"] = safety_score
        
        # Stage 2: Validate response
        is_valid, filtered_response = self.response_validator.validate_response(ai_response, context)
        
        if not is_valid:
            security_metadata["filtered"] = True
            security_metadata["security_events"].append("response_blocked")
            # The validator already logs the blocking event
        
        # Stage 3: Additional content checks for specific contexts
        if context.get("conversation_type") == "telephony":
            filtered_response = self._apply_telephony_response_filters(filtered_response)
        
        # Stage 4: Final length check
        if len(filtered_response) > 2000:
            filtered_response = filtered_response[:1997] + "..."
            security_metadata["security_events"].append("response_truncated")
        
        security_metadata["final_length"] = len(filtered_response)
        
        return filtered_response, security_metadata
    
    def _filter_telephony_context(self, text: str) -> str:
        """Additional filtering for telephony context"""
        # Remove potential DTMF injection sequences
        text = re.sub(r'[*#]{3,}', '', text)
        
        # Remove excessive special characters that could interfere with TTS
        text = re.sub(r'[<>{}|\[\]]{2,}', '', text)
        
        # Clean up audio-unfriendly characters
        text = re.sub(r'[^\w\s.,!?;:\'"()-]', '', text)
        
        return text
    
    def _detect_and_handle_pii(
        self, 
        text: str, 
        conversation_type: str
    ) -> Tuple[List[str], str]:
        """
        Detect and handle personally identifiable information
        
        Args:
            text: Input text to scan
            conversation_type: Type of conversation (affects handling)
            
        Returns:
            Tuple of (pii_types_found, masked_text)
        """
        pii_found = []
        masked_text = text
        
        # For telephony, be more aggressive with PII masking
        mask_fully = conversation_type == "telephony"
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = pattern.findall(text)
            if matches:
                pii_found.append(pii_type)
                
                if mask_fully:
                    # Completely mask PII for telephony
                    masked_text = pattern.sub(f'[{pii_type.upper()}_MASKED]', masked_text)
                else:
                    # Partial masking for web chat
                    if pii_type == 'ssn':
                        masked_text = pattern.sub('XXX-XX-XXXX', masked_text)
                    elif pii_type == 'credit_card':
                        masked_text = pattern.sub('XXXX-XXXX-XXXX-XXXX', masked_text)
                    elif pii_type == 'phone':
                        masked_text = pattern.sub('XXX-XXX-XXXX', masked_text)
                    elif pii_type == 'email':
                        # Keep domain, mask local part
                        def mask_email(match):
                            email = match.group(0)
                            local, domain = email.split('@')
                            masked_local = local[0] + 'X' * (len(local) - 2) + local[-1] if len(local) > 2 else 'XXX'
                            return f"{masked_local}@{domain}"
                        masked_text = pattern.sub(mask_email, masked_text)
                    else:
                        masked_text = pattern.sub(f'[{pii_type.upper()}_MASKED]', masked_text)
        
        return pii_found, masked_text
    
    def _apply_length_limits(self, text: str, context: Dict[str, Any]) -> str:
        """Apply context-appropriate length limits"""
        conversation_type = context.get("conversation_type", "web_chat")
        
        # Different limits for different contexts
        limits = {
            "telephony": 1000,  # Voice interactions should be shorter
            "web_chat": 2000,   # Web chat can be longer
            "internal": 5000    # Internal communications can be longest
        }
        
        limit = limits.get(conversation_type, 2000)
        
        if len(text) > limit:
            # Truncate at word boundary near the limit
            truncated = text[:limit]
            last_space = truncated.rfind(' ')
            if last_space > limit * 0.8:  # Only if we don't lose too much
                truncated = truncated[:last_space]
            return truncated + "..."
        
        return text
    
    def _apply_telephony_response_filters(self, response: str) -> str:
        """Apply telephony-specific response filters"""
        # Ensure response is appropriate for voice synthesis
        
        # Remove URLs (not useful in voice)
        response = re.sub(r'https?://\S+', '[website link]', response)
        
        # Convert symbols to words for better TTS
        response = response.replace('&', ' and ')
        response = response.replace('@', ' at ')
        response = response.replace('#', ' number ')
        response = response.replace('$', ' dollars ')
        response = response.replace('%', ' percent ')
        
        # Clean up formatting that doesn't work well with TTS
        response = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', response)  # Remove markdown bold
        response = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', response)    # Remove markdown italic
        response = re.sub(r'`([^`]+)`', r'\1', response)              # Remove code formatting
        
        # Ensure proper spacing around punctuation for TTS
        response = re.sub(r'([.!?])([A-Z])', r'\1 \2', response)
        
        return response
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security pipeline status"""
        return {
            "pipeline_version": "1.0",
            "components": {
                "prompt_injection_filter": "active",
                "ai_response_validator": "active", 
                "pii_detection": "active",
                "content_sanitization": "active"
            },
            "security_levels": self.security_levels,
            "pii_patterns_count": len(self.pii_patterns),
            "injection_patterns_count": len(self.injection_filter.INJECTION_PATTERNS)
        }


# Global pipeline instance
security_pipeline = ContentSecurityPipeline()