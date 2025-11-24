"""
Tests de qualité du système RAG
Teste la pertinence des résultats pour différents types de questions
"""

import requests
import json
from typing import List, Dict

# Configuration
GATEWAY_URL = "http://localhost:8081/v1/chat/completions"
PROJECT_ID = "ED257730"

# Cas de test
TEST_CASES = [
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
        "name": "Question sur enrobbé (spécifique)",
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


def test_rag_query(question: str, project_id: str = PROJECT_ID) -> Dict:
    """Teste une requête RAG et retourne les résultats"""
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
        response = requests.post(GATEWAY_URL, json=payload, headers=headers, timeout=30)
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
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def evaluate_result(test_case: Dict, result: Dict) -> Dict:
    """Évalue si le résultat correspond aux attentes"""
    evaluation = {
        "test_name": test_case["name"],
        "question": test_case["question"],
        "passed": False,
        "details": [],
    }
    
    if not result["success"]:
        evaluation["details"].append(f"❌ Erreur: {result['error']}")
        return evaluation
    
    answer = result["answer"].lower()
    expected_behavior = test_case["expected_behavior"]
    
    # Vérifier le comportement attendu
    if expected_behavior == "refuse":
        if "manque de contexte" in answer or "pas trouvé" in answer or "suffisamment pertinents" in answer:
            evaluation["details"].append("✅ Refus correct de répondre")
            evaluation["passed"] = True
        else:
            evaluation["details"].append(f"❌ Devrait refuser mais a répondu: {answer[:100]}")
    
    elif expected_behavior == "answer":
        if "manque de contexte" in answer or "pas trouvé" in answer:
            evaluation["details"].append(f"❌ A refusé alors qu'il devrait répondre: {answer[:100]}")
        else:
            evaluation["details"].append("✅ A fourni une réponse")
            
            # Vérifier les mots-clés attendus
            if "expected_keywords" in test_case:
                keywords_found = []
                keywords_missing = []
                for keyword in test_case["expected_keywords"]:
                    if keyword.lower() in answer:
                        keywords_found.append(keyword)
                    else:
                        keywords_missing.append(keyword)
                
                if keywords_found:
                    evaluation["details"].append(f"✅ Mots-clés trouvés: {', '.join(keywords_found)}")
                if keywords_missing:
                    evaluation["details"].append(f"⚠️ Mots-clés manquants: {', '.join(keywords_missing)}")
                
                # Test réussi si au moins 50% des mots-clés sont présents
                if len(keywords_found) >= len(test_case["expected_keywords"]) * 0.5:
                    evaluation["passed"] = True
            else:
                evaluation["passed"] = True
            
            # Vérifier le nombre de sources
            if result["num_sources"] > 0:
                evaluation["details"].append(f"✅ {result['num_sources']} source(s) citée(s)")
            else:
                evaluation["details"].append("⚠️ Aucune source citée")
    
    return evaluation


def run_all_tests():
    """Exécute tous les tests et affiche les résultats"""
    print("=" * 80)
    print("TESTS DE QUALITÉ RAG")
    print("=" * 80)
    print()
    
    results = []
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"Test {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"Question: {test_case['question']}")
        print("-" * 80)
        
        result = test_rag_query(test_case["question"])
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
