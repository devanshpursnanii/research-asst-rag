"""
Token counting utilities using tiktoken.
"""

import tiktoken
from typing import List


# Use cl100k_base encoding (same as GPT-4, GPT-3.5-turbo)
_encoder = None


def get_encoder():
    """Get or create the tiktoken encoder."""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """
    Count tokens in a text string.
    
    Args:
        text: Input text
        
    Returns:
        Number of tokens
    """
    if not text:
        return 0
    encoder = get_encoder()
    return len(encoder.encode(text))


def count_tokens_batch(texts: List[str]) -> List[int]:
    """
    Count tokens for multiple texts.
    
    Args:
        texts: List of text strings
        
    Returns:
        List of token counts
    """
    encoder = get_encoder()
    return [len(encoder.encode(text)) if text else 0 for text in texts]
