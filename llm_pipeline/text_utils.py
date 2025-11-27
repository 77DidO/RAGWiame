"""Text utility functions for RAG pipeline."""
import re
from typing import List


def tokenize(text: str) -> List[str]:
    """Extract alphanumeric tokens from text (lowercase)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def citation_key(source: str, chunk_value) -> str:
    """Generate a unique citation key from source and chunk identifier."""
    return f"{source}::{chunk_value}"
