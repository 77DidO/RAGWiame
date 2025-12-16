"""Petit router pour extraire les filtres AO des questions."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping


@dataclass(slots=True)
class QueryRouterResult:
    """Résultat synthétique retourné par le router."""

    intent: str
    filters: Dict[str, str]
    confidence: float


class QueryRouter:
    """Détecte les intentions AO et reconstitue les filtres qu’on pourra envoyer à Qdrant."""

    AO_ID_PATTERN = re.compile(r"\bED\d{5,7}\b", re.IGNORECASE)
    PHASE_PATTERN = re.compile(r"phase\s*(\d{1,2})", re.IGNORECASE)
    COMMUNE_PATTERN = re.compile(
        r"\b(?:à|pour|dans|sur|de)\s+([A-ZÀÂÄËÉÈÎÏÔÖÙÛÜÇ][\w'\- ]+?)\b", re.IGNORECASE
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
    ROLE_KEYWORDS = {"maître d'oeuvre", "maitre d'oeuvre", "maître d'ouvrage", "maitre d'ouvrage"}
    DOC_ROLE_KEYWORDS = {
        "candidature": "candidature",
        "offre": "offre",
        "planning": "planning",
        "bpu": "bpu",
        "devis": "devis",
    }

    LIST_INTENT_KEYWORDS = {"liste", "inventaire", "quels sont les AO", "quels AO", "quel AO"}

    def analyze(self, question: str) -> QueryRouterResult:
        """Retourne les filtres et l'intention à partir d'une question."""
        text = question.strip()
        lower = text.lower()

        filters: Dict[str, str] = {}
        # AO identifiant
        ao_id_match = self.AO_ID_PATTERN.search(text)
        if ao_id_match:
            filters["ao_id"] = ao_id_match.group(0).upper()

        # Phase
        phase_match = self.PHASE_PATTERN.search(lower)
        if phase_match:
            phase = phase_match.group(1).zfill(2)
            filters["ao_phase_code"] = phase

        # Commune
        commune_match = self.COMMUNE_PATTERN.search(text)
        if commune_match:
            filters["ao_commune"] = commune_match.group(1).upper().strip()

        # Services / roles
        self._match_keywords(lower, self.SERVICE_KEYWORDS, filters, "service")
        self._match_keywords(lower, self.ROLE_KEYWORDS, filters, "role")

        # Document role explicit
        for keyword, value in self.DOC_ROLE_KEYWORDS.items():
            if keyword in lower:
                filters["ao_doc_role"] = value
                break

        # Signed flag
        if "signé" in lower or "signee" in lower:
            filters["ao_signed"] = "true"

        intent = self._resolve_intent(lower, filters)
        confidence = self._estimate_confidence(filters)
        return QueryRouterResult(intent=intent, filters=filters, confidence=confidence)

    def _resolve_intent(self, text: str, filters: Mapping[str, str]) -> str:
        if any(keyword in text for keyword in self.LIST_INTENT_KEYWORDS):
            return "liste_ao"
        if "phase" in text and "ao_phase_code" in filters:
            return "phase_ao"
        if "service" in filters or "role" in filters:
            return "service_role"
        if filters:
            return "recherche_ao"
        return "fallback"

    def _estimate_confidence(self, filters: Mapping[str, str]) -> float:
        base = 0.4
        bonus = min(len(filters) * 0.1, 0.5)
        return min(base + bonus, 0.95)

    @staticmethod
    def _match_keywords(text: str, keywords: Iterable[str], target: Dict[str, str], name: str) -> None:
        for keyword in keywords:
            if keyword in text:
                target[name] = keyword
                return


__all__ = ["QueryRouter", "QueryRouterResult"]
