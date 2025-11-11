"""Pipeline RAG basée sur LlamaIndex et vLLM."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Mapping

from llama_index.core import QueryBundle, VectorStoreIndex
from llama_index.core.prompts import PromptTemplate
from llama_index.core.vector_stores.types import MetadataFilters
from llama_index.llms.openai_like import OpenAILike
from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank


@dataclass(slots=True)
class RagQueryResult:
    """Résultat enrichi retourné au front-end."""

    answer: str
    citations: List[Mapping[str, str]]


class RagPipeline:
    """Orchestre la récupération des chunks et la génération française."""

    def __init__(
        self,
        index: VectorStoreIndex,
        mistral_endpoint: str = "http://vllm:8000/v1",
        api_key: str = "changeme",
        temperature: float = 0.0,
        model_name: str = "mistral",
        top_k: int = 6,
        max_output_tokens: int = 512,
        timeout_seconds: float = 120.0,
        max_chunk_chars: int = 800,
        max_retries: int = 1,
    ) -> None:
        self.index = index
        self.top_k = top_k
        self.max_chunk_chars = max_chunk_chars
        self.initial_top_k = max(top_k * 3, top_k + 2)
        self.llm = OpenAILike(
            model=model_name,
            api_base=mistral_endpoint,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_output_tokens,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )
        self.reranker = SentenceTransformerRerank(
            model="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            top_n=self.top_k,
        )
        self.qa_template = (
            "Tu es un assistant juridique. Réponds UNIQUEMENT en français et en deux phrases maximum.\n"
            "Appuie-toi sur les extraits fournis, mais reformule-les.\n"
            "Ignore les mentions internes de type «Question : ...» ou «Réponse : ...» présentes dans le contexte : "
            "elles ne sont que des exemples.\n"
            "Si aucune information pertinente n'est disponible, réponds exactement : "
            "\"Je n'ai pas trouvé l'information dans les documents.\".\n\n"
            "Contexte pertinent :\n{context}\n\n"
            "Question : {question}\n"
        )
        self.qa_prompt = PromptTemplate(self.qa_template)

    def _format_context(self, nodes: List) -> str:
        chunks: List[str] = []
        for idx, node in enumerate(nodes, start=1):
            metadata = node.metadata or {}
            source = metadata.get("source", "inconnu")
            page = metadata.get("page")
            header = f"[{idx}] Source: {source}"
            if page is not None:
                header += f" | Page: {page}"
            text = ""
            if hasattr(node, "node") and node.node is not None:
                text = node.node.get_content().strip()
            elif hasattr(node, "text"):
                text = str(node.text).strip()
            if not text:
                continue
            text = re.sub(r"\s+", " ", text)
            if len(text) > self.max_chunk_chars:
                text = text[: self.max_chunk_chars].rstrip() + "…"
            chunks.append(f"{header}\n{text}")
        if not chunks:
            return "Aucun extrait pertinent."
        return "\n\n".join(chunks[: self.top_k])

    def query(self, question: str, filters: MetadataFilters | None = None) -> RagQueryResult:
        retriever = self.index.as_retriever(similarity_top_k=self.initial_top_k, filters=filters)
        query_bundle = QueryBundle(question)
        nodes = retriever.retrieve(query_bundle)
        if nodes and self.reranker is not None:
            nodes = self.reranker.postprocess_nodes(nodes, query_bundle=query_bundle)
        context_text = self._format_context(nodes)
        response = self.llm.predict(
            self.qa_prompt,
            context=context_text,
            question=question,
        )
        citations = [
            {
                "source": node.metadata.get("source", "inconnu"),
                "chunk": node.metadata.get("chunk_index", node.id_),
            }
            for node in nodes
        ]
        return RagQueryResult(answer=str(response), citations=citations)


__all__ = ["RagPipeline", "RagQueryResult"]
