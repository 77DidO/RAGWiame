"""Connecteur Excel multi-onglets."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ingestion.config import ConnectorConfig, ExcelConnectorOptions
from ingestion.connectors.base import BaseConnector, DocumentChunk

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
        for path in self.config.paths:
            if path.is_dir():
                yield from path.rglob("*.xlsx") if self.config.recursive else path.glob("*.xlsx")
            elif path.suffix.lower() in {".xls", ".xlsx"}:
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
        # Validation du chunk_size
        chunk_size = getattr(self.options, "chunk_size", 10)
        if chunk_size <= 0:
            raise ValueError("ExcelConnector chunk_size must be a positive integer")
        # Log de debug
        print(f"DEBUG: ExcelConnector.load path={path} chunk_size={chunk_size}", flush=True)
        
        for sheet_name in sheet_names:
            dataframe = excel_file.parse(sheet_name)
            dataframe = self._truncate(dataframe)
            if dataframe.empty:
                continue
            
            headers = dataframe.columns.tolist()
            
            # Générer un chunk par bloc de lignes
            for chunk_idx, start_row in enumerate(range(0, len(dataframe), chunk_size)):
                end_row = min(start_row + chunk_size, len(dataframe))
                chunk_df = dataframe.iloc[start_row:end_row]
                
                # Convertir en texte lisible avec contexte
                lines = []
                lines.append(f"Sheet: {sheet_name}")
                lines.append(f"Rows {start_row+1}-{end_row} of {len(dataframe)}")
                lines.append("")
                
                # Ajouter les données ligne par ligne avec les en-têtes
                for row_idx, row in chunk_df.iterrows():
                    row_lines = []
                    for col_name in headers:
                        value = row[col_name]
                        # Filtrer les valeurs vides ou NaN
                        if pd.notna(value) and str(value).strip():
                            # Gestion des en-têtes "Unnamed"
                            header_str = str(col_name)
                            is_unnamed = header_str.startswith("Unnamed")
                            
                            # Formatage des nombres (ajout de variantes avec espaces pour le RAG)
                            val_str = str(value)
                            if isinstance(value, (int, float)):
                                try:
                                    # Créer une version avec séparateur de milliers (espace)
                                    # Ex: 220792.79 -> "220 792"
                                    int_val = int(value)
                                    if int_val > 999:
                                        space_fmt = f"{int_val:_}".replace("_", " ")
                                        val_str = f"{value} (format lisible: {space_fmt})"
                                except Exception:
                                    pass

                            if is_unnamed:
                                # Si pas d'en-tête, on met juste la valeur
                                row_lines.append(f"{val_str}")
                            else:
                                row_lines.append(f"{header_str}: {val_str}")
                                
                    if row_lines:  # Seulement si la ligne a des données
                        lines.append(f"Row {row_idx + 1}:")
                        lines.extend([f"  - {line}" for line in row_lines])
                        lines.append("")
                
                text = "\n".join(lines)
                
                # Ne créer un chunk que s'il y a des données
                if len(lines) > 3:  # Plus que juste l'en-tête
                    metadata = {
                        "source": str(path),
                        "sheet": sheet_name,
                        "document_type": self.document_type,
                        "chunk_index": chunk_idx,
                        "start_row": start_row + 1,
                        "end_row": end_row,
                    }
                    yield DocumentChunk(
                        id=f"{path.stem}-{sheet_name}-chunk{chunk_idx}",
                        text=text,
                        metadata=metadata,
                    )

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
