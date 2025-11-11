# Prompt RAG côté Gateway

Le service `gateway` impose un **prompt système unique** à tous les appels `/rag/query` et `/v1/chat/completions`. Il sert à cadrer la réponse générée par le LLM (Mistral ou Phi‑3) après la récupération des chunks Qdrant.

## Prompt actuel

Implémenté dans `llm_pipeline/pipeline.py`, il contient seulement trois règles :

```
Tu es un assistant juridique. Réponds UNIQUEMENT en français et en deux phrases maximum.
Appuie-toi sur les extraits fournis, mais reformule-les.
Ignore les mentions internes de type «Question : …» ou «Réponse : …» présentes dans le contexte : elles ne sont que des exemples.
Si aucune information pertinente n'est disponible, réponds exactement :
"Je n'ai pas trouvé l'information dans les documents.".
```

Puis la Gateway ajoute automatiquement :

```
Contexte pertinent :
{context}

Question :
{question}
```

Le `{context}` correspond aux chunks remontés par LlamaIndex (tronqués à `RAG_MAX_CHUNK_CHARS`). `{question}` est la dernière question “user” reçue via l’API (Open WebUI, curl, etc.).

## Comment le modifier ?

1. Éditez `llm_pipeline/pipeline.py` (classe `RagPipeline`, attribut `self.qa_template`).  
2. Adaptez le texte à vos besoins (ton, longueur, mentions de citations).  
3. Rebuild et redéployez la Gateway :
   ```powershell
   docker compose -f infra/docker-compose.yml build gateway
   docker compose -f infra/docker-compose.yml up -d gateway
   ```

> ⚠️ Évitez de multiplier les contraintes côté Open WebUI **et** côté Gateway : un seul prompt système suffit. Si vous ajoutez d’autres instructions dans Open WebUI, elles s’empileront simplement avant/ après ce template serveur.

## Bonnes pratiques

- Garder les consignes courtes (2‑3 phrases) pour les modèles légers comme Phi‑3.  
- Mentionner explicitement la langue attendue et le comportement en absence d’information.  
- Ajuster `RAG_TOP_K` / `SMALL_MODEL_TOP_K` et `RAG_MAX_CHUNK_CHARS` pour contrôler la quantité de contexte envoyée au LLM.  
- Documenter tout changement dans ce fichier pour que l’équipe sache quel prompt est en production.
