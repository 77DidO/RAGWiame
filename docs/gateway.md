# Configuration de la Gateway RAG

La Gateway FastAPI est le point d'entrée unique pour tout le workflow RAG :

- expose `/rag/query` pour les intégrations internes ;
- reproduit l’API OpenAI (`/v1/chat/completions`, `/v1/models`) pour Open WebUI ou n’importe quel client compatible ;
- orchestre la récupération des chunks dans Qdrant puis appelle vLLM (Mistral ou Phi‑3 mini).

Cette page détaille les variables d’environnement et paramètres importants. Toutes les valeurs mentionnées se définissent dans `infra/docker-compose.yml` (section `services.gateway.environment`), mais peuvent aussi être injectées par un orchestrateur externe.

## Variables essentielles

| Variable | Rôle | Valeur par défaut |
| --- | --- | --- |
| `RAG_MODEL_ID` | Nom du modèle « principal » que les clients doivent utiliser (`mistral`, `rag-default`, etc.) | `mistral` |
| `VLLM_ENDPOINT` | URL OpenAI-like exposée par vLLM pour ce modèle | `http://vllm:8000/v1` |
| `VLLM_API_KEY` | Jeton transmis à vLLM (placeholder pour compatibilité) | `changeme` |
| `HF_EMBEDDING_MODEL` | Modèle Hugging Face utilisé pour l’index LlamaIndex | `sentence-transformers/distiluse-base-multilingual-cased-v2` |
| `QDRANT_URL` | Endpoint HTTP de Qdrant | `http://qdrant:6333` |
| `KEYCLOAK_URL` | Base URL de Keycloak (utilisée par l’OAuth2) | `http://keycloak:8080/` |
| `BYPASS_AUTH` | `true` pour ignorer l’OAuth dans les environnements de dev | `true` (dans `docker-compose`) |

## Options Retrieval / RAG

| Variable | Impact | Notes |
| --- | --- | --- |
| `DEFAULT_RAG_SERVICE`, `DEFAULT_RAG_ROLE` | Valeurs injectées automatiquement dans les filtres metadata si l’appelant ne fournit rien | chaînes vides → aucun filtre |
| `RAG_TOP_K` | Nombre de chunks remontés pour le modèle principal | 6 |
| `SMALL_MODEL_TOP_K` | Nombre de chunks pour le modèle léger (Phi‑3, etc.) | 3 |
| `RAG_MAX_CHUNK_CHARS` | Tronque chaque chunk à N caractères après normalisation (espace unique) | 800 |

### Reranker hybride (SBERT + BM25)

1. La Gateway récupère `top_k * 3` chunks densément via LlamaIndex.
2. Un reranker SBERT multilingue garde les `top_k` meilleurs.
3. Un reranker **BM25** (librairie `rank-bm25`) re-scorise ces chunks en fonction des mots présents dans la question pour éviter les réponses hors-sujet (ex. sections FAQ).
4. Seules les phrases contenant les mots-clés de la question sont conservées avant l'appel au LLM, ce qui limite les répétitions inutiles.

Ajustez `RAG_TOP_K` / `SMALL_MODEL_TOP_K` pour contrôler la profondeur avant reranking.

## Options LLM / Génération

| Variable | Impact |
| --- | --- |
| `LLM_TEMPERATURE` | Température envoyée à vLLM (0 ⇒ réponses déterministes). |
| `LLM_TIMEOUT` | Délai maximum en secondes pour la requête vers vLLM avant d’abandonner (évite d’attendre plusieurs minutes). |
| `LLM_MAX_RETRIES` | Nombre de tentatives côté client OpenAI-like ; mettez `1` pour échouer rapidement si vLLM ne répond pas. |
| `ENABLE_SMALL_MODEL` | `true` ⇒ la Gateway expose un deuxième modèle accessible via `SMALL_MODEL_ID`. |
| `SMALL_MODEL_ID` | Nom que les clients doivent spécifier (`phi3-mini`, `llm-small`, …). |
| `SMALL_LLM_ENDPOINT` | URL OpenAI-like pointant vers `vllm-small`. |

> ⚠️ Pour que `phi3-mini` apparaisse dans `/v1/models`, il faut **à la fois** que `ENABLE_SMALL_MODEL=true` et que le service `vllm-small` soit en cours d’exécution.

## Exemple de bloc `gateway` (docker compose)

```yaml
  gateway:
    build:
      context: ../llm_pipeline
      dockerfile: Dockerfile
    ports:
      - "8081:8081"
    environment:
      RAG_MODEL_ID: mistral
      VLLM_ENDPOINT: http://vllm:8000/v1
      ENABLE_SMALL_MODEL: "true"
      SMALL_MODEL_ID: phi3-mini
      SMALL_LLM_ENDPOINT: http://vllm-small:8002/v1
      RAG_TOP_K: "6"
      SMALL_MODEL_TOP_K: "2"
      RAG_MAX_CHUNK_CHARS: "600"
      LLM_TEMPERATURE: "0.0"
      LLM_TIMEOUT: "180"
      LLM_MAX_RETRIES: "1"
      DEFAULT_RAG_SERVICE: support
      DEFAULT_RAG_ROLE: conseiller
      QDRANT_URL: http://qdrant:6333
      KEYCLOAK_URL: http://keycloak:8080/
      BYPASS_AUTH: "false"   # laissez "true" uniquement en dev
```

Adaptez les valeurs selon vos contraintes GPU ou les besoins métier. Toute modification impose un rebuild + redeploy de la Gateway :

```powershell
docker compose -f infra/docker-compose.yml build gateway
docker compose -f infra/docker-compose.yml up -d gateway
```

## Modèles multiples (Mistral + Phi‑3 mini)

1. Lancez les services requis : `docker compose -f infra/docker-compose.yml up -d vllm vllm-small gateway`.
2. Ajoutez dans Open WebUI deux presets pointant vers `http://gateway:8081/v1` mais avec `model` = `mistral` ou `phi3-mini`.
3. Ajustez `SMALL_MODEL_TOP_K` et `RAG_MAX_CHUNK_CHARS` si le modèle léger hallucine ou sature.

## Authentification

- `BYPASS_AUTH=false` : la Gateway exige un token OIDC ; Open WebUI se charge du flux via Keycloak (variables `OAUTH_*` déjà présentes côté UI).  
- En tests locaux, laissez `BYPASS_AUTH=true` pour éviter la redirection OAuth.

## Surveillance & logs

- `docker compose -f infra/docker-compose.yml logs -f gateway` : pipeline, warnings Qdrant, erreurs LLM.  
- `docker compose -f infra/docker-compose.yml logs -f vllm-small` : surveillez les “Avg generation throughput” pour détecter les temps de réponse trop longs.  
- Ajustez `LLM_TIMEOUT` ou `RAG_TOP_K` si vous voyez des `openai.APITimeoutError` dans la Gateway.

## Résumé rapide des réglages critiques

| Besoin | Paramètres à modifier |
| --- | --- |
| Limiter la taille du contexte | `RAG_TOP_K`, `SMALL_MODEL_TOP_K`, `RAG_MAX_CHUNK_CHARS` |
| Durcir les réponses (pas d’hallucinations) | `LLM_TEMPERATURE=0`, prompt fourni dans `pipeline.py` |
| Réduire le temps de réponse | Diminuer `top_k`, augmenter `LLM_TIMEOUT`, arrêter les modèles inutiles |
| Cacher Phi‑3 mini côté clients | `ENABLE_SMALL_MODEL=false` **et** arrêter `vllm-small` |
| Basculer sur un autre modèle Hugging Face | mettre à jour `VLLM_MODEL_NAME` / `VLLM_SERVED_MODEL_NAME` (service `vllm`) et `RAG_MODEL_ID` |

Gardez cette page sous la main lorsque vous adaptez la plateforme à un nouvel environnement ou à un client spécifique. Elle regroupe les leviers principaux qui influent sur la qualité des réponses et la stabilité du pipeline RAG.
