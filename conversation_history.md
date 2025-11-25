# Historique de la conversation (2025‑11‑24 – 2025‑11‑25)

## Objectif initial
- Améliorer la qualité du RAG, notamment l’extraction des données Excel, le ré‑indexage, le réglage du hybrid‑search et le prompt LLM.

## Étapes majeures réalisées

### Session 1 (24-25 novembre) : Améliorations RAG et mise à jour OpenWebUI
1. **Améliorations du connecteur Excel** – gestion des colonnes non nommées, formatage des nombres avec séparateurs et suffixe `EUR`.
2. **Ré‑indexation complète** des fichiers Excel après les changements.
3. **Mise à jour du prompt** dans `llm_pipeline/pipeline.py` pour encourager les réponses partielles et le format monétaire.
4. **Ajustement du hybrid‑search** – top‑k augmenté, fusion RRF, logs de debug.
5. **Exécution des tests de qualité RAG** – 3/6 réussis, problèmes de valeurs `0 EUR` et time‑outs identifiés.
6. **Déploiement et vérification des services Docker** – gateway, vLLM, Qdrant, Elasticsearch fonctionnels.
7. **Mise à jour d’Open‑WebUI** :
   - Création d’un backup du fichier `Citations.svelte`.
   - Ajout du remote `upstream` et reset sur `upstream/main` (v0.6.38).
   - Reconstruction du conteneur `openwebui` (docker compose –‑build).
   - Restauration du fichier personnalisé.
   - Observation : le reset a écrasé toutes les autres personnalisations locales.
8. **Création d’un workflow `update_openwebui.md`** détaillant la procédure de sauvegarde, mise à jour via `upstream`, restauration et rebuild.
9. **Mise à jour du `task.md`** pour refléter la tâche de maintenance et le statut de l’update.

### Session 2 (25 novembre) : Restauration personnalisations RAG et réparation infrastructure

#### Restauration des personnalisations OpenWebUI
1. **Identification des personnalisations perdues** :
   - Bouton RAG dans `MessageInput.svelte`
   - Prop `useRag` dans `Citations.svelte`
   - Propagation de l'état `ragEnabled` dans plusieurs composants
2. **Création de la branche `custom-dev`** dans le sous-module `open-webui`
3. **Restauration du code** à partir du commit `532b8b524`
4. **Commit des personnalisations** : "Restore RAG button and Citations customizations"

#### Réparation de l'infrastructure Docker
5. **Problème identifié** : Qdrant et Elasticsearch ne démarraient pas (erreur ports occupés)
6. **Réorganisation des ports** :
   - Schéma cohérent : 8080 (webui), 8090 (gateway), 8100 (vllm), 8110 (vllm-light), 8120 (elasticsearch), 8130 (qdrant)
   - Mise à jour de `docker-compose.yml`
7. **Résolution du problème de base de données** :
   - Erreur 500 au login causée par incompatibilité DB (migration Alembic échouée)
   - Solution : création d'un nouveau volume DB propre
   - Renommage `openwebui_data_fix` → `openwebui_data`

#### Configuration de l'environnement de développement
8. **Configuration du proxy Vite** pour permettre le développement en temps réel
9. **Ajout du CORS** pour autoriser `localhost:5120` (serveur de dev)
10. **Reconstruction de l'image Docker OpenWebUI** avec les personnalisations

#### Nettoyage et commits
11. **Mise à jour du `.gitignore`** pour exclure fichiers temporaires (*.zip, test_results*, debug_*, .backup/)
12. **Commits effectués** :
    - `d37e8a0c1` (open-webui) : "fix: configuration du proxy vite pour le backend docker"
    - `018de8a` (main) : "chore: mise à jour des ports infra, correction volume db et mise à jour sous-module open-webui"
    - `96207a9` (main) : "fix: renommage du volume openwebui_data_fix vers openwebui_data"
    - `3693f7f` (main) : "feat: ajout scripts de réingestion, améliorations RAG et mise à jour gitignore"

## Problèmes rencontrés

### Session 1
- Le dépôt `open‑webui` était un fork (`77DidO/open‑webui`) en retard ; le reset a donc perdu les développements locaux.
- Aucun backup complet n’était présent, seulement `Citations.svelte`.
- Les tests RAG montraient des valeurs `0 EUR` (problème d’alignement de colonnes Excel).

### Session 2
- Personnalisations RAG perdues après `git reset --hard`
- Conflits de ports empêchant le démarrage de Qdrant/Elasticsearch
- Base de données SQLite corrompue/incompatible (erreur migration Alembic)
- Problèmes CORS entre serveur de dev (5120) et backend Docker (8080)

## Solutions mises en place

### Gestion des personnalisations OpenWebUI
- **Branche dédiée `custom-dev`** pour isoler les modifications
- **Workflow automatisé** `.agent/workflows/update_openwebui.md` pour sauvegarder/restaurer
- **Commits versionnés** de toutes les personnalisations

### Infrastructure
- **Schéma de ports cohérent** (incréments de 10)
- **Volume DB propre** après nettoyage de l'ancien corrompu
- **Configuration Vite** pour développement en temps réel
- **CORS configuré** pour autoriser les origines de développement

## Recommandations / Prochaines étapes
- **Sauvegarder systématiquement** tout le répertoire `open‑webui` avant chaque mise à jour (snapshot ou branche `custom-dev`).
- **Utiliser une branche dédiée** pour les personnalisations et rebaser sur `upstream/main` ou `upstream/dev`.
- **Poursuivre le debugging** du problème `0 EUR` dans le `ExcelConnector` (voir le script `debug_excel_value.py`).
- **Rerun les tests RAG** après correction du connecteur.
- **Documenter** les étapes de sauvegarde/restauration dans le workflow existant.
- **Utiliser la branche `custom-dev`** pour tous les développements OpenWebUI
- **Suivre le workflow `update_openwebui.md`** pour les futures mises à jour
- **Développer en mode dev** (`npm run dev` sur port 5120) pour itérations rapides
- **Reconstruire l'image Docker** uniquement pour validation finale
- **Pousser les commits** vers le dépôt distant

## État actuel du système
- ✅ OpenWebUI fonctionnel sur port 8080 avec bouton RAG
- ✅ Tous les services Docker opérationnels (ports 8080-8130)
- ✅ Environnement de dev configuré (Vite + proxy)
- ✅ Personnalisations versionnées et documentées
- ✅ Workflow de mise à jour en place
- ✅ Dépôt Git propre (aucun fichier non suivi)

*Ce fichier résume l’historique de nos échanges et les actions entreprises afin de garder une trace claire pour les développeurs.*
