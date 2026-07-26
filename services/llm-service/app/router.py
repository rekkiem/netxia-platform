"""
Router de modelos. Traduce la "categoría" pedida por el conversation-engine
(fast/default/reasoning) al modelo Ollama concreto, según la tabla de
estrategia definida en el diseño:

    Saludo inicial / preguntas simples -> Gemma 2B   (fast)
    Consultas de productos / soporte    -> Llama 3.2 3B (default)
    Problemas complejos / derivación     -> Mistral 7B  (reasoning)

Incluye fallback en cascada: si el modelo elegido falla (por RAM,
timeout, modelo no descargado), se reintenta con el siguiente modelo más
liviano en vez de fallar toda la conversación.
"""
import logging

from app.ollama_client import OllamaClient
from shared.config import settings

logger = logging.getLogger("netxia.llm-service.router")

MODEL_BY_CATEGORY = {
    "fast": settings.fast_llm_model,
    "default": settings.default_llm_model,
    "reasoning": settings.reasoning_llm_model,
}

# Orden de fallback: si el modelo "ideal" falla, probamos estos en orden.
FALLBACK_CHAIN = [settings.default_llm_model, settings.fast_llm_model]


class ModelRouter:
    def __init__(self, ollama_client: OllamaClient):
        self._ollama = ollama_client

    def resolve_model_name(self, model_choice: str) -> str:
        return MODEL_BY_CATEGORY.get(model_choice, settings.default_llm_model)

    async def generate(self, model_choice: str, messages: list[dict[str, str]]) -> str:
        primary_model = self.resolve_model_name(model_choice)
        candidates = [primary_model] + [m for m in FALLBACK_CHAIN if m != primary_model]

        last_error: Exception | None = None
        for model in candidates:
            try:
                return await self._ollama.chat(model, messages)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Modelo %s falló, probando siguiente en la cadena de fallback", model)
                continue

        logger.error("Todos los modelos fallaron para la solicitud")
        raise RuntimeError("No fue posible generar una respuesta con ningún modelo disponible") from last_error
