# Workflows de traitement — RAGWiame

Ce document présente les principaux workflows de traitement de la plateforme RAGWiame, du dépôt de documents à la génération de réponses augmentées par retrieval.

---

## 1. Ingestion et Indexation

**Objectif :** Préparer les documents pour la recherche augmentée (RAG).

**Étapes :**
1. **Dépôt des fichiers**
   - Par upload UI (FastAPI) ou copie dans `data/examples/`.
2. **Découverte et segmentation**
   - Pipeline d'ingestion (`ingestion/pipeline.py`) :
     - Connecteurs TXT, PDF, DOCX, Excel, MariaDB.
     - Nettoyage, découpe en chunks, détection de sections/FAQ, enrichissement des métadonnées (`doc_hint`, section, chunk_index).
     - **Filtre de qualité** : exclusion automatique des chunks de faible qualité (>40% de chiffres, <20% de lettres, <50 caractères).
3. **Indexation vectorielle**
   - Conversion des chunks en objets Document (LlamaIndex).
   - Embeddings HuggingFace.
   - Push dans Qdrant (collection `rag_documents`).

**Déclenchement :**
- Via CLI :
  ```powershell
  docker compose -f infra/docker-compose.yml run --rm ingestion
  docker compose -f infra/docker-compose.yml run --rm indexation
  ```
- Ou via l'upload UI (case à cocher "Lancer ingestion + indexation").

---

## 2. Classification LLM

**Objectif :** Typage automatique des documents pour enrichir la base et faciliter les filtres métier.

**Étapes :**
1. **Agrégation des chunks par document**
2. **Appel au LLM (vLLM, OpenAI-like)**
   - Prompt JSON strict, labels par défaut ou libres.
   - Injection du `doc_hint` pour améliorer la classification.
3. **Persistance**
   - Écriture dans MariaDB (table `document_classification`).

**Déclenchement :**
- Via CLI :
  ```powershell
  docker compose -f infra/docker-compose.yml run --rm classification
  ```

---

## 3. Extraction d'insights (totaux DQE)

**Objectif :** Extraire les montants clés des DQE (XLSX) pour répondre aux questions métier.

**Étapes :**
1. **Scan des fichiers Excel**
2. **Détection des lignes TOTAL**
3. **Persistance**
   - Écriture dans MariaDB (table `document_insights`).

**Déclenchement :**
- Via CLI :
  ```powershell
  docker compose -f infra/docker-compose.yml run --rm insights
  ```

---

## 4. Inventaire documentaire

**Objectif :** Maintenir une vue structurée des documents par projet/dossier.

**Étapes :**
1. **Scan de l'arborescence**
2. **Enregistrement des métadonnées (projet, dossier, type, chemin)**
   - Persistance dans MariaDB (table `document_inventory`).

**Déclenchement :**
- Via CLI :
  ```powershell
  docker compose -f infra/docker-compose.yml run --rm inventory
  ```

---

## 5. Recherche augmentée (RAG)

**Objectif :** Générer des réponses enrichies par retrieval contextuel.

**Étapes :**
1. **Réception de la question (API Gateway)**
   - Endpoint `/rag/query` ou `/v1/chat/completions`.
2. **Filtrage par service/role (metadata)**
3. **Retrieval vectoriel (LlamaIndex + Qdrant)**
   - Sélection des chunks pertinents.
   - Rerank optionnel (CrossEncoder).
4. **Formatage du contexte**
   - En-têtes source/page/section, snippets ciblés.
   - Déduplication par source (un extrait par document).
5. **Génération via LLM (vLLM)**
   - Prompt système strict (français) avec règles anti-hallucination.
   - Ajout des citations et liens vers les documents.

**Déclenchement :**
- Via API :
  ```bash
  curl -X POST http://localhost:8081/rag/query ...
  curl -X POST http://localhost:8081/v1/chat/completions ...
  ```
- Via Open WebUI (preset RAG ou chat direct).

---

## 6. Réponses directes (insights/inventaire)

**Objectif :** Court-circuiter le RAG pour répondre directement aux questions métier (montants, inventaire).

**Étapes :**
1. **Détection de la question (totaux/inventaire)**
2. **Lecture directe en base MariaDB**
   - Tables `document_insights` ou `document_inventory`.
3. **Formatage et renvoi de la réponse enrichie (citations, liens).**

---

## 7. Mode "chat direct" (sans RAG)

**Objectif :** Permettre à l'utilisateur de dialoguer avec le LLM sans retrieval documentaire.

**Étapes :**
1. **Flag `use_rag=false` dans la requête**
2. **La Gateway appelle directement le LLM sans retrieval**

**Déclenchement :**
- Via API ou WebUI (toggle, preset, ou directive `#norag`).

---

## Diagramme simplifié

```
[Upload/CLI] → [Ingestion/Indexation] → [Qdrant]
      ↓                ↓
[Classification]   [Insights]   [Inventaire]
      ↓                ↓             ↓
   [MariaDB]      [MariaDB]     [MariaDB]
      ↓                ↓             ↓
         [Gateway API]
              ↓
   [Retrieval RAG] ←→ [Réponses directes]
              ↓
         [LLM/vLLM]
              ↓
         [Réponse enrichie]
```

---

Pour plus de détails, voir aussi :
- `docs/code_overview.md`
- `docs/ingestion.md`
- `docs/gateway.md`
- `docs/prompt_gateway.md`
