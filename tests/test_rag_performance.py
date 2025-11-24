import requests
import time
import json
import statistics
from datetime import datetime

# Configuration
API_URL = "http://localhost:8081/v1/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "X-Use-RAG": "true"
}
MODEL = "mistral"  # Using the model defined in the gateway

# Test Cases generated from Qdrant dump
TEST_CASES = [
    {
        "id": 1,
        "category": "Specific Price",
        "question": "Quel est le prix unitaire du TUBE TELECOM PVC LST D60 ?",
        "expected_keywords": ["1.53", "1,53"],
        "description": "Exact match for item price"
    },
    {
        "id": 2,
        "category": "Specific Price",
        "question": "Quel est le prix du TUYAU ASSAINISSEMENT BETON ARME D1000 ?",
        "expected_keywords": ["139.0", "139,0", "139"],
        "description": "Exact match for item price"
    },
    {
        "id": 3,
        "category": "Labor Cost",
        "question": "Quel est le coût journalier d'un CHEF CHANTIER ?",
        "expected_keywords": ["332"],
        "description": "Labor cost retrieval"
    },
    {
        "id": 4,
        "category": "Labor Cost",
        "question": "Quel est le coût d'un MACON ?",
        "expected_keywords": ["256"],
        "description": "Labor cost retrieval"
    },
    {
        "id": 5,
        "category": "Material Price",
        "question": "Quel est le prix d'un sac de CIMENT COURANT 25KG ?",
        "expected_keywords": ["7.67", "7,67"],
        "description": "Material price retrieval"
    },
    {
        "id": 6,
        "category": "Material Price",
        "question": "Combien coûte la GAINE TPC COURONNE ROUGE D75 ?",
        "expected_keywords": ["44.46", "44,46"],
        "description": "Material price retrieval"
    },
    {
        "id": 7,
        "category": "Equipment Cost",
        "question": "Quel est le coût de la MINI PELLE 8/10T ?",
        "expected_keywords": ["352"],
        "description": "Equipment cost retrieval"
    },
    {
        "id": 8,
        "category": "Equipment Cost",
        "question": "Quel est le coût de la PELLE 21T ?",
        "expected_keywords": ["800"],
        "description": "Equipment cost retrieval"
    },
    {
        "id": 9,
        "category": "Specific Item",
        "question": "Quel est le prix de la TÊTE SÉCURITÉ Ø 500 COMPLÈTE ?",
        "expected_keywords": ["193.94", "193,94"],
        "description": "Specific item price"
    },
    {
        "id": 10,
        "category": "Specific Item",
        "question": "Combien coûte un BURIN 350MM REAFFUTABLE ?",
        "expected_keywords": ["7.20", "7,20"],
        "description": "Specific item price"
    },
    {
        "id": 11,
        "category": "Vague/Context",
        "question": "Donnez-moi les tarifs des tuyaux d'assainissement béton.",
        "expected_keywords": ["139", "28.2", "38.2", "54.49", "70.73"],
        "description": "List retrieval"
    },
    {
        "id": 12,
        "category": "Vague/Context",
        "question": "Quels sont les coûts des différents personnels de chantier ?",
        "expected_keywords": ["Chef", "Macon", "Manoeuvre", "332", "256"],
        "description": "List retrieval"
    },
    {
        "id": 13,
        "category": "Vague/Context",
        "question": "Quels sont les engins disponibles et leurs coûts ?",
        "expected_keywords": ["Pelle", "Camion", "352", "480"],
        "description": "List retrieval"
    },
    {
        "id": 14,
        "category": "Specific Detail",
        "question": "Quel est le code article pour le CIMENT FONDU SAC 25 KG ?",
        "expected_keywords": ["2104010203", "8341"],
        "description": "Code retrieval"
    },
    {
        "id": 15,
        "category": "Specific Detail",
        "question": "Quelle est la référence de la GAINE TPC COURONNE ROUGE D90 ?",
        "expected_keywords": ["D90", "56.18"],
        "description": "Reference retrieval"
    },
    {
        "id": 16,
        "category": "Comparison",
        "question": "Quel est le plus cher entre un CHEF CHANTIER et un CHEF EQUIPE ?",
        "expected_keywords": ["332", "identique", "même prix"],
        "description": "Comparison logic"
    },
    {
        "id": 17,
        "category": "Comparison",
        "question": "Quel est le prix du TUYAU D1000 par rapport au D300 ?",
        "expected_keywords": ["139", "28.2"],
        "description": "Comparison logic"
    },
    {
        "id": 18,
        "category": "Company Info",
        "question": "De quoi parle le document WIAME VRD ?",
        "expected_keywords": ["Présentation", "entreprise", "historique"],
        "description": "Document summary"
    },
    {
        "id": 19,
        "category": "Supplier",
        "question": "Qui est le fournisseur pour les tubes télécom ?",
        "expected_keywords": ["WIAME", "Fourniture"],
        "description": "Supplier retrieval"
    },
    {
        "id": 20,
        "category": "Location",
        "question": "Où se trouve le traitement de déchets ultimes ?",
        "expected_keywords": ["VERT LE GRAND"],
        "description": "Location retrieval"
    }
]

def run_test(test_case):
    print(f"Running Test {test_case['id']}: {test_case['question']}")
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": test_case['question']}],
        "stream": False
    }
    
    start_time = time.time()
    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
        end_time = time.time()
        latency = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Check keywords
            found_keywords = [kw for kw in test_case['expected_keywords'] if kw.lower() in content.lower()]
            success = len(found_keywords) > 0
            
            return {
                "id": test_case['id'],
                "question": test_case['question'],
                "success": success,
                "latency": latency,
                "response": content,
                "found_keywords": found_keywords,
                "missing_keywords": [kw for kw in test_case['expected_keywords'] if kw not in found_keywords]
            }
        else:
            return {
                "id": test_case['id'],
                "question": test_case['question'],
                "success": False,
                "latency": latency,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {
            "id": test_case['id'],
            "question": test_case['question'],
            "success": False,
            "latency": time.time() - start_time,
            "error": str(e)
        }

def generate_report(results):
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    latencies = [r['latency'] for r in results if 'latency' in r]
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
        status = "✅" if r['success'] else "❌"
        keywords = ", ".join(r.get('found_keywords', [])) if r['success'] else "N/A"
        report += f"| {r['id']} | {TEST_CASES[r['id']-1]['category']} | {r['question']} | {status} | {r['latency']:.2f}s | {keywords} |\n"
        
    report += "\n## Failed Tests Analysis\n"
    for r in results:
        if not r['success']:
            report += f"\n### Test {r['id']}: {r['question']}\n"
            report += f"- **Error/Response**: {r.get('response') or r.get('error')}\n"
            report += f"- **Missing Keywords**: {r.get('missing_keywords', [])}\n"
            
    return report

def main():
    print("Starting RAG Performance Tests...")
    results = []
    
    for test_case in TEST_CASES:
        result = run_test(test_case)
        results.append(result)
        print(f"  -> {'Success' if result['success'] else 'Failure'} ({result['latency']:.2f}s)")
        # Small pause to avoid overwhelming the server
        time.sleep(1)
        
    report = generate_report(results)
    
    with open("tests/rag_performance_report.md", "w", encoding="utf-8") as f:
        f.write(report)
        
    print("\nTest Suite Completed. Report saved to tests/rag_performance_report.md")

if __name__ == "__main__":
    main()
