"""Configuration de l'ingestion pour la plateforme RAG."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(slots=True)
class SourceCredentials:
    """Informations d'authentification pour une source de données."""

    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)


DEFAULT_DATA_ROOT = Path("/data")


def _default_paths() -> List[Path]:
    return [DEFAULT_DATA_ROOT]


@dataclass(slots=True)
class ConnectorConfig:
    """Configuration générique d'un connecteur d'ingestion."""

    enabled: bool
    paths: List[Path] = field(default_factory=_default_paths)
    include_metadata: bool = True
    recursive: bool = True
    credentials: SourceCredentials = field(default_factory=SourceCredentials)
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ExcelConnectorOptions:
    """Options spécifiques aux classeurs Excel."""

    load_formulas: bool = True
    max_rows: Optional[int] = None
    max_columns: Optional[int] = None
    sheet_whitelist: Optional[List[str]] = None


@dataclass(slots=True)
class MariaDBConfig:
    """Paramètres de connexion à MariaDB."""

    host: str = "mariadb"
    port: int = 3306
    database: str = "rag"
    user: str = "rag_user"
    password_env: str = "MARIADB_PASSWORD"


@dataclass(slots=True)
class IngestionConfig:
    """Configuration globale de l'ingestion."""

    txt: ConnectorConfig = field(default_factory=lambda: ConnectorConfig(enabled=True))
    docx: ConnectorConfig = field(default_factory=lambda: ConnectorConfig(enabled=True))
    pdf: ConnectorConfig = field(default_factory=lambda: ConnectorConfig(enabled=True))
    excel: ConnectorConfig = field(default_factory=lambda: ConnectorConfig(enabled=True))
    excel_options: ExcelConnectorOptions = field(default_factory=ExcelConnectorOptions)
    mariadb: MariaDBConfig = field(default_factory=MariaDBConfig)
    mariadb_source: ConnectorConfig = field(default_factory=lambda: ConnectorConfig(enabled=False))
    chunk_size: int = 600
    chunk_overlap: int = 80
    language: str = "fr"


DEFAULT_CONFIG = IngestionConfig()


__all__ = [
    "SourceCredentials",
    "ConnectorConfig",
    "ExcelConnectorOptions",
    "MariaDBConfig",
    "IngestionConfig",
    "DEFAULT_CONFIG",
]
