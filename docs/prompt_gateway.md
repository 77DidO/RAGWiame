# Prompt RAG côté Gateway

Le service `gateway` impose un **prompt système unique** à tous les appels `/rag/query` et `/v1/chat/completions`. Il sert à cadrer la réponse générée par le LLM (Mistral ou Phi‑3) après la récupération des chunks Qdrant.

## Prompts Dynamiques (Mistral & Phi-3)

Le système sélectionne désormais automatiquement le format de prompt adapté au modèle utilisé :

### 1. Mistral (Instruct)
Utilise les balises `[INST] ... [/INST]` pour garantir le respect des instructions.

```
[INST] Tu es un assistant qui répond en français à partir du contexte fourni.
...
Contexte : {context}
Question : {question} [/INST]
```

### 2. Phi-3 (Chat)
Utilise les balises `<|user|> ... <|end|><|assistant|>` spécifiques à ce modèle.

```
<|user|>
Tu es un assistant qui répond en français...
...
Contexte : {context}
Question : {question} <|end|>
<|assistant|>
```

## Comment le modifier ?

1. Éditez `llm_pipeline/prompts.py` pour modifier le texte des templates (`get_default_prompt`, `get_phi3_default_prompt`, etc.).
2. La sélection logique se fait dans `llm_pipeline/pipeline.py` (classe `RagPipeline`).
3. **Rebuild obligatoire** pour appliquer les changements :
   ```powershell
   docker compose -f infra/docker-compose.yml build gateway
   docker compose -f infra/docker-compose.yml up -d gateway
   ```

> ⚠️ **Attention** : Ne supprimez pas les balises `[INST]` ou `<|user|>` car elles sont essentielles pour éviter que le modèle ne génère des conversations imaginaires ("hallucinations de complétion").
