"""Tests pour le module reranker."""
import pytest
from unittest.mock import MagicMock, Mock
from llm_pipeline.reranker import CrossEncoderReranker


def test_reranker_initialization():
    """Test que le reranker s'initialise correctement."""
    reranker = CrossEncoderReranker()
    assert reranker.cross_encoder is not None
    assert reranker.batch_size == 8


def test_reranker_empty_nodes():
    """Test avec une liste vide de nodes."""
    reranker = CrossEncoderReranker()
    result = reranker.rerank([], "test question", top_k=5)
    assert result == []


def test_reranker_no_question():
    """Test avec une question vide."""
    reranker = CrossEncoderReranker()
    
    # Mock nodes
    mock_nodes = [Mock(), Mock(), Mock()]
    for i, node in enumerate(mock_nodes):
        node.text = f"text {i}"
        node.get_content = lambda i=i: f"text {i}"
    
    result = reranker.rerank(mock_nodes, "", top_k=2)
    assert len(result) == 2
    assert result == mock_nodes[:2]


def test_reranker_basic_reranking():
    """Test du reranking basique."""
    reranker = CrossEncoderReranker()
    
    # Mock nodes with text
    mock_nodes = []
    for i in range(5):
        node = Mock()
        node.text = f"Document {i} about testing"
        node.get_content = lambda i=i: f"Document {i} about testing"
        mock_nodes.append(node)
    
    # Mock cross_encoder.predict to return scores
    reranker.cross_encoder.predict = Mock(return_value=[0.9, 0.3, 0.7, 0.5, 0.1])
    
    result = reranker.rerank(mock_nodes, "test question", top_k=3)
    
    # Should return top 3 by score
    assert len(result) == 3
    # Verify predict was called
    assert reranker.cross_encoder.predict.called
