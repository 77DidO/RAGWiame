# Architecture fonctionnelle et technique – RAG Wiame

## 1. Vue globale

```
Utilisateur ──(OIDC)──► Open WebUI ──► Gateway FastAPI ──► {Qdrant + Elasticsearch} ──► vLLM (Mistral)
                                             │
                                             └──► vLLM-light (Phi-3 mini, optionnel)

Fichiers / SQL ──► ingestion ──► indexation ──► Qdrant + Elasticsearch
```

Deux flux structurent la plateforme :
1. **Ingestion / indexation** : import des documents, segmentation, embeddings, stockage dans Qdrant + index BM25.
2. **Question / réponse** : Open WebUI consomme la Gateway comme API OpenAI ; la Gateway orchestre la recherche hybride puis délègue la génération au LLM (vLLM).

---

## 2. Pile logicielle et rôles

| Couche | Service / Technos | Conteneur | Rôle principal | Ports |
| --- | --- | --- | --- | --- |
| Interface utilisateur | Open WebUI (Next.js + FastAPI) | `openwebui` | Interface chat, presets, upload de fichiers | 8080 |
| Authentification | Keycloak 24 | `keycloak` | SSO OIDC, mapping des rôles vers `service/role` | 8080/8443 |
| Orchestrateur RAG | FastAPI + LlamaIndex + clients Qdrant/Elastic | `gateway` | API `/rag/query`, `/v1/chat/completions`, classification des questions, formatage contexte, citations | 8081 |
| LLM principal | vLLM + `mistralai/Mistral-7B-Instruct` | `vllm` | Génération des réponses RAG (API OpenAI-compatible) | 8000 |
| LLM léger (optionnel) | vLLM + `microsoft/Phi-3-mini-4k-instruct` | `vllm-light` (profil `light`) | Modèle low VRAM accessible via Gateway si `ENABLE_SMALL_MODEL=true` | 8002 |
| Stockage vectoriel | Qdrant 1.15 | `qdrant` | Collection `rag_documents`, stockage des embeddings + métadonnées | 6333 |
| Index lexical | Elasticsearch 8.12 | `elasticsearch` | Index BM25 `rag_documents`, support de la recherche hybride | 9200 (exposé 8120 sur l’hôte) |
| Pipelines data | Scripts Python / LlamaIndex | `ingestion`, `indexation` | Nettoyage, chunking, embeddings, push vers Qdrant + ES | Jobs `docker compose run` |
| Sources SQL | MariaDB 11 | `mariadb` | Tables optionnelles ingérées (profil `tools`) | 3306 (réseau interne) |
| Upload local (facultatif) | Mini FastAPI | `upload_ui` (hors compose) | Téléversement vers `data/examples/`, déclenche ingestion/indexation | 8001 |
| Jobs utilitaires | `insights`, `inventory`, `classification` | Profil `tools` | Analyses ad hoc, classification automatique | Jobs ponctuels |

> ⚠️ Lancer simultanément `vllm` + `vllm-light` additionne la VRAM consommée. Laisser `ENABLE_SMALL_MODEL=false` lorsque le modèle léger n’est pas nécessaire.

---

## 3. Workflows

### 3.1 Ingestion / indexation
1. **Dépôt** : les documents (PDF, DOCX, TXT, XLSX, etc.) sont placés dans `data/examples/` (manuellement ou via l’Upload UI). Les tables MariaDB peuvent être activées dans `ingestion/config.py`.
2. **Job `ingestion`** (commandes `docker compose --profile tools run --rm ingestion`) :
   - Lecture et nettoyage (UTF‑8, suppression d’artéfacts).
   - Découpage en paragraphes / sections (détection FAQ, titres Markdown, etc.).
   - Ajout des métadonnées : `source`, `service`, `role`, `doc_hint`, `chunk_index`, `page`, etc.
   - Export des chunks intermédiaires.
3. **Job `indexation`** :
   - Embeddings via `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
   - Écriture dans Qdrant (`text-dense`, payload complet).
   - Indexation BM25 dans Elasticsearch (`es_index_document`) pour la partie lexicale.
4. **Résultat** : Qdrant = mémoire vectorielle, Elasticsearch = index lexical. Purge complète possible (`INDEXATION_PURGE=true`) ou suppression ciblée via API Qdrant.

### 3.2 Recherche hybride (dense + lexical)
1. **Classification** : `classify_query_type()` détecte `question_chiffree`, `fiche_identite`, `autre` (mots-clés `effectif`, `nombre de membres`, `chiffre d’affaires`, etc.).
2. **Hybrid Query** (`llm_pipeline/retrieval.hybrid_query`) :
   - Dense : LlamaIndex interroge Qdrant (`similarity_top_k`).
   - Lexical : `bm25_search()` interroge Elasticsearch.
   - Fusion des scores via RRF ou pondération (`HYBRID_FUSION`, `HYBRID_WEIGHT_VECTOR`, `HYBRID_WEIGHT_KEYWORD`).
   - Priorisation numérique : `_prioritize_numeric_nodes()` met les chunks “effectif / CA” en tête.
3. **Formatage** : `format_context()` sélectionne les extraits pertinents et génère les citations `[1]`, `[2]`, …
4. **Prompt** : choix du prompt (`default`, `fiche`, `chiffres`) selon le type de question.
5. **Génération** : appel vLLM via `OpenAILike`, réponse enrichie par la Gateway avec citations + métadonnées.

### 3.3 Flux RAG vs Non-RAG
- **Mode RAG (par défaut)** : Open WebUI envoie `use_rag=true` (ou `x-use-rag: true`). La Gateway exécute la recherche hybride et renvoie une réponse étayée par des sources.
- **Mode non-RAG** : `use_rag=false` → la Gateway passe directement la conversation au LLM (`chat_only`), sans retrieval ni citations. Utile pour un preset “Mistral direct” ou pour tester Phi‑3 sans contexte documentaire.

---

## 4. Chaîne utilisateur → Gateway
1. L’utilisateur s’authentifie sur Open WebUI (Keycloak). Les tokens portent les rôles qui pourront être exploités pour filtrer `service/role` (mécanisme à activer selon besoin).
2. Open WebUI relaie la requête vers `http://gateway:8081/v1/chat/completions` (compatibilité OpenAI). Le preset choisit le modèle (`mistral` ou `phi3-mini`) et la valeur `use_rag`.
3. La Gateway :
   - Valide ou contourne l’auth (selon `BYPASS_AUTH`).
   - Condense la question si historique (réécriture) puis classification.
   - Exécute la recherche dense + BM25, formatte le contexte, choisit le prompt.
   - Appelle vLLM et renvoie la réponse + citations, ou exécute `chat_only` (mode non-RAG).
4. Open WebUI affiche la réponse, les sources et l’historique. Un autre client compatible OpenAI peut consommer la même API.

---

## 5. Emplacements / opérations courantes

- **Dépôt documents** : `C:\Projets\RAGWiame\data\examples`. Relancer `docker compose --profile tools run --rm ingestion` puis `indexation` pour réindexer.
- **Qdrant** : http://localhost:8130/collections/rag_documents (`points/count`, `points/delete`, snapshots…).
- **Elasticsearch** : http://localhost:8120/rag_documents/_search (tests BM25).
- **Gateway** : http://localhost:8090/rag/query (`curl` avec `use_rag=true` pour vérifier les réponses).
- **LLM direct** : http://localhost:8100/v1 (Mistral) ou http://localhost:8110/v1 (Phi-3 light si profil actif).
- **MariaDB** : service interne `mariadb`; ajouter un port (`3306:3306`) ou une UI type phpMyAdmin si besoin d’accès graphique.

---

## 6. Maintenance & observabilité

- `docker compose ps` / `logs <service>` pour la supervision basique.
- Qdrant fournit `collections/<name>` pour vérifier les compteurs, snapshots pour sauvegarder la base.
- Elasticsearch : API `_cat/indices`, `_search` pour auditer les documents BM25.
- vLLM : logs GPU (`vllm.log`), paramètres `VLLM_MAX_MODEL_LEN`, `tensor_parallel_size` ajustables via variables d’environnement.
- Variables centralisées dans `infra/docker-compose.yml` et `.env` (ex : `VLLM_ENDPOINT`, `DEFAULT_RAG_SERVICE`, `HF_EMBEDDING_MODEL`, `HYBRID_FUSION`).

---

### Résumé
- **Open WebUI** = interface + presets.  
- **Gateway** = chef d’orchestre RAG (recherche hybride, prompts, citations) ou chat pur.  
- **vLLM / vLLM-light** = moteurs de génération.  
- **Qdrant + Elasticsearch** = mémoire vectorielle + index BM25 fusionnés.  
- **Ingestion / indexation** = pipeline CLI qui alimente la base documentaire.  
- **Keycloak** = SSO et contrôle d’accès.  

Cette architecture modulaire permet de remplacer un composant (ex. Qdrant par Milvus, vLLM par une autre implémentation OpenAI) sans modifier les couches supérieures, tant que les interfaces restent compatibles.
