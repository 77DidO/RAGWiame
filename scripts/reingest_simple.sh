#!/bin/bash
# Simple re-ingestion script that runs inside the indexation container

cat > /tmp/reingest.py << 'EOFPYTHON'
import os
import sys
from pathlib import Path

sys.path.append("/app")

from ingestion.pipeline import IngestionPipeline, IngestionConfig
from indexation.qdrant_indexer import QdrantIndexer
from llm_pipeline.elastic_client import index_document as es_index_document
from llama_index.core import Document

def _build_documents(chunks):
    return [
        Document(text=chunk.text, metadata=dict(chunk.metadata), doc_id=chunk.id)
        for chunk in chunks
        if chunk.text.strip()
    ]

def _build_es_body(chunk):
    metadata = dict(chunk.metadata)
    metadata.pop("content", None)
    body = {"content": chunk.text}
    for key in ("source", "service", "role", "doc_hint", "chunk_index", "page"):
        if key in metadata:
            body[key] = metadata[key]
    for key, value in metadata.items():
        if key in body:
            continue
        try:
            body[key] = value
        except Exception:
            body[key] = str(value)
    return body

FILES = [
    "/data/ED257730 - MONTMIRAIL - AV DE L EMPEREUR/09-Offre remise/OFFRE 1702/DQE Aménagement sécuritaire Av de l'Empereur_Montmirail.xlsx",
    "/data/ED257730 - MONTMIRAIL - AV DE L EMPEREUR/09-Offre remise/OFFRE 1702/DQE - Montmirail - Av de l'Empereur - Resine sablé sur enrobés.xlsx",
    "/data/ED257730 - MONTMIRAIL - AV DE L EMPEREUR/05-Etude-Devis-SPIGAO/EN.07.01 - Etudes R.07 - 2024.10.xlsx"
]

def main():
    print("Starting re-ingestion...")
    
    valid_paths = [Path(f) for f in FILES if Path(f).exists()]
    print(f"Found {len(valid_paths)} files")
    
    if not valid_paths:
        print("No files found")
        return
    
    config = IngestionConfig(chunk_size=50, chunk_overlap=0)
    config.txt.enabled = False
    config.docx.enabled = False
    config.pdf.enabled = False
    config.mariadb_source.enabled = False
    config.excel.enabled = True
    config.excel.paths = valid_paths
    
    print("Running ingestion...")
    pipeline = IngestionPipeline(config)
    chunks = list(pipeline.run())
    print(f"Generated {len(chunks)} chunks")
    
    if not chunks:
        return
    
    print("Indexing to Qdrant...")
    documents = _build_documents(chunks)
    indexer = QdrantIndexer(qdrant_url="http://qdrant:6333")
    indexer.index_documents(documents)
    print("Qdrant done")
    
    print("Indexing to Elasticsearch...")
    failures = 0
    for chunk in chunks:
        try:
            es_index_document(str(chunk.id), body=_build_es_body(chunk))
        except Exception as e:
            print(f"ES error for {chunk.id}: {e}")
            failures += 1
    print(f"ES done. Failures: {failures}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOFPYTHON

python /tmp/reingest.py
