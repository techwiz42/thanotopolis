import re
import logging
import os
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class InputSanitizer:
    """Sanitizes user input to prevent prompt injection attacks."""
    
    # Patterns that might indicate prompt injection attempts
    SUSPICIOUS_PATTERNS = [
        r"ignore previous instructions",
        r"ignore above instructions",
        r"ignore all previous",
        r"disregard previous",
        r"disregard above",
        r"forget all previous",
        r"ignore your instructions",
        r"system prompt",
        r"you are now",
        r"you're now",
        r"\<\/?system\>",
        r"\<\/?prompt\>",
        r"\<\/?instructions?\>",
        r"\[system\]",
        r"\[instructions\]",
        r"\bsystem:\s",
        r"^system\s",
        r"new persona",
        r"jailbreak",
        r"DAN mode",
    ]
    
    # Control character pattern to detect attempts to use invisible characters
    CONTROL_CHARS = r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"
    
    # Common role-playing prompt boundaries
    ROLE_PLAY_PATTERNS = [
        r"You are (?:now )?(?:a|an) (?!agent|assistant)",  # Match 'You are a' but not if followed by 'agent' or 'assistant'
        r"I want you to act as",
        r"I want you to pretend",
        r"I want you to simulate",
        r"I need you to become",
        r"pretend you are",
        r"You're (?:now )?(?:a|an) (?!agent|assistant)",  # Same as above with contraction
    ]
    
    # Delimiter injection attempts
    DELIMITER_PATTERNS = [
        r"```\s*system",
        r"```\s*user",
        r"```\s*assistant",
        r"```\s*instructions",
        r"\#\#\#\s*system",
        r"\#\#\#\s*user",
        r"\#\#\#\s*assistant",
        r"\#\#\#\s*instructions",
    ]
    
    # Load custom patterns from environment or file if available
    @classmethod
    def load_custom_patterns(cls) -> List[str]:
        """
        Load custom patterns from environment or file.
        
        Returns:
            List of additional regex patterns to check
        """
        patterns = []
        
        # Check environment variable first
        env_patterns = os.environ.get('PROMPT_INJECTION_PATTERNS', '')
        if env_patterns:
            patterns.extend([p.strip() for p in env_patterns.split(',')])
            
        # Check for patterns file next
        patterns_file = os.environ.get('PROMPT_INJECTION_PATTERNS_FILE', '')
        if patterns_file and os.path.exists(patterns_file):
            try:
                with open(patterns_file, 'r') as f:
                    file_patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    patterns.extend(file_patterns)
            except Exception as e:
                logger.error(f"Error loading patterns file: {e}")
                
        return patterns
    
    @classmethod
    def sanitize_input(cls, user_input: str) -> Tuple[str, bool, Optional[List[str]]]:
        """
        Sanitizes user input to protect against prompt injection.
        
        Args:
            user_input: The raw user input
            
        Returns:
            Tuple of (sanitized_input, is_suspicious, detected_patterns)
            - sanitized_input: The cleaned input
            - is_suspicious: Whether the input contained suspicious patterns
            - detected_patterns: List of patterns that were detected, if any
        """
        # Make a copy of the original input
        sanitized = user_input
        detected = []
        
        # Load any custom patterns from environment or file
        custom_patterns = cls.load_custom_patterns()
        
        # Combine all patterns to check
        all_patterns = cls.SUSPICIOUS_PATTERNS + custom_patterns
        
        # Check for suspicious patterns
        for pattern in all_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                detected.append(pattern)
                # Replace the pattern with [FILTERED]
                sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
        
        # Check for control characters
        if re.search(cls.CONTROL_CHARS, sanitized):
            detected.append("control_characters")
            sanitized = re.sub(cls.CONTROL_CHARS, "", sanitized)
        
        # Check for role-playing patterns
        for pattern in cls.ROLE_PLAY_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                detected.append(pattern)
                sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
        
        # Check for delimiter injection
        for pattern in cls.DELIMITER_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                detected.append(pattern)
                # Replace just the delimiter part, keep the code content
                sanitized = re.sub(pattern, "```text", sanitized, flags=re.IGNORECASE)
        
        # Return sanitized input and detection flags
        is_suspicious = len(detected) > 0
        
        if is_suspicious:
            logger.warning(f"Suspicious input detected: {detected}")
            
        return sanitized, is_suspicious, detected if detected else None
    
    @classmethod
    def wrap_user_input(cls, user_input: str) -> str:
        """
        Wraps the user input in tags to clearly delineate it from system instructions.
        
        Args:
            user_input: The sanitized user input
            
        Returns:
            Wrapped user input
        """
        return f"<user_message>\n{user_input}\n</user_message>"

# Create singleton instance
input_sanitizer = InputSanitizer()