# Recherche RAG vs Non‑RAG : workflow détaillé

Ce document résume le fonctionnement des deux modes proposés par la Gateway :
1. **Mode RAG (par défaut)** : la réponse est étayée par les documents indexés (Qdrant + Elasticsearch).
2. **Mode “non‑RAG”** : la Gateway relaie la conversation directement au LLM sans effectuer de retrieval.

---

## 1. Entrée utilisateur

1. L’utilisateur (Open WebUI ou client OpenAI) envoie une requête sur `http://gateway:8081/v1/chat/completions`.
2. Le message contient :
   - `model` (`"mistral"`, `"phi3-mini"`, etc.)
   - les messages (`system`, `user`, `assistant`)
   - l’indicateur `use_rag` (Open WebUI ajoute `x-use-rag: true/false`).
3. La Gateway vérifie l’authentification (JWT Keycloak) puis redirige vers le pipeline correspondant.

---

## 2. Pipeline RAG (use_rag = true)

### 2.1 Préparation

1. **Historique** : la Gateway peut condenser l’historique ou reformuler la question (option “rewrite” selon configuration).
2. **Classification** (`llm_pipeline/query_classification.py`) :
   - `question_chiffree`, `fiche_identite`, `autre`.
   - Cette classification influence le prompt final et la priorisation des chunks.

### 2.2 Recherche hybride

1. **Dense (Qdrant)** :
   - `hybrid_query` appelle `VectorStoreIndex` (LlamaIndex) pour obtenir `similarity_top_k` nodes.
   - Les filtres (`ao_id`, `service/role`) peuvent être appliqués (venant de l’utilisateur ou du token).
2. **Lexicale (Elasticsearch)** :
   - `bm25_search` interroge l’index `rag_documents`.
   - Les résultats BM25 sont fusionnés avec les nœuds dense via `HYBRID_FUSION` (RRF ou pondération).
3. **Reranking** :
   - `_cross_encoder_rerank` (CrossEncoder) réordonne les meilleurs passages.
   - `_prioritize_numeric_nodes` injecte en tête les chunks contenant des chiffres lorsqu’il s’agit d’une question chiffrée (`effectif`, `CA`).
4. **Extraction du texte** :
   - `context_formatting.format_context` assemble plusieurs extraits par source (limités par `max_chunks_per_source`), retire les balises, génère les citations `[1]`, `[2]`.

### 2.3 Génération de la réponse

1. **Choix du prompt** (`llm_pipeline/prompts.py`) :
   - `get_default_prompt`, `get_fiche_prompt`, `get_chiffres_prompt`, etc.
   - Les prompts RAG contiennent des instructions “zero hallucination”.
2. **Appel LLM** :
   - La Gateway appelle vLLM (`mistral-7B` ou `phi3-mini` selon `model`).
   - Le LLM reçoit le prompt + les extraits formatés.
3. **Post-traitement** :
   - Les citations sont renvoyées (sources Qdrant).
   - Les chunks utilisés sont renvoyés dans le champ `chunks` (optionnel).
4. **Retour utilisateur** :
   - Open WebUI affiche la réponse, les sources, etc.

---

## 3. Pipeline non-RAG (use_rag = false)

### 3.1 Déclenchement

1. L’utilisateur choisit un preset “Mistral direct” ou désactive `use_rag` via l’UI.
2. La Gateway contourne totalement la chaîne de recherche.

### 3.2 Traitement

1. **Aucun retrieval** : pas d’appel Qdrant/Elasticsearch, pas de classification spécifique.
2. **Prompt minimal** :
   - Le prompt est celui défini par le preset (ex. “Tu es un assistant généraliste…”).
   - Pas de contexte ni de citations.
3. **Appel LLM** :
   - Directement vers vLLM (`mistral`, `phi3`…).
4. **Réponse** :
   - Retour brut du LLM (sans sources, sans contrôles).

### 3.3 Cas d’usage

- Questions génériques ne nécessitant pas les documents (ex. “Explique la méthode Kanban”).
- Tests rapides de la génération (fiabilité moindre car pas ancrée dans le corpus).

---

## 4. Comparaison synthétique

| Étape | Mode RAG | Mode non-RAG |
|-------|----------|--------------|
| Classification question | Oui | Non (facultatif) |
| Recherche Qdrant | Oui | Non |
| Recherche BM25 | Oui | Non |
| Reranking / prioritisation | Oui | Non |
| Prompt spécialisé métier | Oui | Prompt générique |
| Citations / sources | Oui | Non |
| Latence | Plus élevée (lecture + retrieval) | Réponse immédiate |
| Usage recommandé | Questions sur les documents (AO, chiffres, effectifs) | Questions générales, tests rapides |

---

## 5. Logs / monitoring

- **RAG** :
  - Logs Gateway : `DEBUG: hybrid_query …` , `Retrieval took …`.
  - Logs Qdrant/Elasticsearch : rafales d’inserts lors de l’indexation ; requêtes `POST /collections/.../points/search` lors des questions.
  - Réponses mentionnent les sources `[1]`.
- **Non-RAG** :
  - Gateway logue simplement l’appel LLM (`Calling non-RAG pipeline`).
  - Aucun accès aux sources, pas de citations.

---

## 6. Modèles de requêtes utilisateur (standard)

- **Projet** : `code affaire + type document + date/lot` (ex. `A2458 DOE assainissement 2024`).
- **Client** : `client + type + lieu` (ex. `SNCF plan VRD Lille`).
- **Problème** : `symptôme + équipement + marque` (ex. `fissure enrobé BB 0/10`).
- **Référence** : `réf + fournisseur + norme` (ex. `NF P 98-331 GNT`).
- **Administratif** : `type + n° + mois` (ex. `facture 2025-11 situation 3`).

Objectif : moins de requêtes floues, plus de précision dès le premier message.

En résumé, le mode RAG fournit des réponses fiables mais nécessite l’indexation complète et introduit une latence (lecture + hybrid search). Le mode non-RAG sert de fallback “chat généraliste” sans garantie documentaire. Le choix se fait via `use_rag` et peut être exposé dans Open WebUI (preset RAG vs preset direct).

---

## 7. Booster le classement (ranking)

Si l’outil le permet, appliquer les pondérations suivantes dans le reranking/fusion :

- **Booster Titre + Tags** : x3.
- **Booster métadonnées clés** (code affaire, client, commune/site, type, lot) : x2.
- **Pénaliser** les documents sans tags ni métadonnées.
- **Optionnel** : booster les documents récents ou marqués “référence” (normes, process).
