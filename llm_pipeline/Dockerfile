FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_EMBEDDING_MODEL=sentence-transformers/distiluse-base-multilingual-cased-v2 \
    HF_HOME=/models

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

RUN python - <<'PY'
import os
from huggingface_hub import snapshot_download

model = os.environ.get("HF_EMBEDDING_MODEL", "sentence-transformers/distiluse-base-multilingual-cased-v2")
target_dir = os.path.join(os.environ.get("HF_HOME", "/models"), "embedding")
snapshot_download(
    repo_id=model,
    local_dir=target_dir,
    local_dir_use_symlinks=False,
    resume_download=True,
)
PY

COPY . /app/llm_pipeline

EXPOSE 8081

CMD ["uvicorn", "llm_pipeline.api:app", "--host", "0.0.0.0", "--port", "8081"]
