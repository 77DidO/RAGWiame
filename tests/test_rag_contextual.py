"""
Tests contextuels du RAG.

Objectif : vérifier que, lorsqu'on fournit explicitement un petit extrait
de document (contexte), le modèle retrouve bien les infos clés
et ne répond pas "contexte insuffisant".
"""

from typing import Dict

import pytest
import requests


API_URL = os.getenv("RAG_GATEWAY_URL", "http://localhost:8081/v1/chat/completions")
HEADERS = {
    "Content-Type": "application/json",
    "X-Use-RAG": "true",
}
MODEL = "mistral"


# --- Extraits de contexte (à ajuster si besoin avec les vrais textes) ---

CONTEXT_TUYAU_D1000 = """
DQE - Assainissement
Article : TUYAU ASSAINISSEMENT BETON ARME D1000
Prix unitaire : 139.00 EUR
Commentaire : Tuyau béton armé de diamètre 1000 mm pour réseau d'assainissement.
"""

CONTEXT_GAINE_D90 = """
Référence : GAINE TPC COURONNE ROUGE D90
Désignation : Gaine TPC rouge diamètre 90 mm
Prix unitaire : 56.18 EUR
"""

CONTEXT_WIAME_VRD = """
WIAME VRD - Présentation de l'entreprise
L'entreprise WIAME VRD est spécialisée dans les travaux de voirie et réseaux divers.
Le document présente l'historique de l'entreprise, ses compétences, ses références
et ses valeurs. On y trouve également des informations sur les moyens humains et
matériels et sur l'organisation des chantiers.
"""

CONTEXT_DECHETS = """
Traitement des déchets ultimes :
Les déchets ultimes sont acheminés et traités sur le site de VERT LE GRAND.
Le transport et le traitement sont effectués conformément à la réglementation en vigueur.
"""


def call_with_context(context: str, question: str) -> str:
    """Envoie une requête au gateway avec un contexte injecté dans le message."""
    payload: Dict = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Contexte documentaire :\n"
                    f"{context.strip()}\n\n"
                    "En te basant uniquement sur ce contexte, réponds à la question suivante "
                    "de façon factuelle et concise.\n\n"
                    f"Question : {question}"
                ),
            }
        ],
        "stream": False,
    }

    response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _norm(s: str) -> str:
    return s.lower().replace(" ", "").replace("\u00a0", "")


def test_context_tuyau_d1000_price():
    """Avec le contexte D1000, le modèle doit retrouver ~139 EUR."""
    answer = call_with_context(
        CONTEXT_TUYAU_D1000,
        "Quel est le prix unitaire du TUYAU ASSAINISSEMENT BETON ARME D1000 ?",
    )
    norm = _norm(answer)
    assert "139.00" in answer or "139,00" in answer or "139eur" in norm


def test_context_gaine_d90_price_and_ref():
    """Avec le contexte GAINE D90, on veut au moins la réf D90 et le prix."""
    answer = call_with_context(
        CONTEXT_GAINE_D90,
        "Quelle est la référence et le prix de la GAINE TPC COURONNE ROUGE D90 ?",
    )
    norm = _norm(answer)
    assert "d90" in norm
    assert "56.18" in answer or "56,18" in answer


def test_context_wiame_vrd_summary():
    """Résumé simple du document WIAME VRD."""
    answer = call_with_context(
        CONTEXT_WIAME_VRD,
        "En une phrase, de quoi parle le document WIAME VRD ?",
    )
    norm = _norm(answer)
    # On vérifie surtout qu'il parle de l'entreprise et de ses travaux,
    # sans dépendre d'un accent exact dans "présentation".
    assert "entreprise" in norm
    assert "voirie" in norm or "vrd" in norm or "réseaux" in norm


def test_context_dechets_location():
    """Extraction de la localisation de traitement des déchets ultimes."""
    answer = call_with_context(
        CONTEXT_DECHETS,
        "Où se trouve le traitement des déchets ultimes ?",
    )
    assert "VERT LE GRAND" in answer.upper()
