"""
Punto de entrada del Conversation Engine.

Expone un healthcheck HTTP (para Traefik/Docker) y, en segundo plano,
arranca los consumidores de RabbitMQ que procesan eventos de voz y
WhatsApp de forma continua.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.orchestrator import ConversationOrchestrator
from shared.config import settings
from shared.rabbitmq import RabbitMQClient
from shared.redis_client import RedisClient

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.conversation-engine")

rabbitmq = RabbitMQClient()
redis_client = RedisClient()
orchestrator = ConversationOrchestrator(rabbitmq, redis_client)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await redis_client.connect()
    await rabbitmq.connect()
    await orchestrator.start()
    logger.info("Conversation Engine iniciado correctamente")
    yield
    await orchestrator.shutdown()
    await rabbitmq.close()
    await redis_client.close()
    logger.info("Conversation Engine detenido")


app = FastAPI(title="Netxia Conversation Engine", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "conversation-engine"}
