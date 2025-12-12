"""Utilitaires pour enrichir les métadonnées d'ingestion."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, Mapping

from ingestion.config import ConnectorConfig

# Extensions et dossiers à ignorer par défaut lors de l'ingestion
DEFAULT_EXCLUDED_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".bz2",
    ".bak",
    ".old",
    ".tmp",
    ".cnf",
    ".dat",
    ".ori",
    ".xnf",
    ".rpt",
    ".mpp",
    ".msg",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
}
DEFAULT_EXCLUDED_KEYWORDS = {"sauvegarde", "backup", "__macosx"}

AO_FOLDER_PATTERN = re.compile(
    r"^(?P<id>[A-Za-z0-9_-]+)\s*-\s*(?P<city>[^-]+?)\s*-\s*(?P<object>.+)$"
)
PHASE_PATTERN = re.compile(r"^(?P<code>\d{2})[-_\s]*(?P<label>.+)$")
DOC_ROLE_PATTERNS: Mapping[str, Iterable[str]] = {
    "BPU": ("bpu", "bordereau des prix"),
    "DE": ("detail estimatif", "détail estimatif", "de "),
    "AE": ("acte d'engagement", "ae "),
    "RC": ("reglement de consultation", "règlement de consultation", "rc "),
    "CCAP": ("ccap",),
    "CCTP": ("cctp",),
    "PLANNING": ("planning",),
    "MEMOIRE": ("memoire technique", "mémoire technique"),
    "PRESENTATION": ("presentation de l'entreprise", "présentation de l'entreprise"),
}
DOC_ROLE_LABELS: Mapping[str, str] = {
    "BPU": "Bordereau des prix unitaires",
    "DE": "Détail estimatif",
    "AE": "Acte d'engagement",
    "RC": "Règlement de consultation",
    "CCAP": "Cahier des clauses administratives particulières",
    "CCTP": "Cahier des clauses techniques particulières",
    "PLANNING": "Planning prévisionnel",
    "MEMOIRE": "Mémoire technique",
    "PRESENTATION": "Présentation entreprise",
}
SPIGAO_PATTERN = re.compile(r"DIE\s*-\s*([0-9a-fA-F-]{8,})")
SIGNATURE_PATTERN = re.compile(r"signature\s*(?P<label>[0-9]+)", re.IGNORECASE)
PROOF_KEYWORDS = ("preuve_de_depot", "confirmation de la cloture", "confirmation de dépôt")


def should_exclude_path(path: Path, config: ConnectorConfig) -> bool:
    """Renvoie True si le fichier doit être ignoré selon son extension ou son dossier."""
    ext = path.suffix.lower()
    excluded_exts = {e.lower() for e in config.excluded_extensions}
    excluded_exts.update(DEFAULT_EXCLUDED_EXTENSIONS)
    if ext in excluded_exts:
        return True

    lowered_parts = [part.lower() for part in path.parts]
    keywords = set(DEFAULT_EXCLUDED_KEYWORDS)
    custom_keywords = config.extra.get("excluded_keywords")
    if isinstance(custom_keywords, str):
        keywords.add(custom_keywords.lower())
    elif isinstance(custom_keywords, Iterable):
        keywords.update(str(keyword).lower() for keyword in custom_keywords)

    if any(keyword in lowered_parts for keyword in keywords):
        return True

    return False


def extract_ao_metadata(path: Path) -> Dict[str, object]:
    """Extrait les métadonnées spécifiques aux dossiers AO à partir du chemin."""
    metadata: Dict[str, object] = {}
    ao_root = _find_ao_root(path)
    if ao_root:
        match = AO_FOLDER_PATTERN.match(ao_root.name)
        if match:
            metadata["ao_id"] = match.group("id").strip()
            metadata["ao_commune"] = match.group("city").strip()
            metadata["ao_objet"] = match.group("object").strip()
        metadata["ao_is_global_doc"] = False

        try:
            relative_parts = path.relative_to(ao_root).parts
        except ValueError:
            relative_parts = ()

        if relative_parts:
            phase_part = relative_parts[0]
            phase_match = PHASE_PATTERN.match(phase_part)
            if phase_match:
                metadata["ao_phase_code"] = phase_match.group("code")
                metadata["ao_phase_label"] = phase_match.group("label").strip()
            if len(relative_parts) > 1:
                metadata["ao_section"] = relative_parts[1].split()[0]

    else:
        metadata["ao_is_global_doc"] = True

    name_lower = path.name.lower()
    for code, targets in DOC_ROLE_PATTERNS.items():
        if any(target in name_lower for target in targets):
            metadata["ao_doc_code"] = code
            metadata["ao_doc_role"] = DOC_ROLE_LABELS.get(code, code)
            break

    spigao_match = SPIGAO_PATTERN.search(path.as_posix())
    if spigao_match:
        metadata["spigao_batch_id"] = spigao_match.group(1)

    signature_match = SIGNATURE_PATTERN.search(name_lower)
    if signature_match:
        metadata["ao_signed"] = True
        metadata["ao_signature_label"] = signature_match.group("label")
    elif "signature" in name_lower:
        metadata["ao_signed"] = True

    if any(keyword in name_lower for keyword in PROOF_KEYWORDS):
        metadata["submission_proof"] = True

    if any("sauvegarde" in part.lower() for part in path.parts):
        metadata["ao_safeguard"] = True

    if path.suffix.lower() == ".msg":
        metadata["email_source"] = True

    return metadata


def _find_ao_root(path: Path) -> Path | None:
    """Retourne le dossier parent correspondant à AO/<ID - Commune - Objet>."""
    for ancestor in path.parents:
        if ancestor.parent.name.upper() == "AO":
            return ancestor
    return None


__all__ = [
    "DEFAULT_EXCLUDED_EXTENSIONS",
    "should_exclude_path",
    "extract_ao_metadata",
]
