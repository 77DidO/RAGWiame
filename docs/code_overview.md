# Vue d’ensemble du code — RAGWiame

Ce rapport synthétise la structure du code, les points d’entrée, les principaux flux et les dépendances clés du projet.

## Composants principaux
- Gateway FastAPI: `llm_pipeline/api.py` — expose `/rag/query`, `/v1/chat/completions`, `/v1/models`, `/files/view`, `/healthz`.
- Pipeline RAG: `llm_pipeline/pipeline.py` — retrieval LlamaIndex, rerank CrossEncoder (optionnel), génération via `OpenAILike` (vLLM).
- Ingestion: `ingestion/pipeline.py` — découverte, nettoyage, segmentation, enrichissement (FAQ/sections/doc_hint).
- Connecteurs: `ingestion/connectors/*` — `pdf`, `docx`, `excel`, `text`, `mariadb`.
- Indexation Qdrant: `indexation/qdrant_indexer.py` — embeddings HF, collection `rag_documents`.
- Upload UI: `upload_ui/main.py` — mini FastAPI d’upload, déclenche `indexation` via docker compose.
- Insights & Inventaire: `ingestion/insights*.py`, `ingestion/inventory*.py` + services Gateway `llm_pipeline/insights.py`, `llm_pipeline/inventory.py`.

## Apps FastAPI et routes
- `llm_pipeline/api.py`
  - POST `/rag/query` → RAG + réponses directes (insights/inventaire) + citations.
  - POST `/v1/chat/completions` → Compat OpenAI; passe par RAG ou mode chat selon `metadata.use_rag`.
  - GET `/v1/models` → liste des modèles registrés (ex: `mistral`, `phi3-mini`).
  - GET `/files/view?path=...` → sert les fichiers de `DATA_ROOT` (inline PDF/TXT/HTML sinon download).
  - GET `/healthz` → liveness.
- `upload_ui/main.py`
  - GET `/` → formulaire HTML simple.
  - POST `/` → upload dans `data/examples` + option de lancer `indexation`.

## Ingestion → Indexation
- Pipeline: `IngestionPipeline.run()` parcourt chaque connecteur et segmente avec:
  - Détection de sections (titres/"... :") et blocs FAQ (Question/Réponse)
  - Buffering par paragraphe et découpe par `chunk_size/chunk_overlap`
  - `doc_hint` inféré (courriel, planning, memoire, dqe, tableur, pdf)
- Connecteurs:
  - `PDFConnector` (pdfplumber): page → chunk + métadonnées (Author, Title, Page…)
  - `DocxConnector` (python-docx): paragraphe
  - `ExcelConnector` (pandas): feuille → CSV tronqué (options lignes/colonnes/formules)
  - `TextConnector`: fenêtrage fixe avec chevauchement
  - `MariaDBConnector` (optionnel): requête SQL → lignes formatées key: value
- Indexation: `indexation/qdrant_indexer.py`
  - Convertit les chunks → `llama_index.core.Document`
  - `VectorStoreIndex.from_documents` avec `QdrantVectorStore` et `HuggingFaceEmbedding`

## Chaîne RAG (Gateway)
- Index partagé: `_build_index()` — Qdrant (URL/collection), embeddings HF, LlamaIndex.
- Sélection modèle: `get_pipeline(model_id)` → endpoint `MODEL_ENDPOINTS` (mistral/vllm, phi3-mini/vllm-light) + `top_k`.
- RAG vs Chat: `_resolve_rag_mode(question, explicit)`
  - `DEFAULT_USE_RAG` ou directives inline: `#norag`, `rag:false`, `#forcerag`, `rag:true`.
- Réponses directes (court-circuit RAG):
  - `DocumentInventoryService.try_answer()` → table `document_inventory`
  - `DocumentInsightService.try_answer()` → table `document_insights` (totaux DQE)
- Contexte & citations: `_format_context()` assemble en-têtes [Source|Page|Section], snippets ciblés; `_append_citations_text()` ajoute un bloc Références avec liens `/files/view`.
- Toggle RAG dans Open WebUI :
  - `src/lib/components/chat/Chat.svelte` stocke `ragEnabled` (clé `chat-rag-mode`) et transmet `metadata: { use_rag: ragEnabled }` dans la requête `/v1/chat/completions`.
  - `ChatControls.svelte`/`Controls.svelte` exposent un switch “Mode RAG” pour l’utilisateur.
  - `_resolve_rag_mode()` côté gateway lit ce flag (en plus des directives `#norag`/`#forcerag`) pour choisir entre `RagPipeline.query()` et `chat_only()`.

## Pipeline LLM
- `RagPipeline.query()`
  - `index.as_retriever(similarity_top_k)` + filtres `MetadataFilters` (service/role)
  - Rerank optionnel: `CrossEncoder("amberoad/bert-multilingual-passage-reranking-msmarco")`
  - Prompt QA strict (fr) et tronquage des snippets à `RAG_MAX_CHUNK_CHARS`
- `RagPipeline.chat_only()` → prompt bref sans retrieval

## Classification, Insights, Inventaire (CLIs)
- `ingestion/classify_cli.py` → regroupe par source, tronque, classe via endpoint OpenAI-like (vLLM), écrit dans `document_classification`.
- `ingestion/insights_cli.py` → lit XLSX, détecte lignes TOTAL (valeur max sur la ligne), upsert `document_insights`.
- `ingestion/inventory_cli.py` → scanne arborescence, remplit `document_inventory`.

## Services Docker (infra/docker-compose.yml)
- `mariadb`, `keycloak`, `qdrant`, `vllm` (Mistral), `vllm-light` (Phi‑3 mini, profil `light`), `gateway`, `openwebui`.
- Jobs: `ingestion`, `indexation`, `insights`, `inventory`, `classification`.
- Volumes: données persistées pour MariaDB, Qdrant, modèles vLLM, et `openwebui_data`.

## Paramètres clés (Gateway)
- Modèles: `RAG_MODEL_ID`, `VLLM_ENDPOINT`, `ENABLE_SMALL_MODEL`, `SMALL_MODEL_ID`, `SMALL_LLM_ENDPOINT`.
- RAG: `RAG_TOP_K`, `SMALL_MODEL_TOP_K`, `RAG_MAX_CHUNK_CHARS`, `ENABLE_RERANKER`.
- LLM: `LLM_TEMPERATURE`, `LLM_TIMEOUT`, `LLM_MAX_RETRIES`.
- Données: `QDRANT_URL`, `DATA_ROOT`, `PUBLIC_GATEWAY_URL`.
- Auth & bases: `KEYCLOAK_URL`, `MARIADB_*`, `ENABLE_INSIGHTS`, `ENABLE_INVENTORY`, `BYPASS_AUTH`.

## Points d’extension / Qualité
- Ajouts possibles: 
  - Connecteurs (ex: SharePoint, S3) via `BaseConnector`.
  - Rerankers alternatifs/MLC; réglage `initial_top_k`.
  - Normalisation `document_label` post-classification côté UI ou batch.
- Tests: CLIs Typer testables; endpoints FastAPI couverts via TestClient (à compléter si besoin).

---
Généré automatiquement par analyse du dépôt. Ouvrir: `docs/code_overview.md`.
