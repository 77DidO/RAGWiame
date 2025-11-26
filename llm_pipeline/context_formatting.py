from typing import List, Tuple, Dict, Set
import re
import json

def _select_relevant_text(text: str, keywords: List[str], max_chunk_chars: int = 800) -> str:
    """Select relevant sentences containing keywords, or return truncated text."""
    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()
    
    # Split into sentences (simple regex on punctuation)
    # This splits after . ? ! followed by space
    sentences = re.split(r"(?<=[.!?])\s+", text)
    
    if keywords:
        # Filter sentences containing at least one keyword (case insensitive)
        matches = [
            s for s in sentences 
            if any(k in s.lower() for k in keywords)
        ]
    else:
        matches = []
    
    # If matches found, join them. Otherwise use full text.
    snippet = " ".join(matches) if matches else text
    
    # Truncate if necessary
    if len(snippet) > max_chunk_chars:
        snippet = snippet[:max_chunk_chars].rstrip() + "…"
        
    return snippet


def _extract_node_text(node) -> str:
    """Extract text from a node with robust fallback strategies."""
    text = ""
    
    # 1. Try node.node.get_content() (LlamaIndex TextNode)
    if hasattr(node, "node") and node.node is not None:
        try:
            text = node.node.get_content().strip()
        except Exception:
            pass
            
    # 2. Fallback to node.text
    if not text:
        text = getattr(node, "text", "").strip()
        
    # 3. Fallback to metadata _node_content (Qdrant/LlamaIndex serialization)
    if not text and hasattr(node, "metadata") and node.metadata:
        node_content = node.metadata.get("_node_content")
        if node_content:
            try:
                content_dict = json.loads(node_content)
                text = content_dict.get("text", "").strip()
            except Exception:
                pass
                
    return text


def format_context(
    nodes: List, 
    question: str, 
    max_chunk_chars: int = 800, 
    top_k: int = 6
) -> Tuple[str, Dict[str, str]]:
    """Format context from nodes, deduplicating by source and removing XML tags."""
    
    # Extract keywords for relevance filtering
    keywords = [kw for kw in re.findall(r"[a-z0-9]+", question.lower()) if len(kw) > 2]
    
    chunks: List[str] = []
    snippet_map: Dict[str, str] = {}
    citation_idx_map: Dict[str, int] = {}
    seen_sources: Set[str] = set()
    
    for node in nodes:
        # Stop if we have enough chunks
        if len(chunks) >= top_k:
            break
            
        metadata = getattr(node, "metadata", {}) or {}
        source = metadata.get("source", "inconnu")
        
        # Deduplication: one snippet per source file
        if source in seen_sources:
            continue
            
        text = _extract_node_text(node)
        if not text:
            continue
            
        # Mark source as seen
        seen_sources.add(source)
        
        # Assign citation number
        if source not in citation_idx_map:
            citation_idx_map[source] = len(citation_idx_map) + 1
        citation_num = citation_idx_map[source]
        
        # Build header: [1] or [1] (Page X)
        header = f"[{citation_num}]"
        page = metadata.get("page")
        if page is not None:
            header += f" (Page {page})"
            
        # Select relevant text
        snippet = _select_relevant_text(text, keywords, max_chunk_chars)
        
        # Store in snippet map for citations
        # Key format: source::chunk_index (or id)
        chunk_id = metadata.get("chunk_index", getattr(node, "id_", ""))
        key = f"{source}::{chunk_id}"
        snippet_map[key] = snippet
        
        # Add to context (Clean text, no <source> tags)
        chunks.append(f"{header} {snippet}")
        
    if not chunks:
        return "Aucun extrait pertinent.", snippet_map
        
    return "\n\n".join(chunks), snippet_map
