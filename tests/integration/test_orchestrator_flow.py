"""
Test de integración del ConversationOrchestrator completo, usando un
Redis in-memory (fakeredis) y un RabbitMQClient mockeado, para validar el
flujo de extremo a extremo de `_process_turn` sin depender de PostgreSQL
real (se mockea `session_scope` también, dado que la persistencia no es
el foco de este test).

Requiere: pip install fakeredis pytest-asyncio (ya declarados en
requirements-dev.txt).
"""
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from tests.conftest import use_service

with use_service("conversation-engine"):
    from app.orchestrator import ConversationOrchestrator

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakeRedisClient:
    """Doble de prueba mínimo que implementa la interfaz usada por
    ContextManager, respaldado por diccionarios en memoria."""

    def __init__(self):
        self._contexts: dict[str, dict] = {}
        self._history: dict[str, list] = {}

    def _key(self, tenant_id: str, user_id: str) -> str:
        return f"{tenant_id}:{user_id}"

    async def get_context(self, tenant_id: str, user_id: str) -> dict:
        return self._contexts.get(self._key(tenant_id, user_id), {})

    async def set_context(self, tenant_id: str, user_id: str, context: dict) -> None:
        self._contexts[self._key(tenant_id, user_id)] = context

    async def append_history(self, tenant_id: str, user_id: str, role: str, content: str) -> None:
        key = self._key(tenant_id, user_id)
        self._history.setdefault(key, []).append({"role": role, "content": content})

    async def get_history(self, tenant_id: str, user_id: str) -> list:
        return self._history.get(self._key(tenant_id, user_id), [])

    async def clear_conversation(self, tenant_id: str, user_id: str) -> None:
        key = self._key(tenant_id, user_id)
        self._contexts.pop(key, None)
        self._history.pop(key, None)


@pytest.fixture
def orchestrator():
    # Reestablece el contexto del servicio en cada test: si la suite
    # completa corre junto a tests de otros microservicios, estos pueden
    # haber cambiado sys.path/sys.modules (ver tests/conftest.py). Sin
    # esto, un `patch("app.orchestrator....")` por string podría fallar.
    with use_service("conversation-engine"):
        rabbitmq_mock = AsyncMock()
        redis_client = FakeRedisClient()
        orch = ConversationOrchestrator(rabbitmq_mock, redis_client)
        yield orch, rabbitmq_mock


@pytest.mark.asyncio
class TestProcessTurn:
    async def test_normal_message_calls_llm_and_records_history(self, orchestrator):
        orch, rabbitmq_mock = orchestrator

        with patch.object(orch, "_retrieve_rag_snippets", return_value=[]), patch.object(
            orch, "_call_llm", return_value="Claro, te ayudo con eso."
        ), patch.object(orch, "_persist_conversation_start", return_value=None), patch.object(
            orch, "_persist_messages", return_value=None
        ):
            response = await orch._process_turn(TENANT_ID, "56911112222", "whatsapp", "Hola, tengo una duda")

        assert response == "Claro, te ayudo con eso."
        rabbitmq_mock.publish.assert_not_called()  # no debería escalar en un mensaje normal

    async def test_escalation_request_publishes_transfer_event_and_skips_llm(self, orchestrator):
        orch, rabbitmq_mock = orchestrator

        with patch.object(orch, "_call_llm") as mock_llm, patch.object(
            orch, "_persist_conversation_start", return_value=None
        ):
            response = await orch._process_turn(
                TENANT_ID, "56911112222", "whatsapp", "quiero hablar con un humano"
            )

        mock_llm.assert_not_called()
        rabbitmq_mock.publish.assert_called_once()
        assert "derivar" in response.lower()

    async def test_rag_failure_degrades_gracefully(self, orchestrator):
        orch, _rabbitmq_mock = orchestrator

        class _FakeSessionScope:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, *exc_info):
                return False

        with patch("app.orchestrator.session_scope", return_value=_FakeSessionScope()), patch(
            "app.rag.retrieve_relevant_snippets", side_effect=RuntimeError("DB caída")
        ), patch.object(orch, "_call_llm", return_value="Respuesta sin contexto RAG"), patch.object(
            orch, "_persist_conversation_start", return_value=None
        ), patch.object(orch, "_persist_messages", return_value=None):
            response = await orch._process_turn(TENANT_ID, "56911112222", "whatsapp", "consulta cualquiera")

        assert response == "Respuesta sin contexto RAG"
