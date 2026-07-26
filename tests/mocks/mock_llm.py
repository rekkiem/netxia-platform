"""
Mock de OllamaClient / llm-service, para pruebas unitarias que no deben
depender de tener Ollama corriendo con modelos descargados.
"""
from typing import Optional


class MockOllamaClient:
    """Reemplazo drop-in de app.ollama_client.OllamaClient."""

    def __init__(self, fixed_response: str = "Esta es una respuesta simulada.", should_fail: bool = False):
        self.fixed_response = fixed_response
        self.should_fail = should_fail
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    async def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        self.calls.append((model, messages))
        if self.should_fail:
            raise RuntimeError("Fallo simulado de Ollama")
        return self.fixed_response

    async def is_healthy(self) -> bool:
        return not self.should_fail

    async def close(self) -> None:
        pass


class MockLLMServiceHTTP:
    """Mock del endpoint HTTP /v1/generate de llm-service, para pruebas del
    conversation-engine que usan httpx.AsyncClient real contra un transport
    simulado (ver tests/integration para el uso con httpx.MockTransport)."""

    def __init__(self, response_text: str = "Respuesta simulada del LLM router"):
        self.response_text = response_text
        self.last_payload: Optional[dict] = None

    def handle(self, request) -> dict:
        import json

        self.last_payload = json.loads(request.content)
        return {"text": self.response_text, "model_used": "mock-model"}
