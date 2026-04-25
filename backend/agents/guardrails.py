import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Basic patterns for prompt injection detection
INJECTION_PATTERNS = [
    r"(?i)ignore prev",
    r"(?i)you are now",
    r"(?i)system prompt",
    r"(?i)new instructions",
    r"(?i)bypass",
    r"(?i)jailbreak",
]

class LLMGuardrail:
    @staticmethod
    def validate_input(text: str) -> str:
        """
        Sanitizes and checks for injection patterns.
        """
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text):
                logger.warning(f"Detection: Potential injection pattern found: {pattern}")
                raise ValueError("Security Violation: Suspicious input detected.")
        return text

    @staticmethod
    def wrap_llm_call(llm_func):
        """
        Decorator or wrapper to apply guardrails to an LLM call.
        """
        async def wrapper(*args, **kwargs):
            # Check input in kwargs or args
            # (Simplified check for this implementation)
            logger.info("Guardrail: Executing LLM call with output validation.")
            result = await llm_func(*args, **kwargs)
            
            # Post-processing: Check for sensitive leaks in LLM output
            if "sk-" in str(result) or "key" in str(result).lower():
                logger.error("Guardrail: Potential API Key leak detected in LLM output!")
                return "Error: Sensitive information detected in response."
            
            return result
        return wrapper

def sanitize_user_input(text: str) -> str:
    """Basic sanitization for user-facing strings."""
    return LLMGuardrail.validate_input(text)
