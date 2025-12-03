"""Pipeline d'ingestion orchestrée par LlamaIndex."""
from __future__ import annotations

from typing import Iterable, List, Optional

from ingestion.config import DEFAULT_CONFIG, IngestionConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk
from ingestion.connectors.docx import DocxConnector
from ingestion.connectors.excel import ExcelConnector
from ingestion.connectors.pdf import PDFConnector
from ingestion.connectors.text import TextConnector

# Import optionnel de MariaDB
try:
    from ingestion.connectors.mariadb import MariaDBConnector
except ImportError:
    MariaDBConnector = None  # type: ignore

from ingestion.text_processor import TextProcessor
from ingestion.structure_detector import StructureDetector
from ingestion.metadata_enricher import MetadataEnricher
from ingestion.quality_filter import QualityFilter


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
        if config.mariadb_source.enabled and MariaDBConnector is not None:
            connectors.append(MariaDBConnector(config.mariadb_source, config.mariadb))
        return connectors

    def _chunk_document(self, chunk: DocumentChunk) -> Iterable[DocumentChunk]:
        raw_text = TextProcessor.clean_text(chunk.text)
        if not raw_text:
            return []
        paragraphs = TextProcessor.paragraphs(raw_text)
        if not paragraphs:
            return []

        chunk_metadata = dict(chunk.metadata)
        doc_hint = MetadataEnricher.infer_doc_hint(chunk_metadata)
        if doc_hint:
            chunk_metadata["doc_hint"] = doc_hint
        chunk_metadata.setdefault("parent_id", chunk.id)

        current_section: Optional[str] = None
        section_buffer: List[str] = []
        faq_question: Optional[str] = None

        general_buffer: List[str] = []
        general_len = 0
        size = self.config.chunk_size
        idx = 0

        def flush_general():
            nonlocal general_buffer, general_len, idx
            if not general_buffer:
                return []
            text_block = " ".join(general_buffer).strip()
            chunks = []
            if text_block and not QualityFilter.is_low_quality_chunk(text_block, chunk_metadata):
                metadata = dict(chunk_metadata)
                metadata["chunk_index"] = idx
                chunk_id = f"{chunk.id}-chunk-{idx}"
                idx += 1
                chunks.append(DocumentChunk(id=chunk_id, text=text_block, metadata=metadata))
            general_buffer = []
            general_len = 0
            return chunks

        def flush_section():
            nonlocal section_buffer, current_section, idx
            chunks = []
            if current_section and section_buffer:
                text_block = " ".join(section_buffer).strip()
                if text_block and not QualityFilter.is_low_quality_chunk(text_block, chunk_metadata):
                    metadata = dict(chunk_metadata)
                    metadata["chunk_index"] = idx
                    metadata["section_label"] = current_section
                    chunk_id = f"{chunk.id}-section-{idx}"
                    idx += 1
                    chunks.append(DocumentChunk(id=chunk_id, text=text_block, metadata=metadata))
            section_buffer = []
            current_section = None
            return chunks

        for paragraph in paragraphs:
            # 1. Détection FAQ
            q, a = StructureDetector.detect_faq(paragraph)
            if q:
                faq_question = q
                continue
            if faq_question and a:
                full_faq_text = f"Question: {faq_question}\nRéponse: {a}"
                if not QualityFilter.is_low_quality_chunk(full_faq_text, chunk_metadata):
                    metadata = dict(chunk_metadata)
                    metadata["chunk_index"] = idx
                    metadata["faq_question"] = faq_question
                    chunk_id = f"{chunk.id}-faq-{idx}"
                    idx += 1
                    yield DocumentChunk(
                        id=chunk_id,
                        text=full_faq_text,
                        metadata=metadata,
                    )
                faq_question = None
                continue

            # 2. Détection Section
            label = StructureDetector.detect_section_label(paragraph)
            if label:
                for chunk_obj in flush_section():
                    yield chunk_obj
                current_section = label
                continue

            if current_section:
                section_buffer.append(paragraph)
                continue

            # 3. Buffer général
            paragraph_len = len(paragraph)
            if general_len + paragraph_len > size and general_buffer:
                for chunk_obj in flush_general():
                    yield chunk_obj
            general_buffer.append(paragraph)
            general_len += paragraph_len

        for chunk_obj in flush_section():
            yield chunk_obj
        for chunk_obj in flush_general():
            yield chunk_obj

    def run(self) -> Iterable[DocumentChunk]:
        for connector in self.connectors:
            for item in connector.discover():
                for chunk in connector.load(item):  # type: ignore[arg-type]
                    yield from self._chunk_document(chunk)


__all__ = ["IngestionPipeline"]
