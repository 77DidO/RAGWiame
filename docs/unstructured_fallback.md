# Intégration d’Unstructured comme fallback d’ingestion

Ce document décrit de manière détaillée pourquoi et comment ajouter la librairie **Unstructured** (et son OCR embarqué) dans la chaîne d’ingestion afin d’améliorer la couverture documentaire lorsque nos connecteurs personnalisés n’arrivent pas à extraire un texte exploitable. Il synthétise l’état actuel, la proposition d’architecture, les impacts (techniques, opérationnels) et le plan d’action recommandé.

---

## 1. Contexte et limites actuelles

- **Connecteurs maison** (TXT, DOCX, PDF, Excel, sources SQL) : parfaitement adaptés aux documents structurés et nous permettent d’enrichir les métadonnées (tags Wiame, sections, tables → texte naturel).  
- **Problème** : les PDF scannés ou les formats moins couverts (PPTX, e‑mails, images intégrées) restent mal ingérés voire ignorés. La qualité globale des réponses souffre lorsqu’un document clé n’est pas indexé.  
- **Absence d’OCR natif** : malgré un nettoyage soigné, les documents purement visuels ne sont pas convertis en texte exploitable.  
- **Besoin métier** : pouvoir brancher rapidement un fallback pour couvrir ces cas sans réécrire tous les connecteurs.

Conclusion : il faut un mécanisme optionnel qui prenne le relais lorsque nos connecteurs ne produisent rien ou que le document n’est pas supporté.

---

## 2. Principe de la solution Unstructured

1. **Positionnement** : Unstructured n’écrase pas nos connecteurs existants. Il intervient en **dernier recours** sur les mêmes dossiers d’ingestion.  
2. **Fonctionnement** :
   - Utilise `unstructured.partition.auto.partition` pour détecter le format et, si besoin, applique l’OCR (via Tesseract) sur les pages scannées.
   - Retourne une liste d’`elements` (paragraphes, tables, listes, images) avec leurs métadonnées (type, page, coordonnées).
   - Le connecteur fallback assemble ces éléments en texte “lisible” + métadonnées minimales (`document_type=unstructured`, `element_type`, `page`…) pour les envoyer dans la pipeline LlamaIndex existante.
3. **Couverture** : PDF, DOCX, PPTX, EML, HTML, images (PNG/JPG). Les formats déjà bien gérés restent traités par les connecteurs maison ; Unstructured ne s’active qu’en cas de besoin.

---

## 3. Intégration technique envisagée

### 3.1 Configuration

- Ajouter à `IngestionConfig` une section `unstructured: ConnectorConfig`, désactivée par défaut.  
- Paramètres utiles (via `ConnectorConfig.extra`) :
  - `strategy`: `auto`, `hi_res` (OCR + layout) ou `fast`.
  - `ocr_languages`: (ex. `fra+eng`) pour améliorer la détection.  
  - `extensions`: liste de suffixes ciblés si l’on veut éviter des doublons.

### 3.2 Nouveau connecteur (`ingestion/connectors/unstructured.py`)

Responsabilités :
- Parcourir les chemins comme les autres connecteurs.
- Exclure les fichiers déjà pris en charge (ex : `.docx` si `DocxConnector` a réussi, pour éviter une double ingestion). Cette exclusion peut se faire via un registre des fichiers traités (hash ou simple drapeau en mémoire).
- Appeler `partition()` puis convertir les éléments en `DocumentChunk` :
  - assembler texte ligne par ligne en respectant l’ordre des pages ;
  - inclure les métadonnées utiles (`source`, `page_number`, `element_type`);
  - tagger `document_type="unstructured"`.
- Gérer finement les erreurs (timeout OCR, dépendances manquantes) pour qu’un échec n’arrête pas tout le pipeline.

### 3.3 Chaîne d’ingestion

- Dans `IngestionPipeline._build_connectors`, instancier ce connecteur uniquement si `config.unstructured.enabled` est vrai.  
- L’ordre recommandé : TXT → DOCX → PDF → Excel → (sources SQL) → **Unstructured**.  
- Chaque document produit par Unstructured est ensuite chunké via `_chunk_document` exactement comme les autres.

### 3.4 Docker & dépendances

- Image `infra-indexation` (et `infra-ingestion` si distincte) :  
  - `pip install "unstructured[pdf,docx,pptx]"` (éviter le méta-package `all-docs` si l’on veut limiter le poids) ;  
  - `apt-get install -y poppler-utils libmagic1 tesseract-ocr tesseract-ocr-fra` ;  
  - déplacer ces ajouts dans un bloc dédié pour pouvoir les désactiver si besoin.
- Taille de l’image : +600 à +800 MB, temps de build +1‑2 min.

---

## 4. Workflow opérationnel

1. **Activation** : via variable d’environnement `INDEXATION_UNSTRUCTURED_ENABLED=true` (mappée vers `config.unstructured.enabled`).  
2. **Ingestion** :
   - Les jobs `docker compose --profile tools run --rm ingestion ...` exécutent la pipeline habituelle ; les documents non pris en charge tombent alors automatiquement sur le fallback.  
   - Unstructured génère les chunks → pipeline LlamaIndex (chunking, enrichissement, Qdrant + Elasticsearch).  
3. **Recherche** : aucune modification côté RAG ; les chunks `document_type=unstructured` sont traités comme les autres.  
4. **Monitoring** :
   - Ajouter un compteur dans les logs pour suivre le nombre de documents/passages traités via Unstructured (`processed_with_unstructured=17`).  
   - Prévoir une alerte si la proportion dépasse un seuil (ex : >30 %) → indicateur qu’il faut peut-être écrire un connecteur dédié.

---

## 5. Plan de tests conseillé

| Étape | Description | Attendus |
|-------|-------------|---------|
| Smoke test | Ingestion de 1 PDF scanné + 1 PPTX via `temp_ingestion_config`. | Logs Unstructured présents, pas d’erreur. |
| Validation Qdrant | Interroger `/collections/rag_documents` (points + métadonnées). | `document_type=unstructured`, `source=...` visibles. |
| Qualité RAG | Rejouer 3 questions métier (CA Wiame, effectif, certifications) via `curl 8090/rag/query`. | Les réponses citent désormais les documents scannés si pertinents. |
| Performance | Chrono `docker compose run ingestion` avec et sans fallback. | Mesurer la dégradation et décider si on limite l’usage. |

---

## 6. Impacts & risques

- **Performances** : OCR hi-res rallonge le temps d’ingestion (×1.3 à ×2 selon le nombre de pages scannées). Les jobs doivent être lancés hors pic ou sur une machine plus puissante si nécessaire.  
- **Consommation GPU/CPU** : pas de GPU requis, mais la RAM doit être suffisante (>4 Go libres).  
- **Maintenance** : Unstructured évolue vite. Il faudra épingler la version (`unstructured==0.xx.y`) et ajouter des tests d’intégration.  
- **Qualité** : textualisation générique → il faudra peut-être enrichir les métadonnées (ex : inférer une section “Effectif”) après coup pour rester cohérent avec le reste du corpus.  
- **Sécurité/licence** : Unstructured est sous licence Apache 2.0. Pas d’obligation de publication mais attention si l’on colle des documents sensibles dans des services externes (ici tout reste on-premise).  
- **Fallback seulement** : ne pas oublier que nos connecteurs personnalisés restent la source de vérité pour les documents structurés (ils gèrent des cas métier spécifiques).

---

## 7. Plan d’action proposé

1. **Sprint 1 – Prototype (0.5 j)**
   - Ajouter la config + connecteur Unstructured minimal.
   - Installer les dépendances dans l’image Docker.
   - Tester sur un sous-ensemble via `temp_ingestion_config.json`.
2. **Sprint 2 – Durcissement (1 j)**
   - Gérer l’exclusion/détection des doublons, enrichir les métadonnées, instrumenter les logs.
   - Mettre à jour la documentation (`docs/architecture.md`, `docs/workflows_traitement.md`, README).  
3. **Sprint 3 – Validation métier (0.5 j)**
   - Rejouer les cas d’usage (CA, effectifs, etc.), comparer la pertinence des réponses.
   - Décider si Unstructured reste fallback ou devient le connecteur principal pour certains formats.
4. **Optionnel** : si les résultats sont probants, prévoir une automatisation (ex : activer Unstructured uniquement pour certains dossiers ou via un flag dans `temp_ingestion_config`).

---

## 8. Conclusion

L’ajout d’Unstructured en fallback permet de couvrir rapidement les formats difficiles, en particulier les PDF scannés qui contiennent les informations critiques recherchées (chiffres d’affaires, effectifs, organigrammes). L’effort reste raisonnable (2 jours environ) mais demande :

- une préparation des dépendances Docker,
- un suivi attentif des performances,
- et une phase de qualification métier pour s’assurer que les nouvelles données améliorent effectivement les réponses.

La solution proposée garde la maîtrise de nos connecteurs spécialisés tout en ouvrant la porte à l’intégration d’OCR et de formats additionnels, ce qui constitue la prochaine étape logique pour fiabiliser le RAG Wiame.

