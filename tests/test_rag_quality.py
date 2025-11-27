"""
Tests de qualité du système RAG.
Évalue la pertinence des réponses pour différents types de questions.
"""

from typing import Dict, List

import pytest
import requests


GATEWAY_URL = "http://localhost:8090/v1/chat/completions"
PROJECT_ID = "ED257730"


TEST_CASES: List[Dict] = [
    {
        "name": "Question vague (devrait refuser)",
        "question": "quel est le montant ?",
        "expected_behavior": "refuse",
        "min_score": None,
    },
    {
        "name": "Question spécifique sur montant",
        "question": "Quel est le montant du comparatif fournitures pour le projet Montmirail ?",
        "expected_behavior": "answer",
        "min_score": 0.7,
        "expected_keywords": ["220 792", "EUR", "comparatif"],
    },
    {
        "name": "Question sur équipements",
        "question": "Quels sont les équipements de raboteuse disponibles ?",
        "expected_behavior": "answer",
        "min_score": 0.5,
        "expected_keywords": ["raboteuse", "chenille"],
    },
    {
        "name": "Question sur enrobé (spécifique)",
        "question": "Quel est le montant de la résine sablée sur enrobés ?",
        "expected_behavior": "answer",
        "min_score": 0.5,
        "expected_keywords": ["75 264", "EUR", "résine"],
    },
    {
        "name": "Question impossible (devrait refuser)",
        "question": "Quelle est la couleur du ciel sur Mars ?",
        "expected_behavior": "refuse",
        "min_score": None,
    },
    {
        "name": "Question avec contexte projet",
        "question": "Résumé des montants DQE pour le projet ED257730",
        "expected_behavior": "answer",
        "min_score": 0.6,
        "expected_keywords": ["DQE", "EUR"],
    },
]


def rag_query(question: str, project_id: str = PROJECT_ID) -> Dict:
    """Envoie une requête RAG au gateway et retourne les résultats bruts."""
    payload = {
        "model": "mistral",
        "messages": [{"role": "user", "content": question}],
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Use-RAG": "true",
    }

    try:
        response = requests.post(GATEWAY_URL, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()

        answer = data["choices"][0]["message"]["content"]
        sources = data.get("sources") or []

        return {
            "success": True,
            "answer": answer,
            "sources": sources,
            "num_sources": len(sources),
        }
    except Exception as exc:  # pragma: no cover - dépend du réseau/gateway
        return {
            "success": False,
            "error": str(exc),
        }


def evaluate_result(test_case: Dict, result: Dict) -> Dict:
    """Évalue si le résultat correspond aux attentes métier."""
    evaluation = {
        "test_name": test_case["name"],
        "question": test_case["question"],
        "passed": False,
        "details": [],
    }

    if not result["success"]:
        evaluation["details"].append(f"✗ Erreur: {result['error']}")
        return evaluation

    answer = (result["answer"] or "").lower()
    expected_behavior = test_case["expected_behavior"]

    if expected_behavior == "refuse":
        if any(
            phrase in answer
            for phrase in [
                "manque de contexte",
                "pas trouvé",
                "je ne trouve pas",
                "pas suffisamment pertinent",
                "je ne peux pas répondre",
            ]
        ):
            evaluation["details"].append("✓ Refus correct de répondre")
            evaluation["passed"] = True
        else:
            evaluation["details"].append(
                f"✗ Devrait refuser mais a répondu: {result['answer'][:120]!r}"
            )

    elif expected_behavior == "answer":
        if any(
            phrase in answer
            for phrase in [
                "manque de contexte",
                "pas trouvé",
                "pas suffisamment pertinent",
                "je ne peux pas répondre",
            ]
        ):
            evaluation["details"].append(
                f"✗ A refusé alors qu'il devrait répondre: {result['answer'][:120]!r}"
            )
        else:
            evaluation["details"].append("✓ A fourni une réponse")
            keywords = test_case.get("expected_keywords", [])
            if keywords:
                found = [kw for kw in keywords if kw.lower() in answer]
                missing = [kw for kw in keywords if kw.lower() not in answer]
                if found:
                    evaluation["details"].append(
                        f"✓ Mots-clés trouvés: {', '.join(found)}"
                    )
                if missing:
                    evaluation["details"].append(
                        f"⚠ Mots-clés manquants: {', '.join(missing)}"
                    )
                if len(found) >= max(1, int(len(keywords) * 0.5)):
                    evaluation["passed"] = True
            else:
                evaluation["passed"] = True

            if result["num_sources"] > 0:
                evaluation["details"].append(
                    f"✓ {result['num_sources']} source(s) citée(s)"
                )
            else:
                evaluation["details"].append("⚠ Aucune source citée")

    return evaluation


def run_all_tests() -> List[Dict]:
    """Exécution simple en mode script (hors pytest)."""
    print("=" * 80)
    print("TESTS DE QUALITÉ RAG")
    print("=" * 80)
    print()

    results: List[Dict] = []
    passed = 0
    failed = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"Test {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"Question: {test_case['question']}")
        print("-" * 80)

        result = rag_query(test_case["question"])
        evaluation = evaluate_result(test_case, result)

        for detail in evaluation["details"]:
            print(f"  {detail}")

        if evaluation["passed"]:
            print("  ✅ TEST RÉUSSI")
            passed += 1
        else:
            print("  ❌ TEST ÉCHOUÉ")
            failed += 1

        if result["success"]:
            print(f"\n  Réponse: {result['answer'][:200]}...")

        print()
        results.append(evaluation)

    print("=" * 80)
    print(f"RÉSULTATS: {passed}/{len(TEST_CASES)} tests réussis ({failed} échecs)")
    print("=" * 80)

    return results


if __name__ == "__main__":
    run_all_tests()


@pytest.mark.parametrize("test_case", TEST_CASES, ids=[tc["name"] for tc in TEST_CASES])
def test_rag_quality_case(test_case: Dict) -> None:
    """Version pytest paramétrée des scénarios de qualité RAG."""
    result = rag_query(test_case["question"])
    evaluation = evaluate_result(test_case, result)

    details = " | ".join(evaluation["details"])
    assert evaluation["passed"], details

