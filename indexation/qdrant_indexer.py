"""Service d'indexation Qdrant orchestré par LlamaIndex."""
from __future__ import annotations

from typing import Iterable, List, Mapping, Sequence

from llama_index.core import Document, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from ingestion.connectors.base import DocumentChunk


class QdrantIndexer:
    """Pousse les chunks dans Qdrant avec un encodeur optimisé français."""

    def __init__(
        self,
        qdrant_url: str = "http://qdrant:6333",
        collection_name: str = "rag_documents",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    ) -> None:
        self.client = QdrantClient(url=qdrant_url)
        vector_store = QdrantVectorStore(client=self.client, collection_name=collection_name)
        embed_model = HuggingFaceEmbedding(model_name=embedding_model)
        self.index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)

    def index_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        documents: List[Document] = [
            Document(
                text=chunk.text,
                metadata=dict(chunk.metadata),
                doc_id=chunk.id,
            )
            for chunk in chunks
        ]
        self.index.insert_nodes(documents)


__all__ = ["QdrantIndexer"]
