# Strategie de metadonnees pour les dossiers AO

Ce document analyse l'arborescence `data/examples/AO/...` et propose une normalisation des metadonnees a extraire automatiquement lors de l'ingestion. L'objectif est d'ameliorer la recherche, la tracabilite et la maintenance des appels d'offres (AOs) dans la plateforme RAG.

---

## 1. Constat sur les dossiers d'ingestion

- Les AOs sont ranges dans des repertoires nommes `AO/<ID> - <Commune> - <Objet>`.
- Chaque AO contient des sous-dossiers structures (`01-Document marche`, `05-Etude-Devis-SPIGAO`, `09-Offre remise`, etc.) et des sous-niveaux supplementaires (`OFFRE`, `CANDIDATURE`, `Memoire technique`, `Sauvegarde`).
- Les fichiers eux-memes indiquent souvent leur role (`BPU`, `DE`, `AE`, `Planning`, `WIAME VRD - Presentation`, etc.) ou leur statut (`Signature 1`, `preuve_de_depot`, `contract.json`, `spigao/...`).
- Aujourd'hui, seules les metadonnees minimales (`source`, `document_type`) sont propagees, ce qui limite les possibilites de filtre/boost dans la recherche et complique la purge d'un AO.

---

## 2. Metadonnees a extraire

### 2.1 Contexte AO (niveau dossier racine)

| Champ | Description | Exemple | Utilite |
|-------|-------------|---------|--------|
| `ao_id` | Identifiant unique detecte dans le nom du dossier (ex. ED257914) | `ED257914` | Filtrer les recherches/purger un AO |
| `ao_commune` | Nom de la commune extrait du dossier | `LES ORMES SUR VOULZIE` | Ciblage geographique, UX |
| `ao_objet` | Objet ou lot principal de l'AO | `AMGT PARKING` | Contexte metier |
| `ao_is_global_doc` | Booleen indiquant un document transverse (presentation Wiame, fiches generiques) | `true`/`false` | Eviter d'injecter par erreur un document non specifique |

### 2.2 Phase / section (niveau sous-dossier `01-`, `05-`, `09-`, etc.)

| Champ | Description | Exemple |
|-------|-------------|--------|
| `ao_phase_code` | Numero de phase (01, 05, 09...) | `09` |
| `ao_phase_label` | Libelle textuel (`Document marche`, `Offre remise`...) | `Offre remise` |
| `ao_section` | Sous-type (OFFRE, CANDIDATURE, Memoire technique, Sauvegarde...) | `CANDIDATURE` |

Ces champs permettent de cibler facilement "montre-moi les pieces de candidature de l'AO ED258025" ou de booster automatiquement les documents pertinents si l'utilisateur mentionne "offre" vs "candidature".

### 2.3 Type de document (nom de fichier)

- Introduire `ao_doc_code` base sur des patterns : `AE`, `BPU`, `DE`, `RC`, `CCAP`, `CCTP`, `Planning`, `Memoire`.
  -> Exemple : `ao_doc_code="BPU"` et `ao_doc_role="Bordereau des prix"`.
- Pour les exports Spigao (`DIE - ...`), ajouter `spigao_batch_id` (UUID) afin de relier les multiples formats (xls, pdf, xml, rapports).
- Les preuves de depot, signatures, mails `.msg` recoivent des flags (`submission_proof=true`, `email_source=true`).

### 2.4 Version et statut

- Detecter les suffixes `- Signature 1`, `Signature 2`, `Exp2603`, etc.
  -> Champs : `ao_signed=true`, `ao_signature_label="Signature 1"` / `signature_datetime` si encodee dans le nom (`2025-05-05 09:44:09`).
- Les dossiers `Sauvegarde` contiennent les confirmations officielles ; les tagger avec `ao_safeguard=true`.

### 2.5 Fichiers a exclure

Plusieurs fichiers presents dans les sous-dossiers AO ne doivent pas etre ingeres car ils sont redondants ou inexploitables :

- **Archives `.zip/.rar`** : elles regroupent presque toujours des documents deja extraits (DCE complets, fiches techniques, exports Spigao, preuves de depot). Ingestion = doublons.
- **Exports applicatifs** (`.cnf`, `.dat`, `.ori`, `.xnf`, `.rpt`, `.xml` de signature, `.mpp`) : formats propres a Spigao ou MS Project, sans texte utile pour le RAG.
- **Copies obsoletes** (`*.old`, `*.bak`) : anciennes versions laissees par les outils bureautiques.
- **Captures/PNGs isoles** : sans OCR adapte, ils n'apportent rien (ex. captures d'ecran dans `sauvegarde`).
- **Emails `.msg`** : tant qu'aucun connecteur Outlook n'est implante, ils risquent d'introduire des chunks bruites.

Preconisation : gerer une liste `excluded_extensions` dans la configuration et la verifier dans chaque connecteur, ou deplacer ces fichiers vers un sous-dossier `raw` non parcouru par l'ingestion.

---

## 3. Preconisations techniques

1. **Utilitaire commun**
   - Creer `ingestion/metadata_utils.py` avec des fonctions `extract_ao_context(path: Path)` et `infer_document_role(path: Path)`.
   - Ces fonctions sont appelees dans chaque connecteur (DOCX, PDF, Excel...) avant l'emission du `DocumentChunk`.

2. **Propagation automatique**
   - Utiliser la structure des dossiers (`path.parts`) pour associer les champs (racine AO, phase, section).
   - Pour les documents globaux (ex. `data/examples/WIAME-VRD.txt`), definir `ao_is_global_doc=true` sans `ao_id`.

3. **Normalisation / validation**
   - Stocker la liste des codes autorises (`BPU`, `DE`, etc.) dans un dictionnaire.
   - Si un fichier ne matche aucun pattern, laisser `ao_doc_code` vide pour eviter les erreurs.

4. **Exposition cote recherche**
   - Utiliser ces metadonnees dans Qdrant/Elasticsearch pour filtrer automatiquement lorsqu'un utilisateur selectionne un AO dans l'interface ou mentionne un identifiant.
   - Ajouter des controles dans le gateway ou l'API RAG pour permettre `{"filters":{"ao_id":"ED258025"}}`.

5. **Documentation & procedures**
   - Mettre a jour `docs/workflows_traitement.md` et `docs/architecture.md` pour expliquer la propagation de ces metadonnees.
   - Documenter la purge : "Supprimer toutes les donnees d'un AO = supprimer les points Qdrant ou `ao_id=...` puis relancer ingestion".
   - Ajouter un paragraphe "fichiers exclus" listant les extensions ignorees par defaut.

---

## 4. Gains attendus

- **Recherche plus precise** : possibilite de limiter les reponses a un AO ou a une phase donnee, de booster les documents critiques (BPU, DE, etc.).
- **Tracabilite** : chaque reponse montre l'AO, la phase et la section d'origine.
- **Maintenance** : purge ciblee (par AO, par phase), reperage immediat des documents globaux vs specifiques.
- **Preparation a l'echelle** : cette structure encourage une ingestion massive de dossiers sans retoucher le pipeline pour chaque cas.

---

## 5. Plan d'implementation suggere

1. **Semaine 1** : Ajouter l'utilitaire d'extraction + champs `ao_id/commune/objet/phase` dans tous les connecteurs.
2. **Semaine 2** : Etendre aux typologies `ao_doc_code` et aux flags (signatures, preuves de depot). Adapter l'API RAG pour filtrer par `ao_id`.
3. **Semaine 3** : Mise a jour documentation + tests sur plusieurs AOs (Ormes, Saint Brice, Grande Paroisse). Mesurer l'impact sur les reponses (questions ciblees par AO, recherches de prix, etc.).
4. **Etape optionnelle** : lier l'interface Open WebUI pour qu'un utilisateur puisse selectionner un AO ou une phase avant de poser sa question (utilise directement ces metadonnees).
5. **En parallele** : deployer le filtre d'extensions exclues pour empecher l'ingestion accidentelle des archives, exports Spigao et copies `.old/.bak`.

---

En resume, exploiter systematiquement la structure des dossiers AO permet de doter nos chunks d'un contexte riche (ID, commune, phase, role du document, statut). Cette granularite renforce autant la pertinence des reponses que la capacite a administrer la base documentaire. Il suffit d'ajouter cette logique dans les connecteurs existants et d'en tirer parti cote recherche pour obtenir un gain immediat en qualite.
