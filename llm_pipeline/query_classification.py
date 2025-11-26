"""Classification simple des questions RAG.

Ce module regroupe la logique de détection du type de question
pour pouvoir adapter, plus tard, les prompts ou le choix des
documents sans gonfler `pipeline.py`.
"""
from __future__ import annotations


def classify_query_type(question_lower: str) -> str:
    """Classe grossièrement la question pour ajuster le traitement.

    Types retournés :
    - fiche_identite : présentation entreprise / projet / entité
    - question_chiffree : question centrée sur prix / montant / quantités
    - inventaire_documents : recherche de liste de documents
    - autre : fallback générique
    """
    q = question_lower.strip()

    # Fiche d'identité / présentation
    fiche_keywords = [
        "qui est ",
        "qui sont ",
        "présente",
        "presentation",
        "présentation",
        "donne moi les infos",
        "donne-moi les infos",
        "informations sur",
        "infos sur",
        "parle moi de",
        "parle-moi de",
    ]
    if any(kw in q for kw in fiche_keywords):
        return "fiche_identite"

    # Questions chiffrées
    numeric_keywords = [
        "prix",
        "montant",
        "coût",
        "cout",
        "combien",
        "total",
        "totaux",
        "unitaire",
        "unité",
        "unite",
        "valeur",
        "budget",
    ]
    if any(kw in q for kw in numeric_keywords):
        return "question_chiffree"

    # Inventaire / liste de documents
    inventory_keywords = [
        "documents disponibles",
        "quels sont les documents",
        "liste des documents",
        "fichiers disponibles",
        "liste des fichiers",
        "inventaire des documents",
        "inventaire",
    ]
    if any(kw in q for kw in inventory_keywords):
        return "inventaire_documents"

    return "autre"


__all__ = ["classify_query_type"]

