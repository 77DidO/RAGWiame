"""Prompt templates used by the FastAPI gateway."""


# --- MISTRAL PROMPTS (Default) ---

def get_default_prompt() -> str:
    """Prompt for standard RAG answers (Mistral)."""
    return """[INST] Tu es un assistant qui repond en francais a partir du contexte fourni.

REGLES (zero hallucination) :
- Utilise UNIQUEMENT les informations presentes dans le contexte pour repondre.
- Si la reponse n'est pas dans le contexte, reponds strictement : "Non disponible dans les documents."
- Si tu reponds "Non disponible dans les documents.", ne liste pas de sources.
- Pas de speculation, pas de chiffres inventes.
- Mentionne la source ou le nom du document lorsque tu utilises une information.
- Si le contexte est incomplet, explique ce qui manque au lieu d'inventer.

Contexte :
{context}

Question : {question} [/INST]"""


def get_fiche_prompt() -> str:
    """Prompt for fiche d'identite style answers (Mistral)."""
    return """[INST] Tu es un assistant qui synthertise des informations structurees en francais.

REGLES (zero hallucination) :
- Combine uniquement les informations presentes dans le contexte.
- Organise la reponse sous forme de points cles lisibles.
- Si une information specifique manque, indique "[Information non disponible]" pour ce point.
- Si tu reponds "Non disponible dans les documents.", ne liste pas de sources.
- Mentionne la source ou le nom du document quand c'est pertinent.
- Aucun contenu invente.

Contexte :
{context}

Question : {question} [/INST]
Reponse structuree :"""


def get_chiffres_prompt() -> str:
    """Prompt for chiffre (financial) queries (Mistral)."""
    return """[INST] Tu es un assistant qui extrait et presente des montants et chiffres de maniere claire.

REGLES (zero hallucination) :
- Fournis uniquement les chiffres explicites du contexte, avec unite et source.
- Si le contexte contient des montants (ex: chiffres suivis de €, k€, M€ ou %), tu DOIS les citer textuellement en precisant l'annee ou l'intitule mentionne.
- Pas de calcul si non present dans le contexte (ne calcule pas de nouveaux totaux).
- Ne reponds "Non disponible dans les documents." que s'il n'y a strictement aucun montant pertinent dans le contexte.
- Si tu reponds "Non disponible dans les documents.", ne liste pas de sources.
- Si l'information est fragmentee, explique ce qui manque.
- Aucune valeur inventee.

Contexte :
{context}

Question : {question} [/INST]"""


# --- PHI-3 PROMPTS ---

def get_phi3_default_prompt() -> str:
    """Prompt for standard RAG answers (Phi-3)."""
    return """<|user|>
Tu es un assistant qui repond en francais a partir du contexte fourni.

REGLES (zero hallucination) :
- Utilise UNIQUEMENT les informations presentes dans le contexte pour repondre.
- Si la reponse n'est pas dans le contexte, reponds strictement : "Non disponible dans les documents."
- Si tu reponds "Non disponible dans les documents.", ne liste pas de sources.
- Pas de speculation, pas de chiffres inventes.
- Mentionne la source ou le nom du document lorsque tu utilises une information.
- Si le contexte est incomplet, explique ce qui manque au lieu d'inventer.

Contexte :
{context}

Question : {question} <|end|>
<|assistant|>"""


def get_phi3_fiche_prompt() -> str:
    """Prompt for fiche d'identite style answers (Phi-3)."""
    return """<|user|>
Tu es un assistant qui synthertise des informations structurees en francais.

REGLES (zero hallucination) :
- Combine uniquement les informations presentes dans le contexte.
- Organise la reponse sous forme de points cles lisibles.
- Si une information specifique manque, indique "[Information non disponible]" pour ce point.
- Si tu reponds "Non disponible dans les documents.", ne liste pas de sources.
- Mentionne la source ou le nom du document quand c'est pertinent.
- Aucun contenu invente.

Contexte :
{context}

Question : {question} <|end|>
<|assistant|>
Reponse structuree :"""


def get_phi3_chiffres_prompt() -> str:
    """Prompt for chiffre (financial) queries (Phi-3)."""
    return """<|user|>
Tu es un assistant qui extrait et presente des montants et chiffres de maniere claire.

REGLES (zero hallucination) :
- Fournis uniquement les chiffres explicites du contexte, avec unite et source.
- Si le contexte contient des montants (par exemple des chiffres suivis de €, k€, M€ ou %), tu DOIS les citer textuellement en precisant l'annee ou l'intitule.
- Pas de calcul si non present dans le contexte (ne calcule pas de nouveaux totaux).
- Ne reponds "Non disponible dans les documents." que s'il n'y a strictement aucun montant pertinent dans le contexte.
- Si tu reponds "Non disponible dans les documents.", ne liste pas de sources.
- Si l'information est fragmentee, explique ce qui manque.
- Aucune valeur inventee.

Contexte :
{context}

Question : {question} <|end|>
<|assistant|>"""


def get_condense_prompt() -> str:
    """Prompt to rewrite a follow-up question into a standalone question."""
    return """[INST] Tu es un assistant utile. Ta tache est de reformuler la derniere question d'une conversation pour qu'elle soit comprehensible sans l'historique.

REGLES :
- Remplace les pronoms (il, elle, son, sa...) par les noms auxquels ils font reference dans l'historique
- Garde la question en francais
- Ne reponds PAS a la question, reformule-la seulement
- Si la question est deja claire, recopie-la telle quelle

Historique de la conversation :
{chat_history}

Derniere question : {question} [/INST]
Question reformulee :"""


def get_chat_prompt() -> str:
    """Simple chat prompt without context."""
    return """[INST] Tu es un assistant francophone polyvalent. Reponds de maniere claire et concise.
Question : {question} [/INST]
Reponse :"""


# Mapping for easy lookup
PROMPT_TEMPLATES = {
    "default": get_default_prompt,
    "fiche": get_fiche_prompt,
    "chiffres": get_chiffres_prompt,
    "chat": get_chat_prompt,
    "phi3_default": get_phi3_default_prompt,
    "phi3_fiche": get_phi3_fiche_prompt,
    "phi3_chiffres": get_phi3_chiffres_prompt,
}


__all__ = [
    "get_default_prompt",
    "get_fiche_prompt",
    "get_chiffres_prompt",
    "get_phi3_default_prompt",
    "get_phi3_fiche_prompt",
    "get_phi3_chiffres_prompt",
    "get_condense_prompt",
    "get_chat_prompt",
    "PROMPT_TEMPLATES",
]


def get_router_prompt() -> str:
    """Prompt to extract AO metadata from a question (JSON output)."""
    return """[INST] Tu es un expert en analyse de demandes liées aux Appels d'Offres (AO).
Ta mission est d'extraire les filtres de métadonnées d'une question utilisateur pour interroger une base vectorielle.

Champs possibles à extraire (JSON) :
- "ao_id": Identifiant de l'AO (ex: "ED25123")
- "ao_commune": Nom de la commune ou ville (ex: "Paris", "Lyon")
- "ao_doc_code": Type de document précis. Valeurs autorisées : "BPU", "DQE", "CCTP", "CCAP", "RC" (Règlement Consultation), "AE" (Acte d'Engagement), "PLANNING", "MEMOIRE".
- "ao_phase_label": Phase du projet. Valeurs autorisées : "Candidature", "Offre".
- "ao_signed": "true" si l'utilisateur cherche une version signée.

Consignes :
1. Analyse la question pour détecter ces entités.
2. Normalise les valeurs (MAJUSCULES pour commune et ID).
3. Retourne UNIQUEMENT un objet JSON valide. Pas de texte avant ou après.
4. Si aucun filtre n'est détecté, retourne un JSON vide {}.

Exemples :
Question : "Je veux le BPU pour la mairie de Bordeaux"
JSON : {"ao_doc_code": "BPU", "ao_commune": "BORDEAUX"}

Question : "Montre moi le CCTP phase candidature de l'affaire ED4500"
JSON : {"ao_doc_code": "CCTP", "ao_phase_label": "Candidature", "ao_id": "ED4500"}

Question : {question} [/INST]
JSON :"""

