"""Pipeline d'ingestion orchestrée par LlamaIndex."""
from __future__ import annotations

from collections.abc import Iterable
from typing import List

from ingestion.config import DEFAULT_CONFIG, ConnectorConfig, IngestionConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk
from ingestion.connectors.docx import DocxConnector
from ingestion.connectors.excel import ExcelConnector
from ingestion.connectors.mariadb import MariaDBConnector
from ingestion.connectors.pdf import PDFConnector
from ingestion.connectors.text import TextConnector


class IngestionPipeline:
    """Pipeline orchestrant la découverte, le chunking et l'envoi vers LlamaIndex."""

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

    def run(self) -> Iterable[DocumentChunk]:
        for connector in self.connectors:
            for item in connector.discover():
                for chunk in connector.load(item):  # type: ignore[arg-type]
                    yield chunk


__all__ = ["IngestionPipeline"]
