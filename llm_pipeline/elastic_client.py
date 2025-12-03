"""Wrapper Elasticsearch pour le pipeline RAG (BM25 + indexation)."""
from __future__ import annotations

import os
from typing import Any, Dict, List

from elasticsearch import Elasticsearch

ELASTIC_HOST = os.getenv("ELASTIC_HOST", "http://localhost:9200")
ELASTIC_INDEX = os.getenv("ELASTIC_INDEX", "rag_documents")

_es_client: Elasticsearch | None = None


def _get_client() -> Elasticsearch | None:
    """Initialise et retourne le client Elasticsearch de manière paresseuse.
    Retourne None si la connexion échoue.
    """
    global _es_client
    if _es_client is None:
        try:
            _es_client = Elasticsearch(hosts=[ELASTIC_HOST])
            _es_client.info()
        except Exception as exc:  # pragma: no cover – only when ES is down
            print(f"DEBUG: Échec de la connexion à Elasticsearch à {ELASTIC_HOST}: {exc}", flush=True)
            _es_client = None
    return _es_client


def index_document(doc_id: str, body: Dict[str, Any]) -> None:
    """Indexer un fragment de document dans Elasticsearch.
    The client is obtained lazily; if the service is unavailable the operation is skipped.
    """
    client = _get_client()
    if client is None:
        print(f"DEBUG: Elasticsearch client not available, skipping indexing of {doc_id}", flush=True)
        return
    try:
        client.index(index=ELASTIC_INDEX, id=doc_id, body=body)
    except Exception as exc:  # pragma: no cover – any error results in skipping indexing
        print(f"DEBUG: Elasticsearch indexing failed for {doc_id}: {exc}", flush=True)
        return


def bm25_search(query: str, size: int = 10, filters: Dict[str, str] | None = None) -> List[Dict[str, Any]]:
    """Effectuer une recherche BM25 par mots‑clés (optionnellement filtrée).
    The Elasticsearch client is created lazily; if the service is unavailable the
    function returns an empty list instead of raising at import time.
    """
    # Configuration améliorée pour le français
    must_clauses: List[Dict[str, Any]] = [{
        "match": {
            "content": {
                "query": query,
                "fuzziness": "AUTO",  # Tolérance aux fautes de frappe
                "operator": "or",  # Au moins un mot doit matcher
                "minimum_should_match": "50%"  # Au moins 50% des mots doivent matcher
            }
        }
    }]
    
    if filters:
        for key, value in filters.items():
            if value:
                must_clauses.append({"term": {key: value}})
    
    try:
        client = _get_client()
        if client is None:
            print("DEBUG: Elasticsearch client not available, returning empty list", flush=True)
            return []
        resp = client.search(
            index=ELASTIC_INDEX,
            body={
                "size": size,
                "query": {"bool": {"must": must_clauses}},
            },
        )
        return resp.get("hits", {}).get("hits", [])
    except Exception as exc:  # pragma: no cover – any error results in empty hits
        print(f"DEBUG: BM25 search failed ({exc}), returning empty list", flush=True)
        return []


__all__ = ["index_document", "bm25_search", "ELASTIC_HOST", "ELASTIC_INDEX"]
