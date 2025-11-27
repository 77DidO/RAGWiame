"""Module de traitement et nettoyage de texte pour l'ingestion."""
import re
from typing import List

class TextProcessor:
    """Gère le nettoyage et le découpage du texte."""

    _QUESTION_LABEL = re.compile(r"(?im)^\s*(question|réponse)\s*:\s*", re.UNICODE)

    @staticmethod
    def clean_text(text: str) -> str:
        """Nettoie le texte brut (espaces insécables, retours chariot)."""
        cleaned = text.replace("\u00a0", " ")
        cleaned = cleaned.replace("\r", "\n")
        return cleaned

    @staticmethod
    def split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Découpe le texte en chunks de taille fixe avec recouvrement."""
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
            
        if len(text) <= chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(length, start + chunk_size)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == length:
                break
            start = max(0, end - chunk_overlap)
            if start >= length:
                break
        return chunks

    @classmethod
    def paragraphs(cls, text: str) -> List[str]:
        """Découpe le texte en paragraphes."""
        parts = [p.strip() for p in text.split("\n") if p.strip()]
        return parts
