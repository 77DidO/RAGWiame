# Stratégie de tests

## Tests unitaires

- Connecteurs d'ingestion : couverture des cas de base pour TXT, Excel et MariaDB (mock).
- Pipeline RAG : validation des filtres et du format de réponse.

## Tests d'intégration

1. Ingestion de documents mixtes (TXT, PDF, DOCX, Excel) avec métadonnées variées.
2. Indexation dans Qdrant et vérification de la présence des métadonnées `service` et `role`.
3. Requête RAG via API avec token Keycloak simulé.

## Tests de qualité RAG

### `tests/test_rag_quality.py`

- Tests de scénarios métier (questions vagues, montants DQE, enrobés, etc.) exécutés directement contre le gateway (`/v1/chat/completions`).
- Utilise `X-Use-RAG: true` pour forcer le passage par le pipeline RAG.
- Évalue :
  - si le modèle refuse correctement de répondre quand la question est trop vague ou hors contexte ;
  - si les réponses attendues contiennent des mots-clés et des sources.

Exécution ciblée :

```bash
python -m pytest tests/test_rag_quality.py -q
```

## Tests contextuels (LLM seul)

### `tests/test_rag_contextual.py`

- Tests unitaires de compréhension : on injecte un petit extrait de document (Excel, DOCX, texte) directement dans le message envoyé au gateway.
- Objectif : vérifier que, **à contexte égal**, le modèle retrouve bien les informations clés (prix, codes, résumés, localisation).
- Cela permet de distinguer :
  - les problèmes de retrieval / hybrid-search (Qdrant + Elastic) ;
  - les problèmes de génération ou de lecture du contexte par le LLM.

Exécution :

```bash
python -m pytest tests/test_rag_contextual.py -q
```

Un script complémentaire permet de sauvegarder les réponses brutes dans un fichier Markdown pour comparaison dans le temps :

```bash
python -m tests.generate_rag_contextual_report
```

Le rapport est écrit dans :

- `tests/rag_contextual_report.md`

## Tests de performance

### `tests/test_rag_performance.py`

- Script de perf/qualité end-to-end, exécuté contre le gateway (`/v1/chat/completions`).
- Mesure pour une liste de questions métier :
  - la latence moyenne/min/max ;
  - la présence de mots-clés attendus dans la réponse.
- Couvre des cas sur Excel (prix unitaires, DQE), DOCX (WIAME VRD), localisation, comparaisons, etc.
- Utilise `X-Use-RAG: true` pour tester le pipeline complet (retrieval hybride + LLM).

Exécution :

```bash
python tests/test_rag_performance.py
```

Le script génère un rapport détaillé :

- `tests/rag_performance_report.md`

Ce rapport liste chaque test, la latence observée, les mots-clés trouvés et, en cas d’échec, la réponse ou l’erreur retournée.

## Tests de sécurité

- Tentatives d'accès avec rôles insuffisants (doivent être filtrées).
- Vérification des journaux d'audit.
