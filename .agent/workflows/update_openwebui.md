# Workflow: Mettre à jour OpenWebUI (Méthode Git Rebase)
---
description: Mettre à jour OpenWebUI en préservant les modifications via Git Rebase
---

Cette méthode est plus propre et robuste que la copie manuelle de fichiers. Elle ré-applique vos commits personnalisés au-dessus de la dernière version officielle.

1.  **Préparation**
    Assurez-vous d'être dans le dossier `open-webui` et que votre dépôt est propre.
    ```bash
    cd open-webui
    git status
    ```

2.  **Récupération des mises à jour officielles**
    ```bash
    git fetch upstream
    ```

3.  **Mise à jour de la branche locale (Rebase)**
    On se place sur votre branche `custom-dev` et on la "rebase" sur `upstream/main`.
    ```bash
    git checkout custom-dev
    git rebase upstream/main
    ```

    > [!IMPORTANT]
    > **Gestion des conflits** : Si git signale des conflits, vous devrez les résoudre manuellement pour chaque fichier, puis faire `git add <fichier>` et `git rebase --continue`.

4.  **Mise à jour du dépôt distant (Force Push)**
    Comme l'historique a changé, un push forcé est nécessaire sur votre fork.
    ```bash
    git push --force-with-lease origin custom-dev
    ```

5.  **Reconstruction de l'application**
    Revenez à la racine et relancez les conteneurs.
    ```bash
    cd ..
    docker compose down
    docker compose up -d --build
    ```

6.  **Vérification**
    - Vérifiez que l'application démarre correctement.
    - Vérifiez que vos fonctionnalités personnalisées (RAG, UI) sont toujours présentes.
