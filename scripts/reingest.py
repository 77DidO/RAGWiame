import os
import sys
from pathlib import Path

# Add current directory to path to allow imports
sys.path.append(os.getcwd())

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

def _build_es_body(chunk) -> dict:
    metadata = dict(chunk.metadata)
    metadata.pop("content", None)
    body = {
        "content": chunk.text,
    }
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

# Files to re-ingest
FILES = [
    "/data/ED257730 - MONTMIRAIL - AV DE L EMPEREUR/09-Offre remise/OFFRE 1702/DQE Aménagement sécuritaire Av de l'Empereur_Montmirail.xlsx",
    "/data/ED257730 - MONTMIRAIL - AV DE L EMPEREUR/09-Offre remise/OFFRE 1702/DQE - Montmirail - Av de l'Empereur - Resine sablé sur enrobés.xlsx",
    "/data/ED257730 - MONTMIRAIL - AV DE L EMPEREUR/05-Etude-Devis-SPIGAO/EN.07.01 - Etudes R.07 - 2024.10.xlsx"
]

def main():
    print("Starting re-ingestion of key files...")
    
    # Check if files exist
    valid_paths = []
    for f in FILES:
        p = Path(f)
        if p.exists():
            valid_paths.append(p)
            print(f"Found: {p}")
        else:
            print(f"Warning: File not found: {p}")
    
    if not valid_paths:
        print("No files found to ingest.")
        return

    # Config
    ingestion_config = IngestionConfig(
        chunk_size=50, 
        chunk_overlap=0
    )
    # Disable other connectors
    ingestion_config.txt.enabled = False
    ingestion_config.docx.enabled = False
    ingestion_config.pdf.enabled = False
    ingestion_config.mariadb_source.enabled = False
    
    # Configure Excel connector
    ingestion_config.excel.enabled = True
    ingestion_config.excel.paths = valid_paths
    
    # Run pipeline
    print("Running ingestion pipeline...")
    pipeline = IngestionPipeline(ingestion_config)
    chunks = list(pipeline.run())
    print(f"Generated {len(chunks)} chunks.")
    
    if not chunks:
        print("No chunks generated.")
        return

    # Index Qdrant
    print("Indexing into Qdrant...")
    documents = _build_documents(chunks)
    indexer = QdrantIndexer(qdrant_url="http://qdrant:6333")
    indexer.index_documents(documents)
    print("Qdrant indexing complete.")

    # Index Elasticsearch
    print("Indexing into Elasticsearch...")
    failures = 0
    for chunk in chunks:
        body = _build_es_body(chunk)
        try:
            es_index_document(str(chunk.id), body=body)
        except Exception as e:
            print(f"Error indexing {chunk.id} in ES: {e}")
            failures += 1
    
    print(f"Elasticsearch indexing complete. Failures: {failures}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL ERROR: {e}", flush=True)
        sys.exit(1)
