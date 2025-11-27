"""Module d'enrichissement des métadonnées pour l'ingestion."""
from typing import Dict, Optional

class MetadataEnricher:
    """Enrichit les métadonnées des documents (classification, hints)."""

    @staticmethod
    def infer_doc_hint(metadata: Dict) -> Optional[str]:
        """Déduit le type de document (hint) à partir du nom de fichier source."""
        source = str(metadata.get("source", "")).lower()
        if not source:
            return None

        def contains(*keywords: str) -> bool:
            return any(keyword in source for keyword in keywords)

        if source.endswith(".msg") or contains("courriel", "courrier", "email", "mail"):
            return "courriel"
        if contains("planning", "gantt"):
            return "planning"
        if contains("memoire", "mémoire", "presentation", "présentation"):
            return "memoire"
        if contains("dqe", "bordereau", "bpu", "prix", "det", "detail"):
            return "dqe"
        if source.endswith(".xlsx") or source.endswith(".xls"):
            return "tableur"
        if source.endswith(".pdf"):
            return "pdf"
        return None
