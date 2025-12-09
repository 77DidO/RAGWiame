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
        
        self.db_sessions = {}
        self.user_context = {}  # Store schema info per chat_id

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
        cid = body.get("chat_id", "default")
        # print(f"[Excel Filter] Inlet. ChatID: {cid}")
        
        messages = body.get("messages", [])
        if not messages:
            return body
            
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
                        df = pd.read_csv(file_path)
                        schema_text = self._generate_sheet_preview(df, "CSV", filename)
                        
                        if self.valves.ENABLE_SQL_GENERATION:
                            if cid not in self.db_sessions:
                                self.db_sessions[cid] = sqlite3.connect(':memory:', check_same_thread=False)
                            conn = self.db_sessions[cid]
                            
                            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', filename.split('.')[0])
                            table_name = f"csv_{safe_name}"
                            df.to_sql(table_name, conn, index=False, if_exists='replace')
                            tables_info = f"- Fichier CSV -> Table SQL: `{table_name}`"

                    else:
                        xls = pd.ExcelFile(file_path)
                        schema_parts = []
                        table_names_list = []
                        
                        for sheet_name in xls.sheet_names:
                            df_preview = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=20)
                            preview = self._generate_sheet_preview(df_preview, sheet_name, filename)
                            schema_parts.append(preview)
                            
                            if self.valves.ENABLE_SQL_GENERATION:
                                if cid not in self.db_sessions:
                                    self.db_sessions[cid] = sqlite3.connect(':memory:', check_same_thread=False)
                                conn = self.db_sessions[cid]
                                
                                safe_name = re.sub(r'[^a-zA-Z0-9]', '_', sheet_name)
                                table_name = f"sheet_{safe_name}"
                                
                                df_full = pd.read_excel(xls, sheet_name=sheet_name)
                                df_full.to_sql(table_name, conn, index=False, if_exists='replace')
                                table_names_list.append(f"- Feuille '{sheet_name}' -> Table SQL: `{table_name}`")

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
        # We do this for EVERY message if we have context for this user
        if cid in self.user_context:
            ctx = self.user_context[cid]
            system_prompt_content = f"""
Voici un apercu des fichiers deja analyses (20 lignes max par feuille).

STRUCTURE DES DONNEES DISPONIBLES :
{ctx['tables_info']}

APERCU BRUT :
{ctx['schema_text']}

INSTRUCTIONS :
- Reponds directement aux questions en t'appuyant sur les tableaux ci-dessus (ne dis pas que tu ne peux pas analyser le fichier).
- Si l'utilisateur demande une liste complete, un total ou un calcul exhaustif, genere uniquement un bloc de code SQL valide (pas de texte autour).
- Utilise les noms de tables indiques plus haut.

Exemple de reponse en mode SQL uniquement :
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
        cid = body.get("chat_id", "default")
        print(f"[Excel Filter] Outlet called. SelfID: {id(self)}, ChatID: {cid}")
        # print(f"[Excel Filter] Active Sessions: {list(self.db_sessions.keys())}")
        
        messages = body.get("messages", [])
        if not messages:
            return body
            
        last_message = messages[-1]
        content = last_message.get("content", "")
        
        # Robust Regex: optional sql tag, allow any case, capture content inside backticks
        # Matches: ```sql SELECT ... ``` OR ``` SELECT ... ```
        sql_match = re.search(r"```(?:sql)?\s*(SELECT.*?)```", content, re.DOTALL | re.IGNORECASE)

        if sql_match:
            sql_query = sql_match.group(1).strip()
            print(f"[Excel Filter] DETECTED SQL: {sql_query}")
            
            # Helper to find session
            conn = None
            if cid in self.db_sessions:
                conn = self.db_sessions[cid]
            elif "default" in self.db_sessions:
                messages[-1]["content"] += "

⚠️ Session introuvable pour executer le SQL. Rechargez la page ou re-uploadez le fichier dans ce chat."
                body["messages"] = messages
        else:
            # print("[Excel Filter] NO SQL DETECTED in response.")
            pass

        return body

    def _generate_sheet_preview(self, df: pd.DataFrame, sheet_name: str, filename: str) -> str:
        """Generate a raw markdown preview of the sheet."""
        df_display = df.fillna("")
        markdown_table = df_display.to_markdown(index=False)
        preview = f"""
## 📄 Fichier: {filename} | Feuille: {sheet_name}
**Aperçu (20 premières lignes brutes)** :
{markdown_table}
"""
        return preview
