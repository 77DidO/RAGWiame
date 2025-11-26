# Feuille de route refactorisation RAG

Objectif : rendre `llm_pipeline` plus lisible, testable et extensible, sans casser le comportement actuel.

---

## Phase 1 – Stabilisation de l’existant

- Documenter l’architecture actuelle du pipeline RAG :
  - rôle de `RagPipeline` (`llm_pipeline/pipeline.py`),
  - gateway FastAPI (`llm_pipeline/api.py`),
  - classification de question (`llm_pipeline/query_classification.py`),
  - index Qdrant + Elasticsearch.
- Consolider la classification de questions :
  - Types gérés : `fiche_identite`, `question_chiffree`, `inventaire_documents`, `autre`.
  - Ajuster les mots-clés en fonction des logs réels (questions utilisateurs).

---

## Phase 2 – Prompts & types de questions

- Créer `llm_pipeline/prompts.py` :
  - fonctions pour construire les prompts :
    - `get_default_prompt()`,
    - `get_fiche_prompt()`,
    - `get_chiffres_prompt()`,
    - `get_chat_prompt()`.
- Adapter `RagPipeline.__init__` :
  - remplacer la construction inline des `PromptTemplate` par des appels à `prompts.py`.
- Garder la logique : `question_type` (via `classify_query_type`) → choix du prompt approprié.

---

## Phase 3 – Formatage de contexte

- Créer `llm_pipeline/context_formatting.py` :
  - extraire la logique de :
    - récupération du texte brut d’un node,
    - tokenisation simple,
    - sélection de phrases pertinentes,
    - construction du `context_text` et de la map `snippet_map`.
  - exposer une interface claire :
    - `format_context(nodes, question, max_chunk_chars) -> (context_text, snippet_map)`.
- Adapter `RagPipeline.query()` :
  - remplacer l’appel à `_format_context` interne par `format_context(...)`.
- Ajouter quelques tests unitaires sur `format_context` (avec nodes mockés).

---

## Phase 4 – Retrieval hybride (Qdrant + BM25)

- Créer `llm_pipeline/retrieval.py` :
  - y déplacer la logique :
    - construction des nodes BM25,
    - fusion des scores (RRF / pondération),
    - requêtes hybrides (denses + BM25),
    - normalisation des scores.
  - exposer une fonction de haut niveau :
    - `hybrid_query(question, filters, index, top_k, ...) -> (nodes, hits)`.
- Adapter `RagPipeline.query()` :
  - utiliser `hybrid_query` lorsque `use_hybrid=True`,
  - garder le retrieval simple via `index.as_retriever` sinon.
- Ajouter des tests unitaires ciblés sur `hybrid_query` (faux hits ES, faux nodes Qdrant).

---

## Phase 5 – Clarifier les responsabilités

- Redéfinir le rôle de `RagPipeline` :
  - orchestration uniquement :
    1. classifier la question,
    2. récupérer les nodes (hybride ou simple),
    3. formater le contexte,
    4. choisir le prompt,
    5. appeler le LLM,
    6. construire les citations / hits.
- Documenter les interfaces internes :
  - `classify_query_type`,
  - `format_context`,
  - `hybrid_query`,
  - helpers de `prompts.py`.
- Option : introduire une interface `RagEngine` si plusieurs pipelines doivent coexister (par service, projet, etc.).

---

## Phase 6 – Nettoyage & tests de régression

- Supprimer progressivement du code devenu mort dans `pipeline.py` (helpers non utilisés) après migration complète vers les nouveaux modules.
- Lancer la suite de tests RAG après chaque grosse étape :
  - `tests/test_rag_quality.py`,
  - `tests/test_rag_contextual.py`,
  - `tests/test_rag_performance.py` (si pertinent).
- Mettre à jour la documentation :
  - `docs/tests.md` pour les scénarios RAG,
  - pointer vers cette feuille de route depuis un document d’architecture (`docs/code_overview.md` ou `docs/rag_pipeline.md`).

