# Stratégie de tests

## Tests unitaires

- Connecteurs d'ingestion : couverture des cas de base pour TXT, Excel et MariaDB (mock).
- Pipeline RAG : validation des filtres et du format de réponse.

## Tests d'intégration

1. Ingestion de documents mixtes (TXT, PDF, DOCX, Excel) avec métadonnées variées.
2. Indexation dans Qdrant et vérification de la présence des métadonnées `service` et `role`.
3. Requête RAG via API avec token Keycloak simulé.

## Tests de performance

- Mesure du temps de réponse pour des prompts métiers (AO, RAO, RH) avec un contexte de 5 documents.
- Monitoring de la latence vLLM et du throughput Qdrant.

## Tests de sécurité

- Tentatives d'accès avec rôles insuffisants (doivent être filtrées).
- Vérification des journaux d'audit.
