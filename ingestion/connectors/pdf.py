"""Connecteur PDF basé sur pypdf."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ingestion.config import ConnectorConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk


class PDFConnector(BaseConnector):
    """Découpe les PDF page par page."""

    document_type = "pdf"

    def discover(self) -> Iterable[Path]:
        for path in self.config.paths:
            if path.is_dir():
                yield from path.rglob("*.pdf") if self.config.recursive else path.glob("*.pdf")
            elif path.suffix.lower() == ".pdf":
                yield path

    def load(self, path: Path) -> Iterable[DocumentChunk]:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - dépendance optionnelle
            raise ImportError("pypdf doit être installé pour utiliser le connecteur PDF") from exc

        reader = PdfReader(str(path))
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            metadata = self._build_metadata(path, index, reader)
            yield DocumentChunk(id=f"{path.stem}-page-{index}", text=text, metadata=metadata)

    def _build_metadata(self, path: Path, index: int, reader: "PdfReader") -> dict:
        info = reader.metadata or {}
        metadata: dict = {
            "source": str(path),
            "page": index,
            "document_type": self.document_type,
        }
        for key in ("/Author", "/Creator", "/Producer", "/CreationDate"):
            if key in info:
                metadata[key.strip("/").lower()] = info[key]
        return metadata


__all__ = ["PDFConnector"]
