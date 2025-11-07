# Architecture de référence

## Vue d'ensemble

La plateforme RAGWiame repose sur une architecture modulaire entièrement open source.

- **Ingestion** : connecteurs TXT, DOCX, PDF, Excel et MariaDB pour produire des chunks normalisés.
- **Indexation** : LlamaIndex orchestre l'encodage via un modèle Sentence-BERT et stocke les vecteurs dans Qdrant.
- **Pipeline LLM** : vLLM sert Mistral 7B Instruct et expose une API compatible OpenAI pour la génération en français.
- **Front-end** : Open WebUI fournit l'interface utilisateur, authentifiée par Keycloak.
- **Sécurité** : Keycloak gère les rôles et services, appliqués dans les filtres Qdrant et auditables via l'API.

## Flux principal

1. Les documents sont chargés via la CLI d'ingestion ou une API. Les métadonnées (service, rôle, confidentialité) sont enrichies.
2. Les chunks sont envoyés au service d'indexation qui crée ou met à jour les collections Qdrant.
3. Lors d'une requête, le pipeline RAG récupère les chunks pertinents filtrés par droits, construit un prompt français et interroge Mistral 7B.
4. L'API renvoie la réponse accompagnée des citations et des métadonnées utiles pour l'audit.

## Composants

| Composant | Langage | Conteneur | Description |
|-----------|---------|-----------|-------------|
| ingestion | Python 3.11 | `ingestion` | Connecteurs fichiers et SI, chunking configurable |
| indexation | Python 3.11 | `indexation` | Interaction LlamaIndex/Qdrant |
| llm_pipeline | Python 3.11 | `gateway` & `vllm` | API FastAPI et serveur vLLM |
| openwebui | TypeScript | `openwebui` | Interface conversationnelle |
| keycloak | Java | `keycloak` | Gestion des identités et rôles |
| mariadb | SQL | `mariadb` | Métadonnées et données de référence |

## Données

- **Brutes** : stockées sur disque monté en lecture seule pour ingestion.
- **Vectorielles** : Qdrant avec réplication possible.
- **Métadonnées** : MariaDB, synchronisées avec Keycloak pour les droits.

## Observabilité

- Exporters Prometheus/Grafana (à compléter) pour les services.
- Journaux centralisés via EFK/ELK (points d'intégration prévus dans la compose).
