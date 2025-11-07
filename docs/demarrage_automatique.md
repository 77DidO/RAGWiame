# Script de démarrage `scripts/start.py`

Ce script orchestre l'initialisation Python (`bootstrap.sh`) et le lancement de la stack Docker (`deploy.py`).

## Usage

```bash
python scripts/start.py [--skip-bootstrap] [--skip-deploy]
```

- `--skip-bootstrap` : utile si l'environnement virtuel `.venv` est déjà installé.
- `--skip-deploy` : permet de ne faire que la préparation Python, sans démarrer Docker.

## Comportement par système

- **Linux / macOS** : applique automatiquement le bit exécutable sur `bootstrap.sh` puis l'exécute.
- **Windows** : exige WSL. Les commandes `chmod` et `bootstrap.sh` sont relayées dans WSL afin d'utiliser Bash.

## Pré-requis vérifiés

Le script vérifie la présence des fichiers `bootstrap.sh` et `deploy.py`, ainsi que des commandes `docker` (pour `deploy.py`) et `wsl` sous Windows. En cas d'erreur, il retourne un code de sortie non nul et affiche un message explicite.

## Codes de sortie

- `0` : succès complet.
- `1` : erreur de validation (fichier manquant, commande introuvable, etc.).
- `>0` : code renvoyé par une commande sous-jacente (`bootstrap.sh`, `docker compose`, ...).

## Intégration CI/CD

Ce script peut être invoqué depuis un pipeline CI pour provisionner l'environnement local avant des tests de fumée. Utilisez `--skip-deploy` si vous ne souhaitez préparer que le virtualenv.
