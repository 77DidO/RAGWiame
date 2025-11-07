"""API FastAPI orchestrant le pipeline RAG."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from pydantic import BaseModel
from qdrant_client import QdrantClient

from llm_pipeline.pipeline import RagPipeline

app = FastAPI(title="RAGWiame Gateway", version="0.1.0")

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=os.getenv("KEYCLOAK_URL", "http://keycloak:8080/")
    + "realms/rag/protocol/openid-connect/auth",
    tokenUrl=os.getenv("KEYCLOAK_URL", "http://keycloak:8080/")
    + "realms/rag/protocol/openid-connect/token",
)


class QueryPayload(BaseModel):
    question: str
    service: str
    role: str


class QueryResponse(BaseModel):
    answer: str
    citations: Any


@lru_cache(maxsize=1)
def get_pipeline() -> RagPipeline:
    qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
    vector_store = QdrantVectorStore(client=qdrant_client, collection_name="rag_documents")
    index = VectorStoreIndex.from_vector_store(vector_store)
    pipeline = RagPipeline(index=index, mistral_endpoint=os.getenv("VLLM_ENDPOINT", "http://vllm:8000/v1"))
    return pipeline


def _build_filters(payload: QueryPayload) -> Dict[str, Any]:
    return {
        "service": payload.service,
        "role": payload.role,
    }


@app.post("/rag/query", response_model=QueryResponse)
async def rag_query(payload: QueryPayload, token: str = Depends(oauth2_scheme)) -> QueryResponse:
    if not token:
        raise HTTPException(status_code=401, detail="Token invalide")
    pipeline = get_pipeline()
    result = pipeline.query(payload.question, filters=_build_filters(payload))
    return QueryResponse(answer=result.answer, citations=result.citations)


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
