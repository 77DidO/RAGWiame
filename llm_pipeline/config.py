"""Configuration centralisée pour le Gateway RAG."""
import os
from pathlib import Path
from typing import Dict

# Modèles LLM
RAG_MODEL_ID = os.getenv("RAG_MODEL_ID", "mistral")
RAG_ENDPOINT = os.getenv("VLLM_ENDPOINT", "http://vllm:8000/v1")

SMALL_MODEL_ENABLED = os.getenv("ENABLE_SMALL_MODEL", "false").lower() in {"1", "true", "yes"}
SMALL_MODEL_ID = os.getenv("SMALL_MODEL_ID", "phi3-mini")
SMALL_LLM_ENDPOINT = os.getenv("SMALL_LLM_ENDPOINT", "http://vllm-light:8002/v1")

MODEL_ENDPOINTS: Dict[str, str] = {RAG_MODEL_ID: RAG_ENDPOINT}
if SMALL_MODEL_ENABLED:
    MODEL_ENDPOINTS[SMALL_MODEL_ID] = SMALL_LLM_ENDPOINT

# RAG Configuration
DEFAULT_SERVICE = os.getenv("DEFAULT_RAG_SERVICE", "").strip()
DEFAULT_ROLE = os.getenv("DEFAULT_RAG_ROLE", "").strip()
EMBEDDING_MODEL = os.getenv(
    "HF_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
SMALL_MODEL_TOP_K = int(os.getenv("SMALL_MODEL_TOP_K", "3"))
MAX_CHUNK_CHARS = int(os.getenv("RAG_MAX_CHUNK_CHARS", "800"))
ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "true").lower() in {"1", "true", "yes"}

# LLM Parameters
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))

# Paths
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data")).resolve()
PUBLIC_GATEWAY_URL = os.getenv("PUBLIC_GATEWAY_URL", "http://localhost:8081").rstrip("/")

# RAG Mode
DEFAULT_USE_RAG = os.getenv("DEFAULT_USE_RAG", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Auth
BYPASS_AUTH = os.getenv("BYPASS_AUTH", "false").lower() in {"1", "true", "yes"}
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080/")

# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

# Hybrid Search
HYBRID_FUSION = os.getenv("HYBRID_FUSION", "rrf").strip().lower()
HYBRID_WEIGHT_VECTOR = float(os.getenv("HYBRID_WEIGHT_VECTOR", "0.6"))
HYBRID_WEIGHT_KEYWORD = float(os.getenv("HYBRID_WEIGHT_KEYWORD", "0.4"))
HYBRID_BM25_TOP_K = int(os.getenv("HYBRID_BM25_TOP_K", "30"))
