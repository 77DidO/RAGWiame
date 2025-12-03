<#
.SYNOPSIS
    Lance les outils ponctuels (Ingestion, Indexation, etc.)

.DESCRIPTION
    Ce script permet de lancer les conteneurs "one-shot" qui ne sont pas démarrés
    automatiquement avec l'environnement de développement.
    
    Outils disponibles :
    - ingestion : Ingestion des documents
    - indexation : Indexation dans Qdrant/Elasticsearch
    - insights : Génération d'insights
    - inventory : Inventaire des documents
    - classification : Classification des documents

.PARAMETER Tool
    Nom de l'outil à lancer (ingestion, indexation, insights, inventory, classification)

.EXAMPLE
    .\run-tools.ps1 -Tool ingestion
    Lance le processus d'ingestion

.NOTES
    Auteur: RAGWiame Team
    Version: 1.0
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("ingestion", "indexation", "insights", "inventory", "classification")]
    [string]$Tool
)

$ErrorActionPreference = "Stop"

# Couleurs pour les messages
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Error-Custom { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

# Se positionner dans le répertoire infra
$infraPath = Join-Path $PSScriptRoot "infra"
if (-not (Test-Path $infraPath)) {
    Write-Error-Custom "Le répertoire infra n'existe pas: $infraPath"
    exit 1
}

Push-Location $infraPath

try {
    Write-Info "Construction de l'image pour : $Tool"
    docker compose --profile tools build $Tool
    
    Write-Info "Lancement de l'outil : $Tool"
    
    # Lancer le conteneur avec le profil tools
    # --rm supprime le conteneur après exécution
    docker compose --profile tools run --rm $Tool
    
    if ($LASTEXITCODE -ne 0) {
        throw "Échec de l'exécution de l'outil $Tool"
    }
    
    Write-Success "Outil $Tool exécuté avec succès"
    
}
catch {
    Write-Error-Custom "Erreur lors de l'exécution : $_"
    Pop-Location
    exit 1
}

Pop-Location
