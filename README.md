# RAGWiame

Plateforme RAG open source orientée francophonie. Ce dépôt fournit un kit complet pour déployer ingestion, indexation et génération basées sur LlamaIndex, Qdrant et Mistral 7B propulsé par vLLM.

## Panorama des services

- **vLLM (Mistral)** : sert le modèle `mistralai/Mistral-7B-Instruct-v0.3` via une API compatible OpenAI pour le mode RAG.
- **vLLM (Phi-3 mini)** : second service optionnel pour tester le RAG avec un modèle plus compact (`microsoft/Phi-3-mini-4k-instruct`, servi sous l’alias `phi3-mini`).
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
docker compose -f infra/docker-compose.yml ps
docker compose -f infra/docker-compose.yml logs gateway
```

Ports exposés :

- Gateway RAG : `http://localhost:8081`
- vLLM Mistral : `http://localhost:8000/v1`
- vLLM léger : `http://localhost:8002/v1`
- Qdrant : `http://localhost:6333`
- Open WebUI : `http://localhost:8080` (auth Keycloak)

## Utilisation des API

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

### Accès direct au modèle

Pour interroger Mistral sans retrieval, ciblez directement vLLM :

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mistralai/Mistral-7B-Instruct-v0.3","messages":[{"role":"user","content":"Bonjour"}]}'
```

### Modèle léger pour tester le RAG

Une instance vLLM supplémentaire expose un modèle plus petit (`phi3-mini` par défaut) sur `http://localhost:8002/v1`. La Gateway applique toujours le pipeline RAG (retrieval + réponse), mais utilise ce modèle à la place de Mistral :

```bash
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"phi3-mini","messages":[{"role":"user","content":"Réponds-moi brièvement"}]}'
```

Dans Open WebUI, créez un preset `phi3-mini` (URL identique à `mistral`) : seul le champ `Model` change. Selon la VRAM disponible, vous pouvez démarrer/arrêter `vllm-small` indépendamment (`docker compose up -d vllm-small`, `docker compose stop vllm-small`).

Variables utiles (`infra/docker-compose.yml`) :

- `VLLM_SMALL_MODEL_NAME` / `VLLM_SMALL_SERVED_MODEL_NAME` : modèle Hugging Face et alias exposé.
- `ENABLE_SMALL_MODEL` : permet de masquer l’option côté Gateway lorsqu’il n’est pas lancé.
- `SMALL_MODEL_ID` : valeur attendue dans le champ `model` (doit correspondre à `--served-model-name`).

> ⚠️ Attention : lancer simultanément Mistral 7B et Phi-3 mini consomme la somme de leurs VRAM. Si votre carte ne le permet pas, désactivez `vllm-small` (profils Docker ou `ENABLE_SMALL_MODEL=false`) et ne relancez que lorsque vous souhaitez tester le modèle léger.

## Ingestion et indexation

Deux approches complémentaires sont détaillées dans [docs/ingestion.md](docs/ingestion.md) :

1. **Scripts CLI**
   ```powershell
   # Copier les fichiers dans data/examples/ avant de lancer les jobs
   docker compose -f infra/docker-compose.yml run --rm ingestion
   docker compose -f infra/docker-compose.yml run --rm indexation
   ```
2. **Mini UI FastAPI**
   ```bash
   pip install -r upload_ui/requirements.txt
   uvicorn upload_ui.main:app --port 8001 --reload
   ```
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
