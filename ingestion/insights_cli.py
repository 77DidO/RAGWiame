"""CLI pour extraire les insights métiers (totaux DQE, etc.)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from ingestion.config import IngestionConfig
from ingestion.insights import InsightExtractor
from ingestion.cli import _load_config

app = typer.Typer(add_completion=False, help="Extrait les insights (totaux DQE) et les stocke dans MariaDB.")


@app.command()
def main(
    config_path: Optional[Path] = typer.Option(None, help="Chemin vers la configuration ingestion JSON."),
) -> None:
    env_path = os.getenv("INGESTION_CONFIG_PATH")
    if config_path is None and env_path:
        config_path = Path(env_path)

    config = IngestionConfig()
    if config_path:
        config = _load_config(config_path)

    extractor = InsightExtractor(config)
    extractor.run()
    typer.echo("Extraction des insights terminée.")


if __name__ == "__main__":
    app()
