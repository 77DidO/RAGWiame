"""Modèles Pydantic pour l'API Gateway."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel


class QueryPayload(BaseModel):
    question: str
    service: Optional[str] = ""
    role: Optional[str] = ""
    use_rag: Optional[bool] = None
    use_hybrid: Optional[bool] = False
    return_hits_only: Optional[bool] = False


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
