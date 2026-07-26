"""
Maneja dos direcciones del flujo de WhatsApp:

1. Entrante: recibe el webhook HTTP de Evolution API cuando llega un
   mensaje, lo traduce a un `WhatsAppEvent` y lo publica en RabbitMQ
   (routing key `whatsapp.incoming`) para que lo consuma el
   conversation-engine.

2. Saliente: se suscribe a `whatsapp.outgoing` (publicado por el
   conversation-engine con la respuesta ya generada) y usa
   EvolutionAPIClient para efectivamente enviar el mensaje de vuelta.
"""
import logging
from typing import Any
from uuid import UUID

from app.client import EvolutionAPIClient
from shared.events import EventType, WhatsAppEvent
from shared.rabbitmq import RabbitMQClient

logger = logging.getLogger("netxia.whatsapp-service.webhook")


def parse_evolution_webhook(payload: dict[str, Any], tenant_id: UUID) -> WhatsAppEvent | None:
    """Extrae los campos relevantes del payload crudo de Evolution API.
    Evolution API envía eventos de distinto tipo (`messages.upsert`,
    `connection.update`, etc.); solo nos interesan mensajes de texto
    entrantes de un contacto (no mensajes propios, no grupos)."""
    if payload.get("event") != "messages.upsert":
        return None

    data = payload.get("data", {})
    message = data.get("message", {})
    key = data.get("key", {})

    if key.get("fromMe"):
        return None  # eco de nuestros propios mensajes salientes

    text = message.get("conversation") or message.get("extendedTextMessage", {}).get("text")
    if not text:
        return None  # audio, imagen, etc. — fuera de alcance del MVP

    from_number = key.get("remoteJid", "").split("@")[0]
    instance_id = payload.get("instance")

    return WhatsAppEvent(
        event_type=EventType.WHATSAPP_INCOMING,
        tenant_id=tenant_id,
        from_number=from_number,
        instance_id=instance_id,
        message_id=key.get("id"),
        payload={"text": text},
    )


class OutgoingMessageConsumer:
    def __init__(self, rabbitmq: RabbitMQClient, evolution_client: EvolutionAPIClient):
        self.rabbitmq = rabbitmq
        self.evolution_client = evolution_client

    async def start(self) -> None:
        await self.rabbitmq.subscribe(
            queue_name="whatsapp-service.outgoing",
            routing_keys=[EventType.WHATSAPP_OUTGOING.value],
            event_cls=WhatsAppEvent,
            handler=self._handle_outgoing,
        )

    async def _handle_outgoing(self, event: WhatsAppEvent) -> None:
        text = event.payload.get("text")
        to_number = event.payload.get("to") or event.from_number
        if not text or not to_number or not event.instance_id:
            logger.warning("Evento saliente incompleto, se descarta: %s", event.event_id)
            return
        sent = await self.evolution_client.send_text_message(event.instance_id, to_number, text)
        if not sent:
            logger.error("No se pudo entregar el mensaje a %s (instancia %s)", to_number, event.instance_id)
