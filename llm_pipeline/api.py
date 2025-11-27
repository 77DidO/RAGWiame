"""API FastAPI orchestrant le pipeline RAG et la sélection dynamique des modèles."""
from __future__ import annotations

import mimetypes
import time
import uuid
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import FileResponse
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from llm_pipeline.pipeline import RagPipeline
from llm_pipeline.insights import DocumentInsightService
from llm_pipeline.inventory import DocumentInventoryService
from llm_pipeline.config import (
    RAG_MODEL_ID,
    MODEL_ENDPOINTS,
    EMBEDDING_MODEL,
    DEFAULT_TOP_K,
    SMALL_MODEL_TOP_K,
    SMALL_MODEL_ID,
    SMALL_MODEL_ENABLED,
    LLM_TIMEOUT,
    LLM_TEMPERATURE,
    MAX_CHUNK_CHARS,
    LLM_MAX_RETRIES,
    ENABLE_RERANKER,
    DATA_ROOT,
    BYPASS_AUTH,
    KEYCLOAK_URL,
    QDRANT_URL,
)
from llm_pipeline.models import (
    QueryPayload,
    QueryResponse,
    ModelInfo,
    ChatMessage,
    ChatRequest,
    ChatChoice,
    ChatCompletionResponse,
)
from llm_pipeline.request_utils import (
    build_filters,
    check_vague_question,
    ensure_token,
    normalize_bool,
    resolve_rag_mode,
)
from llm_pipeline.citation_formatter import convert_citations_to_openwebui_format

app = FastAPI(title="RAGWiame Gateway", version="0.1.0")
insight_service = DocumentInsightService()
inventory_service = DocumentInventoryService()

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=KEYCLOAK_URL + "realms/rag/protocol/openid-connect/auth",
    tokenUrl=KEYCLOAK_URL + "realms/rag/protocol/openid-connect/token",
    auto_error=not BYPASS_AUTH,
)


@lru_cache(maxsize=1)
def _build_index() -> VectorStoreIndex:
    qdrant_client = QdrantClient(url=QDRANT_URL)
    vector_store = QdrantVectorStore(
        client=qdrant_client, 
        collection_name="rag_documents",
        enable_hybrid=False,
    )
    embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)
    return VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)


@lru_cache(maxsize=4)
def get_pipeline(model_id: str) -> RagPipeline:
    endpoint = MODEL_ENDPOINTS.get(model_id)
    if endpoint is None:
        raise HTTPException(status_code=400, detail=f"Modèle {model_id} non enregistré côté Gateway")
    top_k = DEFAULT_TOP_K
    if SMALL_MODEL_ENABLED and model_id == SMALL_MODEL_ID:
        top_k = SMALL_MODEL_TOP_K
    return RagPipeline(
        index=_build_index(),
        mistral_endpoint=endpoint,
        api_key="changeme",
        model_name=model_id,
        top_k=top_k,
        timeout_seconds=LLM_TIMEOUT,
        temperature=LLM_TEMPERATURE,
        max_chunk_chars=MAX_CHUNK_CHARS,
        max_retries=LLM_MAX_RETRIES,
        enable_reranker=ENABLE_RERANKER,
    )


def _execute_query(
    payload: QueryPayload, model_id: str, use_hybrid: bool = False, return_hits_only: bool = False
) -> QueryResponse:
    if return_hits_only:
        payload.use_rag = True
    question_text, use_rag = resolve_rag_mode(payload.question, payload.use_rag)
    if use_rag is False and not return_hits_only:
        return _llm_only_answer(question_text, model_id)
    payload.question = question_text
    
    # 1. Check for vague questions immediately
    vague_response = check_vague_question(payload.question)
    if vague_response:
        return vague_response

    # 2. Try specialized services
    if not return_hits_only:
        inventory = inventory_service.try_answer(payload.question)
        if inventory:
            return QueryResponse(answer=inventory["answer"], citations=inventory["citations"])
        insight = insight_service.try_answer(payload.question)
        if insight:
            return QueryResponse(answer=insight["answer"], citations=insight["citations"])
    pipeline = get_pipeline(model_id)
    result = pipeline.query(
        payload.question,
        filters=build_filters(payload),
        use_hybrid=use_hybrid or bool(payload.use_hybrid),
        return_hits_only=return_hits_only or bool(payload.return_hits_only),
    )
    return QueryResponse(answer=result.answer, citations=result.citations, hits=result.hits)


def _llm_only_answer(question: str, model_id: str) -> QueryResponse:
    pipeline = get_pipeline(model_id)
    answer_text = pipeline.chat_only(question)
    return QueryResponse(answer=answer_text, citations=[])


@app.post("/rag/query", response_model=QueryResponse)
async def rag_query(
    payload: QueryPayload,
    token: Optional[str] = Depends(oauth2_scheme),
    model: str = RAG_MODEL_ID,
) -> QueryResponse:
    """Endpoint interne pour tests automatisés."""
    ensure_token(token)
    if model not in MODEL_ENDPOINTS:
        raise HTTPException(status_code=400, detail=f"Modèle {model} non supporté")
    return _execute_query(payload, model)


@app.post("/v1/hybrid/search", response_model=QueryResponse)
async def hybrid_search(
    payload: QueryPayload,
    token: Optional[str] = Depends(oauth2_scheme),
    model: str = RAG_MODEL_ID,
) -> QueryResponse:
    """Recherche hybride dense + BM25 (RRF par défaut)."""
    ensure_token(token)
    if model not in MODEL_ENDPOINTS:
        raise HTTPException(status_code=400, detail=f"Modèle {model} non supporté")
    return _execute_query(payload, model, use_hybrid=True, return_hits_only=bool(payload.return_hits_only))


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models", response_model=Dict[str, list[ModelInfo]])
async def list_models() -> Dict[str, list[ModelInfo]]:
    """Route OpenAI-compatible retournant les modèles disponibles."""
    models = [ModelInfo(id=model_id) for model_id in MODEL_ENDPOINTS.keys()]
    return {"data": models}


INLINE_MEDIA_TYPES = {"application/pdf", "text/plain", "text/html"}


@app.get("/files/view")
async def view_file(path: str):
    target = (DATA_ROOT / path).resolve()
    if not target.is_file() or not str(target).startswith(str(DATA_ROOT)):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    media_type, _ = mimetypes.guess_type(str(target))
    if media_type is None:
        media_type = "application/octet-stream"
    disposition = "inline" if media_type in INLINE_MEDIA_TYPES else "attachment"
    response = FileResponse(target, media_type=media_type)
    response.headers["Content-Disposition"] = f'{disposition}; filename="{target.name}"'
    return response


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatRequest, raw_request: Request, token: Optional[str] = Depends(oauth2_scheme)
) -> ChatCompletionResponse:
    """Compatibilité OpenAI Chat Completions (RAG quel que soit le modèle)."""
    ensure_token(token)
    if request.model not in MODEL_ENDPOINTS:
        raise HTTPException(status_code=400, detail=f"Modèle {request.model} non supporté")
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    last_user_msg = next((m for m in reversed(request.messages) if m.role == "user"), None)
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="at least one user message is required")

    # Read use_rag from header (priority) or metadata (fallback)
    use_rag_header = raw_request.headers.get("x-use-rag")
    use_hybrid_header = raw_request.headers.get("x-hybrid-search")
    print(f"DEBUG: X-Use-RAG header: {use_rag_header}", flush=True)
    print(f"DEBUG: X-Hybrid-Search header: {use_hybrid_header}", flush=True)
    
    if use_rag_header is not None:
        use_rag = normalize_bool(use_rag_header)
    else:
        use_rag = normalize_bool(
            request.metadata.get("use_rag") if request.metadata else None, default=None
        )

    use_hybrid = normalize_bool(
        use_hybrid_header if use_hybrid_header is not None else (request.metadata.get("use_hybrid") if request.metadata else None),
        default=False,
    )

    payload = QueryPayload(
        question=last_user_msg.content,
        service="",
        role="",
        use_rag=use_rag,
        use_hybrid=use_hybrid,
    )
    print(f"DEBUG: Incoming metadata: {request.metadata}", flush=True)
    print(f"DEBUG: Resolved use_rag: {payload.use_rag}", flush=True)
    result = _execute_query(payload, request.model, use_hybrid=use_hybrid)

    # Convert citations to Open WebUI format
    sources = convert_citations_to_openwebui_format(result.citations)
    
    response_message = ChatMessage(role="assistant", content=result.answer)
    choice = ChatChoice(index=0, finish_reason="stop", message=response_message)
    
    return ChatCompletionResponse(
        id=str(uuid.uuid4()),
        created=int(time.time()),
        model=request.model,
        choices=[choice],
        sources=sources if sources else None,
    )
