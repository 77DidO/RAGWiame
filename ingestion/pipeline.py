"""Pipeline d'ingestion orchestrée par LlamaIndex."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Iterable, List, Optional

from ingestion.config import DEFAULT_CONFIG, IngestionConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk
from ingestion.connectors.docx import DocxConnector
from ingestion.connectors.excel import ExcelConnector
from ingestion.connectors.mariadb import MariaDBConnector
from ingestion.connectors.pdf import PDFConnector
from ingestion.connectors.text import TextConnector


class IngestionPipeline:
    """Pipeline orchestrant la découverte, le chunking et l'envoi vers LlamaIndex."""

    _QUESTION_LABEL = re.compile(r"(?im)^\s*(question|réponse)\s*:\s*", re.UNICODE)
    _FAQ_START = re.compile(r"(?is)^\s*question\s*:\s*(.+)$")
    _FAQ_ANSWER = re.compile(r"(?is)^\s*réponse\s*:\s*(.+)$")
    _SECTION_KEYWORDS = [
        "VENDEUR",
        "ACQUEREUR",
        "ACQUÉREUR",
        "ACHETEUR",
        "PROPRIETAIRE",
        "PROPRIÉTAIRE",
        "NOTAIRE",
        "MANDATAIRE",
        "DIAGNOSTIC",
        "DESIGNATION",
        "CONDITIONS",
        "GARANTIES",
        "PAIEMENT",
    ]

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
        cleaned = cleaned.replace("\r", "\n")
        return cleaned

    def _split_text(self, text: str) -> List[str]:
        size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        # Validation des paramètres pour éviter les boucles infinies
        if size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        if overlap >= size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        # Log de debug pour vérifier les valeurs utilisées
        print(f"DEBUG: _split_text size={size} overlap={overlap}", flush=True)
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

    def _paragraphs(self, text: str) -> List[str]:
        cleaned = self._QUESTION_LABEL.sub("", text)
        parts = [p.strip() for p in cleaned.split("\n") if p.strip()]
        return parts

    def _detect_section_label(self, paragraph: str) -> Optional[str]:
        normalized = re.sub(r"\s+", " ", paragraph.strip())
        if not normalized:
            return None
        upper = normalized.upper()
        for keyword in self._SECTION_KEYWORDS:
            if keyword in upper:
                return keyword.title()
        if upper.endswith(":"):
            core = upper.rstrip(": ").title()
            if any(ch.isalpha() for ch in core):
                return core
        return None

    def _chunk_document(self, chunk: DocumentChunk) -> Iterable[DocumentChunk]:
        raw_text = self._clean_text(chunk.text)
        if not raw_text:
            return []
        paragraphs = self._paragraphs(raw_text)
        if not paragraphs:
            return []

        chunk_metadata = dict(chunk.metadata)
        doc_hint = self._infer_doc_hint(chunk_metadata)
        if doc_hint:
            chunk_metadata["doc_hint"] = doc_hint
        chunk_metadata.setdefault("parent_id", chunk.id)

        current_section: Optional[str] = None
        section_buffer: List[str] = []
        faq_question: Optional[str] = None

        general_buffer: List[str] = []
        general_len = 0
        size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        idx = 0

        def flush_general():
            nonlocal general_buffer, general_len, idx
            if not general_buffer:
                return []
            text_block = " ".join(general_buffer).strip()
            chunks = []
            if text_block:
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
                if text_block:
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
            faq_match = self._FAQ_START.match(paragraph)
            if faq_match:
                faq_question = faq_match.group(1).strip()
                continue
            if faq_question:
                faq_answer_match = self._FAQ_ANSWER.match(paragraph)
                if faq_answer_match:
                    answer = faq_answer_match.group(1).strip()
                    metadata = dict(chunk_metadata)
                    metadata["chunk_index"] = idx
                    metadata["faq_question"] = faq_question
                    chunk_id = f"{chunk.id}-faq-{idx}"
                    idx += 1
                    yield DocumentChunk(
                        id=chunk_id,
                        text=f"Question: {faq_question}\nRéponse: {answer}",
                        metadata=metadata,
                    )
                    faq_question = None
                    continue

            label = self._detect_section_label(paragraph)
            if label:
                for chunk_obj in flush_section():
                    yield chunk_obj
                current_section = label
                continue

            if current_section:
                section_buffer.append(paragraph)
                continue

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

    def _infer_doc_hint(self, metadata: dict) -> Optional[str]:
        source = str(metadata.get("source", "")).lower()
        if not source:
            return None

        def contains(*keywords: str) -> bool:
            return any(keyword in source for keyword in keywords)

        if source.endswith(".msg") or contains("courriel", "courrier", "email", "mail"):
            return "courriel"
        if contains("planning", "gantt"):
            return "planning"
        if contains("memoire", "mémoire", "presentation", "présentation"):
            return "memoire"
        if contains("dqe", "bordereau", "bpu", "prix"):
            return "dqe"
        if source.endswith(".xlsx") or source.endswith(".xls"):
            return "tableur"
        if source.endswith(".pdf"):
            return "pdf"
        return None


__all__ = ["IngestionPipeline"]
