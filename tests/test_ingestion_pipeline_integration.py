"""Tests d'intégration pour le pipeline d'ingestion."""
from unittest.mock import MagicMock
from ingestion.pipeline import IngestionPipeline
from ingestion.connectors.base import BaseConnector, DocumentChunk
from ingestion.config import IngestionConfig

class MockConnector(BaseConnector):
    def __init__(self, chunks):
        self.chunks = chunks

    def discover(self):
        return ["mock_item"]

    def load(self, item):
        return self.chunks

def test_ingestion_pipeline_flow():
    # Setup
    mock_chunks = [
        DocumentChunk(
            id="doc1",
            text="Question : Test ?\nRéponse : Ça marche très bien et c'est une réponse suffisamment longue pour passer le filtre de qualité qui exige au moins 50 caractères.\nDESIGNATION : Contenu\nVoici un contenu de section qui est également assez long pour ne pas être filtré par le système de qualité mis en place.",
            metadata={"source": "test.txt"}
        )
    ]
    
    config = IngestionConfig()
    pipeline = IngestionPipeline(config)
    # Replace connectors with our mock
    pipeline.connectors = [MockConnector(mock_chunks)]
    
    # Execute
    results = list(pipeline.run())
    
    # Verify
    # On attend:
    # 1. FAQ chunk (Question/Réponse)
    # 2. Section chunk (Contenu)
    
    assert len(results) >= 2
    
    # Check FAQ
    faq_chunks = [c for c in results if "faq_question" in c.metadata]
    assert len(faq_chunks) == 1
    assert faq_chunks[0].metadata["faq_question"] == "Test ?"
    
    # Check Section
    section_chunks = [c for c in results if c.metadata.get("section_label") == "Designation"]
    assert len(section_chunks) == 1
    assert "Voici un contenu" in section_chunks[0].text
