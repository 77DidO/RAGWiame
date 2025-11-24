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

HYBRID_FUSION = os.getenv("HYBRID_FUSION", "rrf").strip().lower()
HYBRID_WEIGHT_VECTOR = float(os.getenv("HYBRID_WEIGHT_VECTOR", "0.6"))
HYBRID_WEIGHT_KEYWORD = float(os.getenv("HYBRID_WEIGHT_KEYWORD", "0.4"))
HYBRID_BM25_TOP_K = int(os.getenv("HYBRID_BM25_TOP_K", "30"))


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
        self.cross_encoder = None
        self.cross_encoder_batch_size = 8
        if enable_reranker:
            self.cross_encoder = CrossEncoder(
                "amberoad/bert-multilingual-passage-reranking-msmarco",
                default_activation_function=None,
                max_length=512,
            )
        self.qa_template = (
            "Tu es un assistant professionnel et bienveillant.\n"
            "- Réponds à la question en français, de manière claire et structurée.\n"
            "- Utilise des phrases complètes et un ton naturel.\n"
            "- Cite tes sources en utilisant les numéros entre crochets [1], [2], etc. présents dans le contexte.\n"
            "- Si plusieurs informations sont trouvées, présente-les de façon organisée.\n"
            "- Si le contexte ne contient pas l'information demandée, réponds exactement : "
            "\"Je n'ai pas trouvé l'information dans les documents.\"\n\n"
            "Contexte pertinent :\n{context}\n\n"
            "Question : {question}\n"
        )
        self.qa_prompt = PromptTemplate(self.qa_template)
        self.chat_prompt = PromptTemplate(
            "Tu es un assistant francophone polyvalent. Réponds de manière claire et concise.\n"
            "Question : {question}\n"
        )

    def _metadata_filters_to_dict(self, filters: MetadataFilters | None) -> Dict[str, str]:
        if not filters or not getattr(filters, "filters", None):
            return {}
        result: Dict[str, str] = {}
        for f in filters.filters:
            key = getattr(f, "key", None)
            value = getattr(f, "value", None)
            if key and value:
                result[str(key)] = str(value)
        return result

    def _normalize_score_map(self, scores: Dict[str, float]) -> Dict[str, float]:
        if not scores:
            return {}
        values = list(scores.values())
        min_val, max_val = min(values), max(values)
        if math.isclose(max_val, min_val):
            return {k: 1.0 for k in scores.keys()}
        return {k: (v - min_val) / (max_val - min_val) for k, v in scores.items()}

    def _build_bm25_nodes(self, hits: List[Dict[str, any]]) -> List[object]:
        nodes: List[object] = []
        for hit in hits:
            source = hit.get("_source", {}) or {}
            text = str(source.get("content", ""))
            metadata = dict(source)
            metadata.pop("content", None)
            node_id = str(hit.get("_id", ""))
            score = float(hit.get("_score", 0.0))
            # Petit conteneur minimal compatible avec le reste du pipeline
            nodes.append(
                type(
                    "BM25Node",
                    (),
                    {
                        "id_": node_id,
                        "metadata": metadata,
                        "text": text,
                        "score": score,
                    },
                )()
            )
        return nodes

    def _node_id(self, node) -> str:
        if hasattr(node, "node") and node.node is not None and hasattr(node.node, "id_"):
            return str(node.node.id_)
        if hasattr(node, "id_"):
            return str(node.id_)
        if hasattr(node, "node_id"):
            return str(node.node_id)
        return str(getattr(node, "id", ""))

    def _hybrid_query(
        self, question: str, filters: MetadataFilters | None = None
    ) -> Tuple[List, List[Dict[str, Any]]]:
        """Combine Qdrant (dense) et Elasticsearch (BM25) via RRF ou somme pondérée."""
        retriever = self.index.as_retriever(similarity_top_k=self.initial_top_k, filters=filters)
        query_bundle = QueryBundle(question)
        vector_nodes = retriever.retrieve(query_bundle)

        print(f"DEBUG: Vector search returned {len(vector_nodes)} nodes", flush=True)
        for i, node in enumerate(vector_nodes[:5]):
            print(f"  Vector[{i}] ID: {self._node_id(node)} Score: {getattr(node, 'score', 'N/A')} Source: {node.metadata.get('source', 'unknown')}", flush=True)

        filter_dict = self._metadata_filters_to_dict(filters)
        try:
            bm25_hits = bm25_search(
                question, size=max(self.initial_top_k, HYBRID_BM25_TOP_K), filters=filter_dict
            )
        except Exception as exc:  # pragma: no cover - dépend d'Elastic
            print(f"DEBUG: BM25 search failed, fallback to vector only: {exc}", flush=True)
            bm25_hits = []
        
        print(f"DEBUG: BM25 search returned {len(bm25_hits)} hits", flush=True)
        for i, hit in enumerate(bm25_hits[:5]):
            source_val = hit.get('_source', {}).get('source', 'unknown')
            print(f"  BM25[{i}] ID: {hit.get('_id')} Score: {hit.get('_score')} Source: {source_val}", flush=True)

        bm25_nodes = self._build_bm25_nodes(bm25_hits)

        combined_scores: Dict[str, float] = {}
        node_store: Dict[str, object] = {}

        if HYBRID_FUSION == "weighted":
            vec_scores = {self._node_id(node): float(getattr(node, "score", 0.0) or 0.0) for node in vector_nodes}
            kw_scores = {self._node_id(node): float(getattr(node, "score", 0.0) or 0.0) for node in bm25_nodes}

            vec_norm = self._normalize_score_map(vec_scores)
            kw_norm = self._normalize_score_map(kw_scores)

            all_ids = set(vec_norm.keys()) | set(kw_norm.keys())
            for node in vector_nodes:
                node_store[self._node_id(node)] = node
            for node in bm25_nodes:
                node_store.setdefault(self._node_id(node), node)

            for doc_id in all_ids:
                v = vec_norm.get(doc_id, 0.0)
                k = kw_norm.get(doc_id, 0.0)
                combined_scores[doc_id] = HYBRID_WEIGHT_VECTOR * v + HYBRID_WEIGHT_KEYWORD * k
        else:
            # RRF par défaut
            for rank, node in enumerate(vector_nodes):
                doc_id = self._node_id(node)
                node_store[doc_id] = node
                combined_scores[doc_id] = combined_scores.get(doc_id, 0.0) + 1.0 / (rank + 1)
            for rank, node in enumerate(bm25_nodes):
                doc_id = self._node_id(node)
                node_store.setdefault(doc_id, node)
                combined_scores[doc_id] = combined_scores.get(doc_id, 0.0) + 1.0 / (rank + 1)

        sorted_ids = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
        print(f"DEBUG: Fused scores list (len={len(sorted_ids)}): {sorted_ids[:10]}", flush=True)
        
        print(f"DEBUG: Top 5 fused scores (Fusion: {HYBRID_FUSION}):", flush=True)
        for i, (doc_id, score) in enumerate(sorted_ids[:5]):
            node = node_store.get(doc_id)
            source = "unknown"
            if node:
                source = getattr(node, "metadata", {}).get("source", "unknown")
            print(f"  Fused[{i}] ID: {doc_id} Score: {score} Source: {source}", flush=True)
            
        fused_nodes: List[object] = []
        hits: List[Dict[str, any]] = []
        for doc_id, score in sorted_ids[: self.initial_top_k]:
            node = node_store.get(doc_id)
            if not node:
                continue
            setattr(node, "score", score)
            fused_nodes.append(node)
            hit_metadata = getattr(node, "metadata", {}) or {}
            hits.append(
                {
                    "id": doc_id,
                    "score": score,
                    "source": hit_metadata.get("source"),
                    "metadata": hit_metadata,
                    "snippet": self._extract_node_text(node)[:200],
                }
            )
        # Debug: final fused IDs before returning
        print(f"DEBUG: Final fused IDs: {[doc_id for doc_id, _ in sorted_ids[:self.initial_top_k]]}", flush=True)
        return fused_nodes, hits

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
        citation_idx_map: Dict[str, int] = {}
        
        for idx, node in enumerate(nodes, start=1):
            metadata = node.metadata or {}
            source = metadata.get("source", "inconnu")
            page = metadata.get("page")
            
            # Build citation index map
            if source not in citation_idx_map:
                citation_idx_map[source] = len(citation_idx_map) + 1
            
            citation_num = citation_idx_map[source]
            
            # Simplified header with citation number
            header = f"[{citation_num}]"
            if page is not None:
                header += f" (Page {page})"
            
            text = self._extract_node_text(node)
            if not text:
                continue
            snippet = self._select_relevant_text(text, keywords)
            
            # Store snippet for later reference display
            key = self._citation_key(source, metadata.get("chunk_index", node.id_))
            snippet_map[key] = snippet
            
            # Inject source tags like Open WebUI does
            source_tag = f'<source id="{citation_num}">{snippet}</source>'
            chunks.append(f"{header}\n{source_tag}")
            
        if not chunks:
            return "Aucun extrait pertinent.", snippet_map
        return "\n\n".join(chunks[: self.top_k]), snippet_map

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _extract_node_text(self, node) -> str:
        text = ""
        if hasattr(node, "node") and node.node is not None:
            text = node.node.get_content().strip()
        else:
            text = getattr(node, "text", "").strip()
            
        if not text:
            print(f"DEBUG: Empty text for node {node.id_}. Metadata: {node.metadata}", flush=True)
            # Try to fallback to _node_content if available in metadata (hack for Qdrant)
            if hasattr(node, "metadata") and "_node_content" in node.metadata:
                try:
                    import json
                    content = json.loads(node.metadata["_node_content"])
                    text = content.get("text", "").strip()
                    print(f"DEBUG: Recovered text from _node_content: {text[:50]}...", flush=True)
                except Exception as e:
                    print(f"DEBUG: Failed to parse _node_content: {e}", flush=True)
        return text

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
            nodes, hits = self._hybrid_query(question, filters=filters)
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
        MIN_RELEVANCE_SCORE = 0.1  # Lowered to 0.1 to capture more results
        
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

        context_text, snippet_map = self._format_context(relevant_nodes, question)
        response = self.llm.predict(
            self.qa_prompt,
            context=context_text,
            question=question,
        )
        citations = []
        for node in relevant_nodes:  # Iterate over relevant_nodes, not original nodes
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

    @staticmethod
    def _citation_key(source: str, chunk_value) -> str:
        return f"{source}::{chunk_value}"


__all__ = ["RagPipeline", "RagQueryResult"]
