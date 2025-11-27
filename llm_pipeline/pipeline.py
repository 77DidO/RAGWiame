"""Pipeline RAG basée sur LlamaIndex et vLLM."""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from llama_index.core import QueryBundle, VectorStoreIndex
from llama_index.core.prompts import PromptTemplate
from llama_index.core.vector_stores.types import MetadataFilters
from llama_index.llms.openai_like import OpenAILike
from sentence_transformers import CrossEncoder

from llm_pipeline.elastic_client import bm25_search
from llm_pipeline.query_classification import classify_query_type
from llm_pipeline.prompts import (
    get_default_prompt,
    get_chat_prompt,
    get_fiche_prompt,
    get_chiffres_prompt,
)
from llm_pipeline.context_formatting import format_context
from llm_pipeline.retrieval import hybrid_query as pipeline_hybrid_query, node_id
from llm_pipeline.text_utils import tokenize, citation_key
from llm_pipeline.reranker import CrossEncoderReranker


@dataclass(slots=True)
class RagQueryResult:
    """Résultat enrichi retourné au front-end."""

    answer: str
    citations: List[Mapping[str, str]]
    hits: Optional[List[Dict[str, Any]]] = None


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
        self.reranker = CrossEncoderReranker() if enable_reranker else None

        # Prompts pour les différents types de questions
        self.qa_prompt = PromptTemplate(get_default_prompt())
        self.qa_prompt_fiche = PromptTemplate(get_fiche_prompt())
        self.qa_prompt_chiffres = PromptTemplate(get_chiffres_prompt())
        self.chat_prompt = PromptTemplate(get_chat_prompt())







    def _cross_encoder_rerank(self, nodes: List, question: str) -> List:
        if self.reranker is None:
            return nodes[: self.top_k]
        return self.reranker.rerank(nodes, question, self.top_k)

    def query(
        self,
        question: str,
        filters: MetadataFilters | None = None,
        use_hybrid: bool = False,
        return_hits_only: bool = False,
    ) -> RagQueryResult:
        # Detect vague questions
        vague_patterns = [
            r"^quel\s+(est|sont)\s+(le|la|les)\s+\w+\s*\??$",  # "quel est le montant ?"
            r"^quel\s+(est|sont)\s+\w+\s*\??$",  # "quel est montant ?"
            r"^combien\s*\??$",  # "combien ?"
            r"^où\s*\??$",  # "où ?"
            r"^quoi\s*\??$",  # "quoi ?"
            r"^qui\s*\??$",  # "qui ?"
        ]
        
        question_lower = question.lower().strip()
        print(f"DEBUG: Checking vague question: '{question_lower}'", flush=True)
        question_type = classify_query_type(question_lower)
        print(f"DEBUG: Detected question type: {question_type}", flush=True)
        
        for pattern in vague_patterns:
            if re.match(pattern, question_lower):
                print(f"DEBUG: Matched vague pattern: {pattern}", flush=True)
                return RagQueryResult(
                    answer="Je ne peux pas répondre à cette question car elle manque de contexte. "
                           "Pourriez-vous préciser ce que vous cherchez ? Par exemple : "
                           "\"Quel est le montant du DQE pour le projet Montmirail ?\"",
                    citations=[]
                )

        print(f"DEBUG: No vague pattern matched, proceeding with RAG search", flush=True)

        hits: Optional[List[Dict[str, Any]]] = None
        if use_hybrid:
            nodes, hits = pipeline_hybrid_query(self, question, filters=filters)
            query_text = question
            if return_hits_only:
                return RagQueryResult(answer="", citations=[], hits=hits)
        else:
            retriever = self.index.as_retriever(similarity_top_k=self.initial_top_k, filters=filters)
            query_bundle = QueryBundle(question)
            nodes = retriever.retrieve(query_bundle)
            query_text = query_bundle.query_str

        if not nodes:
            return RagQueryResult(
                answer="Je n'ai pas trouvé de documents pertinents pour répondre à cette question.",
                citations=[]
            )

        reranked = self._cross_encoder_rerank(nodes, query_text)
        
        # Check relevance threshold
        MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.1"))
        
        print(f"DEBUG: Reranked nodes scores:", flush=True)
        for i, node in enumerate(reranked[:5]):
            score = node.score if hasattr(node, 'score') else 'N/A'
            print(f"  [{i+1}] Score: {score} - Source: {node.metadata.get('source', 'unknown')[:50]}", flush=True)
        
        relevant_nodes = [node for node in reranked if hasattr(node, 'score') and node.score >= MIN_RELEVANCE_SCORE]
        
        print(f"DEBUG: {len(relevant_nodes)}/{len(reranked)} nodes passed threshold {MIN_RELEVANCE_SCORE}", flush=True)
        
        if not relevant_nodes:
            return RagQueryResult(
                answer="Je n'ai pas trouvé de documents suffisamment pertinents pour répondre à cette question. "
                "Pourriez-vous reformuler ou ajouter plus de contexte ?",
                citations=[],
                hits=hits,
            )

        context_text, snippet_map = format_context(
            relevant_nodes,
            question,
            max_chunk_chars=self.max_chunk_chars,
            top_k=self.top_k,
        )

        # Choisir le prompt adapté au type de question
        if question_type == "fiche_identite":
            qa_prompt = self.qa_prompt_fiche
        elif question_type == "question_chiffree":
            qa_prompt = self.qa_prompt_chiffres
        else:
            qa_prompt = self.qa_prompt

        response = self.llm.predict(
            qa_prompt,
            context=context_text,
            question=question,
        )
        citations = []
        for node in relevant_nodes:  # Iterate over relevant_nodes, not original nodes
            source = node.metadata.get("source", "inconnu")
            chunk_value = node.metadata.get("chunk_index", node.id_)
            key = citation_key(source, chunk_value)
            citations.append(
                {
                    "source": source,
                    "chunk": chunk_value,
                    "snippet": snippet_map.get(key, ""),
                }
            )
        return RagQueryResult(answer=str(response), citations=citations, hits=hits)

    def chat_only(self, question: str) -> str:
        print(f"DEBUG: chat_only called with question: {question}", flush=True)
        try:
            response = self.llm.predict(self.chat_prompt, question=question)
            print(f"DEBUG: chat_only response: '{response}'", flush=True)
            return str(response)
        except Exception as e:
            print(f"DEBUG: chat_only error: {e}", flush=True)
            return f"Error: {e}"




__all__ = ["RagPipeline", "RagQueryResult"]
