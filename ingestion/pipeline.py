"""Pipeline d'ingestion orchestrée par LlamaIndex."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import List

from ingestion.config import IngestionConfig, DEFAULT_CONFIG
from ingestion.connectors.base import BaseConnector, DocumentChunk
from ingestion.connectors.docx import DocxConnector
from ingestion.connectors.excel import ExcelConnector
from ingestion.connectors.mariadb import MariaDBConnector
from ingestion.connectors.pdf import PDFConnector
from ingestion.connectors.text import TextConnector


class IngestionPipeline:
    """Pipeline orchestrant la découverte, le chunking et l'envoi vers LlamaIndex."""

    _QUESTION_LABEL = re.compile(r"(?im)^\s*(question|réponse)\s*:\s*", re.UNICODE)

    def __init__(self, config: IngestionConfig = DEFAULT_CONFIG) -> None:
        self.config = config
        self.connectors: List[BaseConnector] = self._build_connectors(config)

    def _build_connectors(self, config: IngestionConfig) -> List[BaseConnector]:
        connectors: List[BaseConnector] = []
        if config.txt.enabled:
            connectors.append(TextConnector(config.txt, config.chunk_size, config.chunk_overlap))
        if config.docx.enabled:
            connectors.append(DocxConnector(config.docx))
        if config.pdf.enabled:
            connectors.append(PDFConnector(config.pdf))
        if config.excel.enabled:
            connectors.append(ExcelConnector(config.excel, config.excel_options))
        if config.mariadb_source.enabled:
            connectors.append(MariaDBConnector(config.mariadb_source, config.mariadb))
        return connectors

    def _clean_text(self, text: str) -> str:
        cleaned = text.replace("\u00a0", " ")
        cleaned = cleaned.replace("\n", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = self._QUESTION_LABEL.sub("", cleaned)
        return cleaned

    def _split_text(self, text: str) -> List[str]:
        size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        if size <= 0:
            return [text]
        if len(text) <= size:
            return [text]

        chunks: List[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(length, start + size)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == length:
                break
            start = max(0, end - overlap)
            if start >= length:
                break
        return chunks

    def _chunk_document(self, chunk: DocumentChunk) -> Iterable[DocumentChunk]:
        cleaned = self._clean_text(chunk.text)
        if not cleaned:
            return []
        pieces = self._split_text(cleaned)
        chunk_metadata = dict(chunk.metadata)
        chunk_metadata.setdefault("parent_id", chunk.id)
        for idx, piece in enumerate(pieces):
            metadata = dict(chunk_metadata)
            metadata["chunk_index"] = idx
            yield DocumentChunk(
                id=f"{chunk.id}-chunk-{idx}",
                text=piece,
                metadata=metadata,
            )

    def run(self) -> Iterable[DocumentChunk]:
        for connector in self.connectors:
            for item in connector.discover():
                for chunk in connector.load(item):  # type: ignore[arg-type]
                    yield from self._chunk_document(chunk)


__all__ = ["IngestionPipeline"]
