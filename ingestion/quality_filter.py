"""Module de filtrage de qualité pour l'ingestion."""

class QualityFilter:
    """Filtre les chunks de faible qualité."""

    @staticmethod
    def is_low_quality_chunk(text: str) -> bool:
        """Détecte si un chunk est de faible qualité (trop de chiffres, pas assez de lettres)."""
        if not text.strip():
            return True
        
        # Textes trop courts (moins de 50 caractères)
        if len(text.strip()) < 50:
            return True
        
        # Compter les chiffres et les lettres
        digits = sum(c.isdigit() for c in text)
        letters = sum(c.isalpha() for c in text)
        total = len(text)
        
        if total == 0:
            return True
            
        # Si plus de 40% de chiffres, c'est probablement un tableau de données brutes
        if digits / total > 0.4:
            return True
            
        # Si moins de 20% de lettres, c'est suspect (code, bruit, séparateurs)
        if letters / total < 0.2:
            return True
            
        return False
