"""Connecteur DOCX basé sur python-docx."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ingestion.config import ConnectorConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk


class DocxConnector(BaseConnector):
    """Découpe les documents DOCX par paragraphe."""

    document_type = "docx"

    def _iter_docx_files(self, directory: Path) -> Iterable[Path]:
        iterator = directory.rglob("*.docx") if self.config.recursive else directory.glob("*.docx")
        for candidate in iterator:
            if candidate.name.startswith("~$"):
                continue
            yield candidate

    def discover(self) -> Iterable[Path]:
        for path in self.config.paths:
            if path.is_dir():
                yield from self._iter_docx_files(path)
            elif path.suffix.lower() == ".docx" and not path.name.startswith("~$"):
                yield path

    def load(self, path: Path) -> Iterable[DocumentChunk]:
        try:
            from docx import Document
        except ImportError as exc:  # pragma: no cover - dépendance optionnelle
            raise ImportError("python-docx doit être installé pour utiliser le connecteur DOCX") from exc

        document = Document(str(path))
        full_text = []
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                full_text.append(text)
        
        if not full_text:
            return

        joined_text = "\n".join(full_text)
        metadata = {
            "source": str(path),
            "document_type": self.document_type,
        }
        yield DocumentChunk(id=path.stem, text=joined_text, metadata=metadata)


__all__ = ["DocxConnector"]
