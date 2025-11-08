"""CLI d'ingestion."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ingestion.config import DEFAULT_CONFIG, IngestionConfig
from ingestion.pipeline import IngestionPipeline


def main(config_path: Optional[Path] = typer.Option(None, help="Chemin du fichier de configuration")) -> None:
    """Exécute la pipeline d'ingestion et renvoie les chunks JSON."""

    config = DEFAULT_CONFIG
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
    return IngestionConfig(**data)


if __name__ == "__main__":
    typer.run(main)
