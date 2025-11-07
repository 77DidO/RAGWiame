# Déploiement

## Prérequis

- Docker 24+
- Docker Compose v2
- Accès à un GPU compatible CUDA pour vLLM (optionnel mais recommandé)
- Variables d'environnement définies (`MARIADB_PASSWORD`, `OAUTH_CLIENT_SECRET`, etc.)

## Étapes

1. **Démarrage automatisé**
   - **Linux / macOS (Bash)**
     ```bash
     python scripts/start.py
     ```
   - **Windows (PowerShell)**
     ```powershell
     python scripts/start.py
     ```
   - Options utiles :
     - `--skip-bootstrap` : saute `bootstrap.sh` (par exemple si le virtualenv est déjà prêt).
     - `--skip-deploy` : évite `docker compose up` (utile pour une simple préparation locale).
   - Le script vérifie la présence de `docker` et, sous Windows, délègue à WSL pour exécuter `bootstrap.sh`.
2. **Étapes manuelles (facultatif)**
   - Gardez cette approche si vous souhaitez un contrôle fin :
     ```bash
     chmod +x scripts/bootstrap.sh
     ./scripts/bootstrap.sh
     python scripts/deploy.py
     ```
   - Sous Windows, exécutez les commandes `chmod` et `bootstrap.sh` dans WSL avant de lancer `python scripts/deploy.py`.
3. **Accès à l'interface**
   - Open WebUI : http://localhost:8080
   - API Gateway : http://localhost:8081/healthz
   - Qdrant UI : http://localhost:6333 (si activé)

## Helm (esquisse)

- Charts à générer pour chaque composant avec valeurs distinctes (GPU, stockage persistant, secrets).
- Utiliser les Secrets Kubernetes pour les mots de passe MariaDB et Keycloak.
