"""Connecteur Excel multi-onglets."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ingestion.config import ConnectorConfig, ExcelConnectorOptions
from ingestion.connectors.base import BaseConnector, DocumentChunk


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
        for sheet_name in sheet_names:
            dataframe = excel_file.parse(sheet_name)
            dataframe = self._truncate(dataframe)
            if dataframe.empty:
                continue
            text = dataframe.to_csv(index=False)
            metadata = {
                "source": str(path),
                "sheet": sheet_name,
                "document_type": self.document_type,
            }
            yield DocumentChunk(
                id=f"{path.stem}-{sheet_name}",
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
