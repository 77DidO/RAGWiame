FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . /app/llm_pipeline

EXPOSE 8081

CMD ["uvicorn", "llm_pipeline.api:app", "--host", "0.0.0.0", "--port", "8081"]
