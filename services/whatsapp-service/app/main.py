import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, Request

from app.client import EvolutionAPIClient
from app.webhook import OutgoingMessageConsumer, parse_evolution_webhook
from shared.config import settings
from shared.rabbitmq import RabbitMQClient

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.whatsapp-service")

rabbitmq = RabbitMQClient()
evolution_client = EvolutionAPIClient()
outgoing_consumer = OutgoingMessageConsumer(rabbitmq, evolution_client)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await rabbitmq.connect()
    await outgoing_consumer.start()
    logger.info("WhatsApp Service iniciado")
    yield
    await evolution_client.close()
    await rabbitmq.close()


app = FastAPI(title="Netxia WhatsApp Service", version="1.0.0", lifespan=lifespan)


@app.post("/webhook/{tenant_id}")
async def receive_webhook(tenant_id: UUID, request: Request) -> dict[str, str]:
    payload = await request.json()
    event = parse_evolution_webhook(payload, tenant_id)
    if event is None:
        return {"status": "ignored"}
    await rabbitmq.publish(event)
    return {"status": "queued"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "whatsapp-service"}
