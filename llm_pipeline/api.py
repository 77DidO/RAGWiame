"""API FastAPI orchestrant le pipeline RAG et la sélection dynamique des modèles."""
from __future__ import annotations

import mimetypes
import os
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import FileResponse
from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from pydantic import BaseModel
from qdrant_client import QdrantClient

from llm_pipeline.pipeline import RagPipeline
from llm_pipeline.insights import DocumentInsightService
from llm_pipeline.inventory import DocumentInventoryService

RAG_MODEL_ID = os.getenv("RAG_MODEL_ID", "mistral")
RAG_ENDPOINT = os.getenv("VLLM_ENDPOINT", "http://vllm:8000/v1")
BYPASS_AUTH = os.getenv("BYPASS_AUTH", "false").lower() in {"1", "true", "yes"}

SMALL_MODEL_ENABLED = os.getenv("ENABLE_SMALL_MODEL", "false").lower() in {"1", "true", "yes"}
SMALL_MODEL_ID = os.getenv("SMALL_MODEL_ID", "phi3-mini")
SMALL_LLM_ENDPOINT = os.getenv("SMALL_LLM_ENDPOINT", "http://vllm-light:8002/v1")

MODEL_ENDPOINTS: Dict[str, str] = {RAG_MODEL_ID: RAG_ENDPOINT}
if SMALL_MODEL_ENABLED:
    MODEL_ENDPOINTS[SMALL_MODEL_ID] = SMALL_LLM_ENDPOINT

ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "true").lower() in {"1", "true", "yes"}
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data")).resolve()
PUBLIC_GATEWAY_URL = os.getenv("PUBLIC_GATEWAY_URL", "http://localhost:8081").rstrip("/")

app = FastAPI(title="RAGWiame Gateway", version="0.1.0")
insight_service = DocumentInsightService()
inventory_service = DocumentInventoryService()

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=os.getenv("KEYCLOAK_URL", "http://keycloak:8080/")
    + "realms/rag/protocol/openid-connect/auth",
    tokenUrl=os.getenv("KEYCLOAK_URL", "http://keycloak:8080/")
    + "realms/rag/protocol/openid-connect/token",
    auto_error=not BYPASS_AUTH,
)


class QueryPayload(BaseModel):
    question: str
    service: Optional[str] = ""
    role: Optional[str] = ""


DEFAULT_SERVICE = os.getenv("DEFAULT_RAG_SERVICE", "").strip()
DEFAULT_ROLE = os.getenv("DEFAULT_RAG_ROLE", "").strip()
EMBEDDING_MODEL = os.getenv(
    "HF_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
SMALL_MODEL_TOP_K = int(os.getenv("SMALL_MODEL_TOP_K", "3"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
MAX_CHUNK_CHARS = int(os.getenv("RAG_MAX_CHUNK_CHARS", "800"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))


class QueryResponse(BaseModel):
    answer: str
    citations: Any


class ModelInfo(BaseModel):
    id: str
    object: str = "model"


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False


class ChatChoice(BaseModel):
    index: int
    finish_reason: str
    message: ChatMessage


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]


@lru_cache(maxsize=1)
def _build_index() -> VectorStoreIndex:
    qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
    vector_store = QdrantVectorStore(client=qdrant_client, collection_name="rag_documents")
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
        api_key=os.getenv("VLLM_API_KEY", "changeme"),
        model_name=model_id,
        top_k=top_k,
        timeout_seconds=LLM_TIMEOUT,
        temperature=LLM_TEMPERATURE,
        max_chunk_chars=MAX_CHUNK_CHARS,
        max_retries=LLM_MAX_RETRIES,
        enable_reranker=ENABLE_RERANKER,
    )


def _normalize_filter_value(value: Optional[str]) -> str:
    if not value:
        return ""
    cleaned = value.strip()
    if cleaned.lower() in {"", "all", "*", "any"}:
        return ""
    return cleaned


def _build_filters(payload: QueryPayload) -> MetadataFilters:
    filters: List[MetadataFilter] = []
    service = _normalize_filter_value(payload.service)
    role = _normalize_filter_value(payload.role)
    if service:
        filters.append(MetadataFilter(key="service", value=service))
    if role:
        filters.append(MetadataFilter(key="role", value=role))
    return MetadataFilters(filters=filters)


def _execute_query(payload: QueryPayload, model_id: str) -> QueryResponse:
    inventory = inventory_service.try_answer(payload.question)
    if inventory:
        enriched_answer = _append_citations_text(inventory["answer"], inventory["citations"])
        return QueryResponse(answer=enriched_answer, citations=inventory["citations"])
    insight = insight_service.try_answer(payload.question)
    if insight:
        enriched_answer = _append_citations_text(insight["answer"], insight["citations"])
        return QueryResponse(answer=enriched_answer, citations=insight["citations"])
    pipeline = get_pipeline(model_id)
    result = pipeline.query(payload.question, filters=_build_filters(payload))
    enriched_answer = _append_citations_text(result.answer, result.citations)
    return QueryResponse(answer=enriched_answer, citations=result.citations)


def _ensure_token(token: Optional[str]) -> None:
    if BYPASS_AUTH:
        return
    if not token:
        raise HTTPException(status_code=401, detail="Token invalide")


def _append_citations_text(answer: str, citations: List[Dict[str, Any]]) -> str:
    if not citations:
        return answer
    unique: List[Dict[str, Any]] = []
    seen = set()
    for citation in citations:
        source = str(citation.get("source", ""))
        chunk = str(citation.get("chunk", "") or "")
        key = (source, chunk)
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    if not unique:
        return answer
    block_lines = ["> **Références :**"]
    for idx, citation in enumerate(unique, start=1):
        link = _format_reference_link(citation)
        snippet = _format_citation_snippet(citation)
        block_lines.append(f"> {idx}. {link}")
        if snippet:
            block_lines.append(f">    ↳ {snippet}")
    joined = "\n".join(block_lines)
    return f"{answer}\n\n{joined}"


def _format_reference_link(citation: Dict[str, Any]) -> str:
    source = str(citation.get("source", "source inconnue"))
    chunk = str(citation.get("chunk", "") or "").strip()
    relative = source
    if source.startswith("/data/"):
        relative = source[len("/data/") :]
    elif source.startswith(str(DATA_ROOT)):
        relative = str(Path(source).relative_to(DATA_ROOT))
    relative = relative.replace("\\", "/")
    link = f"{PUBLIC_GATEWAY_URL}/files/view?path={quote(relative)}"
    base_name = Path(relative).name or relative
    display_path = relative
    chunk_suffix = _format_chunk_suffix(base_name, chunk)
    if chunk_suffix:
        display_path = f"{relative} · {chunk_suffix}"
    safe_label = display_path.replace("`", "'")
    return f"[{safe_label}]({link})"


def _format_citation_snippet(citation: Dict[str, Any]) -> str:
    snippet = str(citation.get("snippet", "") or "").strip()
    if not snippet:
        return ""
    chunk = str(citation.get("chunk", "") or "")
    normalized_chunk = " ".join(chunk.split()).strip().strip('"').lower()
    normalized_snippet = " ".join(snippet.split()).strip().strip('"').lower()
    if normalized_chunk and normalized_chunk == normalized_snippet:
        return ""
    snippet = " ".join(snippet.split())
    if len(snippet) > 320:
        snippet = snippet[:320].rstrip() + "…"
    return snippet


def _format_chunk_suffix(base_name: str, chunk: str) -> str:
    if not chunk:
        return ""
    cleaned_chunk = " ".join(chunk.split())
    if cleaned_chunk.lower() == base_name.lower():
        return ""
    parts = [part.strip() for part in cleaned_chunk.split("::") if part.strip()]
    if parts and parts[0].lower() == base_name.lower():
        parts = parts[1:]
    return " · ".join(parts)


@app.post("/rag/query", response_model=QueryResponse)
async def rag_query(
    payload: QueryPayload,
    token: Optional[str] = Depends(oauth2_scheme),
    model: str = RAG_MODEL_ID,
) -> QueryResponse:
    """Endpoint interne pour tests automatisés."""
    _ensure_token(token)
    if model not in MODEL_ENDPOINTS:
        raise HTTPException(status_code=400, detail=f"Modèle {model} non supporté")
    return _execute_query(payload, model)


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models", response_model=Dict[str, List[ModelInfo]])
async def list_models() -> Dict[str, List[ModelInfo]]:
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
    request: ChatRequest, token: Optional[str] = Depends(oauth2_scheme)
) -> ChatCompletionResponse:
    """Compatibilité OpenAI Chat Completions (RAG quel que soit le modèle)."""
    _ensure_token(token)
    if request.model not in MODEL_ENDPOINTS:
        raise HTTPException(status_code=400, detail=f"Modèle {request.model} non supporté")
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    last_user_msg = next((m for m in reversed(request.messages) if m.role == "user"), None)
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="at least one user message is required")

    payload = QueryPayload(
        question=last_user_msg.content,
        service=DEFAULT_SERVICE,
        role=DEFAULT_ROLE,
    )
    result = _execute_query(payload, request.model)

    response_message = ChatMessage(role="assistant", content=result.answer)
    choice = ChatChoice(index=0, finish_reason="stop", message=response_message)
    return ChatCompletionResponse(
        id=str(uuid.uuid4()),
        created=int(time.time()),
        model=request.model,
        choices=[choice],
    )



