# Workflow complet d’ingestion/indexation

Ce document résume toutes les étapes effectuées lorsqu’on lance les commandes standards :

```powershell
docker compose --profile tools run --rm ingestion
docker compose --profile tools run --rm indexation
# Optionnel : ajout de --purge pour repartir d’une base propre
```

## 1. Dépôt des documents

1. L’utilisateur place les fichiers dans `data/examples/` (PDF, DOCX, XLSX, TXT, dossiers AO…).
2. La structure des dossiers AO (`AO/<ID - Commune - Objet>/...`) est conservée dans les métadonnées (`ao_id`, `ao_phase_code`, etc.).
3. Les fichiers exclus (`.zip`, `.rar`, `.cnf`, `.dat`, `.old`, `.msg`, dossiers `sauvegarde`, etc.) sont ignorés par les connecteurs en amont grâce à `metadata_utils.should_exclude_path`.

## 2. Job `ingestion`

Commande : `docker compose --profile tools run --rm ingestion`.

Étapes internes :

1. **Découverte des fichiers** via les connecteurs :
   - `TextConnector` (TXT), `DocxConnector`, `PDFConnector`, `ExcelConnector`, `MariadbConnector` (optionnel).
   - Chaque connecteur applique `should_exclude_path` et ajoute les métadonnées AO via `extract_ao_metadata`.
2. **Lecture / normalisation** :
   - **DOCX** : `python-docx` lit paragraphes + tableaux ; `_summarize_table` synthétise CA/effectifs.
   - **PDF** : `pdfplumber` extrait le texte page par page avant re-segmentation.
   - **Excel** : `pandas` (`openpyxl` pour `.xlsx`, `xlrd` pour `.xls`) charge les feuilles. Détection de l’en-tête, nettoyage des lignes/colonnes vides, conversion en DataFrame propre.
3. **Chunking** (dans `IngestionPipeline._chunk_document`) :
   - Nettoyage (`TextProcessor.clean_text`, suppression des artefacts).
   - Détection des FAQ, titres, sections (`StructureDetector.detect_faq`, `detect_section_label`).
   - Enrichissement des métadonnées (`MetadataEnricher.doc_hint`, `parent_id`).
   - Regroupement des paragraphes jusqu’à `chunk_size` et découpage avec chevauchement (`chunk_overlap`).
4. **Production des `DocumentChunk`** : chaque chunk contient `text`, `source`, `chunk_index`, `document_type`, plus les champs AO (`ao_id`, `ao_phase`, `ao_doc_code`, etc.) et tout attribut spécifique (FAQ, section, total, etc.).
5. Les chunks sont conservés en mémoire (et peuvent être inspectés via les logs `DEBUG: ExcelConnector.load path=...`).

## 3. Job `indexation`

Commande : `docker compose --profile tools run --rm indexation` (avec `--purge` pour supprimer collection + index avant réinjection).

Étapes internes (`indexation/qdrant_indexer.py`) :

1. **Option purge** :
   - `DELETE` + `recreate_collection` sur Qdrant (`rag_documents`), reconfiguré avec un vecteur `text-dense`.
   - Suppression de l’index Elasticsearch (`delete_index`).
2. **Construction de la pipeline** (recharge les mêmes fichiers via `IngestionPipeline` si l’on lance `indexation` seul, ou réutilise les chunks produits par `ingestion` lorsque les deux jobs sont chaînés).
3. **Vectorisation** :
   - Chaque chunk est transformé en embedding via `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
4. **Écriture dans Qdrant** :
   - Requêtes `PUT /collections/rag_documents/points?wait=true`.
   - Le payload contient `text-dense` + toutes les métadonnées : `source`, `doc_hint`, `ao_id`, `section_label`, etc.
5. **Indexation BM25** :
   - `llm_pipeline.elastic_client.index_document` pousse en parallèle le texte brut dans Elasticsearch (index `rag_documents`) pour la recherche lexicale.
6. **Logs** :
   - Dans Qdrant (`actix_web::middleware::logger`), on voit des salves de `PUT` : elles apparaissent une fois que le traitement d’un fichier (lecture + chunking) est terminé.
   - L’absence de logs pendant plusieurs minutes correspond aux étapes de lecture/normalisation/chunking des gros documents (Excel Spigao, PDF volumineux).

## 4. Vérifications

1. **Qdrant** :
   ```powershell
   curl http://localhost:8130/collections/rag_documents | ConvertFrom-Json
   ```
   Les champs `points_count` et `indexed_vectors_count` augmentent lorsque l’indexation est terminée.
2. **Elasticsearch** :
   ```powershell
   curl http://localhost:8120/rag_documents/_count
   ```
3. **Filtres AO** : on peut interroger `rag_documents` avec `{"filter":{"must":[{"key":"ao_id","match":{"value":"ED258025"}}]}}` pour vérifier que les métadonnées sont bien présentes.

## 5. Lien avec la recherche RAG

Lorsqu’une requête est envoyée au Gateway (`/rag/query` ou `/v1/chat/completions` avec `use_rag=true`) :

1. **Classification** (`query_classification.py`) détecte les questions chiffrées (`effectif`, `CA`, etc.).
2. **Recherche hybride** (`llm_pipeline/retrieval.py`) :
   - Dense : Qdrant (`similarity_top_k`).
   - Lexicale : Elasticsearch via BM25 (`bm25_search`).
   - Priorisation des chunks chiffrés (`_prioritize_numeric_nodes`).
3. **Formatage** : `context_formatting.format_context` assemble les extraits, `citation_key` numérote les sources.
4. **Génération** : prompts spécialisés (`get_chiffres_prompt`, etc.) sont envoyés à vLLM.

Ainsi, la latence observée dans les logs (bouffées de `PUT`) correspond aux phases lourdes de la pipeline (lecture pandas, segmentation DOCX/PDF, enrichissement). Une fois ces étapes terminées, la recherche RAG exploite les données via Qdrant/Elasticsearch avec toutes les métadonnées AO.

---

## 6. Métadonnées obligatoires (turbo qualité)

Pour chaque document important, s’assurer que les champs suivants sont renseignés/normalisés avant le chunking :

- **Code affaire** (identifiant projet/AO).
- **Client** (maître d’ouvrage, MOE, donneur d’ordre).
- **Commune / site** (localisation principale).
- **Type** (plan / DOE / DICT / devis / facture / CR / photo).
- **Lot / discipline** (VRD, assainissement, CFO/CFA, structure, etc.).
- **Date + version** (AAAA-MM-JJ + suffixe V1/V2 ou horodatage de signature).

Objectif : activer des filtres/boosts fiables et guider l’utilisateur vers des requêtes précises (moins de « recherche floue »).

### 6.1 Sources d’extraction/pré-remplissage

- **Structure AO** : dossier `AO/<ID - Commune - Objet>/...` ⇒ `code_affaire`, `commune`, `lot/objet`.
- **Nom de fichier** : patterns `2025-11_facture_V2.pdf`, `DOE_ED258025_V1.docx`, `DICT_Lille_TRAM.pdf` ⇒ `date`, `type`, `version`.
- **Props document** : DOCX (core props), PDF (metadata si présentes), XLSX (feuille “INFO”/premières lignes).
- **Tags UI / saisie opérateur** : champs fournis lors de l’upload (si UI supportée) pour forcer/écraser.

### 6.2 Normalisation minimale

- Dates au format `AAAA-MM-JJ` (ou `AAAA-MM` si jour inconnu) + suffixe `V1`, `V2` quand applicable.
- Type dans une liste contrôlée : `plan`, `DOE`, `DICT`, `devis`, `facture`, `CR`, `photo` (sinon `type=autre`).
- Lot/disciplines dans une liste courte (VRD, assainissement, CFO, CFA, structure, voirie...).
- Commune/site : nettoyer majuscules, accents, trim.

### 6.3 Validation (bloquante)

- Refuser l’ingestion d’un fichier « important » si `code_affaire` ou `type` manquent.
- Logger en WARN les champs manquants non bloquants (ex. `version`) avec le chemin du fichier.
- En cas d’incertitude, marquer `metadata_confidence=low` et laisser passer avec un flag.

### 6.4 Propagation vers les index

- Qdrant : champs stockés dans `payload` (`code_affaire`, `client`, `commune`, `type`, `lot`, `date`, `version`).
- Elasticsearch : mêmes champs dans le document BM25 pour filtres/boost.
- Reranker : ces métadonnées servent aux boosts/pénalités (type/lot/tag vs absences).
