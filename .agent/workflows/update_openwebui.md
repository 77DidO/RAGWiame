# Workflow: Mettre à jour OpenWebUI tout en préservant les personnalisations RAG
---
description: Mettre à jour OpenWebUI tout en sauvegardant et réappliquant les personnalisations RAG
---
1. **Sauvegarde des fichiers personnalisés**
   ```bash
   mkdir -p .backup/open-webui
   cp src/lib/components/chat/MessageInput.svelte .backup/open-webui/MessageInput.svelte
   cp src/lib/components/chat/Messages/Citations.svelte .backup/open-webui/Citations.svelte
   ```
2. **Mise à jour du sous‑module**
   ```bash
   git fetch upstream
   git checkout main
   git reset --hard upstream/main
   ```
3. **Restauration des personnalisations**
   ```bash
   cp .backup/open-webui/MessageInput.svelte src/lib/components/chat/MessageInput.svelte
   cp .backup/open-webui/Citations.svelte src/lib/components/chat/Messages/Citations.svelte
   git add src/lib/components/chat/MessageInput.svelte src/lib/components/chat/Messages/Citations.svelte
   git commit -m "Re‑appliquer les personnalisations RAG après mise à jour"
   ```
4. **Re‑basage de la branche `custom-dev`**
   ```bash
   git checkout custom-dev
   git rebase main
   ```
5. **Reconstruction du conteneur** (si vous utilisez Docker)
   ```bash
   docker compose build && docker compose up -d
   ```
6. **Vérification**
   - Lancez l’application (`npm run dev` ou via Docker) et assurez‑vous que le bouton **RAG** apparaît et que les citations fonctionnent.
   - Vérifiez la persistance du flag `ragEnabled` dans le stockage local.
---
# Notes
- Ce workflow doit être exécuté chaque fois que vous souhaitez mettre à jour OpenWebUI.
- Vous pouvez ajouter d’autres fichiers personnalisés à la section **Sauvegarde** si nécessaire.
