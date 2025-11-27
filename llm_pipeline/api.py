"""API FastAPI orchestrant le pipeline RAG et la sélection dynamique des modèles."""
from __future__ import annotations

import mimetypes
import os
import time
import uuid
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request
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
DEFAULT_USE_RAG = os.getenv("DEFAULT_USE_RAG", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

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
    use_rag: Optional[bool] = None
    use_hybrid: Optional[bool] = False
    return_hits_only: Optional[bool] = False


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
    hits: Optional[List[Dict[str, Any]]] = None


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
    metadata: Optional[Dict[str, Any]] = None


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
    sources: Optional[List[Dict[str, Any]]] = None


@lru_cache(maxsize=1)
def _build_index() -> VectorStoreIndex:
    qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
    vector_store = QdrantVectorStore(
        client=qdrant_client, 
        collection_name="rag_documents",
        enable_hybrid=False,  # Désactiver le mode hybride natif de Qdrant car nous gérons notre propre fusion
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


def _check_vague_question(question: str) -> Optional[QueryResponse]:
    import re
    vague_patterns = [
        r"^quel\s+(est|sont)\s+(le|la|les)\s+\w+\s*\??$",  # "quel est le montant ?"
        r"^quel\s+(est|sont)\s+\w+\s*\??$",  # "quel est montant ?"
        r"^combien\s*\??$",  # "combien ?"
        r"^où\s*\??$",  # "où ?"
        r"^quoi\s*\??$",  # "quoi ?"
        r"^qui\s*\??$",  # "qui ?"
    ]
    
    question_lower = question.lower().strip()
    for pattern in vague_patterns:
        if re.match(pattern, question_lower):
            return QueryResponse(
                answer="Je ne peux pas répondre à cette question car elle manque de contexte. "
                       "Pourriez-vous préciser ce que vous cherchez ? Par exemple : "
                       "\"Quel est le montant du DQE pour le projet Montmirail ?\"",
                citations=[]
            )
    return None


def _execute_query(
    payload: QueryPayload, model_id: str, use_hybrid: bool = False, return_hits_only: bool = False
) -> QueryResponse:
    if return_hits_only:
        payload.use_rag = True
    question_text, use_rag = _resolve_rag_mode(payload.question, payload.use_rag)
    if use_rag is False and not return_hits_only:
        return _llm_only_answer(question_text, model_id)
    payload.question = question_text
    
    # 1. Check for vague questions immediately
    vague_response = _check_vague_question(payload.question)
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
        filters=_build_filters(payload),
        use_hybrid=use_hybrid or bool(payload.use_hybrid),
        return_hits_only=return_hits_only or bool(payload.return_hits_only),
    )
    return QueryResponse(answer=result.answer, citations=result.citations, hits=result.hits)


def _llm_only_answer(question: str, model_id: str) -> QueryResponse:
    pipeline = get_pipeline(model_id)
    answer_text = pipeline.chat_only(question)
    return QueryResponse(answer=answer_text, citations=[])


def _ensure_token(token: Optional[str]) -> None:
    if BYPASS_AUTH:
        return
    if not token:
        raise HTTPException(status_code=401, detail="Token invalide")


def _normalize_bool(value: Any, default: bool | None = True) -> bool | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


_DISABLE_RAG_PATTERNS = [r"#norag\b", r"\[norag\]", r"rag\s*:\s*false"]
_ENABLE_RAG_PATTERNS = [r"#forcerag\b", r"#userag\b", r"\[rag\]", r"rag\s*:\s*true"]


def _resolve_rag_mode(question: str, explicit: Optional[bool]) -> tuple[str, bool]:
    decision = explicit
    cleaned = question
    for pattern in _DISABLE_RAG_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            decision = False
    for pattern in _ENABLE_RAG_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            decision = True
    if decision is None:
        decision = DEFAULT_USE_RAG
    return cleaned.strip(), decision


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
    block_lines = ["> Références :"]
    for idx, citation in enumerate(unique, start=1):
        link = _format_reference_link(citation)
        snippet = _format_citation_snippet(citation)
        line = f"> {idx}. {link}"
        block_lines.append(line)
        if snippet:
            block_lines.append(f">    ↳ {snippet}")
    joined = "\n".join(block_lines)
    return f"{answer}\n\n{joined}"


def _prettify_display_path(relative: str) -> str:
    """Make citation labels cleaner (strip conversion suffixes like .txt.xlsx)."""
    normalized = relative.replace("\\", "/")
    name = Path(normalized).name
    pretty = re.sub(r"\.txt\.(pdf|docx|xlsx|xls|csv)\b", r".\1", name, flags=re.IGNORECASE)
    pretty = re.sub(r"\.(pdf|docx|xlsx|xls|csv)\.\1\b", r".\1", pretty, flags=re.IGNORECASE)
    if normalized.endswith(name):
        prefix = normalized[: -len(name)]
        return f"{prefix}{pretty}"
    return pretty


def _format_reference_link(citation: Dict[str, Any]) -> str:
    source = str(citation.get("source", "source inconnue"))
    chunk = str(citation.get("chunk", "") or "").strip()
    relative = source
    if source.startswith("/data/"):
        relative = source[len("/data/") :]
    elif source.startswith(str(DATA_ROOT)):
        relative = str(Path(source).relative_to(DATA_ROOT))
    relative = relative.replace("\\", "/")
    display_path = _prettify_display_path(relative)
    link = f"{PUBLIC_GATEWAY_URL}/files/view?path={quote(relative)}"
    base_name = Path(display_path).name or display_path
    chunk_suffix = _format_chunk_suffix(base_name, chunk)
    if chunk_suffix:
        display_path = f"{display_path} - {chunk_suffix}"
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
    if len(snippet) > 120:
        snippet = snippet[:120].rstrip() + "…"
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


def _replace_file_mentions_with_citations(answer: str, citations: List[Dict[str, Any]]) -> str:
    """Replace file path mentions in answer with citation numbers [1], [2], etc.
    
    This ensures consistent citation format even if the LLM doesn't follow instructions perfectly.
    """
    if not citations:
        return answer
    
    print(f"DEBUG POST-PROCESSING: Original answer: {answer[:200]}...", flush=True)
    print(f"DEBUG POST-PROCESSING: Citations count: {len(citations)}", flush=True)
    
    modified_answer = answer
    
    # Build a map of source to citation number
    source_map = {}
    for idx, citation in enumerate(citations, start=1):
        source = str(citation.get("source", ""))
        if source:
            source_map[source] = f"[{idx}]"
            print(f"DEBUG POST-PROCESSING: Citation {idx}: {source}", flush=True)
    
    # Pattern 1: Replace any mention of .xlsx or .docx files with their citation number
    for source, citation_num in source_map.items():
        # Extract filename
        filename = source.split('/')[-1].split('\\')[-1]
        
        # Try multiple patterns
        patterns = [
            # Full path with /data/
            re.escape(source),
            # Partial path (anything before the filename)
            r'[^\s]*' + re.escape(filename),
            # Just the filename
            re.escape(filename),
            # Filename without extension
            re.escape(filename.rsplit('.', 1)[0]) + r'\.xlsx',
            re.escape(filename.rsplit('.', 1)[0]) + r'\.docx',
        ]
        
        for pattern in patterns:
            # Replace with citation number
            before = modified_answer
            modified_answer = re.sub(pattern, citation_num, modified_answer, flags=re.IGNORECASE)
            if before != modified_answer:
                print(f"DEBUG POST-PROCESSING: Pattern '{pattern}' matched!", flush=True)
    
    # Clean up any remaining parentheses around citations like ([1])
    modified_answer = re.sub(r'\(\[(\d+)\]\)', r'[\1]', modified_answer)
    
    # Clean up duplicate citations like [1][1] or [1] [1]
    modified_answer = re.sub(r'(\[\d+\])\s*\1', r'\1', modified_answer)
    
    # Clean up multiple spaces
    modified_answer = re.sub(r'\s+', ' ', modified_answer)
    
    print(f"DEBUG POST-PROCESSING: Modified answer: {modified_answer[:200]}...", flush=True)
    
    return modified_answer


def _convert_citations_to_openwebui_format(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert pipeline citations to Open WebUI format.
    
    Each citation becomes a separate element in the array (not grouped by source).
    This allows Open WebUI to create proper sourceIds for clickable [1], [2], [3].
    """
    if not citations:
        return []
    
    result = []
    for citation in citations:
        source = str(citation.get("source", ""))
        if not source:
            continue
        
        # Generate file URL
        relative = source
        if source.startswith("/data/"):
            relative = source[len("/data/"):]
        elif source.startswith(str(DATA_ROOT)):
            relative = str(Path(source).relative_to(DATA_ROOT))
        relative = relative.replace("\\", "/")
        file_url = f"{PUBLIC_GATEWAY_URL}/files/view?path={quote(relative)}"
        
        # Extract snippet
        snippet = str(citation.get("snippet", "")).strip()
        
        # Extract page number from chunk if present
        chunk = str(citation.get("chunk", ""))
        page_match = re.search(r'page[_\s]*(\d+)', chunk, re.IGNORECASE)
        
        metadata = {"source": source}
        if page_match:
            metadata["page"] = int(page_match.group(1))
        
        # Create individual citation entry
        result.append({
            "source": {
                "name": source,
                "embed_url": file_url
            },
            "document": [snippet] if snippet else [],
            "metadata": [metadata],
            "distances": []
        })
    
    return result


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


@app.post("/v1/hybrid/search", response_model=QueryResponse)
async def hybrid_search(
    payload: QueryPayload,
    token: Optional[str] = Depends(oauth2_scheme),
    model: str = RAG_MODEL_ID,
) -> QueryResponse:
    """Recherche hybride dense + BM25 (RRF par défaut)."""
    _ensure_token(token)
    if model not in MODEL_ENDPOINTS:
        raise HTTPException(status_code=400, detail=f"Modèle {model} non supporté")
    return _execute_query(payload, model, use_hybrid=True, return_hits_only=bool(payload.return_hits_only))


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
    request: ChatRequest, raw_request: Request, token: Optional[str] = Depends(oauth2_scheme)
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

    # Read use_rag from header (priority) or metadata (fallback)
    use_rag_header = raw_request.headers.get("x-use-rag")
    use_hybrid_header = raw_request.headers.get("x-hybrid-search")
    print(f"DEBUG: X-Use-RAG header: {use_rag_header}", flush=True)
    print(f"DEBUG: X-Hybrid-Search header: {use_hybrid_header}", flush=True)
    
    if use_rag_header is not None:
        use_rag = _normalize_bool(use_rag_header)
    else:
        use_rag = _normalize_bool(
            request.metadata.get("use_rag") if request.metadata else None, default=None
        )

    use_hybrid = _normalize_bool(
        use_hybrid_header if use_hybrid_header is not None else (request.metadata.get("use_hybrid") if request.metadata else None),
        default=False,
    )

    payload = QueryPayload(
        question=last_user_msg.content,
        service=DEFAULT_SERVICE,
        role=DEFAULT_ROLE,
        use_rag=use_rag,
        use_hybrid=use_hybrid,
    )
    print(f"DEBUG: Incoming metadata: {request.metadata}", flush=True)
    print(f"DEBUG: Resolved use_rag: {payload.use_rag}", flush=True)
    result = _execute_query(payload, request.model, use_hybrid=use_hybrid)

    # Convert citations to Open WebUI format
    sources = _convert_citations_to_openwebui_format(result.citations)
    
    response_message = ChatMessage(role="assistant", content=result.answer)
    choice = ChatChoice(index=0, finish_reason="stop", message=response_message)
    
    return ChatCompletionResponse(
        id=str(uuid.uuid4()),
        created=int(time.time()),
        model=request.model,
        choices=[choice],
        sources=sources if sources else None,
    )

