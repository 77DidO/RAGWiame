"""CLI pour classer les documents ingérés et stocker le résultat dans MariaDB."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

import typer

from ingestion.classifier import (
    ClassificationLabel,
    ClassificationRepository,
    LLMClassifier,
    build_document_samples,
    collect_documents,
    DEFAULT_LABELS,
)
from ingestion.cli import _load_config
from ingestion.config import IngestionConfig

app = typer.Typer(add_completion=False, help="Classe chaque document via un LLM et stocke le résultat dans MariaDB.")


def _load_labels(path: Optional[Path]) -> List[ClassificationLabel]:
    if path is None:
        return list(DEFAULT_LABELS)
    data = json.loads(path.read_text(encoding="utf-8"))
    labels: List[ClassificationLabel] = []
    for item in data:
        labels.append(ClassificationLabel(label=item["label"], description=item["description"]))
    return labels


@app.command()
def main(
    config_path: Optional[Path] = typer.Option(
        None, help="Fichier JSON de configuration ingestion (identique au job ingestion)."
    ),
    labels_path: Optional[Path] = typer.Option(
        None, help="Liste JSON des labels personnalisés ({\"label\": str, \"description\": str})."
    ),
    max_chars: int = typer.Option(
        int(os.getenv("CLASSIFIER_MAX_DOC_CHARS", "6000")), help="Nombre maximum de caractères analysés par document."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="N'écrit pas dans MariaDB, affiche uniquement les résultats.",
        is_flag=True,
    ),
    allow_free_labels: bool = typer.Option(
        False,
        "--allow-free-labels",
        help="Autorise le LLM à proposer un label inédit (stocké comme raw_label et éditable ensuite).",
        is_flag=True,
    ),
) -> None:
    env_path = os.getenv("INGESTION_CONFIG_PATH")
    if config_path is None and env_path:
        config_path = Path(env_path)

    config = IngestionConfig()
    if config_path:
        config = _load_config(config_path)

    typer.echo("→ Agrégation des documents…")
    documents = collect_documents(config, max_chars=max_chars)
    if not documents:
        typer.echo("Aucun document détecté, rien à classer.")
        raise typer.Exit(code=0)

    labels = _load_labels(labels_path)
    typer.echo(f"→ {len(documents)} documents à classer | {len(labels)} labels définis.")

    env_allow_free = os.getenv("CLASSIFIER_ALLOW_FREE_LABELS")
    if env_allow_free is not None:
        allow_free_labels = env_allow_free.lower() in {"1", "true", "yes"}

    classifier = LLMClassifier(
        labels=labels,
        api_base=os.getenv("CLASSIFIER_API_BASE", "http://vllm:8000/v1"),
        api_key=os.getenv("CLASSIFIER_API_KEY", "changeme"),
        model_id=os.getenv("CLASSIFIER_MODEL_ID", "mistral"),
        temperature=float(os.getenv("CLASSIFIER_TEMPERATURE", "0.0")),
        max_tokens=int(os.getenv("CLASSIFIER_MAX_TOKENS", "256")),
        timeout=int(os.getenv("CLASSIFIER_TIMEOUT", "90")),
        allow_free_labels=allow_free_labels,
    )
    repository = ClassificationRepository(config.mariadb)
    if not dry_run:
        repository.ensure_schema()

    for sample in documents:
        result = classifier.classify(sample)
        typer.echo(
            f"[raw: {result.raw_label:<20} | normalized: {result.normalized_label:<20}] "
            f"{sample.source} (confidence={result.confidence:.2f})"
        )
        if not dry_run:
            repository.upsert(result)

    typer.echo("Classification terminée.")


if __name__ == "__main__":
    app()
