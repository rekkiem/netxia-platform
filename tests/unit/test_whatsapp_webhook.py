from uuid import UUID

from tests.conftest import use_service
from tests.mocks.mock_whatsapp import (
    build_connection_update_payload,
    build_incoming_text_payload,
    build_non_text_payload,
    build_own_echo_payload,
)

with use_service("whatsapp-service"):
    from app.webhook import parse_evolution_webhook

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


class TestParseEvolutionWebhook:
    def test_parses_incoming_text_message(self):
        payload = build_incoming_text_payload(from_number="56912345678", text="Hola, necesito ayuda")
        event = parse_evolution_webhook(payload, TENANT_ID)

        assert event is not None
        assert event.from_number == "56912345678"
        assert event.payload["text"] == "Hola, necesito ayuda"
        assert event.instance_id == "demo"

    def test_ignores_own_echo(self):
        payload = build_own_echo_payload()
        event = parse_evolution_webhook(payload, TENANT_ID)
        assert event is None

    def test_ignores_non_text_messages(self):
        payload = build_non_text_payload()
        event = parse_evolution_webhook(payload, TENANT_ID)
        assert event is None

    def test_ignores_non_message_events(self):
        payload = build_connection_update_payload()
        event = parse_evolution_webhook(payload, TENANT_ID)
        assert event is None

    def test_extended_text_message_format(self):
        payload = build_incoming_text_payload()
        payload["data"]["message"] = {"extendedTextMessage": {"text": "Mensaje citado/respondido"}}
        event = parse_evolution_webhook(payload, TENANT_ID)
        assert event is not None
        assert event.payload["text"] == "Mensaje citado/respondido"
