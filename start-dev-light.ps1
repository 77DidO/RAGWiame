<#
.SYNOPSIS
    Démarre l'environnement de développement "Light" (Phi-3 uniquement)

.DESCRIPTION
    Ce script démarre l'environnement de développement en mode "léger" :
    - Démarre vLLM Light (Phi-3)
    - Arrête vLLM Mistral (pour économiser la VRAM)
    - Démarre le serveur de développement frontend
    
    Services démarrés :
    - Services de base : MariaDB, Keycloak, Qdrant, Elasticsearch
    - LLM léger : vLLM Phi-3 mini (port 8110)
    - Gateway RAG : port 8090
    - OpenWebUI : port 8080
    - Frontend dev server : npm run dev sur port 5120
    
    Services ARRÊTÉS :
    - vLLM Mistral (port 8100)

.EXAMPLE
    .\start-dev-light.ps1
    
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

Write-Host "`n🚀 Démarrage de l'environnement de développement LIGHT" -ForegroundColor Magenta
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
    # Démarrer les services Docker avec le profil light
    Write-Info "Démarrage des services Docker (avec vllm-light)..."
    docker compose --profile light up -d
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec du démarrage des services Docker"
    }
    
    # Arrêter explicitement le gros modèle vLLM Mistral
    Write-Info "Arrêt de vLLM Mistral pour économiser la VRAM..."
    docker compose stop vllm
    
    Write-Success "Services Docker démarrés (Mistral arrêté, Phi-3 actif)"
    
    # Attendre quelques secondes pour que les services démarrent
    Write-Info "Attente du démarrage des services (10 secondes)..."
    Start-Sleep -Seconds 10
    
    # Afficher l'état des services
    Write-Info "État des services Docker:"
    docker compose --profile light ps
    
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
        Write-Host "🎉 Environnement LIGHT démarré avec succès!" -ForegroundColor Green
        Write-Host "=" * 70 -ForegroundColor Magenta
        Write-Host "`n📍 URLs d'accès:" -ForegroundColor Cyan
        Write-Host "   - Frontend Dev:  http://localhost:5120" -ForegroundColor Yellow
        Write-Host "   - OpenWebUI:     http://localhost:8080" -ForegroundColor Yellow
        Write-Host "   - Gateway RAG:   http://localhost:8090" -ForegroundColor Yellow
        Write-Host "   - vLLM Light:    http://localhost:8110" -ForegroundColor Yellow
        Write-Host "   - Qdrant:        http://localhost:8130" -ForegroundColor Yellow
        Write-Host "`n⚠️  Note: vLLM Mistral (port 8100) est ARRÊTÉ." -ForegroundColor Red
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
