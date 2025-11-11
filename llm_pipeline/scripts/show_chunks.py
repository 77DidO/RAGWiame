"""Inspecte les chunks renvoyés par LlamaIndex pour une question donnée."""
from __future__ import annotations

import os
import sys
from typing import Optional

from llama_index.core import QueryBundle

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm_pipeline.api import _build_index  # noqa: E402


def show_chunks(question: str, top_k: int = 5) -> None:
    index = _build_index()
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(QueryBundle(question))
    print(f"Question: {question} | Chunks: {len(nodes)}")
    for idx, node in enumerate(nodes, 1):
        metadata = node.metadata or {}
        section = metadata.get("section_label") or metadata.get("section_title") or metadata.get("faq_question")
        page = metadata.get("page")
        print(f"\n--- Chunk #{idx} | page {page} | section {section}")
        text = node.node.get_content() if hasattr(node, "node") and node.node is not None else getattr(node, "text", "")
        print(text)


if __name__ == "__main__":
    question = os.environ.get("SHOW_CHUNKS_QUESTION", "Quel est le nom du vendeur ?")
    top_k = int(os.environ.get("SHOW_CHUNKS_TOP_K", "5"))
    show_chunks(question, top_k)
