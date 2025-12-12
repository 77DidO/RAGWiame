"""Connecteur Excel multi-onglets."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ingestion.config import ConnectorConfig, ExcelConnectorOptions
from ingestion.connectors.base import BaseConnector, DocumentChunk
from ingestion.metadata_utils import extract_ao_metadata, should_exclude_path

try:
    import pandas as pd
except ImportError:
    pd = None  # Sera vérifié dans load()



class ExcelConnector(BaseConnector):
    """Découpe les classeurs Excel par onglet et par bloc tabulaire."""

    document_type = "excel"

    def __init__(self, config: ConnectorConfig, options: ExcelConnectorOptions) -> None:
        super().__init__(config)
        self.options = options

    def discover(self) -> Iterable[Path]:
        patterns = ("*.xls", "*.xlsx")
        for path in self.config.paths:
            if path.is_dir():
                for pattern in patterns:
                    iterator = path.rglob(pattern) if self.config.recursive else path.glob(pattern)
                    for candidate in iterator:
                        if should_exclude_path(candidate, self.config):
                            continue
                        yield candidate
            elif path.suffix.lower() in {".xls", ".xlsx"} and not should_exclude_path(path, self.config):
                yield path

    def load(self, path: Path) -> Iterable[DocumentChunk]:
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - dépendance optionnelle
            raise ImportError("pandas doit être installé pour utiliser le connecteur Excel") from exc

        excel_file = pd.ExcelFile(path)
        sheet_names = (
            self.options.sheet_whitelist
            if self.options.sheet_whitelist
            else excel_file.sheet_names
        )
        
        print(f"DEBUG: ExcelConnector.load path={path} (semantic chunking enabled)", flush=True)
        
        for sheet_name in sheet_names:
            dataframe = excel_file.parse(sheet_name)
            dataframe = self._truncate(dataframe)
            if dataframe.empty:
                continue
            
            # Détecter le total général s'il existe
            global_total = self._extract_global_total(dataframe, sheet_name)
            
            # Détecter les sections dans le tableau
            sections = self._detect_sections(dataframe)
            
            if sections:
                # Chunking par section sémantique
                print(f"DEBUG: Found {len(sections)} sections in {sheet_name}", flush=True)
                for chunk_idx, section in enumerate(sections):
                    chunk_text = self._format_section_chunk(
                        dataframe, 
                        section, 
                        sheet_name, 
                        global_total
                    )
                    
                    if chunk_text:
                        metadata = {
                            "source": str(path),
                            "sheet": sheet_name,
                            "document_type": self.document_type,
                            "chunk_index": chunk_idx,
                            "section_name": section.get("name", ""),
                            "start_row": section["start_row"] + 1,
                            "end_row": section["end_row"],
                        }
                        
                        # Ajouter le total de section si détecté
                        if section.get("total"):
                            metadata["section_total"] = section["total"]
                        metadata.update(extract_ao_metadata(path))
                        
                        yield DocumentChunk(
                            id=f"{path.stem}-{sheet_name}-section{chunk_idx}",
                            text=chunk_text,
                            metadata=metadata,
                        )
            else:
                # Fallback: chunking par blocs de lignes (amélioré)
                print(f"DEBUG: No sections detected in {sheet_name}, using row-based chunking", flush=True)
                chunk_size = getattr(self.options, "chunk_size", 20)  # Augmenté de 10 à 20
                
                for chunk_idx, start_row in enumerate(range(0, len(dataframe), chunk_size)):
                    end_row = min(start_row + chunk_size, len(dataframe))
                    chunk_text = self._format_row_chunk(
                        dataframe, 
                        start_row, 
                        end_row, 
                        sheet_name, 
                        global_total
                    )
                    
                    if chunk_text:
                        metadata = {
                            "source": str(path),
                            "sheet": sheet_name,
                            "document_type": self.document_type,
                            "chunk_index": chunk_idx,
                            "start_row": start_row + 1,
                            "end_row": end_row,
                        }
                        metadata.update(extract_ao_metadata(path))
                        yield DocumentChunk(
                            id=f"{path.stem}-{sheet_name}-chunk{chunk_idx}",
                            text=chunk_text,
                            metadata=metadata,
                        )

    def _extract_global_total(self, dataframe: "pd.DataFrame", sheet_name: str) -> str:
        """Extrait le total général du tableau s'il existe."""
        import pandas as pd
        
        # Chercher dans les dernières lignes
        for idx in range(max(0, len(dataframe) - 5), len(dataframe)):
            row = dataframe.iloc[idx]
            row_text = " ".join([str(v) for v in row if pd.notna(v)]).lower()
            
            # Patterns de totaux
            if any(keyword in row_text for keyword in ["total", "montant total", "total général", "total ht", "total ttc"]):
                # Extraire les valeurs numériques
                for val in row:
                    if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                        return f"{val:,.2f} EUR".replace(",", " ")
        
        return ""

    def _detect_sections(self, dataframe: "pd.DataFrame") -> list:
        """Détecte les sections dans le tableau (titres, sous-totaux)."""
        import pandas as pd
        import re
        
        sections = []
        current_section = None
        
        for idx, row in dataframe.iterrows():
            row_text = " ".join([str(v) for v in row if pd.notna(v)]).strip().lower()
            
            # Détecter un titre de section (ligne avec peu de colonnes remplies, texte en majuscules)
            non_empty = sum(1 for v in row if pd.notna(v) and str(v).strip())
            
            # Pattern de section : ligne avec 1-3 colonnes remplies, contient des mots-clés
            is_section_header = (
                non_empty <= 3 and 
                len(row_text) > 3 and
                any(keyword in row_text for keyword in [
                    "section", "chapitre", "partie", "lot", 
                    "fourniture", "main", "matériel", "travaux",
                    "sous-traitance", "prestation"
                ])
            )
            
            # Détecter un sous-total
            is_subtotal = any(keyword in row_text for keyword in [
                "sous-total", "sous total", "subtotal", "total partiel"
            ])
            
            if is_section_header:
                # Sauvegarder la section précédente
                if current_section:
                    current_section["end_row"] = idx - 1
                    sections.append(current_section)
                
                # Nouvelle section
                section_name = row_text.title()
                current_section = {
                    "name": section_name,
                    "start_row": idx,
                    "end_row": len(dataframe) - 1,  # Par défaut jusqu'à la fin
                    "total": None
                }
            
            elif is_subtotal and current_section:
                # Extraire le montant du sous-total
                for val in row:
                    if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                        current_section["total"] = f"{val:,.2f} EUR".replace(",", " ")
                        break
        
        # Sauvegarder la dernière section
        if current_section:
            sections.append(current_section)
        
        return sections

    def _format_section_chunk(
        self, 
        dataframe: "pd.DataFrame", 
        section: dict, 
        sheet_name: str, 
        global_total: str
    ) -> str:
        """Formate un chunk pour une section sémantique."""
        import pandas as pd
        
        lines = []
        lines.append(f"Sheet: {sheet_name}")
        
        if global_total:
            lines.append(f"TOTAL GÉNÉRAL: {global_total}")
        
        lines.append("")
        lines.append(f"Section: {section['name']}")
        lines.append(f"Rows {section['start_row'] + 1}-{section['end_row'] + 1}")
        lines.append("")
        
        # Extraire les données de la section
        section_df = dataframe.iloc[section["start_row"]:section["end_row"] + 1]
        headers = dataframe.columns.tolist()
        
        for row_idx, row in section_df.iterrows():
            row_lines = []
            for col_name in headers:
                value = row[col_name]
                if pd.notna(value) and str(value).strip():
                    header_str = str(col_name)
                    is_unnamed = header_str.startswith("Unnamed")
                    
                    # Formatage des nombres
                    val_str = str(value)
                    if isinstance(value, (int, float)):
                        try:
                            if value > 999:
                                space_fmt = f"{int(value):_}".replace("_", " ")
                                val_str = f"{value} (lisible: {space_fmt})"
                        except Exception:
                            pass
                    
                    if not is_unnamed:
                        row_lines.append(f"{header_str}: {val_str}")
                    else:
                        row_lines.append(val_str)
            
            if row_lines:
                lines.append(f"  • {', '.join(row_lines)}")
        
        if section.get("total"):
            lines.append("")
            lines.append(f"SOUS-TOTAL {section['name']}: {section['total']}")
        
        return "\n".join(lines) if len(lines) > 5 else ""

    def _format_row_chunk(
        self, 
        dataframe: "pd.DataFrame", 
        start_row: int, 
        end_row: int, 
        sheet_name: str, 
        global_total: str
    ) -> str:
        """Formate un chunk basé sur des lignes (fallback)."""
        import pandas as pd
        
        chunk_df = dataframe.iloc[start_row:end_row]
        headers = dataframe.columns.tolist()
        
        lines = []
        lines.append(f"Sheet: {sheet_name}")
        
        if global_total:
            lines.append(f"TOTAL GÉNÉRAL: {global_total}")
        
        lines.append(f"Rows {start_row + 1}-{end_row} of {len(dataframe)}")
        lines.append("")
        
        for row_idx, row in chunk_df.iterrows():
            row_lines = []
            for col_name in headers:
                value = row[col_name]
                if pd.notna(value) and str(value).strip():
                    header_str = str(col_name)
                    is_unnamed = header_str.startswith("Unnamed")
                    
                    val_str = str(value)
                    if isinstance(value, (int, float)):
                        try:
                            if value > 999:
                                space_fmt = f"{int(value):_}".replace("_", " ")
                                val_str = f"{value} (lisible: {space_fmt})"
                        except Exception:
                            pass
                    
                    if not is_unnamed:
                        row_lines.append(f"{header_str}: {val_str}")
                    else:
                        row_lines.append(val_str)
            
            if row_lines:
                lines.append(f"Row {row_idx + 1}:")
                lines.extend([f"  - {line}" for line in row_lines])
                lines.append("")
        
        return "\n".join(lines) if len(lines) > 3 else ""


    def _truncate(self, dataframe: "pd.DataFrame") -> "pd.DataFrame":
        rows = self.options.max_rows
        cols = self.options.max_columns
        if rows is not None:
            dataframe = dataframe.head(rows)
        if cols is not None:
            dataframe = dataframe.iloc[:, :cols]
        if self.options.load_formulas and hasattr(dataframe, "attrs"):
            dataframe.attrs["formulas"] = True
        return dataframe


__all__ = ["ExcelConnector"]
