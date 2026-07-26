import pytest

from tests.conftest import use_service
from tests.mocks.mock_llm import MockOllamaClient

with use_service("llm-service"):
    from app.router import FALLBACK_CHAIN, ModelRouter


class TestModelRouterResolveModelName:
    def test_fast_category_resolves_correctly(self):
        router = ModelRouter(MockOllamaClient())
        assert router.resolve_model_name("fast") is not None

    def test_unknown_category_falls_back_to_default(self):
        router = ModelRouter(MockOllamaClient())
        default_model = router.resolve_model_name("default")
        assert router.resolve_model_name("categoria_inexistente") == default_model


class TestModelRouterGenerate:
    @pytest.mark.asyncio
    async def test_successful_generation_returns_text(self):
        mock_client = MockOllamaClient(fixed_response="Hola, ¿en qué puedo ayudarte?")
        router = ModelRouter(mock_client)

        result = await router.generate("default", [{"role": "user", "content": "hola"}])

        assert result == "Hola, ¿en qué puedo ayudarte?"
        assert len(mock_client.calls) == 1

    @pytest.mark.asyncio
    async def test_failure_raises_after_exhausting_fallback_chain(self):
        mock_client = MockOllamaClient(should_fail=True)
        router = ModelRouter(mock_client)

        with pytest.raises(RuntimeError):
            await router.generate("reasoning", [{"role": "user", "content": "hola"}])

        # Debe haber intentado el modelo principal + toda la cadena de fallback
        assert len(mock_client.calls) == 1 + len(FALLBACK_CHAIN)
