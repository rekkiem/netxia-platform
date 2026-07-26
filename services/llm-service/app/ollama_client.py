"""
Cliente HTTP delgado sobre la API de Ollama (/api/chat).
Aislado en su propio módulo para poder reemplazar Ollama por otro runtime
(vLLM, llama.cpp server, etc.) sin tocar el router.
"""
import logging

import httpx

from shared.config import settings

logger = logging.getLogger("netxia.llm-service.ollama")

REQUEST_TIMEOUT_SECONDS = 30.0


class OllamaClient:
    def __init__(self, base_url: str | None = None):
        self._base_url = (base_url or settings.ollama_host).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=REQUEST_TIMEOUT_SECONDS)

    async def close(self) -> None:
        await self._client.aclose()

    async def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        try:
            response = await self._client.post(
                "/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama respondió %s: %s", exc.response.status_code, exc.response.text)
            raise
        except (httpx.RequestError, KeyError) as exc:
            logger.error("Error de comunicación con Ollama: %s", exc)
            raise

    async def is_healthy(self) -> bool:
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False
