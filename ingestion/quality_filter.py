"""Module de filtrage de qualité pour l'ingestion."""

class QualityFilter:
    """Filtre les chunks de faible qualité."""

    @staticmethod
    def is_low_quality_chunk(text: str, metadata: dict = None) -> bool:
        """Détecte si un chunk est de faible qualité (trop de chiffres, pas assez de lettres).
        
        Args:
            text: Le texte du chunk
            metadata: Métadonnées optionnelles pour adapter le filtrage
        """
        if not text.strip():
            return True
        
        # Textes trop courts (moins de 30 caractères) - seuil réduit de 50 à 30
        if len(text.strip()) < 30:
            return True
        
        # Exception pour les documents financiers/techniques
        if metadata:
            doc_hint = metadata.get("doc_hint", "")
            doc_type = metadata.get("document_type", "")
            source = str(metadata.get("source", "")).lower()
            
            # Ne pas filtrer les chunks de documents financiers/techniques
            is_financial = (
                doc_hint in ["dqe", "tableur", "bordereau", "devis", "facture"] or
                doc_type == "excel" or
                any(keyword in source for keyword in ["dqe", "bordereau", "prix", "devis", "facture", ".xlsx", ".xls"])
            )
            
            if is_financial:
                # Pour les documents financiers, seulement filtrer si vraiment vide
                return len(text.strip()) < 20
        
        # Compter les chiffres et les lettres
        digits = sum(c.isdigit() for c in text)
        letters = sum(c.isalpha() for c in text)
        total = len(text)
        
        if total == 0:
            return True
        
        # Seuils assouplis pour les documents généraux
        # Si plus de 60% de chiffres (au lieu de 40%), c'est probablement du bruit
        if digits / total > 0.6:
            return True
        
        # Si moins de 10% de lettres (au lieu de 20%), c'est suspect
        if letters / total < 0.1:
            return True
        
        return False
