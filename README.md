# RAGWiame

Plateforme RAG open source orientée francophonie. Ce dépôt fournit un starter kit complet pour déployer une chaîne d'ingestion, d'indexation et de génération basée sur LlamaIndex, Qdrant et Mistral 7B via vLLM.

## Fonctionnalités

- Ingestion multi-formats (TXT, DOCX, PDF, Excel) et extraction MariaDB.
- Vectorisation avec Sentence-BERT multilingue et stockage dans Qdrant.
- Génération française via Mistral 7B accéléré par vLLM.
- Interface Open WebUI sécurisée par Keycloak (SSO OAuth2).
- Filtrage des réponses par service/rôle et journalisation prête pour l'audit.

## Prise en main rapide

```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
python scripts/deploy.py
```

Consultez `docs/deploiement.md` pour la configuration avancée et `docs/architecture.md` pour la vue d'ensemble.
