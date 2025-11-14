"""Construction d'un inventaire des documents à partir de l'arborescence."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Set

import mariadb

from ingestion.config import DEFAULT_CONFIG, ConnectorConfig, IngestionConfig, MariaDBConfig


@dataclass(slots=True)
class DocumentEntry:
    project: str
    folder: str
    filename: str
    relative_path: str
    doc_type: str


class DocumentInventoryRepository:
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
                CREATE TABLE IF NOT EXISTS document_inventory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project VARCHAR(255) NOT NULL,
                    folder TEXT,
                    filename VARCHAR(255) NOT NULL,
                    relative_path TEXT NOT NULL,
                    doc_type VARCHAR(32),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uniq_path (relative_path(255))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            connection.commit()

    def replace_all(self, entries: Sequence[DocumentEntry]) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("TRUNCATE TABLE document_inventory;")
            cursor.executemany(
                """
                INSERT INTO document_inventory (project, folder, filename, relative_path, doc_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (entry.project, entry.folder, entry.filename, entry.relative_path, entry.doc_type)
                    for entry in entries
                ],
            )
            connection.commit()


class InventoryBuilder:
    """Scanne les dossiers configurés et construit la table document_inventory."""

    SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".msg"}

    def __init__(self, config: IngestionConfig = DEFAULT_CONFIG) -> None:
        self.config = config
        self.repository = DocumentInventoryRepository(config.mariadb)

    def run(self) -> None:
        self.repository.ensure_schema()
        entries = list(self._scan_paths())
        self.repository.replace_all(entries)

    def _scan_paths(self) -> Iterable[DocumentEntry]:
        for base in self._inventory_roots():
            base_path = Path(base)
            if not base_path.exists():
                continue
            for file_path in base_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if not self._is_supported(file_path):
                    continue
                relative = file_path.relative_to(base_path)
                project = relative.parts[0] if relative.parts else base_path.name
                folder = str(Path(*relative.parts[:-1])) if len(relative.parts) > 1 else ""
                yield DocumentEntry(
                    project=project,
                    folder=folder,
                    filename=file_path.name,
                    relative_path=str(file_path.relative_to(base_path)),
                    doc_type=file_path.suffix.lower().lstrip("."),
                )

    def _inventory_roots(self) -> Set[Path]:
        paths: Set[Path] = set()
        for connector in self._all_connectors():
            for path in connector.paths:
                paths.add(Path(path))
        return paths

    def _all_connectors(self) -> Sequence[ConnectorConfig]:
        return [
            self.config.txt,
            self.config.docx,
            self.config.pdf,
            self.config.excel,
        ]

    def _is_supported(self, path: Path) -> bool:
        if not self.SUPPORTED_EXTENSIONS:
            return True
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS


__all__ = ["InventoryBuilder", "DocumentEntry"]
