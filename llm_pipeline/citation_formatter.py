"""Formatage des citations pour l'API Gateway."""
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

from llm_pipeline.config import DATA_ROOT, PUBLIC_GATEWAY_URL


def append_citations_text(answer: str, citations: List[Dict[str, Any]]) -> str:
    """Ajoute un bloc de références formatées à la réponse."""
    if not citations:
        return answer
    unique: List[Dict[str, Any]] = []
    seen = set()
    for citation in citations:
        source = str(citation.get("source", ""))
        chunk = str(citation.get("chunk", "") or "")
        key = (source, chunk)
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    if not unique:
        return answer
    block_lines = ["> Références :"]
    for idx, citation in enumerate(unique, start=1):
        link = format_reference_link(citation)
        snippet = format_citation_snippet(citation)
        line = f"> {idx}. {link}"
        block_lines.append(line)
        if snippet:
            block_lines.append(f">    ↳ {snippet}")
    joined = "\n".join(block_lines)
    return f"{answer}\n\n{joined}"


def prettify_display_path(relative: str) -> str:
    """Make citation labels cleaner (strip conversion suffixes like .txt.xlsx)."""
    normalized = relative.replace("\\", "/")
    name = Path(normalized).name
    pretty = re.sub(r"\.txt\.(pdf|docx|xlsx|xls|csv)\b", r".\1", name, flags=re.IGNORECASE)
    pretty = re.sub(r"\.(pdf|docx|xlsx|xls|csv)\.\1\b", r".\1", pretty, flags=re.IGNORECASE)
    if normalized.endswith(name):
        prefix = normalized[: -len(name)]
        return f"{prefix}{pretty}"
    return pretty


def format_reference_link(citation: Dict[str, Any]) -> str:
    """Formate un lien de citation vers /files/view."""
    source = str(citation.get("source", "source inconnue"))
    chunk = str(citation.get("chunk", "") or "").strip()
    relative = source
    if source.startswith("/data/"):
        relative = source[len("/data/") :]
    elif source.startswith(str(DATA_ROOT)):
        relative = str(Path(source).relative_to(DATA_ROOT))
    relative = relative.replace("\\", "/")
    display_path = prettify_display_path(relative)
    link = f"{PUBLIC_GATEWAY_URL}/files/view?path={quote(relative)}"
    base_name = Path(display_path).name or display_path
    chunk_suffix = format_chunk_suffix(base_name, chunk)
    if chunk_suffix:
        display_path = f"{display_path} - {chunk_suffix}"
    safe_label = display_path.replace("`", "'")
    return f"[{safe_label}]({link})"


def format_citation_snippet(citation: Dict[str, Any]) -> str:
    """Extrait et formate le snippet d'une citation."""
    snippet = str(citation.get("snippet", "") or "").strip()
    if not snippet:
        return ""
    chunk = str(citation.get("chunk", "") or "")
    normalized_chunk = " ".join(chunk.split()).strip().strip('"').lower()
    normalized_snippet = " ".join(snippet.split()).strip().strip('"').lower()
    if normalized_chunk and normalized_chunk == normalized_snippet:
        return ""
    snippet = " ".join(snippet.split())
    if len(snippet) > 120:
        snippet = snippet[:120].rstrip() + "…"
    return snippet


def format_chunk_suffix(base_name: str, chunk: str) -> str:
    """Formate le suffixe de chunk pour affichage."""
    if not chunk:
        return ""
    cleaned_chunk = " ".join(chunk.split())
    if cleaned_chunk.lower() == base_name.lower():
        return ""
    parts = [part.strip() for part in cleaned_chunk.split("::") if part.strip()]
    if parts and parts[0].lower() == base_name.lower():
        parts = parts[1:]
    return " · ".join(parts)


def replace_file_mentions_with_citations(answer: str, citations: List[Dict[str, Any]]) -> str:
    """Replace file path mentions in answer with citation numbers [1], [2], etc.
    
    This ensures consistent citation format even if the LLM doesn't follow instructions perfectly.
    """
    if not citations:
        return answer
    
    print(f"DEBUG POST-PROCESSING: Original answer: {answer[:200]}...", flush=True)
    print(f"DEBUG POST-PROCESSING: Citations count: {len(citations)}", flush=True)
    
    modified_answer = answer
    
    # Build a map of source to citation number
    source_map = {}
    for idx, citation in enumerate(citations, start=1):
        source = str(citation.get("source", ""))
        if source:
            source_map[source] = f"[{idx}]"
            print(f"DEBUG POST-PROCESSING: Citation {idx}: {source}", flush=True)
    
    # Pattern 1: Replace any mention of .xlsx or .docx files with their citation number
    for source, citation_num in source_map.items():
        # Extract filename
        filename = source.split('/')[-1].split('\\')[-1]
        
        # Try multiple patterns
        patterns = [
            # Full path with /data/
            re.escape(source),
            # Partial path (anything before the filename)
            r'[^\s]*' + re.escape(filename),
            # Just the filename
            re.escape(filename),
            # Filename without extension
            re.escape(filename.rsplit('.', 1)[0]) + r'\.xlsx',
            re.escape(filename.rsplit('.', 1)[0]) + r'\.docx',
        ]
        
        for pattern in patterns:
            # Replace with citation number
            before = modified_answer
            modified_answer = re.sub(pattern, citation_num, modified_answer, flags=re.IGNORECASE)
            if before != modified_answer:
                print(f"DEBUG POST-PROCESSING: Pattern '{pattern}' matched!", flush=True)
    
    # Clean up any remaining parentheses around citations like ([1])
    modified_answer = re.sub(r'\(\[(\d+)\]\)', r'[\1]', modified_answer)
    
    # Clean up duplicate citations like [1][1] or [1] [1]
    modified_answer = re.sub(r'(\[\d+\])\s*\1', r'\1', modified_answer)
    
    # Clean up multiple spaces
    modified_answer = re.sub(r'\s+', ' ', modified_answer)
    
    print(f"DEBUG POST-PROCESSING: Modified answer: {modified_answer[:200]}...", flush=True)
    
    return modified_answer


def convert_citations_to_openwebui_format(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert pipeline citations to Open WebUI format.
    
    Each citation becomes a separate element in the array (not grouped by source).
    This allows Open WebUI to create proper sourceIds for clickable [1], [2], [3].
    """
    if not citations:
        return []
    
    result = []
    for citation in citations:
        source = str(citation.get("source", ""))
        if not source:
            continue
        
        # Generate file URL
        relative = source
        if source.startswith("/data/"):
            relative = source[len("/data/"):]
        elif source.startswith(str(DATA_ROOT)):
            relative = str(Path(source).relative_to(DATA_ROOT))
        relative = relative.replace("\\", "/")
        file_url = f"{PUBLIC_GATEWAY_URL}/files/view?path={quote(relative)}"
        
        # Extract snippet
        snippet = str(citation.get("snippet", "")).strip()
        
        # Extract page number from chunk if present
        chunk = str(citation.get("chunk", ""))
        page_match = re.search(r'page[_\s]*(\d+)', chunk, re.IGNORECASE)
        
        metadata = {"source": source}
        if page_match:
            metadata["page"] = int(page_match.group(1))
        
        # Create individual citation entry
        result.append({
            "source": {
                "name": source,
                "embed_url": file_url
            },
            "document": [snippet] if snippet else [],
            "metadata": [metadata],
            "distances": []
        })
    
    return result
