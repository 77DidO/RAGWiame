"""Connecteur d'ingestion de base."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Protocol

from ingestion.config import ConnectorConfig


class Chunk(Protocol):
    """Représente un fragment de document prêt à indexer."""

    id: str
    text: str
    metadata: Mapping[str, object]


@dataclass(slots=True)
class DocumentChunk:
    """Implémentation concrète de Chunk."""

    id: str
    text: str
    metadata: Mapping[str, object]


class BaseConnector(ABC):
    """Spécifie l'interface minimale d'un connecteur d'ingestion."""

    document_type: str

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config

    @abstractmethod
    def discover(self) -> Iterable[Path]:
        """Retourne la liste des fichiers à ingérer."""

    @abstractmethod
    def load(self, path: Path) -> Iterable[DocumentChunk]:
        """Charge un fichier en fragments exploitables."""


__all__ = ["BaseConnector", "DocumentChunk", "Chunk"]
