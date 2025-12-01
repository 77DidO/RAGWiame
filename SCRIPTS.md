# Scripts PowerShell de Démarrage RAGWiame

Ce document décrit les scripts PowerShell disponibles à la racine du projet pour faciliter le démarrage et l'arrêt des environnements de développement et production.

## 📜 Scripts Disponibles

### `start-dev.ps1` - Environnement de Développement (Standard)

Démarre l'environnement de développement avec :
- ✅ Tous les services Docker de base
- ✅ vLLM Mistral 7B (modèle principal)
- ❌ vLLM Phi-3 mini (ARRÊTÉ)
- ✅ Serveur de développement frontend (Vite sur port 5120)

**Utilisation :**
```powershell
.\start-dev.ps1
```

### `start-dev-light.ps1` - Environnement de Développement (Light)

Démarre l'environnement de développement léger (économie VRAM) avec :
- ✅ Tous les services Docker de base
- ❌ vLLM Mistral 7B (ARRÊTÉ)
- ✅ vLLM Phi-3 mini (modèle léger)
- ✅ Serveur de développement frontend (Vite sur port 5120)

**Utilisation :**
```powershell
.\start-dev-light.ps1
```

**URLs d'accès :**
- Frontend Dev: http://localhost:5120
- OpenWebUI: http://localhost:8080
- Gateway RAG: http://localhost:8090
- vLLM Mistral: http://localhost:8100
- vLLM Light: http://localhost:8110
- Qdrant: http://localhost:8130

---

### `start-prod.ps1` - Environnement de Production

Démarre l'environnement de production avec :
- ✅ Tous les services Docker de base
- ✅ vLLM Mistral 7B uniquement (pas de modèle léger)
- ✅ Gateway RAG
- ✅ OpenWebUI (production uniquement, pas de dev server)

**Utilisation :**
```powershell
.\start-prod.ps1
```

**URLs d'accès :**
- OpenWebUI: http://localhost:8080
- Gateway RAG: http://localhost:8090
- vLLM Mistral: http://localhost:8100
- Qdrant: http://localhost:8130

---

### `stop-all.ps1` - Arrêter Tous les Services

Arrête tous les services Docker (y compris le profil 'light').

**Utilisation :**
```powershell
# Arrêter les services (conserver les données)
.\stop-all.ps1

# Arrêter les services ET supprimer les volumes (⚠️ perte de données)
.\stop-all.ps1 -RemoveVolumes
```

---

## 🔧 Prérequis

- **Windows 11** avec PowerShell 5.1+
- **Docker Desktop** installé et démarré
- **Node.js 18+** et **npm** (pour le dev frontend)

---

## 💡 Conseils d'Utilisation

### Développement Frontend

Le script `start-dev.ps1` démarre automatiquement le serveur Vite. Pour arrêter uniquement le frontend :
- Appuyez sur `Ctrl+C` dans le terminal

Les services Docker continueront de tourner en arrière-plan.

### Voir les Logs

```powershell
# Logs de tous les services
docker compose -f infra/docker-compose.yml logs -f

# Logs d'un service spécifique
docker compose -f infra/docker-compose.yml logs -f gateway
docker compose -f infra/docker-compose.yml logs -f vllm
```

### Redémarrer un Service

```powershell
cd infra
docker compose restart gateway
docker compose --profile light restart vllm-light
```

### Vérifier l'État des Services

```powershell
cd infra
docker compose ps
docker compose --profile light ps
```

---

## 🐛 Dépannage

### Docker Desktop n'est pas démarré
```
❌ Docker Desktop n'est pas démarré ou n'est pas installé
⚠️  Veuillez démarrer Docker Desktop et réessayer
```
**Solution :** Démarrez Docker Desktop et attendez qu'il soit complètement initialisé.

### Port déjà utilisé
```
Error response from daemon: driver failed programming external connectivity on endpoint...
Bind for 0.0.0.0:8080 failed: port is already allocated
```
**Solution :** Un autre service utilise le port. Identifiez et arrêtez le processus :
```powershell
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### Erreur npm (frontend)
```
npm ERR! Missing script: "dev"
```
**Solution :** Réinstallez les dépendances :
```powershell
cd open-webui
npm install
```

---

## 📚 Autres Scripts

- `start.py` - Script Python original pour démarrage automatique
- `bootstrap.sh` - Script Bash pour environnements Linux/Mac
- `reingest.py` - Réingestion des documents
- `deploy.py` - Déploiement Docker

---

## 🔗 Documentation Complémentaire

- [README principal](../README.md)
- [Documentation d'architecture](../docs/architecture.md)
- [Guide d'ingestion](../docs/ingestion.md)
- [Configuration Gateway](../docs/gateway.md)
