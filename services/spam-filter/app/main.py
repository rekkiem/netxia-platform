import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI
from pydantic import BaseModel

from app.scorer import register_call_attempt, score_call
from shared.config import settings
from shared.events import EventType, SpamEvent
from shared.rabbitmq import RabbitMQClient
from shared.redis_client import RedisClient

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.spam-filter")

redis_client = RedisClient()
rabbitmq = RabbitMQClient()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await redis_client.connect()
    await rabbitmq.connect()
    logger.info("Spam Filter Service iniciado")
    yield
    await rabbitmq.close()
    await redis_client.close()


app = FastAPI(title="Netxia Spam Filter", version="1.0.0", lifespan=lifespan)


class ScoreRequest(BaseModel):
    tenant_id: UUID
    phone_number: str
    has_caller_id: bool = True


class ScoreResponse(BaseModel):
    score: float
    action: str


@app.post("/v1/score", response_model=ScoreResponse)
async def score(request: ScoreRequest) -> ScoreResponse:
    recent_count = await register_call_attempt(redis_client, request.phone_number)
    score_value, action = await score_call(
        redis_client,
        str(request.tenant_id),
        request.phone_number,
        request.has_caller_id,
        recent_count,
    )
    if action in ("blocked", "flagged"):
        event = SpamEvent(
            event_type=EventType.SPAM_DETECTED,
            tenant_id=request.tenant_id,
            phone_number=request.phone_number,
            score=score_value,
            action=action,
        )
        await rabbitmq.publish(event)
    return ScoreResponse(score=score_value, action=action)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "spam-filter"}
