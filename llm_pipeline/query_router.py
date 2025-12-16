"""Petit router pour extraire les filtres AO des questions."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional

# On utilise les définitions officielles de l'ingestion pour être aligné
from ingestion.metadata_utils import DOC_ROLE_PATTERNS
from llm_pipeline.prompts import get_router_prompt
from llama_index.core.prompts import PromptTemplate


@dataclass(slots=True)
class QueryRouterResult:
    """Résultat synthétique retourné par le router."""

    intent: str
    filters: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


class QueryRouter:
    """Détecte les intentions AO et reconstitue les filtres qu’on pourra envoyer à Qdrant."""

    AO_ID_PATTERN = re.compile(r"\bED\d{5,7}\b", re.IGNORECASE)
    PHASE_PATTERN = re.compile(r"phase\s*(candidature|offre|[0-9]+)", re.IGNORECASE)
    COMMUNE_PATTERN = re.compile(
        r"\b(?:à|pour|dans|sur|de)\s+(la\s+mairie\s+de\s+|la\s+ville\s+de\s+)?([A-ZÀÂÄËÉÈÎÏÔÖÙÛÜÇ][\w'\- ]+?)\b",
        re.IGNORECASE,
    )

    SERVICE_KEYWORDS = {
        "support",
        "maintenance",
        "travaux",
        "achats",
        "logistique",
        "maitrise d'oeuvre",
        "maitrise d oeuvre",
        "etat",
        "projet",
    }
    ROLE_KEYWORDS = {
        "maître d'oeuvre",
        "maitre d'oeuvre",
        "maître d'ouvrage",
        "maitre d'ouvrage",
    }
    
    # Inversion du mapping ingestion pour chercher les labels dans la question
    # DOC_ROLE_PATTERNS = {"BPU": ("bpu", "bordereau des prix"), ...}
    # On veut un mapping "bpu" -> "BPU", "bordereau des prix" -> "BPU"
    DOC_KEYWORD_TO_CODE: Dict[str, str] = {}
    
    def __init__(self) -> None:
        self._build_keyword_map()
        self.router_prompt = PromptTemplate(get_router_prompt())

    def _build_keyword_map(self) -> None:
        """Construit l'index inversé pour la détection rapide."""
        for code, keywords in DOC_ROLE_PATTERNS.items():
            for kw in keywords:
                self.DOC_KEYWORD_TO_CODE[kw.lower()] = code

    def analyze(self, question: str, llm: Any = None) -> QueryRouterResult:
        """Retourne les filtres et l'intention à partir d'une question.
        
        Si un LLM est fourni et que les regex ne trouvent rien de probant, 
        on tente une extraction plus fine.
        """
        text = question.strip()
        lower = text.lower()

        filters: Dict[str, str] = {}
        
        # --- 1. Approche Regex (Rapide et précise sur les ID/Codes) ---
        
        # AO identifiant
        ao_id_match = self.AO_ID_PATTERN.search(text)
        if ao_id_match:
            filters["ao_id"] = ao_id_match.group(0).upper()

        # Phase (rudimentaire)
        phase_match = self.PHASE_PATTERN.search(lower)
        if phase_match:
            val = phase_match.group(1)
            if val.isdigit():
                filters["ao_phase_code"] = val.zfill(2)
            else:
                filters["ao_phase_label"] = val.capitalize()

        # Document code
        # On cherche le keyword le plus long qui matche pour éviter les faux positifs (ex "de" vs "devis")
        found_code = None
        longest_match = 0
        for kw, code in self.DOC_KEYWORD_TO_CODE.items():
            if kw in lower:
                if len(kw) > longest_match:
                    longest_match = len(kw)
                    found_code = code
        
        if found_code:
            filters["ao_doc_code"] = found_code

        # Signed flag
        if "signé" in lower or "signee" in lower:
            filters["ao_signed"] = "true"
            
        # --- 2. Approche LLM (Si nécessaire) ---
        # Si on a un LLM et qu'on a peu de filtres (ou qu'il manque des infos cruciales comme la commune),
        # on peut demander au LLM de compléter.
        # Pour l'instant, on l'appelle si on a rien trouvé, ou si on pense qu'il y a une commune non détectée.
        
        should_call_llm = llm is not None and (len(filters) == 0 or "commune" in lower or "mairie" in lower)
        
        if should_call_llm:
            try:
                llm_filters = self._extract_with_llm(question, llm)
                # On merge les résultats LLM (priorité au LLM pour la commune/phase, priorité Regex pour ID)
                for k, v in llm_filters.items():
                    if k not in filters:
                        filters[k] = v
                    elif k == "ao_commune": # LLM souvent meilleur pour isoler la commune
                        filters[k] = v
            except Exception as e:
                print(f"Warning: LLM router failed: {e}")

        # --- 3. Intention ---
        intent = self._resolve_intent(lower, filters)
        confidence = self._estimate_confidence(filters)
        
        return QueryRouterResult(intent=intent, filters=filters, confidence=confidence)

    def _extract_with_llm(self, question: str, llm: Any) -> Dict[str, str]:
        """Utilise le LLM pour extraire le JSON."""
        response = llm.predict(self.router_prompt, question=question)
        # Nettoyage basique du markdown json
        cleaned = str(response).replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(cleaned)
            return {k: str(v) for k, v in data.items() if v} # Filtre les valeurs vides
        except json.JSONDecodeError:
            return {}

    def _resolve_intent(self, text: str, filters: Mapping[str, str]) -> str:
        LIST_KEYWORDS = {"liste", "inventaire", "quels sont", "donne moi les ao"}
        if any(kw in text for kw in LIST_KEYWORDS):
            return "liste_ao"
        
        if filters:
            return "recherche_doc_ao" # On cherche un doc spécifique dans un AO
            
        return "recherche_generique"

    def _estimate_confidence(self, filters: Mapping[str, str]) -> float:
        if not filters:
            return 0.0
        # Score arbitraire basé sur la spécificité
        score = 0.2
        if "ao_id" in filters: score += 0.5
        if "ao_commune" in filters: score += 0.3
        if "ao_doc_code" in filters: score += 0.2
        return min(score, 1.0)


__all__ = ["QueryRouter", "QueryRouterResult"]
