import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.telegram import TelegramNotifier
from shared.config import settings
from shared.events import BaseEvent, EventType, SpamEvent, TransferEvent
from shared.rabbitmq import RabbitMQClient

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.notification")

rabbitmq = RabbitMQClient()
telegram = TelegramNotifier()


async def _handle_transfer(event: TransferEvent) -> None:
    text = (
        f"*Derivación solicitada*\n"
        f"Conversación: `{event.conversation_id}`\n"
        f"Motivo: {event.reason}\n"
        f"Canal: {event.payload.get('channel', 'desconocido')}"
    )
    await telegram.send(text)


async def _handle_spam(event: SpamEvent) -> None:
    if event.action != "blocked":
        return
    text = f"*Spam bloqueado*\nNúmero: `{event.phone_number}`\nScore: {event.score}"
    await telegram.send(text)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await rabbitmq.connect()
    await rabbitmq.subscribe(
        queue_name="notification.transfer",
        routing_keys=[EventType.TRANSFER_REQUESTED.value],
        event_cls=TransferEvent,
        handler=_handle_transfer,
    )
    await rabbitmq.subscribe(
        queue_name="notification.spam",
        routing_keys=[EventType.SPAM_DETECTED.value],
        event_cls=SpamEvent,
        handler=_handle_spam,
    )
    logger.info("Notification Service iniciado")
    yield
    await telegram.close()
    await rabbitmq.close()


app = FastAPI(title="Netxia Notification Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "notification"}
