"""Connecteur DOCX basé sur python-docx."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ingestion.config import ConnectorConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk


class DocxConnector(BaseConnector):
    """Découpe les documents DOCX par paragraphe."""

    document_type = "docx"

    def discover(self) -> Iterable[Path]:
        for path in self.config.paths:
            if path.is_dir():
                yield from path.rglob("*.docx") if self.config.recursive else path.glob("*.docx")
            elif path.suffix.lower() == ".docx":
                yield path

    def load(self, path: Path) -> Iterable[DocumentChunk]:
        try:
            from docx import Document
        except ImportError as exc:  # pragma: no cover - dépendance optionnelle
            raise ImportError("python-docx doit être installé pour utiliser le connecteur DOCX") from exc

        document = Document(str(path))
        for index, paragraph in enumerate(document.paragraphs):
            text = paragraph.text.strip()
            if not text:
                continue
            metadata = {
                "source": str(path),
                "paragraph": index,
                "document_type": self.document_type,
            }
            yield DocumentChunk(id=f"{path.stem}-paragraph-{index}", text=text, metadata=metadata)


__all__ = ["DocxConnector"]
