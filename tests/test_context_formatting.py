import pytest
from llm_pipeline.context_formatting import format_context, _select_relevant_text, _extract_node_text

class MockNode:
    def __init__(self, text, metadata=None, id_="node_id"):
        self.text = text
        self.metadata = metadata or {}
        self.id_ = id_

def test_select_relevant_text():
    text = "Ceci est une phrase importante. Ceci est du bruit. Le mot clé est ici."
    
    # No keywords -> returns full text (or truncated)
    assert _select_relevant_text(text, []) == text
    
    # Keyword match
    snippet = _select_relevant_text(text, ["clé"])
    assert "Le mot clé est ici" in snippet
    assert "bruit" not in snippet

    # Truncation
    long_text = "a" * 1000
    snippet = _select_relevant_text(long_text, [], max_chunk_chars=100)
    assert len(snippet) <= 101 # 100 + ellipsis potentially

def test_extract_node_text():
    # Simple attribute
    node = MockNode("simple text")
    assert _extract_node_text(node) == "simple text"
    
    # Nested node object (LlamaIndex style mock)
    class InnerNode:
        def get_content(self): return "inner content"
    
    complex_node = MockNode("")
    complex_node.node = InnerNode()
    assert _extract_node_text(complex_node) == "inner content"

def test_format_context():
    nodes = [
        MockNode("Contenu source 1", {"source": "doc1.pdf", "page": 10}, "id1"),
        MockNode("Contenu source 2", {"source": "doc2.txt"}, "id2")
    ]
    
    context, snippet_map = format_context(nodes, "question")
    
    # Check context structure
    assert "[1] (Page 10)" in context
    assert "Contenu source 1" in context
    assert "[2]" in context
    assert "Contenu source 2" in context
    
    # Check snippet map
    assert "doc1.pdf::id1" in snippet_map
    assert snippet_map["doc1.pdf::id1"] == "Contenu source 1"

def test_format_context_deduplication():
    nodes = [
        MockNode("Snippet 1", {"source": "doc1.pdf", "page": 1}, "id1"),
        MockNode("Snippet 2", {"source": "doc1.pdf", "page": 2}, "id2"), # Same source
        MockNode("Snippet 3", {"source": "doc2.pdf", "page": 1}, "id3")
    ]
    
    context, snippet_map = format_context(nodes, "question")
    
    # Should only contain Snippet 1 and Snippet 3
    assert "Snippet 1" in context
    assert "Snippet 3" in context
    assert "Snippet 2" not in context
    
    # Check citation numbers
    assert "[1]" in context
    assert "[2]" in context
    # Should not have [3]
    assert "[3]" not in context
