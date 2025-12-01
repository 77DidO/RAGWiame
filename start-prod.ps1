<#
.SYNOPSIS
    Démarre l'environnement de production RAGWiame

.DESCRIPTION
    Ce script démarre tous les services Docker nécessaires pour la production,
    avec uniquement le modèle LLM principal Mistral (sans vllm-light ni frontend dev).
    
    Services démarrés :
    - Docker Compose : tous les services de base (sans profil 'light')
    - Pas de frontend dev server (utilise OpenWebUI en production)

.EXAMPLE
    .\start-prod.ps1
    
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

Write-Host "`n🚀 Démarrage de l'environnement de production RAGWiame" -ForegroundColor Magenta
Write-Host "=" * 70 -ForegroundColor Magenta

# Vérifier que Docker Desktop est démarré
Write-Info "Vérification de Docker Desktop..."
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker n'est pas accessible"
    }
    Write-Success "Docker Desktop est opérationnel"
}
catch {
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
    # Démarrer les services Docker (sans profil light)
    Write-Info "Démarrage des services Docker (production)..."
    Write-Host "   - Services de base : MariaDB, Keycloak, Qdrant, Elasticsearch" -ForegroundColor Gray
    Write-Host "   - LLM principal : vLLM Mistral 7B (port 8100)" -ForegroundColor Gray
    Write-Host "   - Gateway RAG : port 8090" -ForegroundColor Gray
    Write-Host "   - OpenWebUI : port 8080" -ForegroundColor Gray
    Write-Host "`n   ⚠️  vLLM Light (Phi-3) n'est PAS démarré en production" -ForegroundColor Yellow
    
    docker compose --profile mistral up -d
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec du démarrage des services Docker"
    }
    
    Write-Success "Services Docker démarrés avec succès"
    
    # Attendre quelques secondes pour que les services démarrent
    Write-Info "Attente du démarrage des services (15 secondes)..."
    Start-Sleep -Seconds 15
    
    # Afficher l'état des services
    Write-Info "État des services Docker:"
    docker compose ps
    
    Write-Host "`n" + "=" * 70 -ForegroundColor Magenta
    Write-Host "🎉 Environnement de production démarré avec succès!" -ForegroundColor Green
    Write-Host "=" * 70 -ForegroundColor Magenta
    Write-Host "`n📍 URLs d'accès:" -ForegroundColor Cyan
    Write-Host "   - OpenWebUI:     http://localhost:8080" -ForegroundColor Yellow
    Write-Host "   - Gateway RAG:   http://localhost:8090" -ForegroundColor Yellow
    Write-Host "   - vLLM Mistral:  http://localhost:8100" -ForegroundColor Yellow
    Write-Host "   - Qdrant:        http://localhost:8130" -ForegroundColor Yellow
    Write-Host "   - Elasticsearch: http://localhost:8120" -ForegroundColor Yellow
    
    Write-Host "`n💡 Conseils:" -ForegroundColor Cyan
    Write-Host "   - Voir les logs: docker compose logs -f [service]" -ForegroundColor Gray
    Write-Host "   - Arrêter: .\stop-all.ps1 ou docker compose down" -ForegroundColor Gray
    Write-Host "   - Redémarrer un service: docker compose restart [service]" -ForegroundColor Gray
    
    Write-Host "`n✨ L'environnement est prêt à l'emploi!`n" -ForegroundColor Green
    
}
catch {
    Write-Error-Custom "Erreur lors du démarrage des services Docker: $_"
    Pop-Location
    exit 1
}

Pop-Location
