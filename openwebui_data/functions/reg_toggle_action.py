from openwebui.functions import action

@action(label="Toggle RAG", icon="search")
def toggle_rag(message, context):
    # Alterne le champ use_rag dans metadata
    metadata = message.get("metadata", {})
    metadata["use_rag"] = not metadata.get("use_rag", True)
    message["metadata"] = metadata
    return message