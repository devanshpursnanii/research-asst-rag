"""
API Configuration & Fallback Logic

Manages dual API keys with automatic fallback:
- GOOGLE_API_KEY2 (Personal) → Paper Brain
- GOOGLE_API_KEY1 (Spit account) → Paper Chat

Fallback: KEY2 → KEY1 → raise QuotaExhaustedError
"""

import os
from typing import Callable, Any
from llama_index.llms.google_genai import GoogleGenAI
from dotenv import load_dotenv

load_dotenv()


class QuotaExhaustedError(Exception):
    """Raised when both API keys are exhausted."""
    def __init__(self, message: str, key_type: str):
        self.message = message
        self.key_type = key_type  # "brain" or "chat" or "both"
        super().__init__(self.message)


def get_brain_llm(temperature: float = 0.1) -> GoogleGenAI:
    """
    Get LLM for Paper Brain (uses GOOGLE_API_KEY2 - Personal account).
    
    Args:
        temperature: Model temperature
        
    Returns:
        GoogleGenAI instance configured with KEY2
    """
    api_key = os.getenv("GOOGLE_API_KEY2")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY2 not found in environment variables")
    
    return GoogleGenAI(
        model="models/gemini-2.5-flash-lite",
        api_key=api_key,
        temperature=temperature
    )


def get_chat_llm(temperature: float = 0.7) -> GoogleGenAI:
    """
    Get LLM for Paper Chat (uses GOOGLE_API_KEY1 - Spit account).
    
    Args:
        temperature: Model temperature
        
    Returns:
        GoogleGenAI instance configured with KEY1
    """
    api_key = os.getenv("GOOGLE_API_KEY1")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY1 not found in environment variables")
    
    return GoogleGenAI(
        model="models/gemini-2.5-flash-lite",
        api_key=api_key,
        temperature=temperature
    )


async def try_with_fallback(
    primary_llm: GoogleGenAI,
    fallback_llm: GoogleGenAI,
    operation: Callable,
    *args,
    **kwargs
) -> Any:
    """
    Try operation with primary LLM, fallback to secondary on quota exhaustion.
    
    Args:
        primary_llm: Primary LLM to try first
        fallback_llm: Fallback LLM if primary fails
        operation: Async function to call (e.g., llm.acomplete)
        *args, **kwargs: Arguments to pass to operation
        
    Returns:
        Result from operation
        
    Raises:
        QuotaExhaustedError: If both keys are exhausted
    """
    try:
        # Try primary key
        result = await operation(primary_llm, *args, **kwargs)
        return result
    except Exception as e:
        error_str = str(e).lower()
        
        # Check if it's a quota/resource error
        if "resource" in error_str or "quota" in error_str or "exhausted" in error_str or "429" in error_str:
            print(f"⚠️  Primary API key exhausted, trying fallback...")
            
            try:
                # Try fallback key
                result = await operation(fallback_llm, *args, **kwargs)
                print(f"✓ Fallback successful")
                return result
            except Exception as fallback_error:
                fallback_error_str = str(fallback_error).lower()
                
                if "resource" in fallback_error_str or "quota" in fallback_error_str or "exhausted" in fallback_error_str or "429" in fallback_error_str:
                    # Both keys exhausted
                    raise QuotaExhaustedError(
                        "Both API keys have exhausted their quota. Please try again later.",
                        key_type="both"
                    )
                else:
                    # Some other error on fallback
                    raise fallback_error
        else:
            # Not a quota error, raise original
            raise e


def get_embedding_model():
    """Get embedding model configuration (uses KEY1 by default)."""
    return {
        "model_name": "models/text-embedding-004",
        "api_key": os.getenv("GOOGLE_API_KEY1")
    }
