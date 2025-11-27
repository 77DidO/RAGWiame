"""Tests unitaires pour les composants du pipeline d'ingestion."""
import pytest
from ingestion.text_processor import TextProcessor
from ingestion.structure_detector import StructureDetector
from ingestion.metadata_enricher import MetadataEnricher
from ingestion.quality_filter import QualityFilter

# --- TextProcessor Tests ---

def test_clean_text():
    raw = "Bonjour\u00a0le monde\r"
    cleaned = TextProcessor.clean_text(raw)
    assert cleaned == "Bonjour le monde\n"

def test_split_text():
    text = "1234567890"
    chunks = TextProcessor.split_text(text, chunk_size=5, chunk_overlap=2)
    assert len(chunks) == 3
    assert chunks[0] == "12345"
    assert chunks[1] == "45678"
    assert chunks[2] == "7890"

def test_paragraphs():
    text = "Question : Quelle heure est-il ?\nRéponse : Il est midi."
    parts = TextProcessor.paragraphs(text)
    assert len(parts) == 2
    assert parts[0] == "Question : Quelle heure est-il ?"
    assert parts[1] == "Réponse : Il est midi."

# --- StructureDetector Tests ---

def test_detect_section_label():
    assert StructureDetector.detect_section_label("VENDEUR") == "Vendeur"
    assert StructureDetector.detect_section_label("  ACQUEREUR  ") == "Acquereur"
    assert StructureDetector.detect_section_label("Désignation :") == "Désignation"
    assert StructureDetector.detect_section_label("Autre chose") is None

def test_detect_faq():
    q, a = StructureDetector.detect_faq("Question : Quel est le prix ?")
    assert q == "Quel est le prix ?"
    assert a is None
    
    q, a = StructureDetector.detect_faq("Réponse : 100 euros")
    assert q is None
    assert a == "100 euros"

# --- MetadataEnricher Tests ---

def test_infer_doc_hint():
    assert MetadataEnricher.infer_doc_hint({"source": "mon_email.msg"}) == "courriel"
    assert MetadataEnricher.infer_doc_hint({"source": "projet_planning.xlsx"}) == "planning"
    assert MetadataEnricher.infer_doc_hint({"source": "DQE_Montmirail.pdf"}) == "dqe"
    assert MetadataEnricher.infer_doc_hint({"source": "inconnu.txt"}) is None

# --- QualityFilter Tests ---

def test_is_low_quality_chunk():
    # Trop court
    assert QualityFilter.is_low_quality_chunk("Court") is True
    
    # Trop de chiffres
    digits = "0123456789" * 5 + "abc"
    assert QualityFilter.is_low_quality_chunk(digits) is True
    
    # Bon texte
    good = "Ceci est un texte de qualité suffisante avec assez de mots pour être accepté par le filtre."
    assert QualityFilter.is_low_quality_chunk(good) is False
