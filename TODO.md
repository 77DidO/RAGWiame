# TODO Ingestion & Observabilité

## 1. Interface Upload / Monitoring
- [ ] Ajouter un tableau d’historique listant chaque ingestion (fichier, horodatage, statut, nb de chunks, erreurs éventuelles).
- [ ] Afficher une console temps réel ou timeline des actions (upload, classification, extraction, indexation) avec les logs du pipeline.
- [ ] Fournir un résumé par document terminé (type détecté, principaux champs extraits, taille du JSON, liens vers Qdrant/MariaDB).
- [ ] Proposer un bouton « Logs bruts » pour télécharger/visualiser la trace complète de l’ingestion.
- [ ] Filtrer les jobs par statut (Succès / Erreur / En cours) pour retrouver rapidement un traitement.
- [ ] Implémenter un endpoint `/ingestion/status/<job_id>` et une barre de progression côté UI.
- [ ] Ajouter des hooks “post-ingestion” (ex. relancer automatiquement l’indexation ou recalculer des stats).

## 2. Pipeline LLM utilitaire
- [ ] Classifier chaque document via Mistral/Phi3 afin d’identifier son type (acte, facture, contrat, etc.) et consigner le score de confiance.
- [ ] Appliquer, selon le type, un template d’extraction dédié et produire un JSON structuré (vendeurs, acheteurs, montants, dates, clauses clés).
- [ ] Stocker ces JSON dans MariaDB (ou un dossier versionné) pour audit et réutilisation métier.
- [ ] Enrichir les chunks texte avec les métadonnées issues de l’analyse (doc_type, section_label, champs extraits) avant l’indexation.
- [ ] Ajouter un score lexical (BM25/keywords) calculé à l’ingestion pour compléter le reranker runtime.

## 3. Fiabilité & tooling
- [ ] Empêcher la ré-ingestion accidentelle via un suivi `.processed`/hash des fichiers.
- [ ] Structurer les logs (JSON) à chaque étape : lecture, split, classification, extraction, push Qdrant.
- [ ] Créer un CLI `ingestion status` qui remonte les derniers jobs et leurs statistiques.
- [ ] Prévoir un mode “dry-run” pour tester un document sans l’insérer (utile QA).
- [ ] Fournir un script de maintenance pour réinitialiser Qdrant proprement (delete collection, recreate, relancer ingestion+indexation).
- [ ] Ajouter un script de contrôle du nombre de points par document (page vs chunks) afin de détecter les anomalies.

## 4. Activation modèle léger
- [ ] Documenter le workflow “vllm-light” : démarrage ponctuel (`docker compose --profile light up -d vllm-light`), configuration `ENABLE_SMALL_MODEL`.
- [ ] Exposer dans l’UI une bascule permettant de lancer/arrêter ce service lorsqu’on veut classifier/extraire avec le modèle compact.

> Ces actions doivent être planifiées avant la prochaine itération de dev afin de garantir une ingestion fiable, observable et adaptable aux nouveaux jeux de documents.
