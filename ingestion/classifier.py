"""Classification de documents via un LLM OpenAI-like."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import mariadb
import requests

from ingestion.config import IngestionConfig, MariaDBConfig
from ingestion.connectors.base import DocumentChunk
from ingestion.pipeline import IngestionPipeline

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ClassificationLabel:
    label: str
    description: str


@dataclass(slots=True)
class DocumentSample:
    source: str
    text: str
    metadata: Dict[str, str]
    doc_hint: str | None = None


@dataclass(slots=True)
class ClassificationResult:
    source: str
    source_hash: str
    raw_label: str
    normalized_label: str
    confidence: float
    rationale: str
    model: str
    raw_response: Dict


DEFAULT_LABELS: Sequence[ClassificationLabel] = (
    ClassificationLabel(
        label="document_marche",
        description="Règlement de consultation, CCAP, CCTP, avis ou pièces administratives définissant les règles du marché.",
    ),
    ClassificationLabel(
        label="dqe_bordereau",
        description="Détail quantitatif estimatif, bordereau de prix ou tout document majoritairement chiffré (PDF/XLSX).",
    ),
    ClassificationLabel(
        label="memoire_technique",
        description="Mémoire technique, présentation d'entreprise, méthode, planning ou moyens humains/matériels.",
    ),
    ClassificationLabel(
        label="courriel_consultation",
        description="Courrier électronique ou lettre courte annonçant ou accompagnant l'offre.",
    ),
    ClassificationLabel(
        label="etude_plan",
        description="Études techniques, plans, analyses terrain ou documents graphiques.",
    ),
)


def build_document_samples(chunks: Iterable[DocumentChunk], max_chars: int) -> List[DocumentSample]:
    """Regroupe les chunks par source pour constituer un texte représentatif par document."""
    grouped: Dict[str, Dict[str, List[str] | Dict[str, str]]] = {}
    hint_map: Dict[str, List[str]] = {}
    for chunk in chunks:
        source = chunk.metadata.get("source") or chunk.id
        entry = grouped.setdefault(source, {"texts": [], "metadata": {}})
        entry["texts"].append(chunk.text)
        entry["metadata"] = {k: str(v) for k, v in chunk.metadata.items()}
        hint = chunk.metadata.get("doc_hint")
        if hint:
            hint_map.setdefault(source, []).append(str(hint))

    samples: List[DocumentSample] = []
    for source, payload in grouped.items():
        doc_hint = _select_doc_hint(hint_map.get(source, []))
        texts = payload["texts"]  # type: ignore[assignment]
        text = _summarize_text(texts, doc_hint, max_chars)
        metadata = payload["metadata"]  # type: ignore[assignment]
        if doc_hint:
            metadata = dict(metadata)
            metadata["doc_hint"] = doc_hint
        samples.append(DocumentSample(source=source, text=text, metadata=metadata, doc_hint=doc_hint))
    samples.sort(key=lambda sample: sample.source)
    return samples


def _select_doc_hint(hints: List[str] | None) -> str | None:
    if not hints:
        return None
    counts: Dict[str, int] = {}
    for hint in hints:
        if hint:
            counts[hint] = counts.get(hint, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]


def _summarize_text(texts: List[str], doc_hint: str | None, max_chars: int) -> str:
    joined = " ".join(texts)
    if doc_hint in {"dqe", "tableur"}:
        lines = []
        for text in texts:
            for line in text.splitlines():
                if _looks_like_table(line):
                    lines.append(line.strip())
                if len(" ".join(lines)) >= max_chars:
                    break
            if len(" ".join(lines)) >= max_chars:
                break
        snippet = " ".join(lines).strip() or joined
    elif doc_hint == "courriel":
        first_block = []
        for text in texts:
            first_block.extend(text.splitlines()[:10])
            if len("\n".join(first_block)) >= max_chars:
                break
        snippet = "\n".join(first_block).strip() or joined
    else:
        snippet = joined
    snippet = re.sub(r"\s+", " ", snippet).strip()
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rsplit(" ", 1)[0].rstrip() + " …"
    return snippet


def _looks_like_table(line: str) -> bool:
    tokens = [tok for tok in re.split(r"[;,\t]", line) if tok.strip()]
    has_numbers = any(re.search(r"\d", tok) for tok in tokens)
    return has_numbers and len(tokens) >= 2


class LLMClassifier:
    """Interroge un endpoint OpenAI-like pour classer les documents."""

    def __init__(
        self,
        labels: Sequence[ClassificationLabel],
        api_base: str,
        api_key: str,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: int = 256,
        timeout: int = 90,
        allow_free_labels: bool = False,
    ) -> None:
        self.labels = labels
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.allow_free_labels = allow_free_labels

    def classify(self, sample: DocumentSample) -> ClassificationResult:
        prompt = self._build_prompt(sample)
        body = {
            "model": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu es un expert en appels d'offres. "
                        "Classe chaque document dans UNE SEULE catégorie parmi la liste fournie. "
                        "Réponds en JSON strict sous la forme "
                        '{"label": "...", "confidence": 0.0-1.0, "rationale": "..."}'
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"].strip()
        parsed = self._parse_model_output(content)
        source_hash = hashlib.sha256(sample.source.encode("utf-8")).hexdigest()
        raw_label = parsed["label"]
        normalized_label = self._normalize_with_hint(raw_label, sample.doc_hint)
        return ClassificationResult(
            source=sample.source,
            source_hash=source_hash,
            raw_label=raw_label,
            normalized_label=normalized_label,
            confidence=float(parsed.get("confidence", 0.0)),
            rationale=parsed.get("rationale", ""),
            model=self.model_id,
            raw_response={"model_output": content, "payload": payload},
        )

    def _build_prompt(self, sample: DocumentSample) -> str:
        labels_text = "\n".join(f"- {label.label}: {label.description}" for label in self.labels)
        metadata = "\n".join(f"{key}: {value}" for key, value in sample.metadata.items())
        hint_line = f"Indice automatique: {sample.doc_hint or 'aucun'}"
        if self.allow_free_labels:
            instruction = (
                "Propose UN label clair et court (kebab-case ou snake_case) décrivant le type du document. "
                "Inspire-toi éventuellement de la liste suivante mais crée un nouveau label si nécessaire."
            )
        else:
            instruction = (
                "Choisis exactement UN label dans la liste suivante, celui qui correspond le mieux au document."
            )
        return (
            f"{instruction}\n{labels_text}\n\n"
            f"{hint_line}\n"
            f"Métadonnées document :\n{metadata}\n\n"
            f"Contenu (tronqué à {len(sample.text)} caractères) :\n{sample.text}"
        )

    def _parse_model_output(self, content: str) -> Dict[str, str]:
        if self.allow_free_labels:
            text = content.strip()
            return {
                "label": self._extract_label_from_text(text),
                "confidence": self._extract_confidence_from_text(text),
                "rationale": text,
            }
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            cleaned = content.strip().strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                text = cleaned.strip()
                label = self._extract_label_from_text(text)
                return {"label": label, "confidence": 0.0, "rationale": text}

    def _extract_label_from_text(self, text: str) -> str:
        match = re.search(r"(?:label|réponse|response)\s*[:=]\s*([A-Za-z0-9_\-]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        first_line = text.splitlines()[0].strip()
        first_line = re.sub(r"^[A-Za-zÀ-ÿ ]*[:：]\s*", "", first_line)
        token = first_line.split()[0] if first_line else "unknown"
        return token or "unknown"

    def _extract_confidence_from_text(self, text: str) -> float:
        match = re.search(r"(?:confiance|confidence)\s*[:=]\s*([0-9]+(?:[\.,][0-9]+)?)", text, flags=re.IGNORECASE)
        if not match:
            return 0.0
        raw = match.group(1).replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            return 0.0
        if value > 1.0:
            value = value / 100.0
        return max(0.0, min(1.0, value))

    def _normalize_with_hint(self, raw_label: str, doc_hint: str | None) -> str:
        if not doc_hint:
            return raw_label
        hint = doc_hint.lower()
        mapping = {
            "dqe": "dqe_bordereau",
            "tableur": "dqe_bordereau",
            "courriel": "courriel_consultation",
            "memoire": "memoire_technique",
            "planning": "etude_plan",
        }
        return mapping.get(hint, raw_label)


class ClassificationRepository:
    """Persistance des classifications dans MariaDB."""

    def __init__(self, config: MariaDBConfig) -> None:
        self.config = config

    def _connect(self) -> mariadb.Connection:
        password = os.getenv(self.config.password_env)
        if not password:
            raise RuntimeError(f"Variable d'environnement {self.config.password_env} manquante pour MariaDB.")
        return mariadb.connect(
            user=self.config.user,
            password=password,
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
        )

    def ensure_schema(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS document_classification (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    source_hash CHAR(64) NOT NULL UNIQUE,
                    source_path TEXT NOT NULL,
                    raw_label VARCHAR(255) NOT NULL,
                    document_label VARCHAR(128) NOT NULL,
                    confidence FLOAT NOT NULL,
                    rationale MEDIUMTEXT,
                    model VARCHAR(64) NOT NULL,
                    raw_response LONGTEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            connection.commit()
            self._ensure_additional_columns(connection)

    def _ensure_additional_columns(self, connection: mariadb.Connection) -> None:
        cursor = connection.cursor()
        db_name = self.config.database
        cursor.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema=? AND table_name='document_classification'
            """,
            (db_name,),
        )
        existing = {row[0] for row in cursor.fetchall()}
        alterations = []
        if "raw_label" not in existing:
            alterations.append("ADD COLUMN raw_label VARCHAR(255) NULL AFTER source_path")
        if "document_label" not in existing:
            alterations.append("ADD COLUMN document_label VARCHAR(255) NULL AFTER raw_label")
        if alterations:
            cursor.execute(f"ALTER TABLE document_classification {', '.join(alterations)};")
        # Initialise les nouveaux champs si nécessaire
        cursor.execute(
            """
            UPDATE document_classification
            SET raw_label = document_label
            WHERE (raw_label IS NULL OR raw_label = '') AND document_label IS NOT NULL
            """
        )
        cursor.execute(
            """
            UPDATE document_classification
            SET document_label = raw_label
            WHERE (document_label IS NULL OR document_label = '') AND raw_label IS NOT NULL
            """
        )
        connection.commit()

    def upsert(self, result: ClassificationResult) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO document_classification
                    (source_hash, source_path, raw_label, document_label, confidence, rationale, model, raw_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE
                    raw_label=VALUES(raw_label),
                    document_label=VALUES(document_label),
                    confidence=VALUES(confidence),
                    rationale=VALUES(rationale),
                    model=VALUES(model),
                    raw_response=VALUES(raw_response),
                    updated_at=CURRENT_TIMESTAMP;
                """,
                (
                    result.source_hash,
                    result.source,
                    result.raw_label,
                    result.normalized_label,
                    result.confidence,
                    result.rationale,
                    result.model,
                    json.dumps(result.raw_response, ensure_ascii=False),
                ),
            )
            connection.commit()


def collect_documents(config: IngestionConfig, max_chars: int) -> List[DocumentSample]:
    """Helper prêt à l'emploi pour la CLI."""
    pipeline = IngestionPipeline(config)
    return build_document_samples(pipeline.run(), max_chars=max_chars)
