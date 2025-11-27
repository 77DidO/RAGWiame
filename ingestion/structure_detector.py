"""Module de détection de structure (sections, FAQ) pour l'ingestion."""
import re
from typing import List, Optional, Tuple

class StructureDetector:
    """Détecte les structures logiques dans le texte."""

    _FAQ_START = re.compile(r"(?is)^\s*question\s*:\s*(.+)$")
    _FAQ_ANSWER = re.compile(r"(?is)^\s*réponse\s*:\s*(.+)$")
    
    _SECTION_KEYWORDS = [
        "VENDEUR",
        "ACQUEREUR",
        "ACQUÉREUR",
        "ACHETEUR",
        "PROPRIETAIRE",
        "PROPRIÉTAIRE",
        "NOTAIRE",
        "MANDATAIRE",
        "DIAGNOSTIC",
        "DESIGNATION",
        "CONDITIONS",
        "GARANTIES",
        "PAIEMENT",
    ]

    @classmethod
    def detect_section_label(cls, paragraph: str) -> Optional[str]:
        """Détecte si un paragraphe est un titre de section connu."""
        normalized = re.sub(r"\s+", " ", paragraph.strip())
        if not normalized:
            return None
        upper = normalized.upper()
        
        # 1. Mots-clés exacts
        for keyword in cls._SECTION_KEYWORDS:
            if keyword in upper:
                return keyword.title()
                
        # 2. Titres finissant par deux-points (ex: "Désignation :")
        if upper.endswith(":"):
            core = upper.rstrip(": ").title()
            if any(ch.isalpha() for ch in core):
                return core
        return None

    @classmethod
    def detect_faq(cls, paragraph: str) -> Tuple[Optional[str], Optional[str]]:
        """Détecte une question ou une réponse de FAQ.
        
        Retourne: (question, reponse) où l'un des deux est None.
        """
        faq_match = cls._FAQ_START.match(paragraph)
        if faq_match:
            return faq_match.group(1).strip(), None
            
        answer_match = cls._FAQ_ANSWER.match(paragraph)
        if answer_match:
            return None, answer_match.group(1).strip()
            
        return None, None
