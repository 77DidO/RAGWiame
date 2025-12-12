"""Connecteur PDF basé sur pdfplumber (licence MIT)."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ingestion.config import ConnectorConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk
from ingestion.metadata_utils import extract_ao_metadata, should_exclude_path


class PDFConnector(BaseConnector):
    """Découpe les PDF page par page."""

    document_type = "pdf"

    def discover(self) -> Iterable[Path]:
        for path in self.config.paths:
            if path.is_dir():
                iterator = path.rglob("*.pdf") if self.config.recursive else path.glob("*.pdf")
                for candidate in iterator:
                    if should_exclude_path(candidate, self.config):
                        continue
                    yield candidate
            elif path.suffix.lower() == ".pdf" and not should_exclude_path(path, self.config):
                yield path

    def load(self, path: Path) -> Iterable[DocumentChunk]:
        try:
            import pdfplumber
        except ImportError as exc:  # pragma: no cover
            raise ImportError("pdfplumber doit être installé pour utiliser le connecteur PDF") from exc

        with pdfplumber.open(str(path)) as pdf:
            doc_metadata = pdf.metadata or {}
            full_text = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text:
                    full_text.append(text)

            if not full_text:
                return

            joined_text = "\n".join(full_text)
            metadata = self._build_metadata(path, 0, doc_metadata)
            # On retire 'page' des métadonnées car c'est tout le document
            metadata.pop("page", None)
            metadata.update(extract_ao_metadata(path))
            yield DocumentChunk(id=path.stem, text=joined_text, metadata=metadata)

    def _build_metadata(self, path: Path, index: int, info: dict) -> dict:
        metadata: dict = {
            "source": str(path),
            "page": index,
            "document_type": self.document_type,
        }
        for key in ("Author", "Creator", "Producer", "CreationDate", "Title"):
            value = info.get(key) or info.get(f"/{key}")
            if value:
                metadata[key.lower()] = value
        return metadata


__all__ = ["PDFConnector"]
