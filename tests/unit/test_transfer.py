from tests.conftest import use_service

with use_service("conversation-engine"):
    from app.models.context import ConversationContext
    from app.transfer import should_escalate


def make_context(**overrides) -> "ConversationContext":
    defaults = dict(tenant_id="00000000-0000-0000-0000-000000000001", user_id="56912345678", channel="whatsapp")
    defaults.update(overrides)
    return ConversationContext(**defaults)


class TestShouldEscalate:
    def test_explicit_request_escalates(self):
        context = make_context()
        must_escalate, reason = should_escalate(context, "quiero hablar con un humano")
        assert must_escalate is True
        assert reason == "solicitud_explicita_del_cliente"

    def test_very_negative_sentiment_escalates(self):
        context = make_context(sentiment_score=-0.8)
        must_escalate, reason = should_escalate(context, "consulta normal")
        assert must_escalate is True
        assert reason == "sentimiento_muy_negativo"

    def test_stalled_conversation_escalates(self):
        context = make_context(turn_count=9, collected_slots={})
        must_escalate, reason = should_escalate(context, "sigo sin entender")
        assert must_escalate is True
        assert reason == "conversacion_estancada"

    def test_normal_conversation_does_not_escalate(self):
        context = make_context(turn_count=1, sentiment_score=0.2)
        must_escalate, _ = should_escalate(context, "hola, quiero cotizar un servicio")
        assert must_escalate is False

    def test_stalled_but_with_collected_slots_does_not_escalate(self):
        # si ya se recolectó información, no se considera "estancada"
        context = make_context(turn_count=9, collected_slots={"producto": "plan_basico"})
        must_escalate, _ = should_escalate(context, "una consulta más")
        assert must_escalate is False
