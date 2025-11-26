import pytest
from unittest.mock import MagicMock, patch
from llm_pipeline.retrieval import hybrid_query, _build_bm25_nodes

# Mock LlamaIndex classes
class MockNode:
    def __init__(self, id_, text="", metadata=None, score=0.0):
        self.id_ = id_
        self.text = text
        self.metadata = metadata or {}
        self.score = score
        
    def get_content(self):
        return self.text

def test_build_bm25_nodes():
    hits = [
        {
            "_id": "doc1",
            "_score": 1.5,
            "_source": {"content": "text content", "source": "file.txt"}
        }
    ]
    nodes = _build_bm25_nodes(hits)
    assert len(nodes) == 1
    node = nodes[0]
    assert node.id_ == "doc1"
    assert node.score == 1.5
    assert node.text == "text content"
    assert node.metadata["source"] == "file.txt"

def test_hybrid_query_vector_only():
    # Mock pipeline
    pipeline = MagicMock()
    pipeline.initial_top_k = 5
    pipeline.index.as_retriever.return_value.retrieve.return_value = [
        MockNode("vec1", "vector text", score=0.9)
    ]
    
    # Mock bm25_search to return empty
    with patch("llm_pipeline.retrieval.bm25_search", return_value=[]) as mock_bm25:
        nodes, hits = hybrid_query(pipeline, "question")
        
        assert len(nodes) == 1
        assert nodes[0].id_ == "vec1"
        assert len(hits) == 1
        assert hits[0]["id"] == "vec1"

def test_hybrid_query_fusion():
    pipeline = MagicMock()
    pipeline.initial_top_k = 5
    
    # Vector results
    vec_node = MockNode("vec1", "vec text", score=0.5)
    pipeline.index.as_retriever.return_value.retrieve.return_value = [vec_node]
    
    # BM25 results
    bm25_hits = [{
        "_id": "bm1", "_score": 2.0, "_source": {"content": "bm text"}
    }]
    
    with patch("llm_pipeline.retrieval.bm25_search", return_value=bm25_hits) as mock_bm25:
        nodes, hits = hybrid_query(pipeline, "question")
        
        # Should contain both
        ids = [n.id_ for n in nodes]
        assert "vec1" in ids
        assert "bm1" in ids
