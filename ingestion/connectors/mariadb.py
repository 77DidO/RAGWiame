"""Connecteur MariaDB pour la récupération de métadonnées."""
from __future__ import annotations

import os
from typing import Iterable

import mariadb

from ingestion.config import ConnectorConfig, MariaDBConfig
from ingestion.connectors.base import BaseConnector, DocumentChunk


class MariaDBConnector(BaseConnector):
    """Récupère des enregistrements textuels dans MariaDB."""

    document_type = "mariadb"

    def __init__(self, config: ConnectorConfig, db_config: MariaDBConfig) -> None:
        super().__init__(config)
        self.db_config = db_config

    def discover(self) -> Iterable[str]:  # type: ignore[override]
        query = self.config.extra.get("query")
        if not query:
            raise ValueError("La requête SQL doit être fournie via config.extra['query']")
        yield query

    def load(self, query: str) -> Iterable[DocumentChunk]:  # type: ignore[override]
        password = os.getenv(self.db_config.password_env)
        if not password:
            raise RuntimeError(f"Variable d'environnement {self.db_config.password_env} manquante")
        connection = mariadb.connect(
            user=self.db_config.user,
            password=password,
            host=self.db_config.host,
            port=self.db_config.port,
            database=self.db_config.database,
        )
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            for index, row in enumerate(cursor.fetchall()):
                text = "\n".join(f"{key}: {value}" for key, value in row.items())
                metadata = {
                    "source": f"mariadb://{self.db_config.host}/{self.db_config.database}",
                    "row": index,
                    "document_type": self.document_type,
                }
                yield DocumentChunk(id=f"mariadb-{index}", text=text, metadata=metadata)
        finally:
            connection.close()


__all__ = ["MariaDBConnector"]
