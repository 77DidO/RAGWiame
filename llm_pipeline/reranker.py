"""Module de reranking pour le pipeline RAG."""
from typing import List
from sentence_transformers import CrossEncoder

from llm_pipeline.context_formatting import _extract_node_text


class CrossEncoderReranker:
    """Reranker basé sur CrossEncoder pour améliorer la pertinence des résultats."""
    
    def __init__(
        self,
        model_name: str = "amberoad/bert-multilingual-passage-reranking-msmarco",
        batch_size: int = 8,
    ):
        self.cross_encoder = CrossEncoder(
            model_name,
            default_activation_function=None,
            max_length=512,
        )
        self.batch_size = batch_size
    
    def rerank(self, nodes: List, question: str, top_k: int) -> List:
        """Rerank nodes using cross-encoder scores."""
        if not nodes:
            return nodes
        
        query_text = question.strip()
        if not query_text:
            return nodes[:top_k]
        
        # Prepare pairs for cross-encoder
        pairs = []
        filtered_nodes = []
        for node in nodes:
            text = _extract_node_text(node)
            if not text:
                continue
            filtered_nodes.append(node)
            pairs.append([query_text, text])
        
        if not pairs:
            return nodes[:top_k]
        
        # Get scores from cross-encoder
        scores = self.cross_encoder.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        
        # Normalize scores
        if hasattr(scores, "tolist"):
            scores_seq = scores.tolist()
        else:
            scores_seq = list(scores)
        
        normalized_scores: List[float] = []
        for value in scores_seq:
            if isinstance(value, (list, tuple)):
                if not value:
                    normalized_scores.append(0.0)
                else:
                    normalized_scores.append(float(value[0]))
            else:
                normalized_scores.append(float(value))
        
        # Sort by score and return top_k
        ranked = sorted(
            zip(normalized_scores, filtered_nodes),
            key=lambda item: item[0],
            reverse=True,
        )
        return [node for _, node in ranked[:top_k]]
