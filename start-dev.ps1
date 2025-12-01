<#
.SYNOPSIS
    Démarre l'environnement de développement RAGWiame complet

.DESCRIPTION
    Ce script démarre tous les services Docker nécessaires pour le développement,
    incluant le modèle LLM léger (vllm-light) et le serveur de développement frontend.
    
    Services démarrés :
    - Docker Compose : tous les services de base + vllm-light (profil 'light')
    - Frontend dev server : npm run dev sur port 5120

.EXAMPLE
    .\start-dev.ps1
    
.NOTES
    Auteur: RAGWiame Team
    Version: 1.0
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Couleurs pour les messages
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Error-Custom { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Warning-Custom { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }

Write-Host "`n🚀 Démarrage de l'environnement de développement RAGWiame" -ForegroundColor Magenta
Write-Host "=" * 70 -ForegroundColor Magenta

# Vérifier que Docker Desktop est démarré
Write-Info "Vérification de Docker Desktop..."
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker n'est pas accessible"
    }
    Write-Success "Docker Desktop est opérationnel"
} catch {
    Write-Error-Custom "Docker Desktop n'est pas démarré ou n'est pas installé"
    Write-Warning-Custom "Veuillez démarrer Docker Desktop et réessayer"
    exit 1
}

# Se positionner dans le répertoire infra
$infraPath = Join-Path $PSScriptRoot "infra"
if (-not (Test-Path $infraPath)) {
    Write-Error-Custom "Le répertoire infra n'existe pas: $infraPath"
    exit 1
}

Push-Location $infraPath

try {
    # Démarrer les services Docker SANS le profil light
    Write-Info "Démarrage des services Docker (avec vLLM Mistral uniquement)..."
    Write-Host "   - Services de base : MariaDB, Keycloak, Qdrant, Elasticsearch" -ForegroundColor Gray
    Write-Host "   - LLM principal : vLLM Mistral 7B (port 8100)" -ForegroundColor Gray
    Write-Host "   - Gateway RAG : port 8090" -ForegroundColor Gray
    Write-Host "   - OpenWebUI : port 8080" -ForegroundColor Gray
    Write-Host "`n   ⚠️  vLLM Light (Phi-3) n'est PAS démarré" -ForegroundColor Yellow
    
    docker compose up -d
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec du démarrage des services Docker"
    }
    
    Write-Success "Services Docker démarrés avec succès"
    
    # Attendre quelques secondes pour que les services démarrent
    Write-Info "Attente du démarrage des services (10 secondes)..."
    Start-Sleep -Seconds 10
    
    # Afficher l'état des services
    Write-Info "État des services Docker:"
    docker compose ps
    
} catch {
    Write-Error-Custom "Erreur lors du démarrage des services Docker: $_"
    Pop-Location
    exit 1
}

Pop-Location

# Démarrer le serveur de développement frontend
Write-Info "`nDémarrage du serveur de développement frontend..."
$frontendPath = Join-Path $PSScriptRoot "open-webui"

if (-not (Test-Path $frontendPath)) {
    Write-Warning-Custom "Le répertoire open-webui n'existe pas: $frontendPath"
    Write-Warning-Custom "Le frontend dev ne sera pas démarré"
} else {
    Push-Location $frontendPath
    
    try {
        # Vérifier que node_modules existe
        if (-not (Test-Path "node_modules")) {
            Write-Info "Installation des dépendances npm (première fois)..."
            npm install
        }
        
        Write-Success "Serveur de développement frontend prêt"
        Write-Host "`n" + "=" * 70 -ForegroundColor Magenta
        Write-Host "🎉 Environnement de développement démarré avec succès!" -ForegroundColor Green
        Write-Host "=" * 70 -ForegroundColor Magenta
        Write-Host "`n📍 URLs d'accès:" -ForegroundColor Cyan
        Write-Host "   - Frontend Dev:  http://localhost:5120" -ForegroundColor Yellow
        Write-Host "   - OpenWebUI:     http://localhost:8080" -ForegroundColor Yellow
        Write-Host "   - Gateway RAG:   http://localhost:8090" -ForegroundColor Yellow
        Write-Host "   - vLLM Mistral:  http://localhost:8100" -ForegroundColor Yellow
        Write-Host "   - Qdrant:        http://localhost:8130" -ForegroundColor Yellow
        Write-Host "`n⚡ Démarrage du serveur Vite..." -ForegroundColor Cyan
        Write-Host "   (Appuyez sur Ctrl+C pour arrêter)`n" -ForegroundColor Gray
        
        # Démarrer le serveur de dev (bloquant)
        npm run dev
        
    } catch {
        Write-Error-Custom "Erreur lors du démarrage du frontend: $_"
        Pop-Location
        exit 1
    } finally {
        Pop-Location
    }
}

Write-Host "`n👋 Arrêt du serveur de développement" -ForegroundColor Yellow
