"""Configuration de l'intégration Open WebUI."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FrontendSettings:
    """Paramètres exposés via variables d'environnement."""

    keycloak_url: str = "http://keycloak:8080/"
    client_id: str = "rag-webui"
    realm: str = "rag"
    api_base: str = "http://gateway:8081"
    audit_topic: str = "rag_audit"


DEFAULT_FRONTEND_SETTINGS = FrontendSettings()


__all__ = ["FrontendSettings", "DEFAULT_FRONTEND_SETTINGS"]
