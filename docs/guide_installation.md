# Guide d'Installation Complet - RAGWiame

Ce guide détaille la procédure pas à pas pour installer et lancer le projet RAGWiame sur une nouvelle machine (Windows ou Linux).

## 1. Prérequis

### Matériel Recommandé
*   **CPU** : Processeur moderne (AMD Ryzen 5/7/9 ou Intel i5/i7/i9).
*   **RAM** :
    *   **16 Go** minimum pour tourner avec le modèle léger (Phi-3).
    *   **32 Go** recommandés pour le modèle standard (Mistral 7B).
*   **GPU (Carte Graphique)** :
    *   NVIDIA RTX 3060 / 4060 ou supérieur recommandé (avec au moins 8 Go de VRAM, idéalement 12 Go+).
    *   *Note : Le projet peut tourner sur CPU uniquement, mais la génération de texte sera très lente.*
*   **Disque** : ~50 Go d'espace libre (pour les images Docker et les modèles IA).

### Logiciels
Avant de commencer, installez les outils suivants :

#### Windows
1.  **WSL2 (Windows Subsystem for Linux)** : Ouvrez PowerShell en administrateur et lancez `wsl --install`. Redémarrez si demandé.
2.  **Docker Desktop** : [Télécharger ici](https://www.docker.com/products/docker-desktop/). Assurez-vous dans les paramètres que l'intégration WSL2 est activée.
3.  **Git** : [Télécharger ici](https://git-scm.com/download/win). Lors de l'installation, cochez "Enable experimental support for pseudo consoles" (optionnel mais pratique).
4.  **Python 3.11+** : [Télécharger ici](https://www.python.org/downloads/windows/). **Important** : Cochez la case "Add Python to PATH" à l'installation.

#### Linux
1.  **Docker Engine & Compose** : Suivez la procédure officielle pour votre distribution.
2.  **Drivers NVIDIA** (si GPU) : Installez le `nvidia-container-toolkit`.
3.  **Python 3.11+** et **Git**.

---

## 2. Récupération du Code

C'est l'étape critique où beaucoup d'erreurs surviennent. Ce projet contient une interface personnalisée (Open WebUI) sous forme de **sous-module**.

**Ouvrez votre terminal (PowerShell ou Bash) et exécutez :**

```bash
# Clone récursif (INDISPENSABLE pour avoir l'interface)
git clone --recursive https://github.com/77DidO/RAGWiame.git

# Entrer dans le dossier
cd RAGWiame
```

> **Attention** : Si le dossier `open-webui` est vide après le clone, lancez cette commande de rattrapage :
> ```bash
> git submodule update --init --recursive
> ```

---

## 3. Configuration Initiale

Le projet utilise des fichiers `.env` pour la configuration. Des modèles sont fournis.

1.  Les fichiers d'exemple `.env.example` dans le dossier racine et dans `open-webui` sont utilisés par défaut ou copiés automatiquement par les scripts de démarrage.
2.  Si vous avez besoin de clés API spécifiques (bien que le projet soit conçu pour tourner en local), vous pourrez modifier le fichier `.env` généré après le premier lancement.


---


---

## 4. Construction et Démarrage

### Construction des images Docker

Avant de démarrer les services, Docker doit récupérer les images de base et **construire** celles qui sont spécifiques à votre installation.

**Services construits localement** (via le code source cloned) :
*   **Open WebUI** (`openwebui`) : Construit depuis le sous-module `open-webui` pour inclure vos modifications IHM.
*   **Gateway RAG** (`gateway`) : Notre API Python personnalisée (dans `llm_pipeline`).
*   **Outils d'ingestion** (`ingestion`, `indexation`) : Scripts de traitement de documents.

**Services téléchargés** (images officielles) :
*   `vllm`, `mariadb`, `qdrant`, `elasticsearch`, `pipelines`.

> **Note importante** : Les scripts de démarrage (`start-dev.ps1` etc.) font un `docker compose up -d`.
> *   Au **premier lancement**, cela construit automatiquement les images manquantes.
> *   Mais lors des lancements suivants, cela **réutilise les images existantes** sans les mettre à jour.
>
> C'est pourquoi l'étape ci-dessous (`build`) est recommandée pour être sûr d'avoir la dernière version du code, surtout après un `git pull`.

1.  Placez-vous dans le dossier `infra` :
    ```bash
    cd infra
    ```
2.  Lancez la construction selon le mode choisi (Standard ou Light) :

    **Mode Standard (Mistral 7B)**
    ```bash
    # Télécharge les bases et compile Open WebUI + Gateway
    docker compose --profile mistral build
    ```

    **Mode Light (Phi-3)**
    ```bash
    # Idem pour le profil light
    docker compose --profile light build
    ```

> *C'est à cette étape que vous verrez "Building open-webui". Si cela échoue, vérifiez que vous avez bien fait le `git clone --recursive`.*

### Lancement via les Scripts Automatisés

Revenez à la racine du projet (`cd ..`) et utilisez les scripts qui orchestrent le tout (démarrage + logs + environnement).

**Sur Windows (PowerShell)**

*   **Mode Standard** :
    ```powershell
    .\start-dev.ps1
    ```

*   **Mode Léger** :
    ```powershell
    .\start-dev-light.ps1
    ```

### Sur Linux / Mac

Utilisez le script Python universel :

```bash
# Mode standard
python scripts/start.py

# Mode léger (option --profile light à passer manuellement si besoin, voir doc expert)
# Pour l'instant, préférez éditer infra/docker-compose.yml ou utiliser les commandes docker directes.
```

> **Note** : Le *premier* démarrage sera long (5 à 15 minutes) car il doit :
> 1. Télécharger les images Docker (plusieurs Go).
> 2. Construire l'image personnalisée d'Open WebUI.
> 3. Télécharger les modèles IA (Mistral : ~15 Go, Phi-3 : ~3 Go) au premier appel.

---

## 5. Vérification et Accès

Une fois que le terminal indique que les services sont prêts (ou après quelques minutes), ouvrez votre navigateur :

*   **Interface Utilisateur (Chat)** : [http://localhost:8080](http://localhost:8080)
    *   Créez un compte administrateur lors de la première connexion.
*   **API Gateway (Backend RAG)** : [http://localhost:8081/docs](http://localhost:8081/docs)
*   **Base de données Vectorielle (Qdrant)** : [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### Tester rapidement
1.  Aller sur **Open WebUI** (http://localhost:8080).
2.  Sélectionner le modèle **"Mistral"** (ou "Phi-3" si mode light) en haut à gauche.
3.  Poser une question simple : *"Qui es-tu ?"*.
4.  Si ça répond, l'installation est fonctionnelle !

---

## 6. Dépannage Fréquent

**Problème : "Open WebUI affiche une page blanche ou une erreur de connexion"**
*   Vérifiez que le conteneur `open-webui` tourne : `docker ps`.
*   Si le conteneur redémarre en boucle, c'est souvent un problème de sous-module manquant. Refaites : `git submodule update --init --recursive` puis reconstruisez : `docker compose -f infra/docker-compose.yml up -d --build open-webui`.

**Problème : "CUDA Out of Memory" / Lenteur extrême**
*   Vous n'avez pas assez de VRAM pour Mistral 7B.
*   Arrêtez tout : `.\stop-all.ps1`
*   Passez en mode léger : `.\start-dev-light.ps1`

**Problème : "Docker daemon is not running"**
*   Lancez Docker Desktop avant de lancer les scripts.
