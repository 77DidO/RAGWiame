"""Pipeline RAG basée sur LlamaIndex et vLLM."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Mapping, Tuple

from llama_index.core import QueryBundle, VectorStoreIndex
from llama_index.core.prompts import PromptTemplate
from llama_index.core.vector_stores.types import MetadataFilters
from llama_index.llms.openai_like import OpenAILike
from sentence_transformers import CrossEncoder


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
        enable_reranker: bool = True,
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
        self.cross_encoder = None
        self.cross_encoder_batch_size = 8
        if enable_reranker:
            self.cross_encoder = CrossEncoder(
                "amberoad/bert-multilingual-passage-reranking-msmarco",
                default_activation_function=None,
                max_length=512,
            )
        self.qa_template = (
            "Tu es un assistant juridique concis.\n"
            "- Réponds UNIQUEMENT à la question posée, en français, en une seule phrase courte.\n"
            "- Ne crée jamais d'autres questions ou listes ; ne reformule pas le contexte sous forme Q/R.\n"
            "- Ignore les mentions internes de type «Question : ...» / «Réponse : ...», titres FAQ ou autres exemples.\n"
            "- Si le contexte ne contient pas l'information demandée, réponds exactement : "
            "\"Je n'ai pas trouvé l'information dans les documents.\"\n"
            "- Cite uniquement la donnée demandée et, si utile, sa source.\n\n"
            "Contexte pertinent :\n{context}\n\n"
            "Question : {question}\n"
        )
        self.qa_prompt = PromptTemplate(self.qa_template)

    def _select_relevant_text(self, text: str, keywords: List[str]) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if keywords:
            matches = [
                sentence
                for sentence in sentences
                if any(keyword in sentence.lower() for keyword in keywords)
            ]
        else:
            matches = []
        snippet = " ".join(matches) if matches else text
        if len(snippet) > self.max_chunk_chars:
            snippet = snippet[: self.max_chunk_chars].rstrip() + "…"
        return snippet

    def _format_context(self, nodes: List, question: str) -> Tuple[str, Dict[str, str]]:
        keywords = [kw for kw in self._tokenize(question) if len(kw) > 2]
        chunks: List[str] = []
        snippet_map: Dict[str, str] = {}
        for idx, node in enumerate(nodes, start=1):
            metadata = node.metadata or {}
            source = metadata.get("source", "inconnu")
            page = metadata.get("page")
            section = metadata.get("section_title") or metadata.get("faq_question")
            header = f"[{idx}] Source: {source}"
            if page is not None:
                header += f" | Page: {page}"
            if section:
                header += f" | Section: {section}"
            text = self._extract_node_text(node)
            if not text:
                continue
            snippet = self._select_relevant_text(text, keywords)
            # Store snippet for later reference display
            key = self._citation_key(source, metadata.get("chunk_index", node.id_))
            snippet_map[key] = snippet
            chunks.append(f"{header}\n{snippet}")
        if not chunks:
            return "Aucun extrait pertinent.", snippet_map
        return "\n\n".join(chunks[: self.top_k]), snippet_map

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _extract_node_text(self, node) -> str:
        if hasattr(node, "node") and node.node is not None:
            return node.node.get_content().strip()
        return getattr(node, "text", "").strip()

    def _cross_encoder_rerank(self, nodes: List, question: str) -> List:
        if not nodes:
            return nodes
        if self.cross_encoder is None:
            return nodes[: self.top_k]
        query_text = question.strip()
        if not query_text:
            return nodes[: self.top_k]
        pairs = []
        filtered_nodes = []
        for node in nodes:
            text = self._extract_node_text(node)
            if not text:
                continue
            filtered_nodes.append(node)
            pairs.append([query_text, text])
        if not pairs:
            return nodes[: self.top_k]
        scores = self.cross_encoder.predict(
            pairs,
            batch_size=self.cross_encoder_batch_size,
            show_progress_bar=False,
        )
        if hasattr(scores, "tolist"):
            scores_seq = scores.tolist()
        else:
            scores_seq = list(scores)
        normalized_scores: List[float] = []
        for value in scores_seq:
            if isinstance(value, (list, tuple)):
                if not value:
                    normalized_scores.append(0.0)
                else:
                    normalized_scores.append(float(value[0]))
            else:
                normalized_scores.append(float(value))
        ranked = sorted(
            zip(normalized_scores, filtered_nodes),
            key=lambda item: item[0],
            reverse=True,
        )
        return [node for _, node in ranked[: self.top_k]]

    def query(self, question: str, filters: MetadataFilters | None = None) -> RagQueryResult:
        retriever = self.index.as_retriever(similarity_top_k=self.initial_top_k, filters=filters)
        query_bundle = QueryBundle(question)
        nodes = retriever.retrieve(query_bundle)
        if nodes:
            nodes = self._cross_encoder_rerank(nodes, query_bundle.query_str)
        context_text, snippet_map = self._format_context(nodes, question)
        response = self.llm.predict(
            self.qa_prompt,
            context=context_text,
            question=question,
        )
        citations = []
        for node in nodes:
            source = node.metadata.get("source", "inconnu")
            chunk_value = node.metadata.get("chunk_index", node.id_)
            key = self._citation_key(source, chunk_value)
            citations.append(
                {
                    "source": source,
                    "chunk": chunk_value,
                    "snippet": snippet_map.get(key, ""),
                }
            )
        return RagQueryResult(answer=str(response), citations=citations)

    @staticmethod
    def _citation_key(source: str, chunk_value) -> str:
        return f"{source}::{chunk_value}"


__all__ = ["RagPipeline", "RagQueryResult"]
