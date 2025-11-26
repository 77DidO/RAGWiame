import os
from typing import List, Tuple, Dict, Any
from llama_index.core.vector_stores.types import MetadataFilters
from llama_index.core import QueryBundle

# Import bm25_search directly
try:
    from llm_pipeline.elastic_client import bm25_search
except ImportError:
    bm25_search = None

# Read env vars locally to ensure standalone functionality
HYBRID_FUSION = os.getenv("HYBRID_FUSION", "rrf").strip().lower()
HYBRID_WEIGHT_VECTOR = float(os.getenv("HYBRID_WEIGHT_VECTOR", "0.6"))
HYBRID_WEIGHT_KEYWORD = float(os.getenv("HYBRID_WEIGHT_KEYWORD", "0.4"))
HYBRID_BM25_TOP_K = int(os.getenv("HYBRID_BM25_TOP_K", "30"))


def hybrid_query(pipeline, question: str, filters: MetadataFilters | None = None) -> Tuple[List, List[Dict[str, Any]]]:
    """Perform a hybrid retrieval (dense + BM25) and return nodes + hit metadata.

    *pipeline* is the existing ``RagPipeline`` instance – we need it to access the
    ``index`` and configuration attributes (e.g., ``initial_top_k``).
    """
    # Dense retrieval via the vector store
    retriever = pipeline.index.as_retriever(similarity_top_k=pipeline.initial_top_k, filters=filters)
    query_bundle = QueryBundle(question)
    vector_nodes = retriever.retrieve(query_bundle)

    # Debug output
    print(f"DEBUG: Vector search returned {len(vector_nodes)} nodes", flush=True)

    # BM25 retrieval
    bm25_hits = []
    if bm25_search:
        # We need to convert filters to dict. 
        # If pipeline has the helper, use it; otherwise empty dict.
        filter_dict = {}
        if hasattr(pipeline, "_metadata_filters_to_dict"):
            filter_dict = pipeline._metadata_filters_to_dict(filters)
            
        try:
            bm25_hits = bm25_search(
                question, 
                size=max(pipeline.initial_top_k, HYBRID_BM25_TOP_K), 
                filters=filter_dict
            )
        except Exception as exc:
            print(f"DEBUG: BM25 search failed: {exc}", flush=True)
    
    print(f"DEBUG: BM25 search returned {len(bm25_hits)} hits", flush=True)

    # Convert BM25 hits to nodes
    bm25_nodes = _build_bm25_nodes(bm25_hits)

    # Combine results (RRF or Weighted)
    combined_scores: Dict[str, float] = {}
    node_store: Dict[str, object] = {}

    # Helper to get node ID
    def get_id(node):
        if hasattr(node, "node") and node.node is not None and hasattr(node.node, "id_"):
            return str(node.node.id_)
        if hasattr(node, "id_"):
            return str(node.id_)
        return str(getattr(node, "id", ""))

    if HYBRID_FUSION == "weighted":
        vec_scores = {get_id(node): float(getattr(node, "score", 0.0) or 0.0) for node in vector_nodes}
        kw_scores = {get_id(node): float(getattr(node, "score", 0.0) or 0.0) for node in bm25_nodes}

        # We need a normalization helper. If pipeline has it, use it, else simple local one?
        # For simplicity, let's assume we can access pipeline._normalize_score_map if it exists,
        # or implement a simple one here.
        def normalize(scores):
            if hasattr(pipeline, "_normalize_score_map"):
                return pipeline._normalize_score_map(scores)
            if not scores: return {}
            vals = list(scores.values())
            min_v, max_v = min(vals), max(vals)
            if max_v == min_v: return {k: 1.0 for k in scores}
            return {k: (v - min_v) / (max_v - min_v) for k, v in scores.items()}

        vec_norm = normalize(vec_scores)
        kw_norm = normalize(kw_scores)

        all_ids = set(vec_norm.keys()) | set(kw_norm.keys())
        for node in vector_nodes: node_store[get_id(node)] = node
        for node in bm25_nodes: node_store.setdefault(get_id(node), node)

        for doc_id in all_ids:
            v = vec_norm.get(doc_id, 0.0)
            k = kw_norm.get(doc_id, 0.0)
            combined_scores[doc_id] = HYBRID_WEIGHT_VECTOR * v + HYBRID_WEIGHT_KEYWORD * k
    else:
        # RRF
        for rank, node in enumerate(vector_nodes):
            doc_id = get_id(node)
            node_store[doc_id] = node
            combined_scores[doc_id] = combined_scores.get(doc_id, 0.0) + 1.0 / (rank + 1)
        for rank, node in enumerate(bm25_nodes):
            doc_id = get_id(node)
            node_store.setdefault(doc_id, node)
            combined_scores[doc_id] = combined_scores.get(doc_id, 0.0) + 1.0 / (rank + 1)

    sorted_ids = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
    
    fused_nodes = []
    hits = []
    for doc_id, score in sorted_ids[:pipeline.initial_top_k]:
        node = node_store.get(doc_id)
        if not node: continue
        setattr(node, "score", score)
        fused_nodes.append(node)
        
        # Build hit dict
        metadata = getattr(node, "metadata", {}) or {}
        hits.append({
            "id": doc_id,
            "score": score,
            "source": metadata.get("source"),
            "metadata": metadata,
            "snippet": _extract_node_text(node)[:200]
        })

    return fused_nodes, hits


def _build_bm25_nodes(hits: List[Dict[str, Any]]) -> List[object]:
    """Create minimal node objects from BM25 Elasticsearch hits."""
    nodes: List[object] = []
    for hit in hits:
        source = hit.get("_source", {}) or {}
        text = str(source.get("content", ""))
        metadata = dict(source)
        metadata.pop("content", None)
        node_id = str(hit.get("_id", ""))
        score = float(hit.get("_score", 0.0))
        
        nodes.append(
            type("BM25Node", (), {
                "id_": node_id,
                "metadata": metadata,
                "text": text,
                "score": score,
            })()
        )
    return nodes


def _extract_node_text(node) -> str:
    if hasattr(node, "node") and node.node is not None:
        return node.node.get_content().strip()
    return getattr(node, "text", "").strip()
