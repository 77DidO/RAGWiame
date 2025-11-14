"""Extraction d'insights métiers (totaux DQE, etc.)."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import mariadb
import pandas as pd

from ingestion.config import IngestionConfig, DEFAULT_CONFIG, MariaDBConfig

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DocumentInsight:
    source_path: str
    insight_type: str
    label: str
    value: float
    unit: str | None = None
    metadata: Dict[str, str] | None = None


class DocumentInsightsRepository:
    def __init__(self, config: MariaDBConfig) -> None:
        self.config = config

    def _connect(self) -> mariadb.Connection:
        password = os.getenv(self.config.password_env)
        if not password:
            raise RuntimeError(f"Variable d'environnement {self.config.password_env} manquante.")
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
                CREATE TABLE IF NOT EXISTS document_insights (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    insight_type VARCHAR(64) NOT NULL,
                    insight_label VARCHAR(255) NOT NULL,
                    value DOUBLE NOT NULL,
                    unit VARCHAR(32),
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_insight (source_path(255), insight_type, insight_label)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            connection.commit()

    def upsert_many(self, insights: Sequence[DocumentInsight]) -> None:
        if not insights:
            return
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.executemany(
                """
                INSERT INTO document_insights
                    (source_path, insight_type, insight_label, value, unit, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE
                    value=VALUES(value),
                    unit=VALUES(unit),
                    metadata=VALUES(metadata),
                    updated_at=CURRENT_TIMESTAMP;
                """,
                [
                    (
                        insight.source_path,
                        insight.insight_type,
                        insight.label,
                        insight.value,
                        insight.unit,
                        json.dumps(insight.metadata or {}, ensure_ascii=False),
                    )
                    for insight in insights
                ],
            )
            connection.commit()


class DQETotalExtractor:
    """Parcourt les DQE (XLSX) et extrait les lignes TOTAL."""

    def extract(self, path: Path) -> List[DocumentInsight]:
        records: List[DocumentInsight] = []
        try:
            sheets = pd.read_excel(path, sheet_name=None, header=None, engine="openpyxl")
        except Exception as exc:  # pragma: no cover - dépend des fichiers fournis
            LOGGER.warning("Impossible de lire %s (%s)", path, exc)
            return records

        for sheet_name, df in sheets.items():
            records.extend(self._extract_from_sheet(path, sheet_name, df))
        return records

    def _extract_from_sheet(self, path: Path, sheet_name: str, df: pd.DataFrame) -> List[DocumentInsight]:
        insights: List[DocumentInsight] = []
        for row_idx, row in df.iterrows():
            labels = [str(cell).strip().lower() for cell in row if pd.notna(cell)]
            if not labels:
                continue
            if any("total" in label for label in labels):
                numeric_values = [
                    float(cell)
                    for cell in row
                    if isinstance(cell, (int, float)) and pd.notna(cell) and abs(cell) > 0
                ]
                if not numeric_values:
                    continue
                value = max(numeric_values, key=abs)
                insights.append(
                    DocumentInsight(
                        source_path=str(path),
                        insight_type="dqe_total",
                        label=f"{Path(path).name}::{sheet_name}::ligne_{row_idx}",
                        value=value,
                        unit="EUR",
                        metadata={
                            "sheet": sheet_name,
                            "row_index": str(row_idx),
                        },
                    )
                )
        return insights


class InsightExtractor:
    """Coordonne l'extraction des insights."""

    def __init__(self, config: IngestionConfig = DEFAULT_CONFIG) -> None:
        self.config = config
        self.repository = DocumentInsightsRepository(config.mariadb)
        self.dqe_extractor = DQETotalExtractor()

    def run(self) -> None:
        self.repository.ensure_schema()
        excel_paths = self._discover_excel_paths()
        LOGGER.info("Extraction des totaux DQE sur %s fichiers…", len(excel_paths))
        for path in excel_paths:
            insights = self.dqe_extractor.extract(path)
            if insights:
                self.repository.upsert_many(insights)
                LOGGER.info("→ %s : %s insights enregistrés", path.name, len(insights))

    def _discover_excel_paths(self) -> List[Path]:
        paths: List[Path] = []
        for root in self.config.excel.paths:
            path_obj = Path(root)
            if not path_obj.exists():
                continue
            iterator: Iterable[Path]
            if self.config.excel.recursive:
                iterator = path_obj.rglob("*.xlsx")
            else:
                iterator = path_obj.glob("*.xlsx")
            for file_path in iterator:
                paths.append(file_path)
        return paths


__all__ = ["InsightExtractor", "DocumentInsight"]
