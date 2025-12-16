from typing import List
from llm_pipeline.retrieval import node_id

OFFICIAL_CODES = {"RC", "CCTP", "CCAP", "AE", "BPU", "DE", "MEMOIRE"}


def _is_official_doc(node) -> bool:
    """Renvoie True si le document est considéré comme une source officielle (DCE, BPU, etc)."""
    meta = getattr(node, "metadata", {})
    if not meta:
        return False
        
    # Critère 1: Code document explicite (DCE)
    code = meta.get("ao_doc_code")
    if code and code in OFFICIAL_CODES:
        return True
        
    # Critère 2: Phase "Document marché" (Phase 01)
    # Les fichiers dans 01-Document marché sont la référence
    phase_code = meta.get("ao_phase_code")
    if phase_code == "01":
        return True
        
    return False

def _prioritize_official_docs(nodes: List) -> List:
    """Remonte les documents officiels en tête de liste sans changer l'ordre relatif entre eux."""
    official = []
    others = []
    seen = set()
    
    for node in nodes:
        node_id_val = node_id(node)
        if node_id_val in seen:
            continue
        seen.add(node_id_val)
        
        if _is_official_doc(node):
            official.append(node)
        else:
            others.append(node)
            
    return official + others
