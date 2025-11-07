# Sécurité et gestion des droits

## Authentification et autorisation

- Keycloak est la source de vérité pour les utilisateurs, les rôles et les services.
- Les tokens OIDC sont vérifiés par l'API FastAPI via OAuth2 Authorization Code.
- Les métadonnées des chunks incluent `service` et `role`, utilisés comme filtres côté Qdrant.

## Journalisation

- Chaque requête API doit être journalisée avec l'identité utilisateur, la question, le score des documents et les citations.
- Les conteneurs exposent leurs logs sur stdout pour ingestion par un stack EFK/ELK.

## Protection des données

- Secrets fournis via variables d'environnement ou stores externes (Vault, SOPS).
- Chiffrement en transit via TLS (à activer via reverse proxy en production).
- Sauvegardes régulières de Qdrant et MariaDB.

## Tests de sécurité

- Vérifier la non régression sur les filtres de rôles lors des tests d'intégration.
- Ajouter des scans SAST/DAST dans la CI/CD.
