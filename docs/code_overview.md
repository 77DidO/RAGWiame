# Vue d'ensemble du code — RAGWiame

Ce rapport synthétise la structure du code, les points d'entrée, les principaux flux et les dépendances clés du projet.

## Architecture modulaire

Le projet suit une **architecture modulaire** avec séparation claire des responsabilités :

### LLM Pipeline (`llm_pipeline/`)
- **`api.py`** (260 lignes) : Gateway FastAPI, routes `/rag/query`, `/v1/chat/completions`, `/v1/models`, `/files/view`
- **`pipeline.py`** (220 lignes) : Orchestrateur RAG principal
- **`config.py`** : Configuration centralisée (modèles, RAG, hybrid search)
- **`models.py`** : Modèles Pydantic (QueryPayload, ChatRequest, etc.)
- **`prompts.py`** : Templates de prompts spécialisés (default, fiche, chiffres, chat)
- **`context_formatting.py`** : Formatage du contexte RAG
- **`retrieval.py`** : Recherche hybride (Vector + BM25)
- **`reranker.py`** : CrossEncoder pour reranking
- **`citation_formatter.py`** : Formatage des citations pour OpenWebUI
- **`request_utils.py`** : Utilitaires requêtes (filtres, normalisation, RAG mode)
- **`text_utils.py`** : Fonctions texte (tokenize, citation_key)
- **`query_classification.py`** : Classification des questions
- **`insights.py`**, **`inventory.py`** : Services spécialisés

### Ingestion (`ingestion/`)
- **`pipeline.py`** (160 lignes) : Orchestrateur d'ingestion
- **`text_processor.py`** : Nettoyage et découpage texte
- **`structure_detector.py`** : Détection sections et FAQ
- **`metadata_enricher.py`** : Classification doc_hint
- **`quality_filter.py`** : Filtre de qualité (rejette chunks < 50 chars, >40% chiffres, <20% lettres)
- **`connectors/`** : PDF, DOCX, Excel, Text, MariaDB

### Indexation (`indexation/`)
- **`qdrant_indexer.py`** : Embeddings HF, collection Qdrant

## Flux RAG

1. **Requête** → `api.py` reçoit `/v1/chat/completions`
2. **Classification** → `query_classification.py` détecte le type de question
3. **Recherche** → `retrieval.py` effectue recherche hybride (Vector + BM25)
4. **Reranking** → `reranker.py` réordonne avec CrossEncoder
5. **Contexte** → `context_formatting.py` formate les chunks
6. **Génération** → `pipeline.py` appelle vLLM avec le prompt adapté
7. **Citations** → `citation_formatter.py` formate pour OpenWebUI

## Ingestion → Indexation

1. **Découverte** → Connecteurs scannent `data/`
2. **Chunking** → `text_processor.py` découpe le texte
3. **Structure** → `structure_detector.py` détecte FAQ/sections
4. **Enrichissement** → `metadata_enricher.py` infère doc_hint
5. **Filtrage** → `quality_filter.py` rejette chunks de faible qualité
6. **Indexation** → `qdrant_indexer.py` crée embeddings et indexe

## Tests

- **25+ tests unitaires** couvrant tous les modules
- Tests d'intégration pour ingestion et pipeline
- Tous les tests passent ✅

## Services Docker

- `mariadb`, `keycloak`, `qdrant`, `vllm`, `gateway`, `openwebui`
- Jobs: `ingestion`, `indexation`, `insights`, `inventory`

## Configuration (via `llm_pipeline/config.py`)

- Modèles: `RAG_MODEL_ID`, `SMALL_MODEL_ID`
- RAG: `RAG_TOP_K`, `RAG_MAX_CHUNK_CHARS`, `ENABLE_RERANKER`
- Hybrid: `HYBRID_FUSION`, `HYBRID_WEIGHT_VECTOR`, `HYBRID_BM25_TOP_K`
- LLM: `LLM_TEMPERATURE`, `LLM_TIMEOUT`

---
Mis à jour après refactoring complet (Phases 1-6).
