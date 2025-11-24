# RAGWiame

Plateforme RAG open source orientée francophonie. Ce dépôt fournit un kit complet pour déployer ingestion, indexation et génération basées sur LlamaIndex, Qdrant et Mistral 7B propulsé par vLLM.

## Panorama des services

- **vLLM (Mistral)** : sert le modèle `mistralai/Mistral-7B-Instruct-v0.3` via une API compatible OpenAI pour le mode RAG.
- **vLLM (Phi-3 mini)** : service optionnel à lancer uniquement lorsque la VRAM le permet (`microsoft/Phi-3-mini-4k-instruct`, servi sous l’alias `phi3-mini`).
- **Gateway FastAPI** : applique la logique RAG (retrieval + génération) et expose `/rag/query` ainsi que `/v1/chat/completions`.
- **Qdrant** : stockage vectoriel (collection `rag_documents`) et API HTTP pour maintenance.
- **MariaDB** : source optionnelle pour l’ingestion relationnelle.
- **Open WebUI** : interface conversationnelle (Keycloak/OAuth2 déjà câblé).
- **Pipelines ingestion/indexation** : scripts LlamaIndex pour charger vos documents et produire les embeddings.

## Prérequis

- Windows 11 + Docker Desktop **ou** Linux avec Docker Engine + Compose v2.
- Python 3.11 (utilisé par `scripts/start.py` pour orchestrer bootstrap et déploiement).
- Accès GPU recommandé pour vLLM (CUDA 12+). En CPU, attendez-vous à des temps de réponse plus longs.

## Démarrage rapide

```powershell
# Depuis la racine du dépôt
python scripts/start.py
```

Options utiles :

- `--skip-bootstrap` : saute la création de l’environnement virtuel.
- `--skip-deploy` : n’exécute pas `docker compose`.
- `--skip-build` : réutilise les images déjà construites.

Le script vérifie que Docker Desktop tourne, installe les dépendances Python puis lance `docker compose -f infra/docker-compose.yml up -d`. Consultez `docs/demarrage_automatique.md` pour le détail pas à pas ou `docs/deploiement.md` pour la configuration avancée (profils GPU, variables d’environnement, etc.).

## Vérifier l’infrastructure

```powershell
docker compose -f infra/docker-compose.yml up -d      # démarre tous les services
docker compose -f infra/docker-compose.yml ps         # vérifie leur état
docker compose -f infra/docker-compose.yml logs gateway
```

Ports exposés :

- Gateway RAG : `http://localhost:8081`
- vLLM Mistral : `http://localhost:8000/v1`
- vLLM léger (optionnel) : `http://localhost:8002/v1`
- Qdrant : `http://localhost:6333`
- Open WebUI : `http://localhost:8080` (auth Keycloak)

## Utilisation des API

- **Configurer Open WebUI la première fois** :
  1. Rendez-vous sur `http://localhost:8080` (auth Keycloak). Si la page est vide après un rebuild, forcez un `Ctrl+F5`.
 2. Dans “Sélectionnez un modèle”, créez un preset `Mistral RAG` en pointant vers `http://gateway:8081/v1` (model `mistral`) et définissez-le comme valeur par défaut.
 3. Pour un mode “chat direct”, dupliquez le preset et ajoutez dans les paramètres avancés `{"metadata":{"use_rag":false}}` ou bien forcez ce mode globalement via l’option `DEFAULT_USE_RAG=false` côté Gateway (voir plus bas).
  4. Les données sont stockées dans `openwebui_data`, vous n’aurez plus à refaire ces étapes après un redémarrage.

### RAG natif

```bash
curl -X POST http://localhost:8081/rag/query \
  -H "Content-Type: application/json" \
  -d '{
        "question": "Quels sont les prérequis ?",
        "service": "support",
        "role": "conseiller"
      }'
```

La Gateway applique des filtres `service/role` (metadata Qdrant). Sans documents ingérés, la réponse restera vide : voir la section suivante pour alimenter la base.

### Compatibilité OpenAI

```bash
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral", "messages":[{"role":"user","content":"Bonjour"}]}'
```

La Gateway convertit automatiquement la requête en question RAG, récupère les chunks pertinents puis appelle vLLM. Utilisez `/v1/models` pour vérifier la disponibilité de `mistral`.

### Mode conversation (sans RAG)

La Gateway comprend un flag `use_rag` pour ignorer la partie retrieval quand vous voulez un simple échange “chat” avec Mistral :

```bash
curl -X POST http://localhost:8081/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Parle-moi du projet","use_rag":false}'
```

Sur `/v1/chat/completions`, ajoutez `metadata.use_rag=false` dans la payload. Dans Open WebUI, créez un preset qui envoie ce champ dans la section “Advanced/Extra parameters” (à défaut d’un toggle natif) ou fixez `DEFAULT_USE_RAG=false` côté Gateway pour que toutes les requêtes soient en “chat direct” par défaut.

> Astuce : ajoutez `#norag` ou `rag:false` dans la question pour forcer le mode “chat direct”, et `#forcerag` / `rag:true` pour forcer le RAG. La Gateway nettoie ces directives avant d’envoyer la requête au LLM.

### Accès direct au modèle

Pour interroger Mistral sans retrieval, ciblez directement vLLM :

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mistralai/Mistral-7B-Instruct-v0.3","messages":[{"role":"user","content":"Bonjour"}]}'
```

### Modèle léger pour tester le RAG

Une instance vLLM supplémentaire **optionnelle** peut exposer un modèle plus petit (`phi3-mini` par défaut) sur `http://localhost:8002/v1`. La Gateway applique toujours le pipeline RAG (retrieval + réponse), mais utilise ce modèle à la place de Mistral :

```bash
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"phi3-mini","messages":[{"role":"user","content":"Réponds-moi brièvement"}]}'
```

Dans Open WebUI, créez un preset `phi3-mini` (URL identique à `mistral`) : seul le champ `Model` change. Selon la VRAM disponible, démarrez/arrêtez `vllm-light` indépendamment (`docker compose --profile light up -d vllm-light`, `docker compose --profile light stop vllm-light`).

Variables utiles (`infra/docker-compose.yml`) :

- `VLLM_SMALL_MODEL_NAME` / `VLLM_SMALL_SERVED_MODEL_NAME` : modèle Hugging Face et alias exposé.
- `ENABLE_SMALL_MODEL` : permet de masquer l’option côté Gateway lorsqu’il n’est pas lancé.
- `SMALL_MODEL_ID` : valeur attendue dans le champ `model` (doit correspondre à `--served-model-name`).

> ⚠️ Attention : lancer simultanément Mistral 7B et Phi-3 mini consomme la somme de leurs VRAM. Si votre carte ne le permet pas, laissez `ENABLE_SMALL_MODEL=false` et n'activez le profil `light` (`vllm-light`) que ponctuellement.

### Recherche hybride (Qdrant + Elasticsearch)

- Service `elasticsearch` ajouté dans `infra/docker-compose.yml` (port 9200, `xpack.security.enabled=false` en dev). Variables : `ELASTIC_HOST` (défaut `http://elasticsearch:9200`), `ELASTIC_INDEX` (`rag_documents`).
- Ingestion/indexation : chaque chunk est indexé dans Qdrant **et** Elasticsearch avec `content`, `source`, `service`, `role`, `doc_hint`, `chunk_index`, `page`.
- Gateway : endpoint `POST /v1/hybrid/search` (réponse RAG complète) et option `return_hits_only=true` pour ne retourner que la liste fusionnée des documents.
- OpenAI-like : ajouter l'en-tête `X-Hybrid-Search: true` sur `/v1/chat/completions` ou appeler `/v1/hybrid/completions` (Open WebUI relaie cet en-tête vers la Gateway).
- Fusion : `HYBRID_FUSION=rrf` par défaut (Reciprocal Rank Fusion). Mode pondéré via `HYBRID_FUSION=weighted` + `HYBRID_WEIGHT_VECTOR` / `HYBRID_WEIGHT_KEYWORD`. Taille BM25 configurable (`HYBRID_BM25_TOP_K`).
- Sécurité prod : activer xpack/API key ou cloisonner le réseau ; le mode sans auth est réservé au développement.

## Ingestion et indexation

Deux approches complémentaires sont détaillées dans [docs/ingestion.md](docs/ingestion.md) :

1. **Scripts CLI**
   ```powershell
   # Copier les fichiers dans data/examples/ avant de lancer les jobs
docker compose -f infra/docker-compose.yml run --rm ingestion
docker compose -f infra/docker-compose.yml run --rm indexation
docker compose -f infra/docker-compose.yml run --rm insights   # extraction des totaux DQE
docker compose -f infra/docker-compose.yml run --rm inventory  # inventaire des documents par projet
```
2. **Mini UI FastAPI**
   ```bash
   pip install -r upload_ui/requirements.txt
   uvicorn upload_ui.main:app --port 8001 --reload
   ```

### Classification LLM (document → type)

Après ingestion/indexation, lancez la classification pour typer chaque fichier (résultat stocké dans MariaDB, table `document_classification`) :

```powershell
docker compose -f infra/docker-compose.yml run --rm classification
```

Variables utiles :

- `CLASSIFIER_MODEL_ID` : modèle interrogé (`mistral` par défaut, mettez `phi3-mini` si vous activez le profil light).
- `CLASSIFIER_API_BASE` / `CLASSIFIER_API_KEY` : endpoint OpenAI-like à utiliser (par défaut `http://vllm:8000/v1`).
- `CLASSIFIER_MAX_DOC_CHARS` : nombre de caractères analysés par document (tronqués automatiquement).
- `CLASSIFIER_ALLOW_FREE_LABELS=true` : autorise le LLM à inventer un label libre (`raw_label`). Le champ `document_label`
  est prévu pour une normalisation manuelle dans votre UI (initialement identique au label brut).
- Le pipeline infère automatiquement un `doc_hint` (dqe, courriel, planning, mémoire…) à partir du nom/chemin du fichier
  et l'injecte dans le prompt afin d'améliorer la classification. Résultat : `raw_label` conserve la suggestion brute,
  `document_label` contient la version normalisée (mapped via le `doc_hint`).

⚠️ Par défaut, le classifieur doit choisir son label parmi la liste embarquée (`document_marche`, `dqe_bordereau`,
`memoire_technique`, `courriel_consultation`, `etude_plan`). Fournissez un fichier JSON personnalisé via `--labels-path`
si besoin. En mode libre (`CLASSIFIER_ALLOW_FREE_LABELS=true`), il peut suggérer un label inédit (stocké dans `raw_label`)
que vous pourrez normaliser plus tard dans votre UI (`document_label`). Les jobs `insights` et `inventory` enrichissent
MariaDB avec les montants issus des DQE (lignes `TOTAL`) et l'inventaire complet des documents par projet : la Gateway
peut ainsi répondre directement aux questions « Quel est le montant total ? » et « Quels documents as-tu pour ce projet ? ».
Les références sont renvoyées sous la forme de liens cliquables (`http://localhost:8081/files/view?...`) permettant
d’ouvrir le document à partir de l’UI.
   Rendez-vous sur http://localhost:8001 pour déposer vos documents. Une case à cocher permet de déclencher automatiquement ingestion + indexation.

Le guide [docs/ingestion.md](docs/ingestion.md) explique aussi comment relancer une indexation complète, supprimer certains documents dans Qdrant, ou diagnostiquer via l’API (`/collections`, `points/delete`, etc.).

## Documentation complémentaire

- [docs/architecture.md](docs/architecture.md) : diagrammes et composants.
- [docs/securite.md](docs/securite.md) : intégration Keycloak / OpenID Connect.
- [docs/tests.md](docs/tests.md) : stratégie de validation.
- [docs/ingestion.md](docs/ingestion.md) : guide exhaustif pour l'ajout / retrait de données et les appels API utiles.
- [docs/gateway.md](docs/gateway.md) : toutes les options de configuration de la Gateway (RAG, LLM, Keycloak, modèles multiples).
- [docs/prompt_gateway.md](docs/prompt_gateway.md) : description du prompt système imposé par la Gateway et comment le modifier.

Pour toute question ou contribution, ouvrez une issue ou un pull request.
