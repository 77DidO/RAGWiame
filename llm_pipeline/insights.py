"""Accès aux insights métiers (totaux DQE) pour la Gateway."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import mariadb


@dataclass(slots=True)
class InsightRecord:
    source_path: str
    label: str
    value: float
    unit: str | None


class DocumentInsightService:
    TOTAL_KEYWORDS = {"montant", "total", "coût", "cout", "budget", "ht"}

    def __init__(self) -> None:
        self._enabled = bool(os.getenv("ENABLE_INSIGHTS", "true").lower() in {"1", "true", "yes"})
        self.host = os.getenv("MARIADB_HOST", "mariadb")
        self.port = int(os.getenv("MARIADB_PORT", "3306"))
        self.database = os.getenv("MARIADB_DB", "rag")
        self.user = os.getenv("MARIADB_USER", "rag_user")
        self.password = os.getenv("MARIADB_PASSWORD", "")

    def try_answer(self, question: str) -> dict[str, Any] | None:
        if not self._enabled or not self._question_targets_totals(question):
            return None
        rows = self._fetch_top_totals()
        if not rows:
            return None
        answer = self._format_answer(rows)
        citations = [
            {
                "source": row.source_path,
                "chunk": row.label,
                "snippet": self._format_snippet(row),
            }
            for row in rows
        ]
        return {"answer": answer, "citations": citations}

    def _question_targets_totals(self, question: str) -> bool:
        text = question.lower()
        return any(keyword in text for keyword in self.TOTAL_KEYWORDS)

    def _connect(self) -> mariadb.Connection:
        return mariadb.connect(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def _fetch_top_totals(self, limit: int = 3) -> List[InsightRecord]:
        try:
            with self._connect() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    SELECT source_path, insight_label, value, unit
                    FROM document_insights
                    WHERE insight_type = 'dqe_total'
                    ORDER BY value DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
        except mariadb.Error:
            return []
        return [
            InsightRecord(source_path=row[0], label=row[1], value=float(row[2]), unit=row[3])
            for row in rows
        ]

    def _format_answer(self, rows: Sequence[InsightRecord]) -> str:
        parts = []
        for row in rows:
            value = f"{row.value:,.2f}".replace(",", " ").replace(".", ",")
            unit = row.unit or "EUR"
            label = self._shorten_label(row.label)
            parts.append(f"{label} : {value} {unit}")
        joined = "; ".join(parts)
        return f"Montants détectés (DQE) : {joined}"

    def _format_snippet(self, row: InsightRecord) -> str:
        value = f"{row.value:,.2f}".replace(",", " ").replace(".", ",")
        unit = row.unit or "EUR"
        label = self._shorten_label(row.label)
        return f"{label} → {value} {unit}"

    @staticmethod
    def _shorten_label(label: str) -> str:
        simplified = re.sub(r"::ligne_.*$", "", label).replace("::", " / ")
        return simplified or label


__all__ = ["DocumentInsightService"]
