"""Pipeline RAG basée sur LlamaIndex et vLLM."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Sequence

from llama_index.core import QueryBundle, VectorStoreIndex
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.llms.openai_like import OpenAILike


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
        temperature: float = 0.3,
    ) -> None:
        self.index = index
        self.llm = OpenAILike(
            model="mistral",
            api_base=mistral_endpoint,
            api_key=api_key,
            temperature=temperature,
        )
        self.response_synthesizer = CompactAndRefine(response_mode="tree_summarize", verbose=False)

    def query(self, question: str, filters: Mapping[str, object]) -> RagQueryResult:
        retriever = self.index.as_retriever(similarity_top_k=6, filters=filters)
        nodes = retriever.retrieve(QueryBundle(question))
        response = self.response_synthesizer.synthesize(
            query=QueryBundle(question),
            nodes=nodes,
            llm=self.llm,
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
