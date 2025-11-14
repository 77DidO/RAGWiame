# Architecture fonctionnelle et technique

## 1. Vue globale

```
┌──────────┐    HTTP (Keycloak/OIDC)    ┌──────────┐    gRPC HTTP  ┌───────┐
│ Utilisat│───► Open WebUI ───────────►│ Gateway  │──────────────►│ vLLM  │
└──────────┘                           │ FastAPI  │               └───────┘
                                          │  ▲
                                          │  │
                                    Qdrant │  │ RAG
                                          ▼  │
                                   ┌────────────┐
                                   │ VectorStore│
                                   └────────────┘
                                          ▲
              Fichiers / SQL              │ Embeddings
   ┌──────────────┐   docker compose run  │
   │ Upload UI    │───────────────────────┤
   ├──────────────┤                       │
   │ ingestion    │────► Chunking         │
   │ indexation   │────► Sentence-BERT ───┘
```

Deux flux principaux :

1. **Ingestion / indexation** : import des documents, découpe, génération des vecteurs (Sentence-BERT multilingue) puis stockage dans Qdrant.
2. **Question / réponse** : Open WebUI (ou n’importe quel client OpenAI) appelle la Gateway FastAPI qui interroge Qdrant via LlamaIndex, puis délègue la génération à vLLM/Mistral.

## 2. Pile technologique

| Couche | Technologies | Conteneur | Rôle | Interfaces exposées |
| --- | --- | --- | --- | --- |
| Interface utilisateur | Open WebUI (Next.js + FastAPI) | `openwebui` | Chat, gestion des conversations, paramétrage des presets | HTTP 8080 (protégé par Keycloak) |
| Authentification | Keycloak 24 | `keycloak` | Realm `rag`, clients OpenID Connect, mapping des rôles vers `service/role` | OIDC 8080/8443 |
| Orchestration RAG | FastAPI + LlamaIndex + Qdrant Client | `gateway` | Endpoints `/rag/query`, `/v1/chat/completions`, filtrage service/role, transformation OpenAI ↔ pipeline | HTTP 8081 |
| Modèle de langage (RAG) | vLLM 0.6 + PyTorch + CUDA | `vllm` | Sert `mistralai/Mistral-7B-Instruct-v0.3` (API OpenAI) | HTTP 8000 |
| Modèle de langage léger (optionnel) | vLLM 0.6 + PyTorch + CUDA | `vllm-light` (profil `light`) | Sert `microsoft/Phi-3-mini-4k-instruct` (alias `phi3-mini`) lorsque la VRAM le permet | HTTP 8002 |
| Stockage vectoriel | Qdrant 1.9 | `qdrant` | Collection `rag_documents`, filtrage vectoriel + métadonnées | HTTP 6333 |
| Pipelines données | Scripts Python LlamaIndex | `ingestion`, `indexation` | Nettoyage, chunking, embedding, envoi dans Qdrant | Jobs `docker compose run` |
| Interface import | FastAPI (upload_ui) | hors compose | Téléversement local, copie vers `data/examples`, déclenchement ingestion/indexation | HTTP 8001 |
| Base relationnelle | MariaDB 11 | `mariadb` | Source optionnelle pour ingestion SQL (non obligatoire) | 3306 |

> Remarque : lancer simultanément `vllm` (Mistral 7B) et `vllm-light` (Phi-3 mini) consomme la somme de leurs VRAM. N’activez le profil `light` que ponctuellement et laissez `ENABLE_SMALL_MODEL=false` côté Gateway si vous ne servez pas le modèle léger.

## 3. Flux détaillés

### 3.1 Ingestion / indexation

1. **Source** : documents déposés manuellement dans `data/examples/` ou via l’Upload UI.
2. **Job `ingestion`** :
   - Lecture de chaque fichier.
   - Normalisation (UTF-8, suppression artefacts).
   - Extraction des métadonnées : `source`, `service`, `role`, `confidentialité`, etc.
   - Enregistrement des chunks intermédiaires.
3. **Job `indexation`** :
   - Chargement des chunks en mémoire.
   - Embedding via `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
   - Écriture dans Qdrant (`vectors` + `payload`).
4. **Qdrant** : la collection conserve les IDs, vecteurs et metadata, permettant :
   - Filtrage par `service/role`.
   - Suppression ciblée (via `points/delete`).

### 3.2 Chaîne de question / réponse

1. L’utilisateur se connecte sur Open WebUI (SSO Keycloak). Toutes les requêtes incluent le token OIDC.
2. Open WebUI relaie la requête vers la Gateway (profil RAG) via `/v1/chat/completions`. Selon le champ `model`, la Gateway construit un pipeline RAG reposant sur Mistral (`model: "mistral"`) ou sur Phi-3 mini (`model: "phi3-mini"`). Les deux passent par les mêmes étapes de récupération Qdrant.
3. La Gateway :
   - Valide le token (sauf `BYPASS_AUTH=true`).
   - Transforme la requête en `QueryPayload`.
   - Récupère les chunks pertinents via `VectorStoreIndex.as_retriever(similarity_top_k=6, filters=MetadataFilters)`.
   - Compose le prompt final et appelle vLLM avec `OpenAILike`.
4. vLLM génère la réponse en streaming et renvoie le texte.
5. La Gateway enrichit la réponse (`citations`, `metadata`) avant de la retourner à Open WebUI ou au client OpenAI.

## 4. Intégration avec Open WebUI

- Open WebUI est configuré pour utiliser l’endpoint `http://gateway:8081/v1/chat/completions`.
- Chaque espace ou preset peut pointer soit vers le mode **RAG** (Gateway, `model: "mistral"`), soit vers le **modèle léger** (`model: "phi3-mini"`, toujours via la Gateway), soit, pour un accès direct sans retrieval, vers `http://vllm:8000/v1` ou `http://vllm-light:8002/v1` (profil `light` actif).
- Les droits utilisateurs sont gérés côté Keycloak : le token OIDC inclut les rôles, et la Gateway peut mapper ces rôles vers les filtres `service/role`.
- Il est possible d’ajouter un second preset “Mistral direct” pour les questions hors référentiel, sans impacter le flux RAG.

## 5. Maintenance et observabilité

- `docker compose ps` / `logs` pour vérifier chaque service.
- Qdrant fournit `/collections`, `/points/count`, `/snapshots` pour auditer le référentiel.
- vLLM expose ses métriques GPU dans les logs (`vllm.log`), utile pour ajuster `max_seq_len`, `tensor_parallel_size`.
- Les variables clés sont centralisées dans `infra/docker-compose.yml` (ex : `VLLM_ENDPOINT`, `DEFAULT_RAG_SERVICE`, `HF_EMBEDDING_MODEL`).
- Pour automatiser la supervision, branchez Prometheus/Grafana via les endpoints HTTP existants (non fournis par défaut mais supportés).

## 6. Résumé d’imbriquement

- **Open WebUI** sert d’interface et consomme la Gateway comme un backend OpenAI.
- **Gateway FastAPI** agit comme chef d'orchestre : elle parle à Qdrant via LlamaIndex, puis à vLLM pour générer la réponse.
- **vLLM** encapsule Mistral et fournit les capacités de génération haute performance, tandis qu’un second service facultatif `vllm-light` héberge un modèle plus compact lorsque la VRAM le permet. La Gateway ne propose l’alias `phi3-mini` que si `ENABLE_SMALL_MODEL=true`.
- **Qdrant** conserve la mémoire vectorielle, alimentée par **ingestion/indexation**.
- **Upload UI** et scripts CLI constituent la porte d’entrée des données.
- **Keycloak** garantit que seuls les utilisateurs autorisés accèdent aux fonctionnalités en propulsant l’authentification centralisée.

Cette séparation permet de remplacer une couche sans affecter le reste (ex : changer Qdrant pour Milvus, ou vLLM pour une autre implémentation OpenAI-compatible) tant que les contrats d’API sont respectés.
