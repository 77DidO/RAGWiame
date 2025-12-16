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
from llm_pipeline.query_router import QueryRouter
from llm_pipeline.prompts import (
    get_default_prompt,
    get_chat_prompt,
    get_fiche_prompt,
    get_chiffres_prompt,
    get_condense_prompt,
    get_phi3_default_prompt,
    get_phi3_fiche_prompt,
    get_phi3_chiffres_prompt,
)
from llm_pipeline.models import ChatMessage
from llm_pipeline.context_formatting import format_context, _extract_node_text
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
        self.query_router = QueryRouter()
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
        if "phi" in model_name.lower():
            print(f"DEBUG: Using Phi-3 prompts for model {model_name}", flush=True)
            self.qa_prompt = PromptTemplate(get_phi3_default_prompt())
            self.qa_prompt_fiche = PromptTemplate(get_phi3_fiche_prompt())
            self.qa_prompt_chiffres = PromptTemplate(get_phi3_chiffres_prompt())
        else:
            print(f"DEBUG: Using Mistral prompts for model {model_name}", flush=True)
            self.qa_prompt = PromptTemplate(get_default_prompt())
            self.qa_prompt_fiche = PromptTemplate(get_fiche_prompt())
            self.qa_prompt_chiffres = PromptTemplate(get_chiffres_prompt())
            
        self.chat_prompt = PromptTemplate(get_chat_prompt())
        self.condense_prompt = PromptTemplate(get_condense_prompt())

    def condense_question(self, chat_history: List[ChatMessage], question: str) -> str:
        """Rewrite a follow-up question to be standalone."""
        if not chat_history:
            return question
            
        history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_history[-4:]]) # Keep last 4 messages context
        
        print(f"DEBUG: Rewriting question '{question}' with history...", flush=True)
        response = self.llm.predict(
            self.condense_prompt,
            chat_history=history_str,
            question=question,
            stop=["Question :", "\nQuestion :", "Question:", "\nQuestion:"]
        )
        rewritten = str(response).strip()
        print(f"DEBUG: Rewritten question: '{rewritten}'", flush=True)
        return rewritten

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
        
        # Passage du LLM au router pour l'extraction intelligente si besoin
        router_result = self.query_router.analyze(question, llm=self.llm)
        
        metadata_filters = self._merge_metadata_filters(filters, router_result.filters)
        print(
            f"DEBUG: QueryRouter intent={router_result.intent} filters={router_result.filters} "
            f"confidence={router_result.confidence:.2f}",
            flush=True,
        )
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
            nodes, hits = pipeline_hybrid_query(self, question, filters=metadata_filters)
            query_text = question
            if return_hits_only:
                return RagQueryResult(answer="", citations=[], hits=hits)
        else:
            retriever = self.index.as_retriever(similarity_top_k=self.initial_top_k, filters=metadata_filters)
            query_bundle = QueryBundle(question)
            nodes = retriever.retrieve(query_bundle)
            query_text = query_bundle.query_str

        if "effectif" in question_lower:
            keyword_nodes = _keyword_search_nodes(["effectif", "effectifs"])
            nodes = _merge_unique_nodes(nodes, keyword_nodes)

        if not nodes:
            return RagQueryResult(
                answer="Je n'ai pas trouvé de documents pertinents pour répondre à cette question.",
                citations=[]
            )

        reranked = self._cross_encoder_rerank(nodes, query_text)

        if question_type == "question_chiffree":
            reranked = _prioritize_numeric_nodes(reranked, nodes, self.top_k)
        
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
            stop=["Question :", "\nQuestion :", "Question:", "\nQuestion:"]
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

    def _build_metadata_filters(self, filters: Mapping[str, str]) -> MetadataFilters | None:
        if not filters:
            return None
        
        from llama_index.core.vector_stores.types import MetadataFilter, FilterOperator
        
        filters_list = []
        for key, value in filters.items():
            if not value:
                continue
            filters_list.append(MetadataFilter(key=key, value=value, operator=FilterOperator.EQ))
            
        if not filters_list:
            return None
            
        return MetadataFilters(filters=filters_list)

    def _merge_metadata_filters(
        self, base: MetadataFilters | None, router_filters: Mapping[str, str]
    ) -> MetadataFilters | None:
        router_metadata = self._build_metadata_filters(router_filters)
        if not base:
            return router_metadata
        if not router_metadata:
            return base

        # Fusion des deux objets MetadataFilters
        # On suppose que base contient une liste de filtres dans base.filters
        base_filters = list(base.filters) if base.filters else []
        new_filters = list(router_metadata.filters) if router_metadata.filters else []
        
        # On évite les doublons (clé/valeur identiques)
        existing_keys = {(f.key, f.value) for f in base_filters}
        
        for f in new_filters:
            if (f.key, f.value) not in existing_keys:
                base_filters.append(f)
                
        return MetadataFilters(filters=base_filters, condition=base.condition)

    def chat_only(self, messages: List[ChatMessage] | str) -> str:
        print(f"DEBUG: chat_only called", flush=True)
        try:
            if isinstance(messages, str):
                # Fallback for simple string (legacy)
                prompt = self.chat_prompt.format(question=messages)
            else:
                # Manual prompt construction from history to ensure control over stop tokens
                # Format:
                # User: ...
                # Assistant: ...
                # ...
                # User: ...
                # Assistant:
                
                # Limit to last 3 exchanges (6 messages) to prevent context overflow
                recent_messages = messages[-6:] if len(messages) > 6 else messages
                
                formatted_history = ""
                for msg in recent_messages:
                    role_label = "User" if msg.role == "user" else "Assistant"
                    formatted_history += f"{role_label}: {msg.content}\n"
                
                # Append the final Assistant prompt
                prompt = f"""Tu es un assistant francophone polyvalent. Réponds de manière claire et concise.

{formatted_history}Assistant:"""

            print(f"DEBUG: chat_only prompt:\n{prompt}", flush=True)
            
            response = self.llm.complete(
                prompt,
                stop=["User:", "user:", "Assistant:", "assistant:", "\nUser", "\nAssistant"]
            )
                
            print(f"DEBUG: chat_only response: '{response}'", flush=True)
            return str(response).strip()
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            print(f"DEBUG: chat_only error ({error_type}): {e}", flush=True)
            traceback.print_exc()
            
            # Check if it's a connection error
            if "connect" in str(e).lower() or "connection" in str(e).lower():
                print(f"ERROR: vLLM connection failed. Is vllm-light running and healthy?", flush=True)
                return "Le modèle est temporairement indisponible. Veuillez réessayer dans quelques secondes."
            
            return f"Error: {e}"


NUMERIC_KEYWORDS = [
    "chiffre d'",
    "chiffres d'",
    "c.a",
    "ca ",
    "effectif",
    "effectifs",
    " m\u20ac",
    " k\u20ac",
    " en m\u20ac",
    " en k\u20ac",
    "montant",
    "total groupe",
]


def _contains_numeric_signal(node) -> tuple[bool, bool]:
    """Detecte la presence d'indications chiffrées dans un chunk."""
    text = _extract_node_text(node).lower()
    if not text:
        return False, False
    contains_keyword = any(keyword in text for keyword in NUMERIC_KEYWORDS)
    contains_effectif = "effectif" in text
    if contains_keyword or ("?" in text and any(ch.isdigit() for ch in text)):
        return True, contains_effectif
    return False, False


def _prioritize_numeric_nodes(primary_nodes: List, candidate_nodes: List, limit: int) -> List:
    """Injecte les nodes contenant des chiffres avant le rerank final."""
    if limit <= 0:
        return primary_nodes

    effectif_nodes: List = []
    numeric_nodes: List = []
    ordered: List = []
    seen = set()

    def push(node, bucket: List) -> None:
        key = node_id(node)
        if key in seen:
            return
        bucket.append(node)
        seen.add(key)

    for node in primary_nodes:
        numeric, has_effectif = _contains_numeric_signal(node)
        if has_effectif:
            push(node, effectif_nodes)
        elif numeric:
            push(node, numeric_nodes)

    for node in candidate_nodes:
        numeric, has_effectif = _contains_numeric_signal(node)
        if has_effectif:
            push(node, effectif_nodes)
        elif numeric:
            push(node, numeric_nodes)

    for node in primary_nodes:
        key = node_id(node)
        if key in seen:
            continue
        ordered.append(node)
        seen.add(key)

    ordered = effectif_nodes + numeric_nodes + ordered
    return ordered[:limit]


def _keyword_search_nodes(queries: List[str], size: int = 5) -> List:
    """Ex‚cute des recherches BM25 cibl‚es et renvoie les nodes correspondants."""
    nodes: List = []
    for query in queries:
        hits = bm25_search(query, size=size) if bm25_search else []
        for hit in hits:
            source = hit.get("_source", {}) or {}
            text = str(source.get("content", ""))
            metadata = dict(source)
            metadata.pop("content", None)
            node_id_value = str(hit.get("_id", ""))
            score = float(hit.get("_score", 0.0))
            nodes.append(
                type(
                    "KeywordNode",
                    (),
                    {
                        "id_": node_id_value,
                        "metadata": metadata,
                        "text": text,
                        "score": score,
                    },
                )()
            )
    return nodes


def _merge_unique_nodes(base_nodes: List, extra_nodes: List) -> List:
    """Fusionne des listes de nodes en ‚vitant les doublons."""
    if not extra_nodes:
        return base_nodes
    seen = {node_id(node) for node in base_nodes}
    for node in extra_nodes:
        key = node_id(node)
        if key in seen:
            continue
        base_nodes.append(node)
        seen.add(key)
    return base_nodes


__all__ = ["RagPipeline", "RagQueryResult"]
