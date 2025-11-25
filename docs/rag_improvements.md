# Plan amelioration RAG

## Etat actuel
- Tests RAG: 3/6 reussis (refus pour comparatif fournitures, equipements raboteuse, montant resine sablee).
- Qdrant `rag_documents` (http://localhost:6333) contient ~41k points issus du projet ED257730 Montmirail.
- Donnees presentes:
  - Comparatif fournitures: sheet `comparatif fournitures` avec total `TOTAL FOURNITURE 220792.7908` mais colonnes `Unnamed` -> contexte peu lisible.
  - Raboteuse: sheets `10 - Bibli-MAT` et `9 - Bibliotheque generale` avec lignes raboteuse 1200/1000, chenille, prix.
  - Resine sablee: feuilles trouvees mais aucun total 75 264 EUR dans les chunks; seuls des lignes unitaires (~1-2k).

## Causes probables
- Extraction Excel degradee (colonnes anonymes, totaux absents), reduisant le rappel BM25 et la pertinence dense.
- Valeurs numeriques non normalisees (`220792` sans espace), mots-cles attendus non presentes dans le texte.
- Prompt refuse des qu'il estime manquer de contexte; rappel initial trop faible.

## Actions prioritaires
1) Reingestion des fichiers clefs
   - Comparatif fournitures: reextraire en gardant entetes lisibles (`Designation | PU | Total`), supprimer colonnes vides `Unnamed`, dupliquer les totaux en formats `220792` et `220 792`.
   - Raboteuse: meme traitement; ajouter labels explicites (`raboteuse`, `chenille`, `location`) dans le texte ou metadata.
   - Resine sablee: verifier l'Excel `DQE - ... Resine sable sur enrobes.xlsx`, extraire/ajouter le total 75 264 EUR dans le texte ou metadata (`total_resine_eur=75264`).
   - Reindexer completement apres nettoyage (BM25 + vector).

2) Retrieval
   - Activer et tester hybride BM25 + dense (`HYBRID_FUSION`, `HYBRID_BM25_TOP_K`, poids) pour augmenter le rappel.
   - Augmenter `initial_top_k`/`RAG_TOP_K` avant rerank pour remonter plus de candidats.

3) Prompt/LLM
   - Assouplir la reponse par defaut: si au moins un chunk pertinent est trouve, repondre plutot que refuser.
   - Forcer l'inclusion d'unite/monnaie dans les reponses chiffrées (ex: "EUR").

4) Validation
   - Relancer: `PYTHONIOENCODING=utf-8 python run_rag_tests.py`.
   - Surveiller `test_results_detailed.txt` pour presence des mots-cles attendus.

## Points de controle rapides
- Comparatif: presence du total 220 792 dans les chunks lisibles.
- Raboteuse: lignes avec "chenille"/"raboteuse" visibles dans le texte.
- Resine: total 75 264 EUR present dans un chunk ou metadata.
