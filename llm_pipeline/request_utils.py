"""Utilitaires pour le traitement des requêtes API."""
import re
from typing import Any, List, Optional
from fastapi import HTTPException
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters

from llm_pipeline.models import QueryPayload, QueryResponse
from llm_pipeline.config import DEFAULT_USE_RAG, BYPASS_AUTH


def normalize_filter_value(value: Optional[str]) -> str:
    """Normalise une valeur de filtre (supprime les wildcards)."""
    if not value:
        return ""
    cleaned = value.strip()
    if cleaned.lower() in {"", "all", "*", "any"}:
        return ""
    return cleaned


def build_filters(payload: QueryPayload) -> MetadataFilters:
    """Construit les filtres de métadonnées à partir du payload."""
    filters: List[MetadataFilter] = []
    service = normalize_filter_value(payload.service)
    role = normalize_filter_value(payload.role)
    if service:
        filters.append(MetadataFilter(key="service", value=service))
    if role:
        filters.append(MetadataFilter(key="role", value=role))
    return MetadataFilters(filters=filters)


def check_vague_question(question: str) -> Optional[QueryResponse]:
    """Détecte les questions vagues et retourne une réponse appropriée."""
    vague_patterns = [
        r"^quel\s+(est|sont)\s+(le|la|les)\s+\w+\s*\??$",  # "quel est le montant ?"
        r"^quel\s+(est|sont)\s+\w+\s*\??$",  # "quel est montant ?"
        r"^combien\s*\??$",  # "combien ?"
        r"^où\s*\??$",  # "où ?"
        r"^quoi\s*\??$",  # "quoi ?"
        r"^qui\s*\??$",  # "qui ?"
    ]
    
    question_lower = question.lower().strip()
    for pattern in vague_patterns:
        if re.match(pattern, question_lower):
            return QueryResponse(
                answer="Je ne peux pas répondre à cette question car elle manque de contexte. "
                       "Pourriez-vous préciser ce que vous cherchez ? Par exemple : "
                       "\"Quel est le montant du DQE pour le projet Montmirail ?\"",
                citations=[]
            )
    return None


def ensure_token(token: Optional[str]) -> None:
    """Vérifie la présence d'un token d'authentification."""
    if BYPASS_AUTH:
        return
    if not token:
        raise HTTPException(status_code=401, detail="Token invalide")


def normalize_bool(value: Any, default: bool | None = True) -> bool | None:
    """Normalise une valeur en booléen."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


_DISABLE_RAG_PATTERNS = [r"#norag\b", r"\[norag\]", r"rag\s*:\s*false"]
_ENABLE_RAG_PATTERNS = [r"#forcerag\b", r"#userag\b", r"\[rag\]", r"rag\s*:\s*true"]


def resolve_rag_mode(question: str, explicit: Optional[bool]) -> tuple[str, bool]:
    """Résout le mode RAG à partir de la question et du flag explicite."""
    decision = explicit
    cleaned = question
    for pattern in _DISABLE_RAG_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            decision = False
    for pattern in _ENABLE_RAG_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            decision = True
    if decision is None:
        decision = DEFAULT_USE_RAG
    return cleaned.strip(), decision
