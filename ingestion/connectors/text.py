"""Connecteur pour les fichiers texte."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ingestion.config import ConnectorConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk


class TextConnector(BaseConnector):
    """Découpe les fichiers texte en fragments basés sur la taille."""

    document_type = "txt"

    def __init__(self, config: ConnectorConfig, chunk_size: int, chunk_overlap: int) -> None:
        super().__init__(config)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def discover(self) -> Iterable[Path]:
        for path in self.config.paths:
            if path.is_dir():
                yield from path.rglob("*.txt") if self.config.recursive else path.glob("*.txt")
            elif path.suffix.lower() == ".txt":
                yield path

    def load(self, path: Path) -> Iterable[DocumentChunk]:
        # Lecture robuste des fichiers texte : on essaie UTF‑8 puis un fallback latin‑1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback pour les fichiers encodés en ANSI/Windows‑1252 ou similaires
            text = path.read_text(encoding="latin-1", errors="replace")
        position = 0
        index = 0
        while position < len(text):
            chunk_text = text[position : position + self.chunk_size]
            metadata = {
                "source": str(path),
                "chunk_index": index,
                "document_type": self.document_type,
            }
            yield DocumentChunk(id=f"{path.stem}-{index}", text=chunk_text, metadata=metadata)
            position += self.chunk_size - self.chunk_overlap
            index += 1


__all__ = ["TextConnector"]
