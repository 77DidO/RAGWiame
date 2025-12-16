from typing import List, Tuple, Dict
import re
import json
from llm_pipeline.text_utils import tokenize, citation_key

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
    top_k: int = 6,
    max_chunks_per_source: int = 2,
) -> Tuple[str, Dict[str, str]]:
    """Format context from nodes, permettant plusieurs extraits par source (jusqu'à max_chunks_per_source)."""
    
    # Extract keywords for relevance filtering
    keywords = [kw for kw in tokenize(question) if len(kw) > 2]
    
    chunks: List[str] = []
    snippet_map: Dict[str, str] = {}
    citation_idx_map: Dict[str, int] = {}
    per_source_counts: Dict[str, int] = {}
    
    for node in nodes:
        # Stop if we have enough chunks
        if len(chunks) >= top_k:
            break
            
        metadata = getattr(node, "metadata", {}) or {}
        source = metadata.get("source", "inconnu")
        count_for_source = per_source_counts.get(source, 0)
        
        # Limiter le nombre d'extraits par fichier pour ne pas perdre d'information clé
        if count_for_source >= max_chunks_per_source:
            continue
            
        text = _extract_node_text(node)
        if not text:
            continue
            
        # Update counter for this source
        per_source_counts[source] = count_for_source + 1
        
        # Assign citation number
        if source not in citation_idx_map:
            citation_idx_map[source] = len(citation_idx_map) + 1
        citation_num = citation_idx_map[source]
        
        # Build header: [1] (Source: ... | Date: ... | Type: ...)
        header_parts = []
        
        # 1. Source (Nom fichier)
        clean_source = source.split("/")[-1] if "/" in source else source
        header_parts.append(f"Source: {clean_source}")
        
        # 2. Page (si dispo)
        page = metadata.get("page")
        # Phase / Section (Dossier parent)
        phase = metadata.get("ao_phase_label") or metadata.get("ao_phase_code")
        section = metadata.get("ao_section")
        
        phase_str = f"Phase: {phase}" if phase else ""
        section_str = f"Dossier: {section}" if section else ""
        
        # On combine proprement
        if phase and section:
            header_parts.append(f"{phase_str} ({section_str})")
        elif phase:
            header_parts.append(phase_str)
        elif section:
            header_parts.append(section_str)

        # Type de document spécifique
        doc_type = metadata.get("ao_doc_code") or metadata.get("doc_hint") or metadata.get("ao_doc_role") or metadata.get("content_type_detected")
        if doc_type:
            header_parts.append(f"Type: {doc_type}")
            
        # Statut Signature
        signed = metadata.get("ao_signed")
        if signed: # signed peut être True ou "true" (str)
            label = metadata.get("ao_signature_label", "")
            header_parts.append(f"✅ SIGNE ({label})" if label else "✅ SIGNE")

        # Date
        date_str = metadata.get("date") or metadata.get("creation_date")
        if date_str:
             header_parts.append(f"Date: {date_str.split('T')[0]}")
            
        header = f"[{citation_num}] 📄 {' | '.join(header_parts)}"
            
        # Select relevant text
        snippet = _select_relevant_text(text, keywords, max_chunk_chars)
        
        # Store in snippet map for citations
        # Key format: source::chunk_index (or id)
        chunk_id = metadata.get("chunk_index", getattr(node, "id_", ""))
        key = citation_key(source, chunk_id)
        snippet_map[key] = snippet
        
        # Add to context (Clean text, no <source> tags)
        chunks.append(f"{header} {snippet}")
        
    if not chunks:
        return "Aucun extrait pertinent.", snippet_map
        
    return "\n\n".join(chunks), snippet_map
