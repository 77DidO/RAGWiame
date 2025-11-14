FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 \
    HF_RERANKER_MODEL=amberoad/bert-multilingual-passage-reranking-msmarco \
    HF_HOME=/models

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

RUN python - <<'PY'
import os
from huggingface_hub import snapshot_download

hf_home = os.environ.get("HF_HOME", "/models")

embedding_model = os.environ.get("HF_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
embedding_dir = os.path.join(hf_home, "embedding")
snapshot_download(
    repo_id=embedding_model,
    local_dir=embedding_dir,
    local_dir_use_symlinks=False,
    resume_download=True,
)

reranker_model = os.environ.get("HF_RERANKER_MODEL", "amberoad/bert-multilingual-passage-reranking-msmarco")
reranker_dir = os.path.join(hf_home, "reranker")
snapshot_download(
    repo_id=reranker_model,
    local_dir=reranker_dir,
    local_dir_use_symlinks=False,
    resume_download=True,
)
PY

COPY . /app/llm_pipeline

EXPOSE 8081

CMD ["uvicorn", "llm_pipeline.api:app", "--host", "0.0.0.0", "--port", "8081"]
