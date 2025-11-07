# Déploiement

## Prérequis

- Docker 24+
- Docker Compose v2
- Accès à un GPU compatible CUDA pour vLLM (optionnel mais recommandé)
- Variables d'environnement définies (`MARIADB_PASSWORD`, `OAUTH_CLIENT_SECRET`, etc.)

## Étapes

1. **Initialisation locale**
   ```bash
   chmod +x scripts/bootstrap.sh
   ./scripts/bootstrap.sh
   ```
2. **Lancement des conteneurs**
   ```bash
   python scripts/deploy.py
   ```
3. **Accès à l'interface**
   - Open WebUI : http://localhost:8080
   - API Gateway : http://localhost:8081/healthz
   - Qdrant UI : http://localhost:6333 (si activé)

## Helm (esquisse)

- Charts à générer pour chaque composant avec valeurs distinctes (GPU, stockage persistant, secrets).
- Utiliser les Secrets Kubernetes pour les mots de passe MariaDB et Keycloak.
