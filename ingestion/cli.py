"""CLI d'ingestion."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer

from ingestion.config import ExcelConnectorOptions, IngestionConfig, MariaDBConfig, SourceCredentials
from ingestion.pipeline import IngestionPipeline


def main(
    config_path: Optional[Path] = typer.Option(None, help="Chemin du fichier de configuration"),
) -> None:
    """Exécute la pipeline d'ingestion et renvoie les chunks JSON."""

    env_path = os.getenv("INGESTION_CONFIG_PATH")
    if config_path is None and env_path:
        config_path = Path(env_path)

    config = IngestionConfig()
    if config_path:
        config = _load_config(config_path)
    pipeline = IngestionPipeline(config)
    chunks = [chunk for chunk in pipeline.run()]
    typer.echo(
        json.dumps(
            [{"id": c.id, "text": c.text, "metadata": dict(c.metadata)} for c in chunks],
            ensure_ascii=False,
            indent=2,
        )
    )


def _load_config(path: Path) -> IngestionConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    config = IngestionConfig()

    def _build_credentials(payload: dict | None, current: SourceCredentials) -> SourceCredentials:
        if not payload:
            return current
        return SourceCredentials(
            username=payload.get("username", current.username),
            password=payload.get("password", current.password),
            api_key=payload.get("api_key", current.api_key),
            extra=payload.get("extra", current.extra),
        )

    def _apply_connector(name: str) -> None:
        payload = data.get(name)
        if payload is None:
            return
        connector = getattr(config, name)
        connector.enabled = payload.get("enabled", connector.enabled)
        connector.include_metadata = payload.get("include_metadata", connector.include_metadata)
        connector.recursive = payload.get("recursive", connector.recursive)
        connector.extra = payload.get("extra", connector.extra)
        connector.credentials = _build_credentials(payload.get("credentials"), connector.credentials)
        paths = payload.get("paths")
        if paths is not None:
            connector.paths = [Path(p) for p in paths]

    for key in ("txt", "docx", "pdf", "excel", "mariadb_source"):
        _apply_connector(key)

    if "excel_options" in data:
        options = data["excel_options"]
        config.excel_options = ExcelConnectorOptions(
            load_formulas=options.get("load_formulas", config.excel_options.load_formulas),
            max_rows=options.get("max_rows", config.excel_options.max_rows),
            max_columns=options.get("max_columns", config.excel_options.max_columns),
            sheet_whitelist=options.get("sheet_whitelist", config.excel_options.sheet_whitelist),
        )

    if "mariadb" in data:
        db_cfg = data["mariadb"]
        config.mariadb = MariaDBConfig(
            host=db_cfg.get("host", config.mariadb.host),
            port=db_cfg.get("port", config.mariadb.port),
            database=db_cfg.get("database", config.mariadb.database),
            user=db_cfg.get("user", config.mariadb.user),
            password_env=db_cfg.get("password_env", config.mariadb.password_env),
        )

    config.chunk_size = data.get("chunk_size", config.chunk_size)
    config.chunk_overlap = data.get("chunk_overlap", config.chunk_overlap)
    config.language = data.get("language", config.language)

    return config


if __name__ == "__main__":
    typer.run(main)
