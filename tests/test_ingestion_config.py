"""Tests basiques sur la configuration d'ingestion."""
from ingestion.config import DEFAULT_CONFIG, IngestionConfig


def test_default_language() -> None:
    assert DEFAULT_CONFIG.language == "fr"


def test_chunking_values() -> None:
    config = IngestionConfig()
    assert config.chunk_size > config.chunk_overlap
