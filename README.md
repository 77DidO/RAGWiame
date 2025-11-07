# RAGWiame

Plateforme RAG open source orientée francophonie. Ce dépôt fournit un starter kit complet pour déployer une chaîne d'ingestion, d'indexation et de génération basée sur LlamaIndex, Qdrant et Mistral 7B via vLLM.

## Fonctionnalités

- Ingestion multi-formats (TXT, DOCX, PDF, Excel) et extraction MariaDB.
- Vectorisation avec Sentence-BERT multilingue et stockage dans Qdrant.
- Génération française via Mistral 7B accéléré par vLLM.
- Interface Open WebUI sécurisée par Keycloak (SSO OAuth2).
- Filtrage des réponses par service/rôle et journalisation prête pour l'audit.

## Prise en main rapide

### Linux / macOS (Bash)

```bash
python scripts/start.py
```

### Windows (PowerShell)

```powershell
python scripts/start.py
```

Utilisez `--skip-bootstrap` ou `--skip-deploy` pour exécuter sélectivement les étapes.

Consultez `docs/deploiement.md` pour la configuration avancée, `docs/demarrage_automatique.md` pour le détail du script et `docs/architecture.md` pour la vue d'ensemble.
