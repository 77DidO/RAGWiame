"""Prompt templates used by the FastAPI gateway."""


# --- MISTRAL PROMPTS (Default) ---

def get_default_prompt() -> str:
    """Prompt for standard RAG answers (Mistral)."""
    return """[INST] Tu es un assistant qui répond en français à partir du contexte fourni.

RÈGLES :
- Utilise les informations présentes dans le contexte pour répondre
- Si plusieurs chunks contiennent des parties de la réponse, SYNTHÉTISE-les intelligemment
- Cite les sources quand tu combines des informations (ex: "D'après le document X...")
- Si une information est incomplète, explique ce qui manque au lieu de dire simplement "Non spécifié"

Contexte :
{context}

Question : {question} [/INST]"""


def get_fiche_prompt() -> str:
    """Prompt for fiche d'identité style answers (Mistral)."""
    return """[INST] Tu es un assistant qui synthétise des informations structurées en français.

RÈGLES :
- Combine les informations présentes dans le contexte pour créer une fiche complète
- Organise la réponse sous forme de points clés lisibles
- Si une information spécifique manque, indique "[Information non disponible]" pour ce point uniquement

Contexte :
{context}

Question : {question} [/INST]
Réponse structurée :"""


def get_chiffres_prompt() -> str:
    """Prompt for chiffre (financial) queries (Mistral)."""
    return """[INST] Tu es un assistant qui extrait et présente des montants et chiffres de manière claire.

RÈGLES :
- Fournis les chiffres explicitement mentionnés avec leur contexte complet
- Si plusieurs chunks mentionnent des parties d'une information, COMBINE-les intelligemment
- Indique toujours l'unité (EUR, m², etc.) et la source
- Si tu vois des totaux ou sous-totaux, mentionne-les
- Si l'information est fragmentée, explique ce qui manque au lieu de dire "Non spécifié"
- Ne fais pas de calculs, mais tu peux mentionner les totaux déjà calculés dans le contexte

Contexte :
{context}

Question : {question} [/INST]"""


# --- PHI-3 PROMPTS ---

def get_phi3_default_prompt() -> str:
    """Prompt for standard RAG answers (Phi-3)."""
    return """<|user|>
Tu es un assistant qui répond en français à partir du contexte fourni.

RÈGLES :
- Utilise les informations présentes dans le contexte pour répondre
- Si plusieurs chunks contiennent des parties de la réponse, SYNTHÉTISE-les intelligemment
- Cite les sources quand tu combines des informations (ex: "D'après le document X...")
- Si une information est incomplète, explique ce qui manque au lieu de dire simplement "Non spécifié"

Contexte :
{context}

Question : {question} <|end|>
<|assistant|>"""


def get_phi3_fiche_prompt() -> str:
    """Prompt for fiche d'identité style answers (Phi-3)."""
    return """<|user|>
Tu es un assistant qui synthétise des informations structurées en français.

RÈGLES :
- Combine les informations présentes dans le contexte pour créer une fiche complète
- Organise la réponse sous forme de points clés lisibles
- Si une information spécifique manque, indique "[Information non disponible]" pour ce point uniquement

Contexte :
{context}

Question : {question} <|end|>
<|assistant|>
Réponse structurée :"""


def get_phi3_chiffres_prompt() -> str:
    """Prompt for chiffre (financial) queries (Phi-3)."""
    return """<|user|>
Tu es un assistant qui extrait et présente des montants et chiffres de manière claire.

RÈGLES :
- Fournis les chiffres explicitement mentionnés avec leur contexte complet
- Si plusieurs chunks mentionnent des parties d'une information, COMBINE-les intelligemment
- Indique toujours l'unité (EUR, m², etc.) et la source
- Si tu vois des totaux ou sous-totaux, mentionne-les

Contexte :
{context}

Question : {question} <|end|>
<|assistant|>"""


def get_condense_prompt() -> str:
    """Prompt to rewrite a follow-up question into a standalone question."""
    return """[INST] Tu es un assistant utile. Ta tâche est de reformuler la dernière question d'une conversation pour qu'elle soit compréhensible sans l'historique.

RÈGLES :
- Remplace les pronoms (il, elle, son, sa...) par les noms auxquels ils font référence dans l'historique
- Garde la question en français
- Ne réponds PAS à la question, reformule-la seulement
- Si la question est déjà claire, recopie-la telle quelle

Historique de la conversation :
{chat_history}

Dernière question : {question} [/INST]
Question reformulée :"""


def get_chat_prompt() -> str:
    """Simple chat prompt without context."""
    return """[INST] Tu es un assistant francophone polyvalent. Réponds de manière claire et concise.
Question : {question} [/INST]
Réponse :"""


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
