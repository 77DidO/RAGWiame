"""
title: File Analyzer Pipeline
author: WIAME RAG Team
date: 2024-12-08
version: 1.0
license: MIT
description: Analyse de fichiers Excel/CSV en Markdown pour LLM (mode non-RAG)
requirements: pandas, openpyxl, tabulate
"""

import pandas as pd
from typing import Optional
import os

class Pipeline:
    def __init__(self):
        self.name = "File Analyzer"
        
    def pipe(self, body: dict) -> dict:
        """
        Pipeline qui convertit les fichiers Excel/CSV en tableaux Markdown
        pour permettre au LLM de les analyser directement (sans RAG).
        
        Args:
            body: Dict contenant messages, files, etc.
            
        Returns:
            body modifié avec le contenu du fichier injecté
        """
        files = body.get("files", [])
        messages = body.get("messages", [])
        
        if not files or not messages:
            return body
        
        enhanced_content = messages[-1].get("content", "")
        
        for file in files:
            file_type = file.get("type", "")
            file_path = file.get("path", "")
            file_name = file.get("name", "fichier")
            
            # Traiter Excel/CSV uniquement
            if any(ext in file_type for ext in ["spreadsheet", "csv", "excel"]):
                try:
                    # Lire le fichier
                    if "csv" in file_type:
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)
                    
                    # Obtenir les stats du fichier
                    num_rows, num_cols = df.shape
                    
                    # Limiter les lignes pour éviter token explosion
                    max_rows = 100
                    if num_rows > max_rows:
                        df_preview = df.head(max_rows)
                        truncation_note = f"\n\n⚠️ **Fichier tronqué** : {num_rows} lignes au total, seules les {max_rows} premières sont affichées.\n"
                    else:
                        df_preview = df
                        truncation_note = ""
                    
                    # Convertir en Markdown
                    markdown_table = df_preview.to_markdown(index=False)
                    
                    # Calculer des statistiques de base
                    stats = []
                    for col in df.select_dtypes(include=['float64', 'int64']).columns:
                        stats.append(f"- **{col}** : min={df[col].min()}, max={df[col].max()}, moyenne={df[col].mean():.2f}")
                    
                    stats_section = ""
                    if stats:
                        stats_section = f"\n\n**Statistiques des colonnes numériques :**\n" + "\n".join(stats)
                    
                    # Injecter avant la question utilisateur
                    enhanced_content = f"""📊 **Fichier uploadé : {file_name}**

**Structure** : {num_rows} lignes × {num_cols} colonnes

**Aperçu des données :**

{markdown_table}{truncation_note}{stats_section}

---

**Question de l'utilisateur :**

{enhanced_content}
"""
                except Exception as e:
                    enhanced_content += f"\n\n❌ **Erreur lors de la lecture du fichier** : {str(e)}"
            
            # Autres types de fichiers (PDF, DOCX, etc.)  - À implémenter si besoin
            # elif "pdf" in file_type:
            #     # Extraction PDF
            #     pass
        
        # Mettre à jour le message
        messages[-1]["content"] = enhanced_content
        body["messages"] = messages
        
        return body
