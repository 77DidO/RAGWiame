"""CLI pour construire l'inventaire des documents."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from ingestion.config import IngestionConfig
from ingestion.inventory import InventoryBuilder
from ingestion.cli import _load_config

app = typer.Typer(add_completion=False, help="Construit l'inventaire des documents à partir de l'arborescence.")


@app.command()
def main(
    config_path: Optional[Path] = typer.Option(None, help="Chemin du fichier de configuration ingestion"),
) -> None:
    env_path = os.getenv("INGESTION_CONFIG_PATH")
    if config_path is None and env_path:
        config_path = Path(env_path)

    config = IngestionConfig()
    if config_path:
        config = _load_config(config_path)

    builder = InventoryBuilder(config)
    builder.run()
    typer.echo("Inventaire des documents mis à jour.")


if __name__ == "__main__":
    app()
