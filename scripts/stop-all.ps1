<#
.SYNOPSIS
    Arrête tous les services RAGWiame

.DESCRIPTION
    Ce script arrête tous les services Docker (y compris ceux du profil 'light')
    et nettoie les ressources.

.PARAMETER RemoveVolumes
    Si spécifié, supprime également les volumes Docker (données persistantes)

.EXAMPLE
    .\stop-all.ps1
    Arrête tous les services sans supprimer les données

.EXAMPLE
    .\stop-all.ps1 -RemoveVolumes
    Arrête tous les services et supprime les volumes (⚠️ perte de données)
    
.NOTES
    Auteur: RAGWiame Team
    Version: 1.0
#>

[CmdletBinding()]
param(
    [switch]$RemoveVolumes
)

$ErrorActionPreference = "Stop"

# Couleurs pour les messages
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Error-Custom { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Warning-Custom { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }

Write-Host "`n🛑 Arrêt de l'environnement RAGWiame" -ForegroundColor Magenta
Write-Host "=" * 70 -ForegroundColor Magenta

# Se positionner dans le répertoire infra
$infraPath = Join-Path $PSScriptRoot "..\infra"
if (-not (Test-Path $infraPath)) {
    Write-Error-Custom "Le répertoire infra n'existe pas: $infraPath"
    exit 1
}

Push-Location $infraPath

try {
    # Arrêter les services avec profil light
    Write-Info "Arrêt des services Docker (incluant profil 'light')..."
    docker compose --profile light down $(if ($RemoveVolumes) { "-v" } else { "" })
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec de l'arrêt des services Docker"
    }
    
    Write-Success "Services Docker arrêtés avec succès"
    
    if ($RemoveVolumes) {
        Write-Warning-Custom "Les volumes Docker ont été supprimés (données perdues)"
    } else {
        Write-Info "Les volumes Docker ont été conservés (données persistantes)"
    }
    
    Write-Host "`n" + "=" * 70 -ForegroundColor Magenta
    Write-Host "✅ Tous les services ont été arrêtés" -ForegroundColor Green
    Write-Host "=" * 70 -ForegroundColor Magenta
    
    Write-Host "`n💡 Pour redémarrer:" -ForegroundColor Cyan
    Write-Host "   - Dev:  .\start-dev.ps1" -ForegroundColor Gray
    Write-Host "   - Prod: .\start-prod.ps1" -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Error-Custom "Erreur lors de l'arrêt des services: $_"
    Pop-Location
    exit 1
}

Pop-Location
