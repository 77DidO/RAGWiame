# Guide ingestion & indexation

Ce document explique comment alimenter la base documentaire de RAGWiame, vérifier que les embeddings sont bien produits et maintenir la collection Qdrant `rag_documents`.

## 1. Vue d'ensemble

```
data/examples        <- fichiers prêts à être ingérés
data/uploads         <- dépôt temporaire utilisé par la mini UI FastAPI
docker compose run ingestion  -> lit data/examples, nettoie/normalise les textes
docker compose run indexation -> découpe les documents en chunks et pousse les embeddings dans Qdrant
Qdrant (rag_documents)        -> stocke les vecteurs + métadonnées service/role/source
```

Formats pris en charge : TXT, PDF, DOCX, PPTX, XLSX (via LlamaIndex) et tables MariaDB configurées dans `ingestion/config`. Chaque chunk reçoit automatiquement les champs `source`, `chunk_index`, `service`, `role`, `ingested_at`.

### Découpage et nettoyage automatiques

- Les PDF/DOCX sont extraits page par page puis re-segmentés par **paragraphes** : chaque paragraphe est nettoyé, les titres en majuscules deviennent des `section_title`, et les blocs du type `Question : ... / Réponse : ...` sont stockés individuellement avec les métadonnées `faq_question` / `faq_answer`.
- Pour les PDF, l'extraction passe par **pdfplumber** (licence MIT), ce qui évite les artefacts produits auparavant par `pypdf`.
- Les paragraphes sont regroupés jusqu'à atteindre `chunk_size` caractères (1024 par défaut) avec un chevauchement `chunk_overlap` de 80 caractères. Chaque chunk hérite du `source`, du `page`, d'un `chunk_index` et éventuellement de la `section_title`.

Vous pouvez ajuster ces valeurs dans `ingestion/config.py` ou dans un fichier JSON personnalisé (champ `chunk_size` / `chunk_overlap`).

## 2. Préparer les documents

1. Copier les fichiers à ingérer dans `data/examples/`.
2. (Optionnel) Organiser par sous-dossiers : ils seront conservés dans le champ `source`.
3. Supprimer les doublons ou versions obsolètes avant lancement pour éviter la multiplication des chunks.

## 3. Lancer ingestion/indexation en CLI

```powershell
# Depuis la racine du dépôt
docker compose -f infra/docker-compose.yml run --rm ingestion
docker compose -f infra/docker-compose.yml run --rm indexation
```

Conseils :

- Ajouter `--config-path /app/ingestion/config/custom.json` pour cibler un profil spécifique.
- Définir `QDRANT_URL` ou `HF_EMBEDDING_MODEL` à la volée :
  ```powershell
  $env:QDRANT_URL="http://localhost:6333"
  docker compose -f infra/docker-compose.yml run --rm indexation
  ```
- Les journaux restent disponibles via `docker compose -f infra/docker-compose.yml logs -f ingestion`.

À la fin, `data/examples/.processed` liste les fichiers déjà traités, ce qui évite de les réingérer par mégarde.

## 4. Mini UI d'upload (FastAPI)

Une interface très légère est fournie dans `upload_ui` pour tester rapidement l’ingestion sans ligne de commande.

```bash
pip install -r upload_ui/requirements.txt
uvicorn upload_ui.main:app --port 8001 --reload
```

Rendez-vous sur http://localhost:8001 :

1. Sélectionnez un ou plusieurs fichiers.
2. Cochez **« Lancer ingestion + indexation »** pour déclencher automatiquement les deux services via Docker Compose.
3. Le message de retour indique les codes de sortie des jobs (0 = succès). En cas d’échec, consultez les logs des conteneurs correspondants.

Les fichiers sont copiés dans `data/examples/`, ce qui permet d’alterner ensuite avec la méthode CLI classique.

## 5. API utiles pour vérifier les données

Tous les exemples utilisent PowerShell (`^` pour l’échappement). Sous Bash, remplacez par `\`.

- **Lister les collections**
  ```powershell
  curl.exe http://localhost:6333/collections
  ```
- **Créer la collection (si supprimée)**
  ```powershell
  curl.exe -X PUT http://localhost:6333/collections/rag_documents ^
    -H "Content-Type: application/json" ^
    -d "{\"vectors\":{\"size\":768,\"distance\":\"Cosine\"}}"
  ```
- **Compter les points indexés**
  ```powershell
  curl.exe http://localhost:6333/collections/rag_documents/points/count
  ```
- **Rechercher un point précis par ID**
  ```powershell
  curl.exe -X POST http://localhost:6333/collections/rag_documents/points/scroll ^
    -H "Content-Type: application/json" ^
    -d "{\"filter\":{\"must\":[{\"key\":\"source\",\"match\":{\"value\":\"guide.pdf\"}}]}}"
  ```

## 6. Suppression ciblée

Avant suppression, retirez le fichier concerné de `data/examples/` (sinon il sera réingéré à la prochaine exécution).

Exemple : supprimer tous les chunks issus de `charte_ssp.pdf` pour le service `support` et le rôle `conseiller` :

```powershell
curl.exe -X POST http://localhost:6333/collections/rag_documents/points/delete ^
  -H "Content-Type: application/json" ^
  -d "{
        \"filter\": {
          \"must\": [
            {\"key\": \"source\",  \"match\": {\"value\": \"charte_ssp.pdf\"}},
            {\"key\": \"service\", \"match\": {\"value\": \"support\"}},
            {\"key\": \"role\",    \"match\": {\"value\": \"conseiller\"}}
          ]
        }
      }"
```

Les filtres (`must`, `should`, `must_not`) suivent la syntaxe officielle Qdrant. Les noms de services/rôles doivent correspondre à ceux définis dans les métadonnées lors de l’ingestion (cf. configuration dans `ingestion/config`).

## 7. Réindexation complète

1. **Purger la collection**
   ```powershell
   curl.exe -X DELETE http://localhost:6333/collections/rag_documents
   ```
2. **Recréer la collection**
   ```powershell
   curl.exe -X PUT http://localhost:6333/collections/rag_documents ^
     -H "Content-Type: application/json" ^
     -d "{\"vectors\":{\"size\":768,\"distance\":\"Cosine\"}}"
   ```
3. **Relancer ingestion + indexation**
   ```powershell
   docker compose -f infra/docker-compose.yml run --rm ingestion
   docker compose -f infra/docker-compose.yml run --rm indexation
   ```

Cette procédure est recommandée lorsque vous changez de modèle d’embedding ou que vous souhaitez repartir d’un état propre.

## 8. Dépannage rapide

| Problème | Cause probable | Solution |
| --- | --- | --- |
| `Got unexpected extra argument (run)` dans ingestion | Commande `python -m ingestion.cli run` (obsolete) | Utiliser `docker compose run ingestion` ou `python -m ingestion.cli --help` |
| `Collection ... already exists` | La collection n’a pas été supprimée avant recréation | Ignorer le message ou supprimer avant PUT |
| `mariadb_config not found` lors du build | Dépendances système manquantes dans l’image `ingestion` | L’image Docker installe désormais `libmariadb-dev`; reconstruire avec `docker compose build ingestion` |
| Réponse `"Empty Response"` côté Gateway | Aucun document indexé ou filtres trop restrictifs | Vérifier `points/count`, relancer ingestion, ajuster `service/role` |
| vLLM redémarre en boucle | GPU insuffisant ou VRAM saturée | Réduire `max_model_len` (variable `VLLM_MAX_SEQ_LEN`) ou basculer en CPU |

Pour plus de détails, combinez ce guide avec `docs/deploiement.md` (paramétrage Docker) et `docs/architecture.md` (schéma global).
