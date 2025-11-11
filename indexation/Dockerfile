FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

COPY indexation/requirements.txt /tmp/indexation-requirements.txt
COPY ingestion/requirements.txt /tmp/ingestion-requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/indexation-requirements.txt \
    && pip install --no-cache-dir -r /tmp/ingestion-requirements.txt

COPY ingestion /app/ingestion
COPY indexation /app/indexation

ENTRYPOINT ["python", "-m", "indexation.qdrant_indexer"]
