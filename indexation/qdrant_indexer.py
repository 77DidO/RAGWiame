"""Service d'indexation Qdrant orchestré par LlamaIndex."""
from __future__ import annotations

print("DEBUG: qdrant_indexer script early start", flush=True)

import os
from pathlib import Path
from typing import List, Optional, Sequence

import typer
from ingestion.cli import _load_config as load_ingestion_config
from ingestion.config import IngestionConfig
from ingestion.pipeline import IngestionPipeline
from llm_pipeline.elastic_client import index_document as es_index_document
from llama_index.core import Document, StorageContext, VectorStoreIndex
# Import corrigé pour HuggingFaceEmbedding
try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
except ImportError:
    try:
        from llama_index.legacy.embeddings.huggingface import HuggingFaceEmbedding
    except ImportError:
        # Fallback pour les versions plus récentes
        from llama_index.core.embeddings import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient


class QdrantIndexer:
    """Pousse les chunks dans Qdrant avec un encodeur optimisé français."""

    def __init__(
        self,
        qdrant_url: str = "http://qdrant:6333",
        collection_name: str = "rag_documents",
        embedding_model: Optional[str] = None,
    ) -> None:
        model_name = embedding_model or os.getenv(
            "HF_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.client = QdrantClient(url=qdrant_url)
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            vector_name="text-dense",
        )
        self.embed_model = HuggingFaceEmbedding(model_name=model_name)

    def index_documents(self, documents: Sequence[Document]) -> None:
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        VectorStoreIndex.from_documents(
            list(documents),
            storage_context=storage_context,
            embed_model=self.embed_model,
        )


def _build_documents(chunks: Sequence) -> List[Document]:
    return [
        Document(text=chunk.text, metadata=dict(chunk.metadata), doc_id=chunk.id)
        for chunk in chunks
        if chunk.text.strip()
    ]


def _build_es_body(chunk) -> dict:
    """Prépare le document Elasticsearch avec le texte et les métadonnées utiles."""
    metadata = dict(chunk.metadata)
    metadata.pop("content", None)
    body = {
        "content": chunk.text,
    }
    for key in ("source", "service", "role", "doc_hint", "chunk_index", "page"):
        if key in metadata:
            body[key] = metadata[key]
    # On conserve le reste des métadonnées pour faciliter le debug (si JSON-serialisable)
    for key, value in metadata.items():
        if key in body:
            continue
        try:
            body[key] = value
        except Exception:
            body[key] = str(value)
    return body


app = typer.Typer(add_completion=False)


@app.command()
def main(
    config_path: Optional[Path] = typer.Option(None, help="Chemin d'un fichier d'ingestion JSON"),
    qdrant_url: str = typer.Option("http://qdrant:6333", help="URL du service Qdrant"),
    collection_name: str = typer.Option("rag_documents", help="Nom de la collection Qdrant"),
    embedding_model: Optional[str] = typer.Option(None, help="Modèle d'embedding HuggingFace"),
) -> None:
    """Exécute l'ingestion puis indexe les documents dans Qdrant."""
    print("DEBUG: qdrant_indexer script started", flush=True)
    env_path = os.getenv("INGESTION_CONFIG_PATH")
    if config_path is None and env_path:
        config_path = Path(env_path)

    ingestion_config = IngestionConfig()
    if config_path:
        ingestion_config = load_ingestion_config(config_path)

    pipeline = IngestionPipeline(ingestion_config)
    chunks = list(pipeline.run())
    if not chunks:
        typer.echo("Aucun document détecté durant l'ingestion. Vérifiez la configuration.")
        raise typer.Exit(code=0)

    # Indexation Qdrant
    documents = _build_documents(chunks)
    indexer = QdrantIndexer(
        qdrant_url=qdrant_url, collection_name=collection_name, embedding_model=embedding_model
    )
    indexer.index_documents(documents)
    typer.echo(f"{len(documents)} documents indexés dans la collection '{collection_name}'.")

    # Indexation Elasticsearch (BM25)
    failures = 0
    for chunk in chunks:
        body = _build_es_body(chunk)
        try:
            print(f"DEBUG: Indexing chunk {chunk.id} into Elasticsearch", flush=True)
            es_index_document(str(chunk.id), body=body)
            print(f"DEBUG: Successfully indexed chunk {chunk.id}", flush=True)
        except Exception as exc:  # pragma: no cover - dépend de la dispo ES
            failures += 1
            typer.echo(f"[AVERTISSEMENT] Indexation Elasticsearch échouée pour {chunk.id}: {exc}")

    if failures:
        typer.echo(f"{failures} fragments n'ont pas pu être indexés dans Elasticsearch.")
    else:
        typer.echo("Indexation Elasticsearch terminée.")


if __name__ == "__main__":
    app()
