"""Module d'enrichissement des métadonnées pour l'ingestion."""
import re
from typing import Dict, List, Optional


class MetadataEnricher:
    """Enrichit les métadonnées des documents (classification, hints, entités)."""

    @staticmethod
    def infer_doc_hint(metadata: Dict) -> Optional[str]:
        """Déduit le type de document (hint) à partir du nom de fichier source."""
        source = str(metadata.get("source", "")).lower()
        if not source:
            return None

        def contains(*keywords: str) -> bool:
            return any(keyword in source for keyword in keywords)

        # Ordre de priorité pour la détection
        if contains("dqe", "bordereau", "bpu", "det", "detail"):
            return "dqe"
        if contains("devis", "facture", "prix"):
            return "devis"
        if source.endswith(".msg") or contains("courriel", "courrier", "email", "mail"):
            return "courriel"
        if contains("planning", "gantt", "calendrier"):
            return "planning"
        if contains("memoire", "mémoire", "presentation", "présentation"):
            return "memoire"
        if contains("contrat", "marche", "marché", "cctp", "ccap"):
            return "contrat"
        if source.endswith(".xlsx") or source.endswith(".xls"):
            return "tableur"
        if source.endswith(".pdf"):
            return "pdf"
        return None

    @staticmethod
    def extract_entities(text: str, metadata: Dict) -> Dict[str, any]:
        """Extrait les entités nommées du texte (projets, entreprises, montants, dates)."""
        entities = {}
        
        # 1. Extraire les montants (avec unités)
        amounts = []
        # Pattern pour montants: 123 456.78 EUR ou 123456,78 € ou 123 456 EUR
        amount_patterns = [
            r'(\d+(?:\s?\d{3})*(?:[.,]\d{2})?)\s*(?:EUR|€)',
            r'(\d+(?:\s?\d{3})*(?:[.,]\d{2})?)\s*(?:euros?)',
        ]
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Normaliser le format
                normalized = match.replace(' ', '').replace(',', '.')
                try:
                    value = float(normalized)
                    if value > 0:
                        amounts.append(value)
                except ValueError:
                    pass
        
        if amounts:
            entities["amounts"] = amounts
            entities["max_amount"] = max(amounts)
            entities["total_amount"] = sum(amounts) if len(amounts) <= 10 else None  # Éviter les sommes aberrantes
        
        # 2. Extraire les noms de projets (patterns courants)
        project_patterns = [
            r'(?:projet|chantier|opération|programme)\s+([A-ZÀ-Ü][a-zA-ZÀ-ü\s-]{3,30})',
            r'(?:site|lieu)\s+(?:de|du|à)\s+([A-ZÀ-Ü][a-zA-ZÀ-ü\s-]{3,30})',
        ]
        projects = []
        for pattern in project_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                project_name = match.strip()
                if len(project_name) > 3 and project_name not in projects:
                    projects.append(project_name)
        
        if projects:
            entities["projects"] = projects[:3]  # Limiter à 3 projets max
        
        # 3. Extraire les noms d'entreprises (patterns simples)
        company_patterns = [
            r'(?:entreprise|société|SARL|SAS|SA)\s+([A-ZÀ-Ü][a-zA-ZÀ-ü\s&-]{3,40})',
            r'([A-ZÀ-Ü][A-Z\s&-]{3,40})\s+(?:SARL|SAS|SA|EURL)',
        ]
        companies = []
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                company_name = match.strip()
                if len(company_name) > 3 and company_name not in companies:
                    companies.append(company_name)
        
        if companies:
            entities["companies"] = companies[:3]  # Limiter à 3 entreprises max
        
        # 4. Extraire les dates
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # 01/12/2024 ou 01-12-24
            r'\b(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})\b',
        ]
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        if dates:
            entities["dates"] = dates[:5]  # Limiter à 5 dates max
        
        # 5. Détecter le type de contenu basé sur les entités
        if amounts and len(amounts) > 5:
            entities["content_type"] = "financial"
        elif projects:
            entities["content_type"] = "project_description"
        elif companies:
            entities["content_type"] = "contractual"
        
        return entities

    @staticmethod
    def enrich_chunk_metadata(text: str, metadata: Dict) -> Dict:
        """Enrichit les métadonnées d'un chunk avec les entités extraites."""
        enriched = dict(metadata)
        
        # Ajouter le doc_hint si pas déjà présent
        if "doc_hint" not in enriched:
            doc_hint = MetadataEnricher.infer_doc_hint(metadata)
            if doc_hint:
                enriched["doc_hint"] = doc_hint
        
        # Extraire et ajouter les entités
        entities = MetadataEnricher.extract_entities(text, metadata)
        
        # Ajouter les entités pertinentes aux métadonnées
        if "projects" in entities:
            enriched["project_names"] = ", ".join(entities["projects"])
        
        if "companies" in entities:
            enriched["company_names"] = ", ".join(entities["companies"])
        
        if "max_amount" in entities:
            enriched["max_amount"] = entities["max_amount"]
        
        if "content_type" in entities:
            enriched["content_type_detected"] = entities["content_type"]
        
        return enriched


__all__ = ["MetadataEnricher"]
