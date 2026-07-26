"""
Sistema de prompts. Centraliza el system prompt base y la construcción del
prompt final combinando: identidad del bot, contexto del tenant, historial
reciente y resultados de RAG.

Todo texto de cara al cliente es en español de Chile.
"""
from typing import Optional

BASE_SYSTEM_PROMPT = """Eres el asistente conversacional de {tenant_name}, atendiendo por {channel}.
Responde siempre en español de Chile, de forma clara, breve y profesional.
Si no sabes algo, dilo honestamente y ofrece derivar a un humano.
Nunca inventes precios, políticas ni información que no esté en el contexto entregado.
Si detectas que el cliente está muy frustrado o pide explícitamente un humano, indica que
lo vas a derivar."""


def build_system_prompt(tenant_name: str, channel: str, extra_instructions: Optional[str] = None) -> str:
    prompt = BASE_SYSTEM_PROMPT.format(tenant_name=tenant_name, channel=channel)
    if extra_instructions:
        prompt += f"\n\nInstrucciones adicionales del tenant:\n{extra_instructions}"
    return prompt


def build_user_turn(
    user_message: str,
    rag_snippets: Optional[list[str]] = None,
) -> str:
    parts = []
    if rag_snippets:
        joined = "\n---\n".join(rag_snippets)
        parts.append(f"[Contexto relevante de la base de conocimiento]\n{joined}")
    parts.append(f"[Mensaje del cliente]\n{user_message}")
    return "\n\n".join(parts)


def build_messages(
    tenant_name: str,
    channel: str,
    history: list[dict[str, str]],
    user_message: str,
    rag_snippets: Optional[list[str]] = None,
    extra_instructions: Optional[str] = None,
) -> list[dict[str, str]]:
    """Construye la lista de mensajes en formato chat (compatible con Ollama /
    OpenAI-style APIs) lista para enviar al LLM router."""
    messages = [{"role": "system", "content": build_system_prompt(tenant_name, channel, extra_instructions)}]
    messages.extend(history)
    messages.append({"role": "user", "content": build_user_turn(user_message, rag_snippets)})
    return messages
