"""
Definición canónica de eventos del bus (RabbitMQ).

Regla de oro: ningún servicio debe construir un dict "a mano" para publicar
un evento. Todo evento pasa por una de estas clases, se serializa con
`.model_dump_json()` y se publica en el exchange `netxia.events` con el
routing key igual al `event_type`.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    VOICE_INCOMING = "voice.incoming"
    VOICE_OUTGOING = "voice.outgoing"
    VOICE_HANGUP = "voice.hangup"
    WHATSAPP_INCOMING = "whatsapp.incoming"
    WHATSAPP_OUTGOING = "whatsapp.outgoing"
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ENDED = "conversation.ended"
    SPAM_DETECTED = "spam.detected"
    TRANSFER_REQUESTED = "transfer.requested"
    CRM_SYNC = "crm.sync"


class BaseEvent(BaseModel):
    """Envoltura común para todos los eventos publicados en RabbitMQ."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    tenant_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[UUID] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class VoiceEvent(BaseEvent):
    channel: str = "voice"
    caller_number: Optional[str] = None
    call_id: Optional[str] = None


class WhatsAppEvent(BaseEvent):
    channel: str = "whatsapp"
    from_number: Optional[str] = None
    instance_id: Optional[str] = None
    message_id: Optional[str] = None


class SpamEvent(BaseEvent):
    phone_number: str
    score: float
    action: str  # "blocked" | "flagged" | "allowed"


class TransferEvent(BaseEvent):
    conversation_id: UUID
    reason: str
    sentiment_score: Optional[float] = None
