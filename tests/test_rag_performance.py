"""
Script de tests de performance/qualité du RAG.
Mesure les temps de réponse et la présence de mots-clés attendus
sur différents types de documents (Excel, DOCX, etc.).
"""

import os
import time
import statistics
from datetime import datetime
from typing import Any, Dict, List

import requests


# Configuration : gateway HTTP (Docker)
API_URL = os.getenv("RAG_GATEWAY_URL", "http://localhost:8081/v1/chat/completions")
HEADERS = {
    "Content-Type": "application/json",
    "X-Use-RAG": "true",
}
MODEL = "mistral"


TEST_CASES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "category": "Specific Price",
        "question": "Quel est le prix unitaire du TUBE TELECOM PVC LST D60 ?",
        "expected_keywords": ["1.53", "1,53"],
        "description": "Exact match for item price (Excel SPIGAO)",
    },
    {
        "id": 2,
        "category": "Specific Price",
        "question": "Quel est le prix du TUYAU ASSAINISSEMENT BETON ARME D1000 ?",
        "expected_keywords": ["139.0", "139,0", "139"],
        "description": "Exact match for item price (Excel SPIGAO)",
    },
    {
        "id": 3,
        "category": "Labor Cost",
        "question": "Quel est le coût journalier d'un CHEF CHANTIER ?",
        "expected_keywords": ["332"],
        "description": "Labor cost retrieval (DQE / bordereau)",
    },
    {
        "id": 4,
        "category": "Labor Cost",
        "question": "Quel est le coût d'un MACON ?",
        "expected_keywords": ["256"],
        "description": "Labor cost retrieval (DQE / bordereau)",
    },
    {
        "id": 5,
        "category": "Material Price",
        "question": "Quel est le prix d'un sac de CIMENT COURANT 25KG ?",
        "expected_keywords": ["7.67", "7,67"],
        "description": "Material price retrieval (Excel fournitures)",
    },
    {
        "id": 6,
        "category": "Material Price",
        "question": "Combien coûte la GAINE TPC COURONNE ROUGE D75 ?",
        "expected_keywords": ["44.46", "44,46"],
        "description": "Material price retrieval (Excel fournitures)",
    },
    {
        "id": 7,
        "category": "Equipment Cost",
        "question": "Quel est le coût de la MINI PELLE 8/10T ?",
        "expected_keywords": ["352"],
        "description": "Equipment cost retrieval (engins)",
    },
    {
        "id": 8,
        "category": "Equipment Cost",
        "question": "Quel est le coût de la PELLE 21T ?",
        "expected_keywords": ["800"],
        "description": "Equipment cost retrieval (engins)",
    },
    {
        "id": 9,
        "category": "Specific Item",
        "question": "Quel est le prix de la TETE SECURITE Ø 500 COMPLETE ?",
        "expected_keywords": ["193.94", "193,94"],
        "description": "Specific item price (catalogue fournitures)",
    },
    {
        "id": 10,
        "category": "Specific Item",
        "question": "Combien coûte un BURIN 350MM REAFFUTABLE ?",
        "expected_keywords": ["7.20", "7,20"],
        "description": "Specific item price (catalogue fournitures)",
    },
    {
        "id": 11,
        "category": "Vague/Context",
        "question": "Donnez-moi les tarifs des tuyaux d'assainissement béton.",
        "expected_keywords": ["139", "28.2", "38.2", "54.49", "70.73"],
        "description": "List retrieval (plusieurs diamètres)",
    },
    {
        "id": 12,
        "category": "Vague/Context",
        "question": "Quels sont les coûts des différents personnels de chantier ?",
        "expected_keywords": ["Chef", "Maçon", "Manoeuvre", "332", "256"],
        "description": "List retrieval (profils + montants)",
    },
    {
        "id": 13,
        "category": "Vague/Context",
        "question": "Quels sont les engins disponibles et leurs coûts ?",
        "expected_keywords": ["Pelle", "Camion", "352", "480"],
        "description": "List retrieval (engins + montants)",
    },
    {
        "id": 14,
        "category": "Specific Detail",
        "question": "Quel est le code article pour le CIMENT FONDU SAC 25 KG ?",
        "expected_keywords": ["2104010203", "8341"],
        "description": "Code article retrieval (référence interne)",
    },
    {
        "id": 15,
        "category": "Specific Detail",
        "question": "Quelle est la référence de la GAINE TPC COURONNE ROUGE D90 ?",
        "expected_keywords": ["D90", "56.18"],
        "description": "Reference retrieval (diamètre + prix)",
    },
    {
        "id": 16,
        "category": "Comparison",
        "question": "Quel est le plus cher entre un CHEF CHANTIER et un CHEF EQUIPE ?",
        "expected_keywords": ["332", "identique", "même prix"],
        "description": "Comparison logic (si les montants sont égaux)",
    },
    {
        "id": 17,
        "category": "Comparison",
        "question": "Quel est le prix du TUYAU D1000 par rapport au D300 ?",
        "expected_keywords": ["139", "28.2"],
        "description": "Comparison logic (deux diamètres)",
    },
    {
        "id": 18,
        "category": "Company Info (DOCX)",
        "question": "De quoi parle le document WIAME VRD ?",
        "expected_keywords": ["présentation", "entreprise", "historique"],
        "description": "Résumé de document Word (mémoire technique)",
    },
    {
        "id": 19,
        "category": "Supplier (DOCX/Excel)",
        "question": "Qui est le fournisseur pour les tubes telecom ?",
        "expected_keywords": ["WIAME", "Fourniture"],
        "description": "Extraction de fournisseur dans les documents",
    },
    {
        "id": 20,
        "category": "Location (PDF/DOCX)",
        "question": "Où se trouve le traitement de déchets ultimes ?",
        "expected_keywords": ["VERT LE GRAND"],
        "description": "Localisation extraite d'un document contractuel ou mémoire",
    },
]


def run_test(test_case: Dict[str, Any]) -> Dict[str, Any]:
    print(f"Running Test {test_case['id']}: {test_case['question']}")

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": test_case["question"]}],
        "stream": False,
    }

    start_time = time.time()
    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=120)
        end_time = time.time()
        latency = end_time - start_time

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            content_lower = content.lower()

            found_keywords = [
                kw for kw in test_case["expected_keywords"] if kw.lower() in content_lower
            ]
            success = len(found_keywords) > 0

            return {
                "id": test_case["id"],
                "question": test_case["question"],
                "success": success,
                "latency": latency,
                "response": content,
                "found_keywords": found_keywords,
                "missing_keywords": [
                    kw for kw in test_case["expected_keywords"] if kw not in found_keywords
                ],
            }
        else:
            return {
                "id": test_case["id"],
                "question": test_case["question"],
                "success": False,
                "latency": latency,
                "error": f"HTTP {response.status_code}: {response.text}",
            }

    except Exception as exc:
        return {
            "id": test_case["id"],
            "question": test_case["question"],
            "success": False,
            "latency": time.time() - start_time,
            "error": str(exc),
        }


def generate_report(results: List[Dict[str, Any]]) -> str:
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    latencies = [r["latency"] for r in results if "latency" in r]
    avg_latency = statistics.mean(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0

    report = f"""# RAG Performance & Quality Report
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary
- **Total Tests**: {total_tests}
- **Success Rate**: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)
- **Average Latency**: {avg_latency:.2f}s
- **Min Latency**: {min_latency:.2f}s
- **Max Latency**: {max_latency:.2f}s

## Detailed Results

| ID | Category | Question | Success | Latency | Keywords Found |
|----|----------|----------|---------|---------|----------------|
"""

    for r in results:
        status = "✅" if r["success"] else "❌"
        keywords = ", ".join(r.get("found_keywords", [])) if r["success"] else "N/A"
        report += (
            f"| {r['id']} | {TEST_CASES[r['id']-1]['category']} | {r['question']} | "
            f"{status} | {r['latency']:.2f}s | {keywords} |\n"
        )

    report += "\n## Failed Tests Analysis\n"
    for r in results:
        if not r["success"]:
            report += f"\n### Test {r['id']}: {r['question']}\n"
            report += f"- **Error/Response**: {r.get('response') or r.get('error')}\n"
            report += f"- **Missing Keywords**: {r.get('missing_keywords', [])}\n"

    return report


def main() -> None:
    print(f"Starting RAG Performance Tests against {API_URL} ...")
    results: List[Dict[str, Any]] = []

    for test_case in TEST_CASES:
        result = run_test(test_case)
        results.append(result)
        status = "Success" if result["success"] else "Failure"
        print(f"  -> {status} ({result['latency']:.2f}s)")
        time.sleep(1)

    report = generate_report(results)

    output_path = "tests/rag_performance_report.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nTest Suite Completed. Report saved to {output_path}")


if __name__ == "__main__":
    main()

