"""
Génère un rapport Markdown des réponses RAG sur des cas contextuels.

Objectif : garder une trace des réponses (texte complet) pour pouvoir les
comparer dans le temps, indépendamment du verdict des tests pytest.
"""

import os
from dataclasses import dataclass
from typing import List

from tests.test_rag_contextual import (
    API_URL,
    HEADERS,
    call_with_context,
    CONTEXT_TUYAU_D1000,
    CONTEXT_GAINE_D90,
    CONTEXT_WIAME_VRD,
    CONTEXT_DECHETS,
)


@dataclass
class ContextualCase:
    id: int
    name: str
    question: str
    context_label: str
    context: str
    expected_hint: str


CASES: List[ContextualCase] = [
    ContextualCase(
        id=1,
        name="Prix TUYAU D1000",
        question="Quel est le prix unitaire du TUYAU ASSAINISSEMENT BETON ARME D1000 ?",
        context_label="CONTEXT_TUYAU_D1000",
        context=CONTEXT_TUYAU_D1000,
        expected_hint="~139 EUR",
    ),
    ContextualCase(
        id=2,
        name="Référence GAINE D90",
        question="Quelle est la référence et le prix de la GAINE TPC COURONNE ROUGE D90 ?",
        context_label="CONTEXT_GAINE_D90",
        context=CONTEXT_GAINE_D90,
        expected_hint="D90 • ~56.18 EUR",
    ),
    ContextualCase(
        id=3,
        name="Résumé WIAME VRD",
        question="En une phrase, de quoi parle le document WIAME VRD ?",
        context_label="CONTEXT_WIAME_VRD",
        context=CONTEXT_WIAME_VRD,
        expected_hint="présentation de l'entreprise WIAME VRD",
    ),
    ContextualCase(
        id=4,
        name="Localisation déchets ultimes",
        question="Où se trouve le traitement des déchets ultimes ?",
        context_label="CONTEXT_DECHETS",
        context=CONTEXT_DECHETS,
        expected_hint="VERT LE GRAND",
    ),
]


def main() -> None:
    print(f"Génération du rapport contextuel contre {API_URL} ...")
    rows = []

    for case in CASES:
        print(f"- Case {case.id}: {case.name}")
        answer = call_with_context(case.context, case.question)
        rows.append((case, answer))

    out_path = "tests/rag_contextual_report.md"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# RAG Contextual Quality Report\n")
        f.write("\n")
        f.write(f"- API URL: `{API_URL}`\n")
        f.write("- Headers: `X-Use-RAG: true`\n")
        f.write("\n")

        f.write("## Résumé\n\n")
        f.write("| ID | Nom | Contexte | Attendu (hint) |\n")
        f.write("|----|-----|----------|----------------|\n")
        for case, _ in rows:
            f.write(
                f"| {case.id} | {case.name} | {case.context_label} | {case.expected_hint} |\n"
            )

        f.write("\n## Détails par cas\n")
        for case, answer in rows:
            f.write(f"\n### Case {case.id}: {case.name}\n\n")
            f.write(f"- Question : `{case.question}`\n")
            f.write(f"- Contexte : `{case.context_label}`\n")
            f.write(f"- Attendu (hint) : `{case.expected_hint}`\n\n")
            f.write("**Réponse brute :**\n\n")
            f.write("```\n")
            f.write(answer.strip())
            f.write("\n```\n")

    print(f"Rapport écrit dans {out_path}")


if __name__ == "__main__":
    main()

