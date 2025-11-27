import pytest
from llm_pipeline.prompts import get_default_prompt, get_fiche_prompt, get_chiffres_prompt, get_chat_prompt, PROMPT_TEMPLATES

def test_prompts_return_strings():
    assert isinstance(get_default_prompt(), str)
    assert isinstance(get_fiche_prompt(), str)
    assert isinstance(get_chiffres_prompt(), str)
    assert isinstance(get_chat_prompt(), str)

def test_prompts_content():
    default = get_default_prompt()
    assert "{context}" in default
    assert "{question}" in default
    
    fiche = get_fiche_prompt()
    assert "informations structurées" in fiche
    
    chiffres = get_chiffres_prompt()
    assert "chiffres" in chiffres

def test_prompt_templates_dict():
    assert "default" in PROMPT_TEMPLATES
    assert "fiche" in PROMPT_TEMPLATES
    assert "chiffres" in PROMPT_TEMPLATES
    assert "chat" in PROMPT_TEMPLATES
    assert PROMPT_TEMPLATES["default"] == get_default_prompt
