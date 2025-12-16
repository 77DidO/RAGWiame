"""Script de test manuel pour le QueryRouter."""
import os
import sys

# Ajouter la racine du projet au path
sys.path.append(os.getcwd())

# from llama_index.llms.openai_like import OpenAILike
from llm_pipeline.query_router import QueryRouter

def test_router():
    print("--- Initialisation du Router et du LLM (Mock) ---")
    
    # On mocke le LLM car on ne veut pas dépendre du serveur vLLM pour ce test unitaire rapide
    # Si vous avez vLLM qui tourne, vous pouvez décommenter la vraie classe
    class MockLLM:
        def predict(self, prompt, **kwargs):
            question = kwargs.get("question", "")
            print(f" [LLM Mock] Analyzing: {question}")
            if "Bordeaux" in question:
                return '{"ao_commune": "BORDEAUX", "ao_doc_code": "BPU"}'
            if "ED4500" in question:
                return '{"ao_id": "ED4500", "ao_phase_label": "Candidature"}'
            return "{}"
            
    llm = MockLLM()
    # Pour tester avec le vrai vLLM si disponible :
    # llm = OpenAILike(api_base="http://localhost:8000/v1", api_key="fake", model="mistral")

    router = QueryRouter()
    
    test_cases = [
        "J'ai besoin du BPU pour l'affaire ED12345", 
        "Donne moi le CCTP de la mairie de Bordeaux", # Nécessite LLM pour Bordeaux (si regex pas assez puissante) ou Regex
        "Quel est le prix pour la phase candidature ?",
        "Je veux le règlement de consultation pour Lyon",
        "Liste des documents signés pour le projet ED99999"
    ]

    print("\n--- Démarrage des tests ---")
    for q in test_cases:
        print(f"\nQ: {q}")
        # Test sans LLM d'abord (Pur Regex)
        # res_regex = router.analyze(q, llm=None)
        # print(f"  -> Regex Only: {res_regex.filters}")
        
        # Test avec LLM
        res_full = router.analyze(q, llm=llm)
        print(f"  -> Full Router: {res_full.filters} (Conf: {res_full.confidence:.2f})")

    # Cas 4 : Question générique sur AO (Doit retourner tous les codes officiels)
    print("\n--- Test 4 : Question générique 'Infos sur AO ED258239' ---")
    res4 = router.analyze("Donne moi les infos sur l'AO ED258239")
    print(f"Intent: {res4.intent}")
    print(f"Filters: {res4.filters}")
    if "ao_doc_code" in res4.filters and isinstance(res4.filters["ao_doc_code"], list):
        print("✅ SUCCESS: Liste de codes documents injectée par défaut.")
    else:
        print("❌ FAILURE: Pas de liste de codes documents par défaut.")

if __name__ == "__main__":
    test_router()
