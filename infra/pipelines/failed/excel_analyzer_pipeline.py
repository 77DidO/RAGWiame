"""
title: Excel/CSV Analyzer Filter
author: RAGWiame Team
date: 2025-12-09
version: 2.3
license: MIT
description: Automatic filter that detects Excel/CSV files, previews data for LLM, and enables SQL execution for complex queries.
requirements: pandas, openpyxl, tabulate
"""

import pandas as pd
import sqlite3
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = []
        priority: int = 0
        MAX_ROWS_PREVIEW: int = 20
        ENABLE_SQL_GENERATION: bool = True

    def __init__(self):
        self.type = "filter"
        self.name = "Excel/CSV Analyzer Filter"

        self.valves = self.Valves(
            **{
                "pipelines": ["*"],  # Connect to all models
            }
        )

        self.db_sessions: Dict[str, sqlite3.Connection] = {}
        self.user_context: Dict[str, Dict[str, str]] = {}

    async def on_startup(self):
        print(f"[Excel Filter] Starting up...")

    async def on_shutdown(self):
        for conn in self.db_sessions.values():
            conn.close()
        print(f"[Excel Filter] Shut down, cleaned sessions")

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        Automatically detects Excel/CSV files and injects context.
        Also re-injects context for follow-up questions.
        """
        cid = body.get("chat_id") or body.get("metadata", {}).get("chat_id") or "default"

        messages = body.get("messages", [])
        if not messages:
            return body

        preview_limit = self.valves.MAX_ROWS_PREVIEW

        # 1. HANDLE NEW FILES
        files = body.get("files", [])
        if files:
            for file_obj in files:
                filename = file_obj.get("name", file_obj.get("filename", ""))
                file_path = file_obj.get("path", file_obj.get("file", {}).get("path"))

                if not filename.endswith(('.xlsx', '.xls', '.csv')):
                    continue

                print(f"[Excel Filter] Processing new file: {filename}")

                try:
                    tables_info = ""
                    schema_text = ""

                    if filename.endswith('.csv'):
                        df_raw = pd.read_csv(file_path, header=None)
                        header_row = self._detect_header_row(df_raw)
                        df_full = pd.read_csv(file_path, header=header_row)
                        df_full = self._cleanup_df(df_full)
                        columns_sql = self._normalize_columns(df_full)
                        total_rows = len(df_full)
                        df_preview = df_full.head(preview_limit)
                        schema_text = self._generate_sheet_preview(df_preview, "CSV", filename, columns_sql, total_rows, preview_limit)

                        if self.valves.ENABLE_SQL_GENERATION:
                            if cid not in self.db_sessions:
                                self.db_sessions[cid] = sqlite3.connect(':memory:', check_same_thread=False)
                            conn = self.db_sessions[cid]

                            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', filename.split('.')[0])
                            table_name = f"csv_{safe_name}"
                            df_full.to_sql(table_name, conn, index=False, if_exists='replace')
                            tables_info = f"- Fichier CSV -> Table SQL: `{table_name}` ({total_rows} lignes totales, apercu {preview_limit}) | Colonnes SQL: {', '.join(columns_sql)}"

                    else:
                        xls = pd.ExcelFile(file_path)
                        schema_parts: List[str] = []
                        table_names_list: List[str] = []

                        for sheet_name in xls.sheet_names:
                            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                            header_row = self._detect_header_row(df_raw)
                            df_full = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)
                            df_full = self._cleanup_df(df_full)
                            columns_sql = self._normalize_columns(df_full)
                            total_rows = len(df_full)
                            df_preview = df_full.head(preview_limit)
                            preview = self._generate_sheet_preview(df_preview, sheet_name, filename, columns_sql, total_rows, preview_limit)
                            schema_parts.append(preview)

                            if self.valves.ENABLE_SQL_GENERATION:
                                if cid not in self.db_sessions:
                                    self.db_sessions[cid] = sqlite3.connect(':memory:', check_same_thread=False)
                                conn = self.db_sessions[cid]

                                safe_name = re.sub(r'[^a-zA-Z0-9]', '_', sheet_name)
                                table_name = f"sheet_{safe_name}"

                                df_full.to_sql(table_name, conn, index=False, if_exists='replace')
                                table_names_list.append(
                                    f"- Feuille '{sheet_name}' -> Table SQL: `{table_name}` ({total_rows} lignes totales, apercu {preview_limit}) | Colonnes SQL: {', '.join(columns_sql)}"
                                )

                        schema_text = "\n\n".join(schema_parts)
                        tables_info = "\n".join(table_names_list)

                    # SAVE CONTEXT FOR SESSION
                    self.user_context[cid] = {
                        "tables_info": tables_info,
                        "schema_text": schema_text
                    }
                    print(f"[Excel Filter] Context saved for {cid}")

                except Exception as e:
                    print(f"[Excel Filter] Error processing {filename}: {e}")
                    import traceback
                    traceback.print_exc()

        # 2. INJECT CONTEXT (IF AVAILABLE)
        if cid in self.user_context:
            ctx = self.user_context[cid]
            system_prompt_content = f"""
Voici un apercu des fichiers deja analyses (20 lignes max par feuille).

STRUCTURE DES DONNEES DISPONIBLES :
{ctx['tables_info']}

APERCU BRUT :
{ctx['schema_text']}

INSTRUCTIONS :
- Utilise strictement les noms de colonnes SQL fournis (pas d'espaces, pas d'accents). Si besoin, entoure-les de backticks.
- Toujours indiquer la table cible dans le FROM (ex. `sheet_Feuil1` ou `sheet_Feuil2`).
- Si le nombre total de lignes d'une table est <= {preview_limit}, reponds directement en utilisant ces tableaux.
- Si une table a plus de {preview_limit} lignes OU que la question demande une liste complete / un total / un comptage global (ex. "liste", "tous les", "total", "combien"), genere un bloc SQL complet (un seul bloc, pas de texte autour) en utilisant les noms de tables indiques plus haut.
- Ne genere pas de SQL vide ou incoherent : la requete doit toujours contenir SELECT ... FROM ... et utiliser des colonnes existantes.

Exemple de reponse SQL uniquement (si besoin de tout le fichier) :
```sql
SELECT * FROM sheet_NomDeLaTable;
```
Je vais intercepter ce code, l'executer sur toutes les lignes, puis te renvoyer le resultat.
"""
            system_msg = {"role": "system", "content": system_prompt_content}

            system_idx = next((i for i, msg in enumerate(messages) if msg.get("role") == "system"), -1)

            if system_idx >= 0:
                if "STRUCTURE DES DONNEES DISPONIBLES" not in messages[system_idx]["content"]:
                    messages[system_idx]["content"] += f"\n\n{system_prompt_content}"
            else:
                messages.insert(0, system_msg)

        body["messages"] = messages
        return body

    async def pipe(self, body: dict, user: dict = None) -> dict:
        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Intercepts the LLM response to execute SQL if present."""
        cid = body.get("chat_id") or body.get("metadata", {}).get("chat_id") or "default"
        print(f"[Excel Filter] Outlet called. SelfID: {id(self)}, ChatID: {cid}")

        messages = body.get("messages", [])
        if not messages:
            return body

        last_message = messages[-1]
        content = last_message.get("content", "")

        # Robust Regex: optional sql tag, allow any case, capture content inside backticks
        sql_match = re.search(r"```(?:sql)?\s*(SELECT.*?)```", content, re.DOTALL | re.IGNORECASE)

        if sql_match:
            sql_query = sql_match.group(1).strip()
            print(f"[Excel Filter] DETECTED SQL: {sql_query}")

            # Basic validation: must contain SELECT and FROM
            if not re.search(r\"\\bselect\\b\", sql_query, re.IGNORECASE) or not re.search(r\"\\bfrom\\b\", sql_query, re.IGNORECASE):
                messages[-1]["content"] += "\n\n⚠️ Requete SQL invalide (SELECT/FROM manquants). Reformule en incluant SELECT ... FROM table."
                body["messages"] = messages
                return body

            # Reuse session for this chat, or fall back to default if available
            conn = self.db_sessions.get(cid) or self.db_sessions.get("default")
            if conn is None:
                messages[-1]["content"] += "\n\n⚠️ Session introuvable pour executer le SQL. Rechargez la page ou re-uploadez le fichier dans ce chat."
                body["messages"] = messages
            else:
                try:
                    df_res = pd.read_sql_query(sql_query, conn)
                    preview = df_res.head(200)
                    md = preview.to_markdown(index=False)
                    messages[-1]["content"] += f"\n\nSQL execute :\n```sql\n{sql_query}\n```\n\nResultat SQL (premieres lignes):\n\n{md}"
                    if len(df_res) > len(preview):
                        messages[-1]["content"] += f"\n\n(Tronque a {len(preview)} lignes sur {len(df_res)})"
                    body["messages"] = messages
                except Exception as e:
                    messages[-1]["content"] += f"\n\n⚠️ Erreur SQL: {e}"
                    body["messages"] = messages

        return body

    def _generate_sheet_preview(
        self,
        df: pd.DataFrame,
        sheet_name: str,
        filename: str,
        columns_sql: List[str],
        total_rows: int,
        preview_limit: int,
    ) -> str:
        """Generate a raw markdown preview of the sheet with columns info."""
        df_display = df.fillna("")
        markdown_table = df_display.to_markdown(index=False)
        cols = ", ".join(columns_sql)
        preview = f"""
## Fichier: {filename} | Feuille: {sheet_name}
**Colonnes SQL:** {cols}
**Apercu ({min(preview_limit, total_rows)} premieres lignes / {total_rows} lignes totales)** :
{markdown_table}
"""
        return preview

    def _detect_header_row(self, df_raw: pd.DataFrame) -> int:
        """Try to detect header row by looking for common keywords."""
        keywords = ["POSTES", "DESIGNATION", "PRIX", "QUANTITE", "TOTAL", "UNITAIRE", "U"]
        best_row = 0
        best_score = 0
        for idx, row in df_raw.iterrows():
            score = 0
            for cell in row:
                cell_str = str(cell).upper()
                if any(kw in cell_str for kw in keywords):
                    score += 1
            if score > best_score:
                best_score = score
                best_row = idx
        return best_row

    def _normalize_columns(self, df: pd.DataFrame) -> List[str]:
        """Normalize column names to SQL-friendly format."""
        normalized = []
        for i, col in enumerate(df.columns):
            col_str = str(col).strip()
            if not col_str or col_str.lower().startswith("unnamed"):
                name = f"col_{i}"
            else:
                name = re.sub(r'[^a-zA-Z0-9]+', '_', col_str).strip('_').lower()
                if not name:
                    name = f"col_{i}"
            normalized.append(name)
        df.columns = normalized
        return normalized

    def _cleanup_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove fully empty rows/cols."""
        df = df.dropna(axis=0, how="all")
        df = df.dropna(axis=1, how="all")
        return df
