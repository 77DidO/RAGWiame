# TODO Ingestion & Observabilité

## ✅ Tâches complétées (Session 25 novembre 2025)

### Infrastructure et personnalisations OpenWebUI
- [x] Restauration du bouton RAG et des personnalisations perdues après `git reset --hard`
- [x] Création de la branche `custom-dev` pour isoler les modifications OpenWebUI
- [x] Mise en place du workflow automatisé `.agent/workflows/update_openwebui.md`
- [x] Réorganisation des ports Docker (schéma cohérent 8080-8130)
- [x] Résolution du problème de base de données corrompue (migration Alembic)
- [x] Configuration du proxy Vite pour développement en temps réel
- [x] Configuration CORS pour autoriser le serveur de dev (port 5120)
- [x] Nettoyage du dépôt Git (suppression fichiers temporaires, mise à jour `.gitignore`)
- [x] Documentation complète dans `conversation_history.md`

### Scripts et outils
- [x] Création des scripts de réingestion (`reingest.py`, `reingest_simple.sh`)
- [x] Amélioration du connecteur Excel (formatage nombres, gestion colonnes non nommées)
- [x] Documentation des améliorations RAG dans `docs/rag_improvements.md`

## 🔴 Priorités immédiates

### 1. Debugging et tests RAG
- [x] **Résoudre le problème des valeurs `0 EUR`** dans les résultats RAG (alignement colonnes Excel)
- [x] **Relancer les tests de qualité RAG** après correction du connecteur
- [x] **Analyser les time-outs** sur certaines requêtes complexes (Timeouts augmentés à 300s)
- [x] **Valider le hybrid-search** (RRF, top-k, reranker) sur cas réels
- [x] **Corriger `tests/test_rag_performance.py`** pour cibler `http://localhost:8081/v1/chat/completions` via variable d'environnement `RAG_GATEWAY_URL` et pouvoir générer un rapport de performance fiable

### 2. Pousser les commits vers le dépôt distant
- [x] **Push de la branche `main`** avec tous les commits récents (Commits effectués localement)
- [ ] **Push de la branche `custom-dev`** du sous-module `open-webui`
- [ ] **Vérifier la synchronisation** entre local et distant

## 📋 Backlog : Interface Upload / Monitoring

- [ ] Ajouter un tableau d'historique listant chaque ingestion (fichier, horodatage, statut, nb de chunks, erreurs éventuelles).
- [ ] Afficher une console temps réel ou timeline des actions (upload, classification, extraction, indexation) avec les logs du pipeline.
- [ ] Fournir un résumé par document terminé (type détecté, principaux champs extraits, taille du JSON, liens vers Qdrant/MariaDB).
- [ ] Proposer un bouton « Logs bruts » pour télécharger/visualiser la trace complète de l'ingestion.
- [ ] Filtrer les jobs par statut (Succès / Erreur / En cours) pour retrouver rapidement un traitement.
- [ ] Implémenter un endpoint `/ingestion/status/<job_id>` et une barre de progression côté UI.
- [ ] Ajouter des hooks "post-ingestion" (ex. relancer automatiquement l'indexation ou recalculer des stats).

## 📋 Backlog : Pipeline LLM utilitaire

- [ ] Classifier chaque document via Mistral/Phi3 afin d'identifier son type (acte, facture, contrat, etc.) et consigner le score de confiance.
- [ ] Appliquer, selon le type, un template d'extraction dédié et produire un JSON structuré (vendeurs, acheteurs, montants, dates, clauses clés).
- [ ] Stocker ces JSON dans MariaDB (ou un dossier versionné) pour audit et réutilisation métier.
- [ ] Enrichir les chunks texte avec les métadonnées issues de l'analyse (doc_type, section_label, champs extraits) avant l'indexation.
- [ ] Ajouter un score lexical (BM25/keywords) calculé à l'ingestion pour compléter le reranker runtime.

## 📋 Backlog : Fiabilité & tooling

- [ ] Empêcher la ré-ingestion accidentelle via un suivi `.processed`/hash des fichiers.
- [ ] Structurer les logs (JSON) à chaque étape : lecture, split, classification, extraction, push Qdrant.
- [ ] Créer un CLI `ingestion status` qui remonte les derniers jobs et leurs statistiques.
- [ ] Prévoir un mode "dry-run" pour tester un document sans l'insérer (utile QA).
- [ ] Fournir un script de maintenance pour réinitialiser Qdrant proprement (delete collection, recreate, relancer ingestion+indexation).
- [ ] Ajouter un script de contrôle du nombre de points par document (page vs chunks) afin de détecter les anomalies.

## 📋 Backlog : Activation modèle léger

- [ ] Documenter le workflow "vllm-light" : démarrage ponctuel (`docker compose --profile light up -d vllm-light`), configuration `ENABLE_SMALL_MODEL`.
- [ ] Exposer dans l'UI une bascule permettant de lancer/arrêter ce service lorsqu'on veut classifier/extraire avec le modèle compact.

---

**Notes :**
- Les tâches marquées ✅ ont été complétées lors de la session du 25 novembre 2025
- Les priorités 🔴 doivent être traitées avant de continuer le développement de nouvelles fonctionnalités
- Le backlog 📋 contient les améliorations futures planifiées
 - [ ] Ajouter un mode "SQL forcé" pour le pipeline Excel (bloc SQL obligatoire, garde-fous bloc vide, preview plus longue pour guider le modèle).
- [ ] Ajouter un mode "SQL force" pour le pipeline Excel (bloc SQL obligatoire, garde-fous bloc vide, preview plus longue pour guider le modele).
- [ ] Finaliser integration du pipeline Data Interpreter IA (excel-extension) : dependances DuckDB/LLM, valves, DB_FILE/HISTORY_DB_FILE, test de chargement et execution.
