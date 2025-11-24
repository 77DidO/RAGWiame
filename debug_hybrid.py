import requests
import json
import sys

def debug_query(query, description):
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"QUERY: {query}")
    print(f"{'='*80}")

    url = "http://localhost:8081/v1/hybrid/search"
    payload = {
        "question": query,
        "return_hits_only": False
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        hits = data.get("hits", [])
        
        print(f"Found {len(hits)} chunks:")
        for i, chunk in enumerate(hits):
            print(f"\n--- Chunk {i+1} (Score: {chunk.get('score', 'N/A')}) ---")
            print(f"ID: {chunk.get('id', 'N/A')}")
            print(f"Metadata: {json.dumps(chunk.get('metadata', {}), indent=2, ensure_ascii=False)}")
            print(f"Full Text:\n{chunk.get('text', '')}")
            print("-" * 40)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test case 1: Montmirail supplies
    debug_query(
        "Quel est le montant du comparatif fournitures pour le projet Montmirail ?",
        "Montant comparatif fournitures (Expected: 220 792 EUR)"
    )

    # Test case 2: Résine sablée
    debug_query(
        "Quel est le montant de la résine sablée sur enrobés ?",
        "Montant résine sablée (Expected: 75 264 EUR)"
    )
