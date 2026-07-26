"""
Decide y ejecuta la derivación de una conversación a un agente humano.
Publica un evento `transfer.requested` que el servicio de notificaciones
(notification-service) consume para avisar por Telegram/email al equipo.
"""
import logging
from uuid import UUID

from app.models.context import ConversationContext
from app.sentiment import wants_human_escalation
from shared.events import EventType, TransferEvent
from shared.rabbitmq import RabbitMQClient

logger = logging.getLogger("netxia.conversation-engine.transfer")

SENTIMENT_ESCALATION_THRESHOLD = -0.5
MAX_TURNS_WITHOUT_RESOLUTION = 8


def should_escalate(context: ConversationContext, user_message: str) -> tuple[bool, str]:
    """Retorna (debe_escalar, motivo)."""
    if wants_human_escalation(user_message):
        return True, "solicitud_explicita_del_cliente"
    if context.sentiment_score <= SENTIMENT_ESCALATION_THRESHOLD:
        return True, "sentimiento_muy_negativo"
    if context.turn_count >= MAX_TURNS_WITHOUT_RESOLUTION and not context.collected_slots:
        return True, "conversacion_estancada"
    return False, ""


async def escalate_to_human(
    rabbitmq: RabbitMQClient,
    context: ConversationContext,
    reason: str,
) -> None:
    if not context.conversation_id:
        logger.warning("Intento de escalar sin conversation_id, se omite el evento")
        return
    event = TransferEvent(
        event_type=EventType.TRANSFER_REQUESTED,
        tenant_id=UUID(context.tenant_id),
        conversation_id=UUID(context.conversation_id),
        reason=reason,
        sentiment_score=context.sentiment_score,
        payload={"user_id": context.user_id, "channel": context.channel},
    )
    await rabbitmq.publish(event)
    context.escalation_flag = True
    logger.info("Conversación %s escalada a humano. Motivo: %s", context.conversation_id, reason)
