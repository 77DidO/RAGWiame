# Roadmap Technique RAGWiame

Dernière mise à jour : 14/12/2025

## ✅ Complété (Infrastructure & Git)
- [x] **Git Submodules** : Ajout de `.gitmodules` pour lier le fork `open-webui` (custom-dev).
- [x] **Documentation** : Instructions de clonage récursif ajoutées au README.
- [x] **Push Sync** : Synchronisation des commits UI (badges, bordures) sur GitHub.
- [x] **vLLM** : Stabilisation mémoire (Shm-size 10GB, Max-len 4096).
- [x] **Data Interpreter** : Restauration des pipelines perdus et nettoyage log paths.

## 🔴 Priorité Immédiate : Intelligence Documentaire (AO)
L'ingestion est fonctionnelle (métadonnées présentes), mais le RAG est "aveugle" lors de la recherche.
- [ ] **Développer `QueryRouter`** : Analyseur de requête (LLM léger) pour extraire les filtres (Commune, ID AO).
- [ ] **Connecter au Pipeline** : Injecter ces filtres dans la requête Qdrant (`pipeline.py`).
- [ ] **Tests** : Vérifier la distinction entre deux AO de communes différentes.

## 🧩 Moyen Terme : Qualité & Agents
### 1. Ingestion Avancée
- [ ] **Intégration Docling** : Remplacer les parseurs actuels pour une meilleure gestion des **tableaux complexes** (PDF/Excel) et de la mise en page.
- [ ] **Tableau de bord Ingestion** : UI pour suivre l'état des indexations (Succès/Erreur/Nb Chunks).

### 2. Data Interpreter (Analyste Excel)
- [ ] **Pipeline LangGraph** : Refondre la logique séquentielle actuelle (trop rigide) vers un graphe d'états (Planifier -> Coder -> Vérifier -> Corriger).
- [ ] **Garde-fous SQL** : Forcer la validation des requêtes générées avant exécution.

## 📋 Backlog : Maintenance
- [ ] **Monitoring** : Exposer les logs ingestion/API dans une interface admin.
- [ ] **Tests de Performance** : Benchmark vLLM (Tokens/sec) et latence RAG avec locust/pytest.
- [ ] **Cleanup** : Supprimer les anciens scripts de migration devenus inutiles.
