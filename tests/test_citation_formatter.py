"""Tests pour le module citation_formatter."""
import pytest
from llm_pipeline.citation_formatter import (
    prettify_display_path,
    format_chunk_suffix,
    format_citation_snippet,
    append_citations_text,
)


def test_prettify_display_path():
    # Remove .txt.xlsx suffix
    assert prettify_display_path("data/file.txt.xlsx") == "data/file.xlsx"
    
    # Remove duplicate extensions
    assert prettify_display_path("data/file.pdf.pdf") == "data/file.pdf"
    
    # Normal path unchanged
    assert prettify_display_path("data/normal.pdf") == "data/normal.pdf"


def test_format_chunk_suffix():
    # Empty chunk
    assert format_chunk_suffix("file.pdf", "") == ""
    
    # Chunk same as basename
    assert format_chunk_suffix("file.pdf", "file.pdf") == ""
    
    # Chunk with :: separator
    result = format_chunk_suffix("file.pdf", "file.pdf::Section 1::Page 2")
    assert result == "Section 1 · Page 2"


def test_format_citation_snippet():
    citation = {"snippet": "This is a test snippet", "chunk": "different"}
    snippet = format_citation_snippet(citation)
    assert snippet == "This is a test snippet"
    
    # Snippet same as chunk (should return empty)
    citation = {"snippet": "same text", "chunk": "same text"}
    assert format_citation_snippet(citation) == ""
    
    # Long snippet (should truncate)
    long_text = "a" * 150
    citation = {"snippet": long_text, "chunk": "different"}
    snippet = format_citation_snippet(citation)
    assert len(snippet) <= 121  # 120 + ellipsis
    assert snippet.endswith("…")


def test_append_citations_text():
    answer = "This is the answer."
    citations = [
        {"source": "/data/file1.pdf", "chunk": "chunk1", "snippet": "snippet1"},
        {"source": "/data/file2.pdf", "chunk": "chunk2", "snippet": "snippet2"},
    ]
    
    result = append_citations_text(answer, citations)
    
    assert "This is the answer." in result
    assert "> Références :" in result
    assert "file1.pdf" in result
    assert "file2.pdf" in result
    
    # Empty citations
    assert append_citations_text(answer, []) == answer
    
    # Deduplication
    citations_dup = [
        {"source": "/data/file1.pdf", "chunk": "chunk1", "snippet": "snippet1"},
        {"source": "/data/file1.pdf", "chunk": "chunk1", "snippet": "snippet1"},
    ]
    result = append_citations_text(answer, citations_dup)
    # Should only have one citation entry ("> 1.")
    assert result.count("> 1.") == 1
    assert "> 2." not in result  # No second citation
