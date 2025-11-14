"""Service d'inventaire des documents pour répondre aux questions de type 'quels documents ?'."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List

import mariadb


@dataclass(slots=True)
class InventoryRecord:
    project: str
    folder: str
    filename: str
    relative_path: str
    doc_type: str


class DocumentInventoryService:
    KEYWORDS = {"document", "documents", "fichier", "fichiers", "dossier", "dossiers"}

    def __init__(self) -> None:
        self.enabled = os.getenv("ENABLE_INVENTORY", "true").lower() in {"1", "true", "yes"}
        self.host = os.getenv("MARIADB_HOST", "mariadb")
        self.port = int(os.getenv("MARIADB_PORT", "3306"))
        self.database = os.getenv("MARIADB_DB", "rag")
        self.user = os.getenv("MARIADB_USER", "rag_user")
        self.password = os.getenv("MARIADB_PASSWORD", "")
        self._projects_cache: Dict[str, str] = {}

    def try_answer(self, question: str) -> Dict[str, Any] | None:
        if not self.enabled or not self._looks_like_inventory_question(question):
            return None
        project = self._detect_project(question)
        if not project:
            return None
        records = self._fetch_documents(project)
        if not records:
            return None
        return {
            "answer": self._format_answer(project, records),
            "citations": [
                {
                    "source": f"/data/{record.relative_path}",
                    "chunk": record.filename,
                    "snippet": self._format_snippet(record),
                }
                for record in records
            ],
        }

    def _looks_like_inventory_question(self, question: str) -> bool:
        text = question.lower()
        return any(keyword in text for keyword in self.KEYWORDS)

    def _normalize(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    def _detect_project(self, question: str) -> str | None:
        normalized_question = self._normalize(question)
        if not self._projects_cache:
            self._projects_cache = self._load_projects()
        for project, normalized in self._projects_cache.items():
            if normalized and normalized in normalized_question:
                return project
        # fallback: si un seul projet existe, retourner celui-ci
        if len(self._projects_cache) == 1:
            return next(iter(self._projects_cache.keys()))
        return None

    def _connect(self) -> mariadb.Connection:
        return mariadb.connect(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def _load_projects(self) -> Dict[str, str]:
        projects: Dict[str, str] = {}
        try:
            with self._connect() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT DISTINCT project FROM document_inventory;")
                for (project,) in cursor.fetchall():
                    projects[project] = self._normalize(project)
        except mariadb.Error:
            return {}
        return projects

    def _fetch_documents(self, project: str) -> List[InventoryRecord]:
        try:
            with self._connect() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    SELECT project, folder, filename, relative_path, doc_type
                    FROM document_inventory
                    WHERE project = ?
                    ORDER BY folder, filename
                    """,
                    (project,),
                )
                rows = cursor.fetchall()
        except mariadb.Error:
            return []
        return [
            InventoryRecord(
                project=row[0],
                folder=row[1] or "",
                filename=row[2],
                relative_path=row[3],
                doc_type=row[4] or "",
            )
            for row in rows
        ]

    def _format_answer(self, project: str, records: List[InventoryRecord]) -> str:
        total = len(records)
        items = []
        for record in records:
            folder = record.folder or "(racine)"
            items.append(f"- {folder} / {record.filename}")
        joined = "\n".join(items)
        return f"Documents disponibles pour {project} ({total} fichiers) :\n{joined}"

    @staticmethod
    def _format_snippet(record: InventoryRecord) -> str:
        folder = record.folder or "(racine)"
        kind = (record.doc_type or "document").upper()
        return f"Aperçu indisponible (inventaire). Dossier : {folder} | Type : {kind}"


__all__ = ["DocumentInventoryService"]
