"""Tests pour le module request_utils."""
import pytest
from llm_pipeline.request_utils import (
    normalize_filter_value,
    normalize_bool,
    resolve_rag_mode,
    check_vague_question,
)
from llm_pipeline.models import QueryPayload


def test_normalize_filter_value():
    assert normalize_filter_value("service1") == "service1"
    assert normalize_filter_value("  service1  ") == "service1"
    assert normalize_filter_value("all") == ""
    assert normalize_filter_value("*") == ""
    assert normalize_filter_value("ANY") == ""
    assert normalize_filter_value(None) == ""
    assert normalize_filter_value("") == ""


def test_normalize_bool():
    # Boolean values
    assert normalize_bool(True) is True
    assert normalize_bool(False) is False
    
    # String values
    assert normalize_bool("true") is True
    assert normalize_bool("1") is True
    assert normalize_bool("yes") is True
    assert normalize_bool("on") is True
    assert normalize_bool("false") is False
    assert normalize_bool("0") is False
    assert normalize_bool("no") is False
    
    # None with default
    assert normalize_bool(None, default=True) is True
    assert normalize_bool(None, default=False) is False
    
    # Numbers
    assert normalize_bool(1) is True
    assert normalize_bool(0) is False


def test_resolve_rag_mode():
    # Explicit flag takes precedence
    text, use_rag = resolve_rag_mode("test question", explicit=True)
    assert use_rag is True
    assert text == "test question"
    
    # Disable patterns
    text, use_rag = resolve_rag_mode("test #norag question", explicit=None)
    assert use_rag is False
    assert "#norag" not in text
    
    text, use_rag = resolve_rag_mode("test [norag] question", explicit=None)
    assert use_rag is False
    
    # Enable patterns
    text, use_rag = resolve_rag_mode("test #forcerag question", explicit=None)
    assert use_rag is True
    assert "#forcerag" not in text


def test_check_vague_question():
    # Vague questions should return a response
    result = check_vague_question("quel est le montant ?")
    assert result is not None
    assert "manque de contexte" in result.answer.lower()
    
    result = check_vague_question("combien ?")
    assert result is not None
    
    result = check_vague_question("où ?")
    assert result is not None
    
    # Specific questions should return None
    result = check_vague_question("Quel est le montant du DQE pour le projet Montmirail ?")
    assert result is None
    
    result = check_vague_question("Combien coûte le projet X ?")
    assert result is None
